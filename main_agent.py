"""
AI YouTube Agent
Alur kerja: riset topik + naskah (Gemini) -> suara + waktu tiap kata (Edge-TTS)
-> gambar visual (Pollinations) -> render video (Remotion) -> unggah ke YouTube.

Cara pakai (contoh):
    python main_agent.py                      # jalan penuh sampai unggah
    python main_agent.py --tanpa-upload       # berhenti setelah video jadi (untuk uji coba)
    python main_agent.py --topik "cara kerja lift gedung"
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.parse
from io import BytesIO

import requests
from PIL import Image, ImageDraw

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv bersifat opsional
    load_dotenv = None

# Supaya tulisan di terminal Windows tidak error
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ========================================================
# 1. KONFIGURASI
# ========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REMOTION_DIR = os.path.join(BASE_DIR, "video_engine")
PUBLIC_DIR = os.path.join(REMOTION_DIR, "public")
OUT_DIR = os.path.join(REMOTION_DIR, "out")
HISTORY_PATH = os.path.join(BASE_DIR, "riwayat_topik.json")

if load_dotenv:
    load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
# Kalau model pertama tidak tersedia, agen otomatis mencoba yang berikutnya
GEMINI_MODELS = [
    m for m in [
        os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        "gemini-3.6-flash",
        "gemini-flash-latest",
    ] if m
]

VOICE = os.getenv("VOICE", "id-ID-ArdiNeural")  # suara cowok; cewek: id-ID-GadisNeural
VOICE_RATE = os.getenv("VOICE_RATE", "+15%")
PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")  # private / unlisted / public
FPS = 30
IMG_W, IMG_H = 1080, 1920
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Pollinations versi gratis hanya mengizinkan 1 gambar tiap 45 detik per koneksi internet
POLLINATIONS_GAP_SECONDS = 46


def info(msg):
    print(msg, flush=True)


# ========================================================
# 2. RISET DAN NASKAH (GEMINI)
# ========================================================
def load_history():
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(title):
    history = load_history()
    history.append(title)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, ensure_ascii=False, indent=2)


def extract_json(text):
    """Ambil JSON dari jawaban Gemini walaupun ada tambahan teks atau tanda kutip kode."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Jawaban Gemini tidak berisi JSON.")
    return json.loads(text[start:end + 1])


def build_prompt(forced_topic, done_titles):
    if forced_topic:
        topic_rule = f"Topik wajib: {forced_topic}."
    else:
        topic_rule = (
            "Pilih satu topik secara acak dari tiga kelompok ini:\n"
            "    1. Cara kerja benda atau infrastruktur sehari-hari (contoh: cara kerja lift gedung, "
            "konstruksi MRT bawah tanah, mekanisme rice cooker).\n"
            "    2. Fakta sains dan teknik di balik benda atau fenomena fisik (contoh: ilmu di balik "
            "dinding batu bata, kenapa gergaji medis tidak melukai kulit).\n"
            "    3. Cerita sejarah dan kisah nyata yang unik (contoh: kisah bertahan hidup, budaya unik)."
        )
    avoid = ""
    if done_titles:
        avoid = "Jangan ulangi topik yang sudah pernah dibuat: " + "; ".join(done_titles[-30:]) + "."

    return f"""
Kamu adalah scriptwriter YouTube Shorts edukasi berbahasa Indonesia, gaya Kok Bisa / Veritasium.
{topic_rule}
{avoid}

Tulis naskah narasi yang seru, cepat, dan santai ala kreator konten modern, sekitar 80-100 kata
(durasi sekitar 35-40 detik). Mulai dengan kalimat pembuka yang bikin penasaran.
Naskah hanya berisi kalimat yang diucapkan: tanpa instruksi panggung, tanpa emoji, tanpa tanda bintang,
tanpa hashtag, dan jangan pakai singkatan yang sulit dibaca.

Buat tepat 3 prompt gambar (dalam bahasa Inggris) untuk 3 scene berurutan. Gaya visual: infografis dan
animasi digital, misalnya isometric 3D cutaway, diagram alur, mind map, atau skema transparan.
Setiap prompt harus menggambarkan bagian cerita yang sesuai urutan naskah.
Semua gambar tidak boleh mengandung tulisan, huruf, atau logo.

Keluarkan HANYA JSON murni dengan format persis ini:
{{
  "title": "Judul menarik maksimal 60 karakter",
  "description": "Deskripsi singkat 2-3 kalimat. #Shorts #Sains #Teknologi",
  "tags": ["sains", "teknologi", "carakerja", "shorts", "edukasi"],
  "full_script": "Seluruh teks narasi dari awal sampai akhir.",
  "prompts": ["prompt scene 1", "prompt scene 2", "prompt scene 3"]
}}
"""


