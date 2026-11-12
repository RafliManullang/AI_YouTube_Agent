"""
AI YouTube Agent
Alur kerja: riset topik + naskah per adegan (Gemini) -> suara + waktu tiap kata (Edge-TTS)
-> video latar gratis (Pexels, opsional) -> render video beranimasi (Remotion) -> unggah ke YouTube.

Cara pakai (contoh):
    python main_agent.py                      # jalan penuh sampai unggah
    python main_agent.py --tanpa-upload       # berhenti setelah video jadi (untuk uji coba)
    python main_agent.py --unggah-saja        # unggah video yang sudah jadi, tanpa membuat baru
    python main_agent.py --topik "cara kerja lift gedung"
    python main_agent.py --jadwal 13:00       # unggah, lalu YouTube menayangkannya jam 13:00 WIB
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
import random
import tempfile
import traceback
from datetime import datetime, timedelta, timezone

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
VIDEO_PATH = os.path.join(OUT_DIR, "shorts_final.mp4")
META_PATH = os.path.join(OUT_DIR, "catatan_video.json")  # judul, deskripsi, tag video terakhir

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
SCENE_TYPES = ("flow", "mindmap", "counter", "timeline", "barchart", "compare", "gauge", "footage",
               "cutaway", "microscale", "story")
MOODS = ("senang", "takut", "kaget", "sedih", "tegang", "bangga")
WEATHERS = ("cerah", "hujan", "salju", "badai", "malam", "kabut")
AMBIENCES = ("angin", "gesekan", "benturan", "mesin", "air", "hening")
MUSICS = ("misterius", "semangat", "tenang")
# Dua pembawa obrolan: nama -> (suara Edge-TTS, tambahan nada Hz). Bisa diganti lewat .env
SPEAKERS = {
    "shela": (os.getenv("VOICE_SHELA", "id-ID-GadisNeural"), 0),
    "flay": (os.getenv("VOICE_FLAY", os.getenv("VOICE", "id-ID-ArdiNeural")), 0),
}
DIALOG = os.getenv("DIALOG", "on").strip().lower() != "off"  # DIALOG=off: satu narator saja
# Urutan harus sama dengan THEMES di video_engine/src/types.ts
THEME_NAMES = ("pelangi", "neon", "senja", "hutan", "samudra", "emas", "kosmik", "sepia")
# Tema dipilih agen sendiri sesuai kategori, dan tidak mengulang tema 3 video terakhir
CATEGORY_THEMES = {
    "CARA KERJA": ("pelangi", "samudra", "hutan", "senja", "neon", "emas"),
    "FAKTA SAINS": ("kosmik", "samudra", "neon", "pelangi", "hutan", "senja"),
    "KISAH NYATA": ("sepia", "emas", "senja", "hutan"),
}
THEME_HISTORY_PATH = os.path.join(BASE_DIR, "riwayat_tema.json")
CATEGORIES = ("CARA KERJA", "FAKTA SAINS", "KISAH NYATA")
THUMB_PATH = os.path.join(OUT_DIR, "thumbnail.jpg")
WIB = timezone(timedelta(hours=7))
# Gaya suara per adegan: (tambahan kecepatan dalam persen, perubahan nada dalam Hz)
TONES = {
    "semangat": (8, 5),
    "santai": (0, 0),
    "misterius": (-12, -6),
    "tegas": (3, -3),
}


def info(msg):
    print(msg, flush=True)


def save_video_notes(data):
    """Simpan judul, deskripsi, dan tag supaya video yang sudah jadi bisa diunggah belakangan."""
    os.makedirs(OUT_DIR, exist_ok=True)
    notes = {"title": data["title"], "description": data["description"], "tags": data["tags"]}
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def load_video_notes():
    """Baca catatan video terakhir. Kalau tidak ada (video lama), pakai judul dari riwayat."""
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            notes = json.load(f)
        if notes.get("title"):
            return notes
    except Exception:
        pass
    history = load_history()
    return {
        "title": history[-1] if history else "Fakta Sains Menarik",
        "description": "Fakta sains dan cara kerja benda sehari-hari. #Shorts #Sains #Teknologi",
        "tags": ["sains", "teknologi", "carakerja", "shorts", "edukasi"],
    }


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


def load_theme_history():
    try:
        with open(THEME_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [t for t in data if t in THEME_NAMES] if isinstance(data, list) else []
    except Exception:
        return []


def save_theme(name):
    history = load_theme_history()
    history.append(name)
    with open(THEME_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history[-20:], f, ensure_ascii=False)


def pick_theme(category):
    """Pilih tema warna yang cocok dengan kategori dan belum dipakai di 3 video terakhir."""
    pool = list(CATEGORY_THEMES.get(category, THEME_NAMES))
    recent = load_theme_history()
    fresh = [t for t in pool if t not in recent[-3:]] or [t for t in pool if t not in recent[-1:]] or pool
    return random.choice(fresh)


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
        raise ValueError("Jawaban penulis naskah tidak berisi JSON.")
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
    topic_rule += (
        "\nSUDUT PANDANG TOPIK (penting): jangan topik dasar yang semua orang sudah tahu. Pilih sudut yang bikin "
        "penonton bilang \"wah, baru tahu!\": sesuatu yang sering dilihat tapi jarang dipahami, kebalikan dari "
        "dugaan umum, atau punya angka ekstrem yang bisa dibayangkan. Hanya pakai fakta yang kamu yakin benar. "
        "Kalau tidak yakin dengan sebuah angka, pakai kata \"sekitar\" atau pilih topik lain."
    )
    avoid = ""
    if done_titles:
        avoid = "Jangan ulangi topik yang sudah pernah dibuat: " + "; ".join(done_titles[-30:]) + "."

    if DIALOG:
        style_rule = (
            "FORMAT OBROLAN: video ini percakapan santai dua orang. Shela (cewek, penasaran, suka bertanya "
            "dan menyahut spontan) dan Flay (cowok, paham topiknya, menjelaskan dengan seru). Tiap adegan "
            "punya \"lines\" berisi 1 sampai 3 giliran bicara pendek (5 sampai 16 kata per giliran) dengan "
            "\"speaker\" \"shela\" atau \"flay\". Bergantian secara natural: Shela bertanya atau kaget "
            "(\"Hah, serius?\", \"Terus gimana?\"), Flay menjawab dengan fakta. Semua poin penting tetap "
            "tersampaikan lewat obrolan, jangan sampai obrolannya melantur. Gaya bahasa lisan sehari-hari."
        )
    else:
        style_rule = (
            "FORMAT NARASI: satu narator (speaker selalu \"flay\"), tiap adegan punya \"lines\" berisi "
            "1 giliran bicara 10 sampai 25 kata. Gaya seru, cepat, santai ala kreator konten modern."
        )
    return f"""
