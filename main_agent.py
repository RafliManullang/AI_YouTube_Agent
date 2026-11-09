"""
AI YouTube Agent
Alur kerja: riset topik + naskah per adegan (Gemini) -> suara + waktu tiap kata (Edge-TTS)
-> video latar gratis (Pexels, opsional) -> render video beranimasi (Remotion) -> unggah ke YouTube.

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

import requests

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
PEXELS_KEY = os.getenv("PEXELS_API_KEY") or ""  # opsional: video latar gratis dari Pexels
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY") or ""  # opsional: video latar gratis dari Pixabay
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
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SCENE_TYPES = ("flow", "mindmap", "counter")


def info(msg):
    print(msg, flush=True)


# ========================================================
# 2. RISET DAN NASKAH PER ADEGAN (GEMINI)
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

Pecah video menjadi 5 sampai 6 ADEGAN berurutan. Setiap adegan punya narasi yang diucapkan dan
visual infografis beranimasi. Total seluruh narasi sekitar 80-100 kata (durasi 35-40 detik).
Gaya narasi: seru, cepat, santai ala kreator konten modern. Adegan pertama harus kalimat pembuka yang
bikin penasaran, adegan terakhir penutup singkat. Narasi hanya berisi kalimat yang diucapkan:
tanpa instruksi panggung, tanpa emoji, tanpa tanda bintang, tanpa hashtag.

Aturan visual tiap adegan (field "type"):
- "flow"    : alur langkah berurutan. "points" berisi 3 sampai 4 langkah.
- "mindmap" : peta pikiran dengan judul di tengah. "points" berisi 3 sampai 5 cabang.
- "counter" : angka besar yang menghitung naik. Wajib isi "number" (angka saja) dan "unit"
              (satuannya). "points" berisi 2 sampai 3 label pendek. Pakai HANYA kalau ada angka
              yang benar-benar faktual, jangan mengarang angka.
Pakai campuran tipe, minimal ada satu "flow" dan satu "mindmap".
"title" maksimal 4 kata. Setiap isi "points" maksimal 4 kata, tanpa emoji dan tanpa tanda baca.
"footage_query" berisi 2 sampai 3 kata bahasa Inggris untuk mencari video latar gratis yang umum dan
mudah ditemukan (contoh: "elevator building", "rice cooking", "underground tunnel").

Keluarkan HANYA JSON murni dengan format persis ini:
{{
  "title": "Judul menarik maksimal 60 karakter",
  "description": "Deskripsi singkat 2-3 kalimat. #Shorts #Sains #Teknologi",
  "tags": ["sains", "teknologi", "carakerja", "shorts", "edukasi"],
  "scenes": [
    {{
      "narration": "Kalimat yang diucapkan pada adegan ini.",
      "title": "Judul adegan",
      "type": "flow",
      "points": ["langkah satu", "langkah dua", "langkah tiga"],
      "number": null,
      "unit": null,
      "footage_query": "elevator building"
    }}
  ]
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


def clean_text(value, limit):
    text = re.sub(r"[*#_`]", "", str(value or "")).strip()
    return text[:limit]


def validate_content(data):
    for key in ("title", "description", "tags", "scenes"):
        if key not in data:
            raise ValueError(f"JSON dari Gemini kekurangan kolom '{key}'.")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) < 3:
        raise ValueError("Jumlah adegan terlalu sedikit.")
    if not isinstance(data["tags"], list):
        data["tags"] = [str(data["tags"])]

    scenes = []
    for raw in data["scenes"][:7]:
        narration = clean_text(raw.get("narration"), 400)
        if len(narration.split()) < 4:
            continue
        scene_type = raw.get("type") if raw.get("type") in SCENE_TYPES else "flow"
        points = [clean_text(p, 40) for p in (raw.get("points") or []) if str(p).strip()]
        number = raw.get("number")
        try:
            number = float(number) if number is not None else None
        except (TypeError, ValueError):
            number = None
        if number is not None and number == int(number):
            number = int(number)

        # Perbaiki kombinasi yang tidak lengkap supaya tampilan tidak kosong
        if scene_type == "counter" and number is None:
            scene_type = "flow"
        if not points:
            points = [clean_text(raw.get("title"), 40) or "Intinya"]
        if scene_type == "flow" and len(points) < 2:
            scene_type = "mindmap"

        scenes.append({
            "narration": narration,
            "title": clean_text(raw.get("title"), 40) or "Tahukah kamu",
            "type": scene_type,
            "points": points[:5],
            "number": number,
            "unit": clean_text(raw.get("unit"), 40) or None,
            "footage_query": clean_text(raw.get("footage_query"), 60),
        })

    if len(scenes) < 3:
        raise ValueError("Adegan yang valid terlalu sedikit.")

    data["scenes"] = scenes
    data["full_script"] = " ".join(s["narration"] for s in scenes)
    if len(data["full_script"].split()) < 20:
        raise ValueError("Naskah terlalu pendek.")
    data["title"] = clean_text(data["title"], 80)


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


def assign_scene_times(scenes, words, duration):
    """Tentukan kapan tiap adegan mulai dan selesai, berdasarkan jumlah kata narasinya."""
    counts = [max(1, len(s["narration"].split())) for s in scenes]
    total_count = sum(counts)
    cumulative = 0
    for i, scene in enumerate(scenes):
        if i == 0:
            scene["start"] = 0.0
        else:
            idx = min(len(words) - 1, round(cumulative / total_count * len(words)))
            scene["start"] = float(words[idx]["start"])
        cumulative += counts[i]

    # Pastikan urutan waktu masuk akal dan tiap adegan minimal 1,5 detik
    for i in range(1, len(scenes)):
        scenes[i]["start"] = max(scenes[i]["start"], scenes[i - 1]["start"] + 1.5)
    for i in range(len(scenes) - 1, 0, -1):
        scenes[i]["start"] = min(scenes[i]["start"], duration - 1.5 * (len(scenes) - i))
    for i, scene in enumerate(scenes):
        scene["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else float(duration)
        scene["start"] = round(scene["start"], 2)
        scene["end"] = round(scene["end"], 2)


# ========================================================
# 4. VIDEO LATAR GRATIS (PEXELS, OPSIONAL)
# ========================================================
def pick_pexels_file(videos, min_seconds):
    """Pilih satu file video vertikal dengan ukuran sedang dari hasil pencarian Pexels."""
    for video in videos:
        if video.get("duration", 0) < min_seconds:
            continue
        candidates = [
            f for f in video.get("video_files", [])
            if f.get("file_type") == "video/mp4"
            and (f.get("width") or 0) >= 540
            and (f.get("height") or 0) >= (f.get("width") or 0)
        ]
        if candidates:
            # ambil yang paling kecil tapi masih cukup tajam supaya cepat diunduh dan dirender
            candidates.sort(key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))
            return candidates[0].get("link")
    return None


def pick_pixabay_file(hits, min_seconds):
    """Pilih satu video dari hasil pencarian Pixabay (ukuran sedang cukup karena latarnya digelapkan)."""
    for hit in hits:
        if hit.get("duration", 0) < min_seconds:
            continue
        files = hit.get("videos") or {}
        for size in ("medium", "small"):
            clip = files.get(size) or {}
            if clip.get("url") and clip.get("size", 0) > 0:
                return clip["url"]
    return None


def find_clip_link(query, min_seconds):
    """Cari video latar: Pexels dulu kalau ada key-nya, lalu Pixabay. Hasil: (link, nama sumber)."""
    if PEXELS_KEY:
        try:
            res = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 8},
                timeout=30,
            )
            res.raise_for_status()
            link = pick_pexels_file(res.json().get("videos", []), min_seconds)
            if link:
                return link, "Pexels"
        except Exception as e:
            info(f"  -> Pexels gagal ({str(e)[:80]}), mencoba sumber lain...")
    if PIXABAY_KEY:
        try:
            res = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": PIXABAY_KEY, "q": query[:100], "per_page": 10, "safesearch": "true"},
                timeout=30,
            )
            res.raise_for_status()
            link = pick_pixabay_file(res.json().get("hits", []), min_seconds)
            if link:
                return link, "Pixabay"
        except Exception as e:
            info(f"  -> Pixabay gagal ({str(e)[:80]}).")
    return None, None


def fetch_stock_videos(scenes):
    """Unduh video latar tiap adegan. Hasilnya: daftar nama sumber yang dipakai (untuk kredit)."""
    info("[3/5] Menyiapkan visual latar...")
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # Hapus klip dan gambar lama supaya tidak terpakai lagi tanpa sengaja
    for name in os.listdir(PUBLIC_DIR):
        if re.fullmatch(r"scene_\d+\.(png|jpg|mp4)", name):
            os.remove(os.path.join(PUBLIC_DIR, name))

    credits = set()
    if not PEXELS_KEY and not PIXABAY_KEY:
        info("  -> Key video latar belum diisi: memakai latar animasi bawaan (tetap bergerak dan berwarna).")
        return credits

    for i, scene in enumerate(scenes):
        query = scene.get("footage_query")
        if not query:
            continue
        try:
            link, source = find_clip_link(query, scene["end"] - scene["start"] + 1)
            if not link:
                info(f"  -> Adegan {i + 1}: tidak ada video cocok untuk '{query}', pakai latar animasi.")
                continue

            filename = f"scene_{i}.mp4"
            filepath = os.path.join(PUBLIC_DIR, filename)
            with requests.get(link, timeout=120, stream=True) as clip:
                clip.raise_for_status()
                with open(filepath, "wb") as f:
                    for block in clip.iter_content(chunk_size=1024 * 256):
                        f.write(block)
            if os.path.getsize(filepath) < 10_000:
                os.remove(filepath)
                continue
            scene["video"] = filename
            credits.add(source)
            info(f"  -> Adegan {i + 1}: video latar '{query}' siap (dari {source}).")
        except Exception as e:
            info(f"  -> Adegan {i + 1}: video latar gagal diunduh ({str(e)[:100]}), pakai latar animasi.")
    return credits


# ========================================================
# 5. RENDER DENGAN REMOTION
# ========================================================
def run_command(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def render_remotion_video(words, scenes, duration):
    info("[4/5] Menjalankan Remotion (membuat video beranimasi)...")
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

    props = {
        "audioUrl": "voice.mp3",
        "scenes": [
            {
                "type": s["type"],
                "title": s["title"],
                "points": s["points"],
                "number": s.get("number"),
                "unit": s.get("unit"),
                "start": s["start"],
                "end": s["end"],
                **({"video": s["video"]} if s.get("video") else {}),
            }
            for s in scenes
        ],
        "words": words,
        "durationInSeconds": duration,
    }
    # Musik latar: taruh file bgm.mp3 di video_engine/public, otomatis dipakai dengan volume pelan
    if os.path.exists(os.path.join(PUBLIC_DIR, "bgm.mp3")):
        props["bgmUrl"] = "bgm.mp3"
        info("  -> Musik latar bgm.mp3 ditemukan dan dipakai.")

    props_path = os.path.join(REMOTION_DIR, "render_props.json")
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
        info(f"  -> Topik dipilih: {data['title']} ({len(data['scenes'])} adegan)")

        os.makedirs(PUBLIC_DIR, exist_ok=True)
        audio_dest = os.path.join(PUBLIC_DIR, "voice.mp3")
        words, duration = asyncio.run(generate_voice_and_timestamps(data["full_script"], audio_dest))
        info(f"  -> Durasi video: {duration} detik, {len(words)} kata")

        assign_scene_times(data["scenes"], words, duration)
        credits = fetch_stock_videos(data["scenes"])
        if credits:
            data["description"] += "\n\nVideo latar: " + ", ".join(sorted(credits))
        final_video = render_remotion_video(words, data["scenes"], duration)
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