def research_and_write(forced_topic=None):
    info("\n[1/5] Agen AI sedang meriset topik dan menulis naskah...")
    if not GEMINI_KEY or GEMINI_KEY == "ISI_KEY_DI_SINI":
        raise RuntimeError(
            "API key Gemini belum diisi. Buat file .env di folder proyek, lalu isi baris:\n"
            "GEMINI_API_KEY=kunci_anda   (lihat file .env.example)"
        )

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_KEY)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0)
    prompt = build_prompt(forced_topic, load_history())

    last_error = None
    for model_name in GEMINI_MODELS:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt, config=config)
                data = extract_json(response.text)
                validate_content(data)
                info(f"  -> Naskah dibuat dengan model {model_name}")
                return data
            except Exception as e:
                last_error = e
                message = str(e)
                # model tidak ditemukan -> langsung coba model lain
                if "404" in message or "NOT_FOUND" in message:
                    info(f"  -> Model {model_name} tidak tersedia, mencoba model lain...")
                    break
                info(f"  -> Percobaan {attempt}/3 dengan {model_name} gagal: {message[:150]}")
                time.sleep(5 * attempt)
    raise RuntimeError(f"Gemini gagal membuat naskah: {last_error}")


def validate_content(data):
    for key in ("title", "description", "tags", "full_script", "prompts"):
        if key not in data:
            raise ValueError(f"JSON dari Gemini kekurangan kolom '{key}'.")
    if not isinstance(data["prompts"], list) or not data["prompts"]:
        raise ValueError("Kolom 'prompts' kosong.")
    if not isinstance(data["tags"], list):
        data["tags"] = [str(data["tags"])]
    data["full_script"] = re.sub(r"[*#_`]", "", str(data["full_script"])).strip()
    if len(data["full_script"].split()) < 20:
        raise ValueError("Naskah terlalu pendek.")
    data["title"] = str(data["title"]).strip()[:80]


# ========================================================
# 3. SUARA + WAKTU TIAP KATA (EDGE-TTS)
# ========================================================
def estimate_words(text, duration):
    """Cadangan: kalau waktu kata tidak diterima, bagi rata sepanjang durasi suara."""
    tokens = text.split()
    if not tokens:
        return []
    step = duration / len(tokens)
    return [
        {"word": w, "start": round(i * step, 2), "end": round((i + 1) * step, 2)}
        for i, w in enumerate(tokens)
    ]