Kamu adalah scriptwriter YouTube Shorts edukasi berbahasa Indonesia, gaya Kok Bisa / Veritasium.
{topic_rule}
{avoid}

Pecah video menjadi 6 sampai 7 ADEGAN berurutan. Setiap adegan punya percakapan yang diucapkan dan
visual beranimasi. Total seluruh ucapan sekitar 90-110 kata (durasi 38-45 detik).
{style_rule}
HOOK 3 DETIK PERTAMA (paling penting): kalimat pertama WAJIB langsung menghentak, maksimal 12 kata, berupa
fakta mengejutkan, peringatan, atau pertanyaan yang memancing penasaran (contoh: "Jangan pernah pakai kaca
rumah untuk mobil, ini akibatnya!"). DILARANG membuka dengan sapaan (halo, hai, selamat datang), basa-basi,
"kali ini kita bahas", atau percakapan santai bernada datar. Visual adegan pertama harus langsung
memperlihatkan inti masalahnya, bukan pemandangan umum.
ALUR CERITA (supaya orang menonton sampai habis): (1) HOOK menghentak; (2) TARUHAN: kenapa ini penting
atau bahaya apa yang mengintai; (3) PENJELASAN bertahap dengan analogi benda sehari-hari yang mudah dibayangkan;
(4) TITIK BALIK tepat di tengah video: kalimat seperti "Tapi tunggu, ada yang lebih gila..." disusul fakta
yang berlawanan dengan dugaan; (5) ANGKA GILA yang dibandingkan dengan benda yang akrab (contoh: "setara
berat 6 ekor gajah", "sepanjang lapangan bola"), minimal 2 perbandingan seperti ini di seluruh video;
(6) JAWABAN yang memuaskan rasa penasaran. Jangan membocorkan jawaban inti di awal: simpan sampai bagian
(6). Penutup menyambung kembali ke hook atau melempar pertanyaan ke penonton supaya mereka berkomentar
atau menonton ulang.
TEMPO PADAT: kalimat pendek, tanpa pengantar bertele-tele, tanpa pengulangan. Setiap kalimat membawa
informasi baru. Adegan terakhir penutup singkat yang bikin orang ingin menonton ulang. Ucapan hanya berisi
kalimat yang diucapkan: tanpa instruksi panggung, tanpa emoji, tanpa tanda bintang, tanpa hashtag.

Aturan visual tiap adegan (field "type"):
- "flow"     : alur langkah berurutan. "points" berisi 3 sampai 4 langkah.
- "mindmap"  : peta pikiran dengan judul di tengah. "points" berisi 3 sampai 5 cabang.
- "counter"  : angka besar yang menghitung naik. Wajib isi "number" (angka saja) dan "unit"
               (satuannya). "points" berisi 2 sampai 3 label pendek.
- "timeline" : garis waktu untuk cerita sejarah atau kronologi. Isi "items" dengan 3 sampai 5 peristiwa
               berurutan, tiap item berbentuk {{"label": "tahun atau waktu, maksimal 7 karakter",
               "value": "kejadian, maksimal 7 kata"}}.
- "barchart" : grafik batang untuk membandingkan angka. Isi "items" dengan 2 sampai 5 item berbentuk
               {{"label": "nama maksimal 3 kata", "value": angka}} dan isi "unit" (satuan angka itu).
- "gauge"    : jam kecepatan dengan jarum yang naik, untuk membandingkan kecepatan, tekanan, suhu, atau
               angka dramatis lain. Isi "items" dengan 1 sampai 2 item {{"label": "nama maksimal 3 kata",
               "value": angka}} dan isi "unit". Dua item = dua jam berdampingan (misalnya ban mobil
               lawan ban pesawat).
- "footage"  : rekaman video asli layar penuh dengan judul besar. WAJIB dipakai untuk adegan pertama (hook)
               dan boleh untuk 1 adegan lain. "points" berisi 1 label pendek (opsional). Wajib isi
               "footage_query" yang menggambarkan kejadian nyatanya (contoh: "airplane landing runway").
- "cutaway"  : potongan melintang / tembus pandang (X-ray) untuk memperlihatkan bagian dalam benda yang
               sedang bekerja, dengan panah arah gerak. Isi "items" dengan 2 sampai 4 komponen
               {{"label": "nama komponen maksimal 3 kata", "value": "fungsinya maksimal 7 kata"}} berurutan
               sesuai alur kerja. Isi "variant": "device" (benda seperti lift atau rice cooker) atau
               "ground" (konstruksi bawah tanah seperti MRT atau terowongan, dengan lapisan tanah).
- "microscale": zoom dari benda utuh ke tingkat mikro (getaran, molekul, gaya) untuk membongkar rahasia
               sains. Isi "items" dengan TEPAT 2 item yang dikontraskan (misalnya kaku lawan kenyal)
               {{"label": "nama bahan maksimal 2 kata", "value": "perilaku di tingkat mikro maksimal 8 kata"}}.
- "story"    : ilustrasi buku cerita (cut-out kertas) dengan karakter berekspresi, untuk kisah sejarah dan
               kisah nyata. Isi "mood" (salah satu: "senang", "takut", "kaget", "sedih", "tegang", "bangga"),
               "weather" (salah satu: "cerah", "hujan", "salju", "badai", "malam", "kabut"), dan "points"
               berisi 1 sampai 3 keterangan pendek (maksimal 5 kata).
- "compare"  : sebelum dan sesudah, atau dua hal yang dibandingkan. Isi "items" dengan TEPAT 2 item
               berbentuk {{"label": "judul sisi maksimal 2 kata, misalnya Sebelum / Sesudah / Dulu / Kini",
               "value": "penjelasan maksimal 8 kata"}}.
Pakai "counter" dan "barchart" HANYA kalau angkanya benar-benar faktual, jangan mengarang angka.
Pakai "timeline" hanya kalau memang ada urutan waktu. Pakai campuran minimal 4 tipe yang berbeda. Hindari tampilan abstrak: sebisa mungkin sebut benda nyatanya.
PILIH GAYA ANIMASI SESUAI KATEGORI: kategori "CARA KERJA" utamakan "cutaway" (minimal 2 adegan) ditambah
"flow"; kategori "FAKTA SAINS" utamakan "microscale" (minimal 1 adegan) ditambah "gauge", "barchart" atau
"compare"; kategori "KISAH NYATA" utamakan "story" (minimal 2 adegan) ditambah "timeline" atau "footage".
"title" maksimal 4 kata. Setiap isi "points" maksimal 4 kata, tanpa emoji dan tanpa tanda baca.
VISUAL SESUAI ISI KALIMAT: setiap giliran bicara di "lines" boleh punya "footage_query" sendiri, yaitu 2 sampai
4 kata bahasa Inggris untuk rekaman nyata yang cocok dengan kalimat itu (contoh untuk video kaca mobil:
awal "car crash test", saat bahas pemanasan "glass factory furnace", saat bahas butiran "broken car window
closeup"). Pakai benda atau kejadian konkret, bukan konsep abstrak, dan jangan memakai satu rekaman yang sama
dari awal sampai akhir. "footage_query" di tingkat adegan juga diisi untuk semua adegan (cadangan).
"keywords" berisi 1 sampai 3 kata kunci terpenting dari ucapan adegan itu, ditulis persis seperti yang
diucapkan (contoh: "tempered glass", "600 derajat", "butiran"). Kata ini akan ditonjolkan di subtitle.
"sound" adalah suara latar adegan, pilih satu: "angin", "gesekan" (ban atau benda bergesek), "benturan",
"mesin", "air", atau "hening". Pilih yang cocok dengan kejadian di adegan itu.
"music" adalah musik latar seluruh video: "misterius", "semangat", atau "tenang".

"tone" adalah gaya suara narator pada adegan itu. Pilih salah satu: "semangat" (pembuka atau momen seru),
"santai" (penjelasan biasa), "misterius" (teka-teki atau rahasia), "tegas" (fakta penting atau penutup).
Variasikan supaya suara tidak monoton, jangan semua adegan sama.

"category" salah satu dari: "CARA KERJA", "FAKTA SAINS", "KISAH NYATA".
"thumbnail_text" adalah 2 sampai 4 kata huruf besar yang memancing penasaran untuk gambar sampul,
boleh diakhiri tanda tanya, tanpa emoji.

Keluarkan HANYA JSON murni dengan format persis ini:
{{
  "title": "Judul menarik maksimal 60 karakter",
  "description": "Deskripsi singkat 2-3 kalimat. #Shorts #Sains #Teknologi",
  "tags": ["sains", "teknologi", "carakerja", "shorts", "edukasi"],
  "category": "CARA KERJA",
  "thumbnail_text": "KOK BISA JATUH?",
  "music": "misterius",
  "scenes": [
    {{
      "lines": [{{"speaker": "shela", "text": "Kalimat yang diucapkan.", "footage_query": "elevator door"}}, {{"speaker": "flay", "text": "Jawabannya."}}],
      "title": "Judul adegan",
      "type": "flow",
      "tone": "semangat",
      "points": ["langkah satu", "langkah dua", "langkah tiga"],
      "items": [],
      "number": null,
      "unit": null,
      "footage_query": "elevator building",
      "keywords": ["kabel baja"],
      "variant": "device",
      "mood": "tegang",
      "weather": "cerah",
      "sound": "mesin"
    }}
  ]
}}
"""


GROQ_KEY = os.getenv("GROQ_API_KEY") or ""
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY") or ""
# Penyedia cadangan (gratis) yang memakai format OpenAI: (nama, alamat, key, daftar model)
BACKUP_PROVIDERS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions", GROQ_KEY,
     [m for m in [os.getenv("GROQ_MODEL"), "llama-3.3-70b-versatile", "openai/gpt-oss-120b"] if m]),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions", CEREBRAS_KEY,
     [m for m in [os.getenv("CEREBRAS_MODEL"), "gpt-oss-120b", "llama-3.3-70b"] if m]),
]


def call_openai_style(url, key, model, prompt):
    """Panggil penyedia berformat OpenAI (Groq, Cerebras) dan kembalikan teks jawabannya."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Kamu menjawab HANYA dengan satu objek JSON yang valid, tanpa teks lain."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    res = requests.post(url, headers=headers, json=body, timeout=90)
    if res.status_code == 400 and "response_format" in res.text:
        body.pop("response_format")  # model ini tidak mendukung mode JSON
        res = requests.post(url, headers=headers, json=body, timeout=90)
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code} {res.text[:200]}")
    return res.json()["choices"][0]["message"]["content"]


def build_text_sources(prompt):
    """Daftar sumber penulis naskah berurutan: Gemini dulu, lalu cadangan gratis.
    Tiap item: (nama, fungsi yang mengembalikan teks JSON)."""
    sources = []
    if GEMINI_KEY and GEMINI_KEY != "ISI_KEY_DI_SINI":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_KEY)
        config = types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0)
        for model_name in GEMINI_MODELS:
            sources.append((
                f"Gemini {model_name}",
                lambda mn=model_name: client.models.generate_content(model=mn, contents=prompt, config=config).text,
            ))
    for name, url, key, models in BACKUP_PROVIDERS:
        if not key:
            continue
        for model_name in models:
            sources.append((
                f"{name} {model_name}",
                lambda u=url, k=key, mn=model_name: call_openai_style(u, k, mn, prompt),
            ))
    return sources


