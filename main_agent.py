import os
import time 
import sys
import json
import asyncio
import subprocess
import urllib.parse
import requests
from PIL import Image
import google.generativeai as genai
import edge_tts

# YouTube Google Client Library
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========================================================
# 1. KONFIGURASI API & FOLDER
# ========================================================
GEMINI_KEY = "ISI_KEY_DI_SINI"  # <-- Masukkan API Key Anda di sini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-3.8-flash")

VOICE = "id-ID-ArdiNeural" # Suara Cowok Natural
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REMOTION_DIR = os.path.join(BASE_DIR, "video_engine")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ========================================================
# 2. RISET DAN NASKAH SAINS (GEMINI)
# ========================================================
def research_and_write():
    print("\n[1/6] Agen AI sedang meriset topik sains & teknik...")
    prompt = """
    Kamu adalah scriptwriter YouTube Shorts edukasi sains, cara kerja benda, dan teknologi rekayasa (ala Kok Bisa / Veritasium).
    Pilih satu topik edukasi secara acak:
    - Mekanisme benda sehari-hari (contoh: cara kerja rice cooker menjaga nasi hangat, cara kerja rem lift).
    - Fenomena fisika di balik teknologi (contoh: kenapa gergaji medis dokter tidak memotong kulit).
    
    Tulis naskah bahasa Indonesia yang seru, cepat, dan santai (~35-40 detik, sekitar 80-100 kata).
    Buat 3 scene visual dengan konsep 3D isometric cutaway / diagram skematik transparan.

    Wajib berikan output HANYA JSON murni tanpa markdown penutup:
    {
      "title": "Judul Menarik Maks 60 Karakter",
      "description": "Deskripsi singkat edukatif #Shorts #Sains #Teknologi",
      "tags": ["sains", "teknologi", "carakerja", "shorts", "edukasi"],
      "full_script": "Tuliskan seluruh teks naskah narasi di sini dari awal sampai akhir tanpa instruksi panggung.",
      "prompts": [
        "isometric 3D cutaway diagram of [objek bagian 1], mechanical engineering, transparent parts, blender render, clean solid background",
        "isometric 3D exploded view schematic of [mekanisme bagian 2], technical infographic, floating parts, ultra detailed",
        "isometric 3D cross-section view of [fungsi akhir], glowing energy line arrows showing mechanics, technical illustration"
      ]
    }
    """
    res = model.generate_content(prompt)
    clean = res.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)

# ========================================================
# 3. AUDIO & TIMESTAMP PER KATA (EDGE-TTS)
# ========================================================
async def generate_voice_and_timestamps(text, output_audio_path):
    print("[2/6] Memproses suara AI & sinkronisasi kata per kata...")
    communicate = edge_tts.Communicate(text, VOICE, rate="+15%")
    words = []

    with open(output_audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                duration = chunk["duration"] / 10_000_000
                words.append({
                    "word": chunk["text"],
                    "start": round(start, 2),
                    "end": round(start + duration, 2)
                })

    total_duration = words[-1]["end"] + 1.0 if words else 35.0
    return words, total_duration

# ========================================================
# 4. GENERATOR GAMBAR 3D (POLLINATIONS)
# ========================================================
def generate_images(prompts):
    print("[3/6] Merender diagram visual 3D skematik...")
    image_paths = []
    public_folder = os.path.join(REMOTION_DIR, "public")
    os.makedirs(public_folder, exist_ok=True)

    for idx, prompt in enumerate(prompts):
        encoded = urllib.parse.quote(prompt + ", 8k, crisp technical drawing, clean render")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={idx+12}"
        
        # Coba unduh hingga 3 kali jika terjadi timeout / koneksi terputus
        res = None
        for attempt in range(3):
            try:
                res = requests.get(url, timeout=30)
                if res.status_code == 200:
                    break
            except Exception:
                print(f"  -> Koneksi lambat, mencoba ulang gambar {idx+1} (Percobaan {attempt+1}/3)...")
        
        filename = f"scene_{idx}.png"
        filepath = os.path.join(public_folder, filename)
        if res and res.content:
            with open(filepath, "wb") as f:
                f.write(res.content)
            
        image_paths.append(filename)
    return image_paths

# ========================================================
# 5. RENDER DENGAN REMOTION
# ========================================================
def render_remotion_video(words, images, duration):
    print("[4/6] Menjalankan Remotion Engine (Rendering Teks Kinetik & Visual)...")
    out_dir = os.path.join(REMOTION_DIR, "out")
    os.makedirs(out_dir, exist_ok=True)
    output_mp4 = os.path.join(out_dir, "shorts_final.mp4")

    # Pastikan mengambil nama file murninya saja (misal: scene_0.png)
    clean_images = [os.path.basename(img) for img in images]

    props_path = os.path.join(REMOTION_DIR, "render_props.json")
    props_data = {
        "audioUrl": "voice.mp3",
        "images": clean_images,
        "words": words,
        "durationInSeconds": duration
    }
    
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props_data, f)

    cmd = f'npx remotion render ShortsComp "{output_mp4}" --props="./render_props.json" --durationInFrames={int(duration * 30)}'
    subprocess.run(cmd, cwd=REMOTION_DIR, shell=True, check=True)
    return output_mp4

# ========================================================
# 6. UPLOAD OTOMATIS KE YOUTUBE
# ========================================================
def get_yt_service():
    creds = None
    token_path = os.path.join(BASE_DIR, "token.json")
    client_secret = os.path.join(BASE_DIR, "client_secret.json")

    if not os.path.exists(client_secret):
        raise FileNotFoundError("File client_secret.json belum ditemukan di folder D:\\AI_YouTube_Agent!")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path, content_data):
    print("[5/6] Mengunggah Shorts ke YouTube Channel Anda...")
    youtube = get_yt_service()
    
    body = {
        "snippet": {
            "title": content_data["title"] + " #Shorts",
            "description": content_data["description"],
            "tags": content_data["tags"],
            "categoryId": "28"  # Kategori: Sains & Teknologi
        },
        "status": {
            "privacyStatus": "public",  # Bisa diubah ke 'unlisted' atau 'private' untuk uji coba
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("\n=======================================================")
    print(f" SUKSES! Video Shorts Tayang: https://youtu.be/{response['id']}")
    print("=======================================================\n")

# ========================================================
# EKSEKUTOR UTAMA
# ========================================================
def main():
    try:
        # 1. Riset & Naskah
        data = research_and_write()
        print(f"  -> Topik Dipilih: {data['title']}")

        # 2. Audio & Timestamps
        public_dir = os.path.join(REMOTION_DIR, "public")
        os.makedirs(public_dir, exist_ok=True)
        audio_dest = os.path.join(public_dir, "voice.mp3")
        
        words, duration = asyncio.run(generate_voice_and_timestamps(data["full_script"], audio_dest))

        # 3. Visual 3D
        images = generate_images(data["prompts"])

        # 4. Rendering Video via Remotion
        final_video = render_remotion_video(words, images, duration)

        # 5. Upload ke YouTube
        upload_video(final_video, data)

    except Exception as e:
        print(f"\n[ERROR] Terjadi kendala: {str(e)}")

if __name__ == "__main__":
    main()