async def generate_voice_and_timestamps(text, output_audio_path):
    import edge_tts

    info("[2/5] Membuat suara AI dan sinkronisasi kata demi kata...")
    last_error = None
    for attempt in range(1, 4):
        try:
            # boundary="WordBoundary" wajib: tanpa ini edge-tts hanya memberi waktu per kalimat
            communicate = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE, boundary="WordBoundary")
            words = []
            with open(output_audio_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start = chunk["offset"] / 10_000_000
                        length = chunk["duration"] / 10_000_000
                        words.append({
                            "word": chunk["text"],
                            "start": round(start, 2),
                            "end": round(start + length, 2),
                        })
            if os.path.getsize(output_audio_path) < 1000:
                raise RuntimeError("File suara kosong.")
            break
        except Exception as e:
            last_error = e
            info(f"  -> Percobaan suara {attempt}/3 gagal: {e}")
            await asyncio.sleep(3 * attempt)
    else:
        raise RuntimeError(f"Gagal membuat suara: {last_error}")

    # Edge-TTS menghasilkan MP3 48 kbps (6000 byte per detik) -> perkiraan durasi
    audio_seconds = os.path.getsize(output_audio_path) / 6000
    if not words:
        info("  -> Waktu kata tidak diterima, memakai perkiraan waktu rata.")
        words = estimate_words(text, audio_seconds)

    total_duration = max(words[-1]["end"], 1.0) + 1.0
    return words, round(total_duration, 2)


# ========================================================
# 4. GAMBAR VISUAL (POLLINATIONS)
# ========================================================
def fit_to_vertical(img):
    """Potong dan ubah ukuran gambar supaya pas 1080x1920 tanpa gepeng."""
    img = img.convert("RGB")
    target_ratio = IMG_W / IMG_H
    w, h = img.size
    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return img.resize((IMG_W, IMG_H), Image.LANCZOS)


def make_placeholder(path, index):
    """Gambar cadangan bergaya skema teknis, dipakai kalau gambar AI gagal dibuat."""
    palettes = [((11, 15, 25), (20, 90, 120)), ((20, 12, 40), (110, 50, 140)), ((10, 25, 20), (30, 120, 90))]
    top, bottom = palettes[index % len(palettes)]
    img = Image.new("RGB", (IMG_W, IMG_H))
    draw = ImageDraw.Draw(img)
    for y in range(IMG_H):
        t = y / IMG_H
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (IMG_W, y)], fill=color)
    # garis kotak tipis ala kertas gambar teknik
    overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for x in range(0, IMG_W, 90):
        odraw.line([(x, 0), (x, IMG_H)], fill=(255, 255, 255, 25), width=2)
    for y in range(0, IMG_H, 90):
        odraw.line([(0, y), (IMG_W, y)], fill=(255, 255, 255, 25), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img.save(path, "JPEG", quality=90)


def download_image(prompt, seed, dest_path):
    encoded = urllib.parse.quote(prompt + ", technical infographic, clean render, no text, no watermark")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={IMG_W}&height={IMG_H}&nologo=true&seed={seed}"
    )
    for attempt in range(1, 5):
        wait = POLLINATIONS_GAP_SECONDS + 4
        try:
            res = requests.get(url, timeout=180)
            content_type = res.headers.get("content-type", "")
            if res.status_code == 200 and content_type.startswith("image"):
                img = Image.open(BytesIO(res.content))
                img.load()  # memastikan gambar benar-benar bisa dibaca
                fit_to_vertical(img).save(dest_path, "JPEG", quality=92)
                return True
            # Batas gratis tercapai (kode 402) -> ikuti waktu tunggu yang diminta server
            match = re.search(r"[Rr]etry after (\d+)s", res.text or "")
            if match:
                wait = int(match.group(1)) + 3
            info(f"  -> Server gambar menolak (kode {res.status_code}), menunggu {wait} detik...")
        except Exception as e:
            info(f"  -> Gambar gagal diunduh ({str(e)[:100]}), percobaan {attempt}/4...")
        time.sleep(wait)
    return False


def generate_images(prompts):
    info("[3/5] Membuat gambar visual (sekitar 45 detik per gambar karena batas versi gratis)...")
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # Hapus gambar lama supaya tidak terpakai lagi tanpa sengaja
    for name in os.listdir(PUBLIC_DIR):
        if re.fullmatch(r"scene_\d+\.(png|jpg)", name):
            os.remove(os.path.join(PUBLIC_DIR, name))

    image_names = []
    last_download = 0.0
    for idx, prompt in enumerate(prompts):
        filename = f"scene_{idx}.jpg"
        filepath = os.path.join(PUBLIC_DIR, filename)

        gap = POLLINATIONS_GAP_SECONDS - (time.time() - last_download)
        if last_download and gap > 0:
            info(f"  -> Menunggu {int(gap)} detik sebelum gambar berikutnya...")
            time.sleep(gap)

        info(f"  -> Gambar {idx + 1}/{len(prompts)}")
        ok = download_image(prompt, 12 + idx, filepath)
        last_download = time.time()
        if not ok:
            info(f"  -> Gambar {idx + 1} gagal, memakai gambar cadangan.")
            make_placeholder(filepath, idx)
        image_names.append(filename)
    return image_names