GREETINGS = ("halo", "hai", "hay", "selamat datang", "kali ini", "hari ini kita", "apa kabar", "teman-teman")
DRAFT_SCENE_KEYS = ("lines", "title", "type", "tone", "points", "items", "number", "unit", "footage_query",
                    "keywords", "variant", "mood", "weather", "sound")


def polish_script(data, base_prompt):
    """Putaran editor: naskah pertama ditulis ulang oleh editor supaya hook lebih kuat, ada titik balik,
    angka yang mudah dibayangkan, dan faktanya dicek. Kalau gagal, naskah pertama dipakai apa adanya."""
    if os.getenv("EDITOR", "on").strip().lower() == "off":
        return data
    info("  -> Editor sedang menyempurnakan naskah (hook, titik balik, angka, cek fakta)...")
    draft = {k: data[k] for k in ("title", "description", "tags", "category", "thumbnail_text", "music") if k in data}
    draft["scenes"] = [{k: sc[k] for k in DRAFT_SCENE_KEYS if k in sc} for sc in data["scenes"]]
    editor_prompt = (
        base_prompt
        + "\n\n===== TUGAS KAMU SEKARANG: EDITOR =====\n"
        "Di bawah ini ada DRAF naskah untuk topik di atas. Kamu editor video viral yang sangat kritis. Tulis ulang "
        "draf itu menjadi versi yang jauh lebih menarik, dengan TOPIK YANG SAMA dan FORMAT JSON YANG SAMA PERSIS "
        "seperti aturan di atas (jumlah adegan 6 sampai 7).\n"
        "Periksa dan perbaiki satu per satu:\n"
        "1. Hook: apakah 3 detik pertama membuat orang berhenti scroll? Kalau datar, ganti dengan fakta "
        "mengejutkan atau peringatan yang lebih tajam. Tanpa sapaan.\n"
        "2. Rasa penasaran: apakah ada pertanyaan yang baru terjawab di akhir? Pastikan jawaban tidak bocor di awal.\n"
        "3. Titik balik di tengah video yang berlawanan dengan dugaan penonton.\n"
        "4. Minimal 2 angka atau perbandingan yang mudah dibayangkan dengan benda akrab.\n"
        "5. Hapus kalimat pengisi; setiap kalimat harus membawa informasi baru. Total ucapan 90 sampai 110 kata.\n"
        "6. CEK FAKTA: perbaiki atau hapus klaim yang tidak pasti benar. Jangan mengarang angka; kalau ragu "
        "pakai \"sekitar\" atau buang klaimnya.\n"
        "7. Obrolan Shela dan Flay terdengar natural dan lucu-ringan, bukan membaca teks.\n"
        "8. Penutup menyambung ke hook atau mengajak penonton berkomentar.\n"
        "9. Pilih tipe adegan, footage_query, dan keywords yang paling pas untuk tiap kalimat.\n"
        "Jawab HANYA dengan JSON hasil perbaikan.\n\nDRAF:\n"
        + json.dumps(draft, ensure_ascii=False)
    )
    dead = set()
    for name, call in build_text_sources(editor_prompt):
        if name in dead:
            continue
        try:
            better = extract_json(call())
            validate_content(better)
            words = sum(len(sc["narration"].split()) for sc in better["scenes"])
            first = better["scenes"][0]["narration"].lower()
            if not (4 <= len(better["scenes"]) <= 8 and 55 <= words <= 150):
                raise ValueError(f"hasil editor tidak wajar ({len(better['scenes'])} adegan, {words} kata)")
            if any(first.startswith(g) for g in GREETINGS):
                raise ValueError("hasil editor masih dibuka dengan sapaan")
            info(f"  -> Naskah disempurnakan oleh editor ({name})")
            return better
        except Exception as e:
            message = str(e)
            if any(x in message for x in ("404", "NOT_FOUND", "401", "403", "invalid_api_key", "model_not_found")):
                dead.add(name)
            info(f"  -> Editor ({name}) dilewati: {message[:100]}")
    info("  -> Tahap editor tidak berhasil, memakai naskah pertama.")
    return data


def research_and_write(forced_topic=None):
    info("\n[1/5] Agen AI sedang meriset topik dan menulis naskah...")
    prompt = build_prompt(forced_topic, load_history())
    sources = build_text_sources(prompt)
    if not sources:
        raise RuntimeError(
            "Belum ada API key penulis naskah. Buat file .env di folder proyek, lalu isi baris:\n"
            "GEMINI_API_KEY=kunci_anda   (lihat file .env.example). Cadangan gratis: GROQ_API_KEY atau CEREBRAS_API_KEY."
        )

    last_error = None
    dead = set()  # sumber yang tidak tersedia (model tidak ada atau key salah) dilewati pada putaran berikutnya
    for round_no in (1, 2):
        for name, call in sources:
            if name in dead:
                continue
            # model yang sedang sibuk dicoba 2 kali saja, lalu pindah ke sumber berikutnya
            for attempt in (1, 2):
                try:
                    data = extract_json(call())
                    validate_content(data)
                    info(f"  -> Naskah dibuat dengan {name}")
                    return polish_script(data, prompt)
                except Exception as e:
                    last_error = e
                    message = str(e)
                    if any(x in message for x in ("404", "NOT_FOUND", "401", "403", "invalid_api_key", "model_not_found")):
                        info(f"  -> {name} tidak bisa dipakai ({message[:90]}), mencoba sumber lain...")
                        dead.add(name)
                        break
                    info(f"  -> Percobaan {attempt}/2 dengan {name} gagal: {message[:130]}")
                    time.sleep(3 * attempt)
        if round_no == 1 and len(dead) < len(sources):
            info("  -> Semua sumber sedang sibuk. Menunggu 40 detik lalu mengulang dari awal...")
            time.sleep(40)
    raise RuntimeError(f"Semua penulis naskah gagal. Kesalahan terakhir: {last_error}")


def clean_text(value, limit):
    text = re.sub(r"[*#_`]", "", str(value or "")).strip()
    return text[:limit]


def clean_lines(raw):
    """Ambil giliran bicara dari Gemini. Kalau hanya ada 'narration', dijadikan satu giliran."""
    lines = []
    for ln in raw.get("lines") or []:
        if not isinstance(ln, dict):
            continue
        text = clean_text(ln.get("text"), 220)
        if len(text.split()) < 1:
            continue
        who = str(ln.get("speaker") or "").strip().lower()
        if who not in SPEAKERS:
            who = "flay" if not lines or lines[-1]["speaker"] == "shela" else "shela"
        lines.append({
            "speaker": who if DIALOG else "flay",
            "text": text,
            "footage_query": clean_text(ln.get("footage_query"), 60),
        })
    if not lines:
        text = clean_text(raw.get("narration"), 400)
        if text:
            lines = [{"speaker": "flay", "text": text, "footage_query": ""}]
    return lines[:3]


def clean_items(raw_items, numeric):
    """Rapikan daftar {label, value} dari Gemini. numeric=True berarti value wajib angka."""
    items = []
    for it in raw_items or []:
        if not isinstance(it, dict):
            continue
        label = clean_text(it.get("label"), 24)
        value = it.get("value")
        if not label or value is None:
            continue
        if numeric:
            try:
                value = float(str(value).replace(",", "."))
            except ValueError:
                continue
            if value == int(value):
                value = int(value)
        else:
            value = clean_text(value, 70)
            if not value:
                continue
        items.append({"label": label, "value": value})
    return items