# ========================================================
# 5. RENDER DENGAN REMOTION
# ========================================================
def run_command(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def render_remotion_video(words, images, duration):
    info("[4/5] Menjalankan Remotion (membuat video dengan teks kinetik)...")
    npm = shutil.which("npm")
    npx = shutil.which("npx")
    if not npm or not npx:
        raise RuntimeError("Node.js belum terpasang. Unduh dari https://nodejs.org lalu jalankan ulang.")

    # Pasang paket Remotion otomatis kalau belum ada
    if not os.path.isdir(os.path.join(REMOTION_DIR, "node_modules")):
        info("  -> Pertama kali: memasang paket Remotion (butuh beberapa menit)...")
        run_command([npm, "install", "--no-audit", "--no-fund"], REMOTION_DIR)

    os.makedirs(OUT_DIR, exist_ok=True)
    output_mp4 = os.path.join(OUT_DIR, "shorts_final.mp4")
    if os.path.exists(output_mp4):
        os.remove(output_mp4)

    props_path = os.path.join(REMOTION_DIR, "render_props.json")
    props = {
        "audioUrl": "voice.mp3",
        "images": [os.path.basename(i) for i in images],
        "words": words,
        "durationInSeconds": duration,
    }
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    cmd = [npx, "remotion", "render", "src/index.ts", "ShortsComp", output_mp4, "--props=render_props.json"]
    run_command(cmd, REMOTION_DIR)

    if not os.path.exists(output_mp4) or os.path.getsize(output_mp4) < 10_000:
        raise RuntimeError("Video hasil render tidak ditemukan atau rusak.")
    return output_mp4


# ========================================================
# 6. UNGGAH OTOMATIS KE YOUTUBE
# ========================================================
def get_yt_service():
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = os.path.join(BASE_DIR, "token.json")
    client_secret = os.path.join(BASE_DIR, "client_secret.json")

    if not os.path.exists(client_secret):
        raise FileNotFoundError(f"File client_secret.json belum ada di folder {BASE_DIR}")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            info("  -> Izin lama sudah kedaluwarsa, login ulang diperlukan.")
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(token_path, "w", encoding="utf-8") as token:
        token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload_video(video_path, content_data, privacy):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    info(f"[5/5] Mengunggah Shorts ke YouTube (status: {privacy})...")
    youtube = get_yt_service()

    title = content_data["title"]
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"
    description = content_data["description"]
    if "#shorts" not in description.lower():
        description += "\n\n#Shorts"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": [str(t) for t in content_data["tags"]][:15],
            "categoryId": "28",  # Sains & Teknologi
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                info(f"  -> Terunggah {int(status.progress() * 100)}%")
    except HttpError as e:
        raise RuntimeError(f"YouTube menolak unggahan: {e}") from e

    info("\n=======================================================")
    info(f" SUKSES! Video: https://youtu.be/{response['id']}")
    info("=======================================================\n")


# ========================================================
# EKSEKUTOR UTAMA
# ========================================================
def main():
    parser = argparse.ArgumentParser(description="AI YouTube Agent")
    parser.add_argument("--tanpa-upload", action="store_true", help="Buat video saja, jangan diunggah")
    parser.add_argument("--topik", default=None, help="Tentukan topik sendiri (kalau kosong, dipilih acak)")
    parser.add_argument(
        "--privasi", default=PRIVACY, choices=["private", "unlisted", "public"],
        help="Status video di YouTube (bawaan: private)",
    )
    args = parser.parse_args()

    try:
        data = research_and_write(args.topik)
        info(f"  -> Topik dipilih: {data['title']}")

        os.makedirs(PUBLIC_DIR, exist_ok=True)
        audio_dest = os.path.join(PUBLIC_DIR, "voice.mp3")
        words, duration = asyncio.run(generate_voice_and_timestamps(data["full_script"], audio_dest))
        info(f"  -> Durasi video: {duration} detik, {len(words)} kata")

        images = generate_images(data["prompts"])
        final_video = render_remotion_video(words, images, duration)
        info(f"  -> Video selesai: {final_video}")

        if args.tanpa_upload:
            info("Unggah dilewati (--tanpa-upload). Video bisa dicek dulu di folder video_engine/out.")
        else:
            upload_video(final_video, data, args.privasi)
        save_history(data["title"])

    except Exception as e:
        traceback.print_exc()
        info(f"\n[ERROR] Terjadi kendala: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