def validate_content(data):
    for key in ("title", "description", "tags", "scenes"):
        if key not in data:
            raise ValueError(f"JSON dari Gemini kekurangan kolom '{key}'.")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) < 3:
        raise ValueError("Jumlah adegan terlalu sedikit.")
    if not isinstance(data["tags"], list):
        data["tags"] = [str(data["tags"])]

    scenes = []
    for raw in data["scenes"][:8]:
        lines = clean_lines(raw)
        narration = " ".join(l["text"] for l in lines)
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

        # Jenis baru butuh data "items"; kalau tidak lengkap, turun ke tampilan yang lebih sederhana
        items = []
        if scene_type == "barchart":
            items = clean_items(raw.get("items"), True)[:5]
            if len(items) < 2 or min(i["value"] for i in items) < 0 or max(i["value"] for i in items) <= 0:
                scene_type, items = "flow", []
        elif scene_type == "timeline":
            items = clean_items(raw.get("items"), False)[:5]
            if len(items) < 3:
                scene_type, items = "flow", []
        elif scene_type == "compare":
            items = clean_items(raw.get("items"), False)[:2]
            if len(items) < 2:
                scene_type, items = "flow", []
        elif scene_type == "cutaway":
            items = clean_items(raw.get("items"), False)[:4]
            if len(items) < 2:
                scene_type, items = "flow", []
        elif scene_type == "microscale":
            items = clean_items(raw.get("items"), False)[:2]
            if len(items) < 2:
                scene_type, items = "mindmap", []
        elif scene_type == "gauge":
            items = clean_items(raw.get("items"), True)[:2]
            if not items and number is not None:
                items = [{"label": clean_text(raw.get("title"), 24) or "Angka", "value": number}]
            if not items or min(i["value"] for i in items) < 0 or max(i["value"] for i in items) <= 0:
                scene_type, items = "flow", []

        # Perbaiki kombinasi yang tidak lengkap supaya tampilan tidak kosong
        if scene_type == "story" and not points:
            points = [clean_text(raw.get("title"), 40) or "Kisah nyata"]
        if scene_type == "counter" and number is None:
            scene_type = "flow"
        if not points:
            points = [clean_text(raw.get("title"), 40) or "Intinya"]
        if scene_type == "flow" and len(points) < 2:
            scene_type = "mindmap"

        tone = raw.get("tone") if raw.get("tone") in TONES else None
        sound = str(raw.get("sound") or "").strip().lower()
        variant = str(raw.get("variant") or "").strip().lower()
        mood = str(raw.get("mood") or "").strip().lower()
        weather = str(raw.get("weather") or "").strip().lower()
        keywords = [clean_text(k, 30) for k in (raw.get("keywords") or []) if str(k).strip()][:3]
        scenes.append({
            "variant": variant if variant in ("device", "ground") else "device",
            "mood": mood if mood in MOODS else "tegang",
            "weather": weather if weather in WEATHERS else "cerah",
            "keywords": keywords,
            "narration": narration,
            "lines": lines,
            "sound": sound if sound in AMBIENCES else "hening",
            "title": clean_text(raw.get("title"), 40) or "Tahukah kamu",
            "type": scene_type,
            "tone": tone,
            "points": points[:5],
            "items": items,
            "number": number,
            "unit": clean_text(raw.get("unit"), 40) or None,
            "footage_query": clean_text(raw.get("footage_query"), 60),
        })

    if len(scenes) < 3:
        raise ValueError("Adegan yang valid terlalu sedikit.")

    # Nada suara yang kosong diisi otomatis: pembuka bersemangat, penutup tegas, tengahnya bergantian
    for i, scene in enumerate(scenes):
        if scene["tone"] is None:
            if i == 0:
                scene["tone"] = "semangat"
            elif i == len(scenes) - 1:
                scene["tone"] = "tegas"
            else:
                scene["tone"] = "santai" if i % 2 else "semangat"

    # Adegan pembuka sebaiknya rekaman asli (hook). Kalau videonya tidak ada, nanti diturunkan otomatis.
    if scenes[0]["type"] != "footage" and scenes[0].get("footage_query"):
        scenes[0]["type"] = "footage"
    for scene in scenes:
        if scene["type"] == "footage" and not scene.get("footage_query"):
            scene["type"] = "mindmap" if len(scene["points"]) >= 2 else "flow"
    # cadangan: adegan tanpa kueri footage memakai kueri giliran bicara pertamanya yang punya kueri
    for scene in scenes:
        if not scene.get("footage_query"):
            scene["footage_query"] = next((l["footage_query"] for l in scene["lines"] if l.get("footage_query")), "")

    data["scenes"] = scenes
    data["full_script"] = " ".join(s["narration"] for s in scenes)
    if len(data["full_script"].split()) < 20:
        raise ValueError("Naskah terlalu pendek.")
    data["title"] = clean_text(data["title"], 80)

    # Kategori, lalu tema warna dipilih agen sendiri (selalu berganti dan sesuai kategori)
    category = str(data.get("category") or "").strip().upper()
    data["category"] = category if category in CATEGORIES else "FAKTA SAINS"
    data["theme_index"] = THEME_NAMES.index(pick_theme(data["category"]))
    thumb = clean_text(data.get("thumbnail_text"), 32).upper()
    if len(thumb.split()) < 1:
        thumb = " ".join(data["title"].upper().split()[:3])
    data["thumbnail_text"] = thumb

    music = str(data.get("music") or "").strip().lower()
    if music not in MUSICS:
        tones = [s["tone"] for s in scenes]
        music = "misterius" if tones.count("misterius") >= 2 else "semangat" if tones.count("semangat") >= 3 else "tenang"
    data["music"] = music
    data["bg_seed"] = random.randrange(1, 1000)


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


def base_rate_percent():
    """Kecepatan dasar suara (angka persen) dari pengaturan VOICE_RATE."""
    digits = re.sub(r"[^\d+-]", "", VOICE_RATE)
    try:
        return int(digits)
    except ValueError:
        return 15


async def synth_segment(text, rate, pitch, voice=None):
    """Buat suara satu giliran bicara. Hasil: (data mp3, daftar kata beserta waktunya)."""
    import edge_tts

    # boundary="WordBoundary" wajib: tanpa ini edge-tts hanya memberi waktu per kalimat
    communicate = edge_tts.Communicate(text, voice or VOICE, rate=rate, pitch=pitch, boundary="WordBoundary")
    audio = bytearray()
    words = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 10_000_000
            length = chunk["duration"] / 10_000_000
            words.append({"word": chunk["text"], "start": start, "end": start + length})
    return bytes(audio), words


def norm_token(text):
    return re.sub(r"[^0-9a-zA-Z]", "", str(text)).lower()


def align_words(words, text, who, keywords=()):
    """Pakai tulisan asli (lengkap dengan tanda baca) kalau jumlah katanya sama, tandai pembicaranya,
    dan tandai kata kunci supaya ditonjolkan di subtitle."""
    tokens = text.split()
    use_tokens = len(tokens) == len(words)
    out = []
    for i, w in enumerate(words):
        out.append({
            "word": tokens[i] if use_tokens else w["word"],
            "start": w["start"],
            "end": w["end"],
            "who": who,
        })
    normed = [norm_token(w["word"]) for w in out]
    for kw in keywords:
        parts = [norm_token(x) for x in str(kw).split() if norm_token(x)]
        if not parts:
            continue
        for i in range(len(normed) - len(parts) + 1):
            if normed[i:i + len(parts)] == parts:
                for j in range(i, i + len(parts)):
                    out[j]["emphasis"] = True
    return out


_FFMPEG = None


def ffmpeg_prefix():
    """Cari ffmpeg: yang terpasang di komputer, atau yang ikut dibawa Remotion."""
    global _FFMPEG
    if _FFMPEG is None:
        if shutil.which("ffmpeg"):
            _FFMPEG = [shutil.which("ffmpeg")]
        elif shutil.which("npx") and os.path.isdir(os.path.join(REMOTION_DIR, "node_modules")):
            _FFMPEG = [shutil.which("npx"), "remotion", "ffmpeg"]
        else:
            _FFMPEG = []
    return _FFMPEG


def trim_breaths(audio, words, seconds):
    """Potong hening di awal dan akhir suara (jeda napas) supaya tempo lebih padat.
    Pemotongan tanpa mengubah kualitas suara. Kalau gagal, suara asli dipakai apa adanya."""
    prefix = ffmpeg_prefix()
    if not prefix or not words or os.getenv("TRIM_BREATH", "on").strip().lower() == "off":
        return audio, words, seconds
    frame = 0.024  # satu bingkai MP3 = 24 milidetik
    lead = max(0.0, words[0]["start"] - 0.05)
    lead = int(lead / frame) * frame
    end = min(seconds, words[-1]["end"] + 0.12)
    if lead < 0.06 and seconds - end < 0.1:
        return audio, words, seconds
    tmp = tempfile.mkdtemp(prefix="trim_")
    try:
        src, dst = os.path.join(tmp, "in.mp3"), os.path.join(tmp, "out.mp3")
        with open(src, "wb") as f:
            f.write(audio)
        subprocess.run(
            prefix + ["-y", "-v", "error", "-i", src, "-ss", f"{lead:.3f}", "-to", f"{end:.3f}",
                      "-c", "copy", "-write_xing", "0", "-id3v2_version", "0", dst],
            cwd=REMOTION_DIR, check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with open(dst, "rb") as f:
            new_audio = f.read()
        new_seconds = len(new_audio) / 6000
        if len(new_audio) < 800 or new_seconds < words[-1]["end"] - lead - 0.2:
            return audio, words, seconds
        shifted = [dict(w, start=max(0.0, w["start"] - lead), end=max(0.0, w["end"] - lead)) for w in words]
        return new_audio, shifted, new_seconds
    except Exception:
        return audio, words, seconds
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def generate_scene_voices(scenes, output_audio_path):
    """Suara dibuat per giliran bicara (Shela atau Flay) dengan kecepatan dan nada sesuai adegan.
    Sekaligus menentukan waktu mulai dan selesai tiap adegan secara tepat."""
    info("[2/5] Membuat suara AI per giliran bicara dan sinkronisasi kata demi kata...")
    base = base_rate_percent()
    all_words = []
    offset = 0.0

    with open(output_audio_path, "wb") as out:
        for i, scene in enumerate(scenes):
            d_rate, d_pitch = TONES[scene["tone"]]
            lines = scene.get("lines") or [{"speaker": "flay", "text": scene["narration"]}]
            scene["start"] = round(offset, 2)
            for j, line in enumerate(lines):
                voice, voice_pitch = SPEAKERS.get(line["speaker"], SPEAKERS["flay"])
                # percobaan ketiga memakai suara polos, kalau-kalau pengaturan nada ditolak server
                attempts = [(base + d_rate, d_pitch + voice_pitch), (base + d_rate, d_pitch + voice_pitch), (base, 0)]
                result, last_error = None, None
                for n, (rate, pitch) in enumerate(attempts, 1):
                    try:
                        audio, words = await synth_segment(line["text"], f"{rate:+d}%", f"{pitch:+d}Hz", voice)
                        if len(audio) < 800:
                            raise RuntimeError("File suara kosong.")
                        result = (audio, words)
                        break
                    except Exception as e:
                        last_error = e
                        info(f"  -> Adegan {i + 1}.{j + 1}, percobaan suara {n}/3 gagal: {e}")
                        await asyncio.sleep(2 * n)
                if result is None:
                    raise RuntimeError(f"Gagal membuat suara adegan {i + 1}: {last_error}")

                audio, words = result
                # Edge-TTS menghasilkan MP3 48 kbps (6000 byte per detik) -> panjang giliran bicara
                seconds = len(audio) / 6000
                if not words:
                    words = estimate_words(line["text"], seconds)
                audio, words, seconds = trim_breaths(audio, words, seconds)
                line["start"] = round(offset, 2)
                line["end"] = round(offset + seconds, 2)
                for w in align_words(words, line["text"], line["speaker"], scene.get("keywords") or ()):
                    w["start"] = round(w["start"] + offset, 2)
                    w["end"] = round(w["end"] + offset, 2)
                    all_words.append(w)
                out.write(audio)
                offset += seconds

    if os.path.getsize(output_audio_path) < 1000:
        raise RuntimeError("File suara kosong.")

    duration = round(offset + 0.6, 2)
    for i, scene in enumerate(scenes):
        scene["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else duration
    return all_words, duration


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
            return candidates[0].get("link"), video.get("duration", 0)
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
                return clip["url"], hit.get("duration", 0)
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
            found = pick_pexels_file(res.json().get("videos", []), min_seconds)
            if found:
                return found[0], "Pexels", found[1]
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
            found = pick_pixabay_file(res.json().get("hits", []), min_seconds)
            if found:
                return found[0], "Pixabay", found[1]
        except Exception as e:
            info(f"  -> Pixabay gagal ({str(e)[:80]}).")
    return None, None, 0


def query_variants(query):
    """Kalau pencarian lengkap tidak ketemu, coba versi yang lebih pendek dan umum."""
    words = query.split()
    variants = [query]
    if len(words) > 2:
        variants.append(" ".join(words[:2]))
        variants.append(" ".join(words[-2:]))
    if len(words) > 1:
        variants.append(words[0])
    seen, out = set(), []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def download_clip(query, filename):
    """Cari dan unduh satu klip untuk kueri ini. Hasil: (detik klip, nama sumber) atau None."""
    link, source, clip_seconds = None, None, 0
    for q in query_variants(query):
        link, source, clip_seconds = find_clip_link(q, 3)
        if link:
            break
    if not link:
        return None
    filepath = os.path.join(PUBLIC_DIR, filename)
    with requests.get(link, timeout=120, stream=True) as clip:
        clip.raise_for_status()
        with open(filepath, "wb") as f:
            for block in clip.iter_content(chunk_size=1024 * 256):
                f.write(block)
    if os.path.getsize(filepath) < 10_000:
        os.remove(filepath)
        return None
    return clip_seconds, source


def plan_clips(scene):
    """Bagi adegan jadi beberapa potongan: tiap giliran bicara dengan kueri berbeda punya klip sendiri.
    Hasil: daftar [kueri, mulai, selesai] dengan waktu relatif terhadap awal adegan."""
    length = max(0.5, scene["end"] - scene["start"])
    plan = []
    for line in scene.get("lines") or []:
        query = line.get("footage_query") or scene.get("footage_query") or ""
        if not query or "start" not in line:
            continue
        start = max(0.0, line["start"] - scene["start"])
        end = min(length, line["end"] - scene["start"])
        if plan and plan[-1][0] == query:
            plan[-1][2] = end  # kueri sama dengan sebelumnya: perpanjang klip yang sama
        else:
            plan.append([query, start, end])
    if not plan and scene.get("footage_query"):
        plan = [[scene["footage_query"], 0.0, length]]
    if plan:
        plan[0][1] = 0.0  # klip pertama mulai dari awal adegan
        plan[-1][2] = length  # klip terakhir sampai akhir adegan
        for i in range(1, len(plan)):
            plan[i][1] = plan[i - 1][2]  # tanpa celah antar klip
    return plan[:3]


def fetch_stock_videos(scenes):
    """Unduh video latar tiap adegan, satu klip per kalimat bila kuerinya berbeda.
    Hasilnya: daftar nama sumber yang dipakai (untuk kredit)."""
    info("[3/5] Menyiapkan visual latar...")
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # Hapus klip dan gambar lama supaya tidak terpakai lagi tanpa sengaja
    for name in os.listdir(PUBLIC_DIR):
        if re.fullmatch(r"scene_\d+(_\d+)?\.(png|jpg|mp4)", name):
            os.remove(os.path.join(PUBLIC_DIR, name))

    credits = set()
    if not PEXELS_KEY and not PIXABAY_KEY:
        info("  -> Key video latar belum diisi: memakai latar animasi bawaan. Isi PIXABAY_API_KEY di .env supaya video memakai rekaman asli.")
        downgrade_footage(scenes)
        return credits

    cache = {}  # kueri sama dipakai ulang tanpa unduh lagi
    for i, scene in enumerate(scenes):
        scene.pop("clips", None)
        clips = []
        for j, (query, start, end) in enumerate(plan_clips(scene)):
            try:
                if query in cache:
                    filename, clip_seconds = cache[query]
                else:
                    filename = f"scene_{i}_{j}.mp4"
                    got = download_clip(query, filename)
                    if not got:
                        info(f"  -> Adegan {i + 1}.{j + 1}: tidak ada video cocok untuk '{query}'.")
                        continue
                    clip_seconds, source = got
                    credits.add(source)
                    cache[query] = (filename, clip_seconds)
                    info(f"  -> Adegan {i + 1}.{j + 1}: video '{query}' siap (dari {source}).")
                clips.append({"file": filename, "start": round(start, 2), "end": round(end, 2), "seconds": clip_seconds})
            except Exception as e:
                info(f"  -> Adegan {i + 1}.{j + 1}: video gagal diunduh ({str(e)[:100]}).")
        if clips:
            # celah akibat klip yang gagal ditutup oleh klip sebelumnya
            clips[0]["start"] = 0.0
            for k in range(len(clips) - 1):
                clips[k]["end"] = clips[k + 1]["start"]
            clips[-1]["end"] = round(max(0.5, scene["end"] - scene["start"]), 2)
            scene["clips"] = clips
            scene["video"] = clips[0]["file"]
            scene["video_seconds"] = clips[0]["seconds"]
        else:
            info(f"  -> Adegan {i + 1}: pakai latar animasi.")
    downgrade_footage(scenes)
    return credits


def downgrade_footage(scenes):
    """Adegan 'footage' tanpa video tidak bisa tampil, jadi diganti tampilan infografis."""
    for scene in scenes:
        if scene["type"] == "footage" and not scene.get("video"):
            if len(scene["points"]) >= 2:
                scene["type"] = "mindmap"
            else:
                scene["type"] = "flow"
                scene["points"] = (scene["points"] + [scene["title"], "Intinya"])[:3]


# ========================================================
# 5. RENDER DENGAN REMOTION
# ========================================================
def run_command(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def render_remotion_video(words, scenes, duration, theme_index=0, music=None, bg_seed=0):
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
                "items": s.get("items") or [],
                "number": s.get("number"),
                "unit": s.get("unit"),
                "start": s["start"],
                "end": s["end"],
                "sound": s.get("sound", "hening"),
                "variant": s.get("variant", "device"),
                "mood": s.get("mood", "tegang"),
                "weather": s.get("weather", "cerah"),
                **({"video": s["video"], "videoSeconds": s.get("video_seconds") or 0} if s.get("video") else {}),
                **({"clips": s["clips"]} if s.get("clips") else {}),
            }
            for s in scenes
        ],
        "words": words,
        "durationInSeconds": duration,
        "themeIndex": theme_index,
        "bgSeed": bg_seed,
        # Efek suara bisa dimatikan dengan menulis SFX=off di file .env
        "sfx": os.getenv("SFX", "on").strip().lower() != "off",
    }
    # Musik latar: taruh file bgm.mp3 di video_engine/public, otomatis dipakai dengan volume pelan
    if os.path.exists(os.path.join(PUBLIC_DIR, "bgm.mp3")):
        props["bgmUrl"] = "bgm.mp3"
        info("  -> Musik latar bgm.mp3 ditemukan dan dipakai.")
    elif music and os.getenv("BGM", "on").strip().lower() != "off" and os.path.exists(os.path.join(PUBLIC_DIR, "bgm", f"{music}.wav")):
        props["bgmUrl"] = f"bgm/{music}.wav"
        info(f"  -> Musik latar bawaan: {music}.")

    props_path = os.path.join(REMOTION_DIR, "render_props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    cmd = [npx, "remotion", "render", "src/index.ts", "ShortsComp", output_mp4, "--props=render_props.json"]
    run_command(cmd, REMOTION_DIR)

    if not os.path.exists(output_mp4) or os.path.getsize(output_mp4) < 10_000:
        raise RuntimeError("Video hasil render tidak ditemukan atau rusak.")
    return output_mp4


def render_thumbnail(data, scenes):
    """Buat gambar sampul. Kalau gagal, videonya tetap lanjut tanpa sampul."""
    if os.path.exists(THUMB_PATH):
        os.remove(THUMB_PATH)
    try:
        info("  -> Membuat thumbnail...")
        props = {
            "text": data["thumbnail_text"],
            "category": data["category"],
            "themeIndex": data["theme_index"],
        }
        first_video = next((s["video"] for s in scenes if s.get("video")), None)
        if first_video:
            props["video"] = first_video
        with open(os.path.join(REMOTION_DIR, "thumbnail_props.json"), "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        cmd = [
            shutil.which("npx"), "remotion", "still", "src/index.ts", "Thumbnail", THUMB_PATH,
            "--props=thumbnail_props.json", "--frame=30", "--image-format=jpeg", "--jpeg-quality=88",
        ]
        run_command(cmd, REMOTION_DIR)
        if not os.path.exists(THUMB_PATH):
            raise RuntimeError("file thumbnail tidak terbentuk")
        info(f"  -> Thumbnail siap: {THUMB_PATH}")
    except Exception as e:
        info(f"  -> Thumbnail gagal dibuat ({str(e)[:100]}). Tidak masalah, videonya tetap jadi.")


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


def next_publish_time(text):
    """Ubah jam seperti '13:00' menjadi waktu tayang berikutnya (WIB). Minimal 15 menit dari sekarang."""
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", str(text).strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ValueError("Format jadwal salah. Contoh yang benar: --jadwal 13:00")
    now = datetime.now(WIB)
    target = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    if target - now < timedelta(minutes=15):
        target += timedelta(days=1)
    return target


def upload_video(video_path, content_data, privacy, publish_at=None):
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

    if publish_at is not None:
        # Video diunggah sebagai privat, lalu YouTube sendiri yang menayangkannya pada jam yang dipilih
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        info(f"  -> Dijadwalkan tayang: {publish_at.strftime('%d-%m-%Y jam %H:%M')} WIB")

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

    if os.path.exists(THUMB_PATH):
        try:
            youtube.thumbnails().set(
                videoId=response["id"],
                media_body=MediaFileUpload(THUMB_PATH, mimetype="image/jpeg"),
            ).execute()
            info("  -> Thumbnail terpasang.")
        except Exception as e:
            info(
                f"  -> Thumbnail gagal dipasang ({str(e)[:120]}). Videonya tetap aman. "
                "Biasanya karena channel belum diverifikasi nomor teleponnya di YouTube."
            )

    info("\n=======================================================")
    info(f" SUKSES! Video: https://youtu.be/{response['id']}")
    info("=======================================================\n")


# ========================================================
# EKSEKUTOR UTAMA
# ========================================================
def main():
    parser = argparse.ArgumentParser(description="AI YouTube Agent")
    parser.add_argument("--tanpa-upload", action="store_true", help="Buat video saja, jangan diunggah")
    parser.add_argument("--unggah-saja", action="store_true",
                        help="Unggah video yang sudah jadi (hasil terakhir) tanpa membuat video baru")
    parser.add_argument("--jadwal", default=None, metavar="JAM",
                        help="Jam tayang di YouTube (WIB), contoh: 13:00. Video diunggah dulu, tayang otomatis di jam itu")
    parser.add_argument("--topik", default=None, help="Tentukan topik sendiri (kalau kosong, dipilih acak)")
    parser.add_argument(
        "--privasi", default=PRIVACY, choices=["private", "unlisted", "public"],
        help="Status video di YouTube (bawaan: private)",
    )
    args = parser.parse_args()

    try:
        publish_at = next_publish_time(args.jadwal) if args.jadwal else None

        if args.unggah_saja:
            if not os.path.exists(VIDEO_PATH) or os.path.getsize(VIDEO_PATH) < 10_000:
                raise RuntimeError("Belum ada video jadi. Buat dulu dengan: jalankan_agen.bat --tanpa-upload")
            notes = load_video_notes()
            info(f"Mengunggah video yang sudah jadi: {notes['title']}")
            upload_video(VIDEO_PATH, notes, args.privasi, publish_at)
            return

        data = research_and_write(args.topik)
        info(f"  -> Topik dipilih: {data['title']} ({len(data['scenes'])} adegan)")
        info(f"  -> Tema warna: {THEME_NAMES[data['theme_index']]}")

        os.makedirs(PUBLIC_DIR, exist_ok=True)
        audio_dest = os.path.join(PUBLIC_DIR, "voice.mp3")
        words, duration = asyncio.run(generate_scene_voices(data["scenes"], audio_dest))
        info(f"  -> Durasi video: {duration} detik, {len(words)} kata")

        credits = fetch_stock_videos(data["scenes"])
        if credits:
            data["description"] += "\n\nVideo latar: " + ", ".join(sorted(credits))
        final_video = render_remotion_video(
            words, data["scenes"], duration, data["theme_index"], data.get("music"), data.get("bg_seed", 0)
        )
        info(f"  -> Video selesai: {final_video}")
        render_thumbnail(data, data["scenes"])
        save_video_notes(data)

        if args.tanpa_upload:
            info("Unggah dilewati (--tanpa-upload). Kalau videonya sudah bagus, unggah dengan: jalankan_agen.bat --unggah-saja")
        else:
            upload_video(final_video, data, args.privasi, publish_at)
        save_history(data["title"])
        save_theme(THEME_NAMES[data["theme_index"]])

    except Exception as e:
        traceback.print_exc()
        info(f"\n[ERROR] Terjadi kendala: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
