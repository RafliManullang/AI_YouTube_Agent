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

import ai_art
import models3d
import sim_presets
import sim_scenes

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
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ] if m
]

VOICE = os.getenv("VOICE", "id-ID-ArdiNeural")  # suara cowok; cewek: id-ID-GadisNeural
VOICE_RATE = os.getenv("VOICE_RATE", "+15%")
# Suara narator: "auto" memakai Gemini TTS (lebih natural) kalau ada key Gemini, dan Edge-TTS kalau gagal.
# TTS=edge memaksa Edge-TTS saja. GEMINI_VOICE: Puck (ceria), Charon (informatif), Kore (tegas), Fenrir, Orus, dll.
TTS_MODE = os.getenv("TTS", "auto").strip().lower()
GEMINI_VOICE = os.getenv("GEMINI_VOICE", "Puck")
GEMINI_TTS_MODELS = [m for m in [os.getenv("GEMINI_TTS_MODEL"), "gemini-3.1-flash-tts-preview",
                                 "gemini-2.5-flash-preview-tts"] if m]
TTS_STYLE = (
    "Bacakan teks berikut dalam Bahasa Indonesia seperti kreator konten yang sedang bercerita ke teman dengan "
    "penuh semangat: intonasi hidup dan ekspresif, tekankan kata-kata penting, tempo cepat dan padat, penasaran "
    "di bagian pertanyaan, dan tegas di kalimat penutup. Harus terdengar seperti manusia sungguhan, bukan robot"
)
PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")  # private / unlisted / public
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SCENE_TYPES = ("flow", "mindmap", "counter", "timeline", "barchart", "compare", "gauge", "footage",
               "cutaway", "microscale", "story", "mechanism", "question")
MECHANISMS = ("katrol_lift", "roda_gigi", "piston", "tuas", "aliran", "panas", "rangkaian", "tekanan",
              "nozel_bensin", "roda_kerucut", "eskalator", "kunci_silinder", "sprinkler", "venturi",
              "eddy_current", "jembatan", "airbag", "mesin_ice")
MOODS = ("senang", "takut", "kaget", "sedih", "tegang", "bangga")
WEATHERS = ("cerah", "hujan", "salju", "badai", "malam", "kabut")
AMBIENCES = ("angin", "gesekan", "benturan", "mesin", "air", "hening")
MUSICS = ("misterius", "semangat", "tenang")
# Dua pembawa obrolan: nama -> (suara Edge-TTS, tambahan nada Hz). Bisa diganti lewat .env
SPEAKERS = {
    "shela": (os.getenv("VOICE_SHELA", "id-ID-GadisNeural"), 0),
    "flay": (os.getenv("VOICE_FLAY", os.getenv("VOICE", "id-ID-ArdiNeural")), 0),
}
DIALOG = os.getenv("DIALOG", "off").strip().lower() == "on"  # bawaan: satu narator. DIALOG=on: obrolan Shela dan Flay
# Urutan harus sama dengan THEMES di video_engine/src/types.ts
THEME_NAMES = ("pelangi", "neon", "senja", "hutan", "samudra", "emas", "kosmik", "sepia")
# Tema dipilih agen sendiri sesuai kategori, dan tidak mengulang tema 3 video terakhir
CATEGORY_THEMES = {
    "CARA KERJA": ("pelangi", "samudra", "hutan", "senja", "neon", "emas"),
    "FAKTA SAINS": ("kosmik", "samudra", "neon", "pelangi", "hutan", "senja"),
    "KISAH NYATA": ("sepia", "emas", "senja", "hutan"),
}
THEME_HISTORY_PATH = os.path.join(BASE_DIR, "riwayat_tema.json")
SFX_HISTORY_PATH = os.path.join(BASE_DIR, "riwayat_sfx.json")
SFX_NAMES = ("whoosh", "impact", "clank", "hiss", "zap", "thud", "sizzle", "bubble", "ding", "bell", "glitch",
             "riser", "beep", "screech")
KEY_SOUNDS = ("clank", "hiss", "zap", "thud", "sizzle", "bubble", "ding", "impact", "glitch", "riser", "bell")
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
        "description": "Fakta sains dan cara kerja benda sehari-hari. #Sains #Teknologi",
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


def pick_sfx_map():
    """Pilih variasi bunyi (a sampai d) untuk tiap jenis efek, selalu berbeda dari video sebelumnya."""
    try:
        with open(SFX_HISTORY_PATH, "r", encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = {}
    new = {}
    for name in SFX_NAMES:
        choices = [i for i in range(4) if i != old.get(name)]
        new[name] = random.choice(choices)
    try:
        with open(SFX_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(new, f)
    except OSError:
        pass
    return new


THUMB_HISTORY_PATH = os.path.join(BASE_DIR, "riwayat_thumb.json")
THUMB_LAYOUTS = 5


STRUCTURES = (
    ("MITOS LAWAN FAKTA", "buka dengan keyakinan umum yang salah, patahkan pelan-pelan dengan bukti, tutup dengan fakta sebenarnya"),
    ("DETEKTIF", "rangkaian pertanyaan: tiap jawaban memunculkan pertanyaan baru yang lebih besar, sampai terpecahkan"),
    ("HITUNG MUNDUR", "tiga alasan atau tiga bagian bernomor (3, 2, 1) dengan yang paling mengejutkan di nomor terakhir"),
    ("ANDAI TIDAK ADA", "eksperimen pikiran: apa yang terjadi kalau benda ini dihilangkan atau dibuat salah, lalu tunjukkan versi yang benar"),
    ("BEDAH LANGKAH DEMI LANGKAH", "ikuti satu kejadian dari detik pertama sampai akhir, tiap adegan satu tahap, tanpa analogi"),
    ("ORANG DI BALIKNYA", "mulai dari seseorang atau kejadian nyata yang melahirkan benda ini, lalu hubungkan ke cara kerjanya sekarang"),
)
STRUCTURE_HISTORY_PATH = os.path.join(BASE_DIR, "riwayat_alur.json")


def pick_structure():
    """Pilih kerangka cerita yang beda dari dua video terakhir supaya video tidak terasa seperti cetakan yang sama."""
    try:
        with open(STRUCTURE_HISTORY_PATH, "r", encoding="utf-8") as f:
            old = [int(x) for x in json.load(f)]
    except Exception:
        old = []
    fresh = [i for i in range(len(STRUCTURES)) if i not in old[-2:]] or list(range(len(STRUCTURES)))
    pick = random.choice(fresh)
    try:
        with open(STRUCTURE_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump((old + [pick])[-4:], f)
    except OSError:
        pass
    name, desc = STRUCTURES[pick]
    return (f"KERANGKA CERITA VIDEO INI: \"{name}\": {desc}. Susun semua adegan mengikuti kerangka ini; elemen lain "
            "(taruhan, analogi, titik balik, angka) hanya dipakai kalau pas dengan kerangka.")


def pick_thumb_layout():
    """Pilih tata letak thumbnail yang tidak sama dengan dua video terakhir."""
    try:
        with open(THUMB_HISTORY_PATH, "r", encoding="utf-8") as f:
            old = [int(x) for x in json.load(f)]
    except Exception:
        old = []
    fresh = [i for i in range(THUMB_LAYOUTS) if i not in old[-2:]] or list(range(THUMB_LAYOUTS))
    pick = random.choice(fresh)
    try:
        with open(THUMB_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump((old + [pick])[-4:], f)
    except OSError:
        pass
    return pick


def render_thumb_background(scenes):
    """Ambil satu gambar bersih (tanpa teks/subtitle) dari adegan terbaik sebagai latar thumbnail."""
    props_path = os.path.join(REMOTION_DIR, "render_props.json")
    out = os.path.join(PUBLIC_DIR, "thumb_bg.jpg")
    if os.path.exists(out):
        os.remove(out)
    try:
        with open(props_path, "r", encoding="utf-8") as f:
            props = json.load(f)
        cands = [s for s in props["scenes"] if s.get("sim")] or [s for s in props["scenes"] if s.get("artUrls") or s.get("art")]
        if not cands:
            return None
        sc = cands[min(1, len(cands) - 1)] if len(cands) > 1 else cands[0]
        frame = int((sc["start"] + (sc["end"] - sc["start"]) * 0.66) * 30)
        props["clean"] = True
        with open(os.path.join(REMOTION_DIR, "thumb_bg_props.json"), "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        cmd = [shutil.which("npx"), "remotion", "still", "src/index.ts", "ShortsComp", out,
               "--props=thumb_bg_props.json", f"--frame={frame}", "--image-format=jpeg", "--jpeg-quality=88"]
        if sc.get("sim"):
            cmd.append("--gl=" + (os.getenv("GL_MODE") or "angle"))
        run_command(cmd, REMOTION_DIR)
        return "thumb_bg.jpg" if os.path.exists(out) else None
    except Exception as e:
        info(f"  -> Latar thumbnail dari animasi gagal ({str(e)[:80]}), pakai latar biasa.")
        return None


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
            "FORMAT NARASI: SATU narator manusia yang bercerita langsung ke penonton (speaker selalu \"flay\"), "
            "tiap adegan punya \"lines\" berisi 1 sampai 2 kalimat (10 sampai 25 kata). Gaya bertutur seperti "
            "kreator yang sedang bercerita ke teman: ekspresif, ada penekanan, boleh bertanya ke penonton, tanpa "
            "basa-basi dan tanpa tanya-jawab dengan orang lain."
        )
    STRUCTURE_RULE = pick_structure()
    return f"""
Kamu adalah scriptwriter YouTube Shorts edukasi berbahasa Indonesia, gaya Kok Bisa / Veritasium.
{topic_rule}
{avoid}

Pecah video menjadi 8 sampai 10 ADEGAN berurutan. Setiap adegan punya ucapan dan visual beranimasi.
Total seluruh ucapan sekitar 150-175 kata (durasi sekitar 60 detik), padat, langsung ke inti, dan alurnya
runtut dari awal sampai akhir.
{style_rule}
HOOK 3 DETIK PERTAMA (paling penting): kalimat pertama WAJIB langsung menghentak, maksimal 12 kata, berupa
fakta mengejutkan, peringatan, atau premis yang memancing penasaran dan menyebut benda konkretnya (contoh:
"Di balik dinding lift ini ada balok besi seberat mobil. Kamu naik, dia turun. Buat apa?" atau "Jangan pernah
pakai kaca rumah untuk mobil, ini akibatnya!"). Visual adegan pertama sudah memperlihatkan benda itu di detik
ke-0 (pakai tipe "mechanism" atau "cutaway" kalau topiknya cara kerja benda). DILARANG membuka dengan sapaan (halo, hai, selamat datang), basa-basi,
"kali ini kita bahas", atau percakapan santai bernada datar. Visual adegan pertama harus langsung
memperlihatkan inti masalahnya, bukan pemandangan umum.
ALUR CERITA (supaya orang menonton sampai habis; ini kotak peralatan, BUKAN urutan wajib, ikuti KERANGKA CERITA VIDEO INI di bawah): (1) HOOK menghentak; (2) TARUHAN: kenapa ini penting
atau bahaya apa yang mengintai; (3) PENJELASAN bertahap dengan analogi benda sehari-hari yang mudah dibayangkan;
(4) TITIK BALIK tepat di tengah video: kalimat seperti "Tapi tunggu, ada yang lebih gila..." disusul fakta
yang berlawanan dengan dugaan; (5) ANGKA GILA yang dibandingkan dengan benda yang akrab (contoh: "setara
berat 6 ekor gajah", "sepanjang lapangan bola"), minimal 1 dan paling banyak 2 perbandingan seperti ini;
BATAS ANGKA (supaya otak penonton tidak lelah): di SELURUH ucapan hanya boleh ada 3 angka penting, paling banyak
satu angka per kalimat, dan jangan ada dua angka di kalimat berdekatan. Pilih angka yang paling mengejutkan, buang
sisanya, lalu ganti dengan perbandingan kata-kata ("sedikit lebih cepat", "seberat mobil"). Tiap angka yang
disebut harus punya adegan sendiri yang memperlihatkannya (counter, barchart, gauge, atau animasi 3D);
(6) JAWABAN yang memuaskan rasa penasaran. Jangan membocorkan jawaban inti di awal: simpan sampai bagian
(6). PENUTUP MELINGKAR (seamless loop): kalimat terakhir adalah PERTANYAAN PANCINGAN pendek (maksimal 10 kata)
yang dijawab langsung oleh kalimat pembuka saat video berulang. JANGAN mengulang kata-kata pembuka di penutup
(pengulangan kata terdengar seperti gagap). Contoh: pembuka "Tiga pesawat hancur di udara gara-gara jendela
kotak." dan penutup "Jadi, apa jadinya kalau jendela pesawat berbentuk kotak?". Contoh lain: pembuka "Karena
di baliknya ada balok besi seberat mobil." dan penutup "Lalu kenapa lift tidak pernah jatuh?".
{STRUCTURE_RULE}
LARANGAN KLISE (supaya video tidak terasa seperti cetakan yang sama): jangan memakai "Tapi tunggu", "ternyata",
"bayangkan kamu", "rahasianya adalah", "inilah rahasia", dan jangan memberi judul adegan "ANALOGI ...". Tidak semua
video perlu analogi; pakai hanya kalau benar-benar membantu. Judul adegan harus spesifik pada isi (contoh:
"Pin pegas", bukan "Penjelasan"). Variasikan jenis adegan, jangan selalu counter lalu gauge lalu barchart.
STORYBOARD PER KATEGORI (contoh urutan adegan, boleh disesuaikan dengan kerangka cerita di atas):
- CARA KERJA: (1) hook: benda konkret + "question" atau "footage" (kenapa begini?); (2) taruhan: apa bahayanya kalau
  tidak ada bagian rahasia ini; (3) "mechanism" atau "cutaway" yang menyorot bagian rahasia dengan label; (4) proses
  alirannya (panah dan aliran bercahaya) dalam "mechanism"; (5) klimaks: momen bagian itu bekerja memutus atau
  menahan, diucapkan dengan kalimat paling dramatis; (6) fakta mencengangkan berupa angka besar ("counter" atau
  "gauge"), lalu kalimat penutup yang menyambung ke pembuka.
- FAKTA SAINS: (1) hook "question" yang melawan akal sehat; (2) bongkar mitos ("compare"); (3) "microscale" atau
  "mechanism" yang memperlihatkan rahasianya; (4) proses saat kejadian, diucapkan pelan dan jelas agar paham;
  (5) kesimpulan jenius satu kalimat yang mudah diingat; (6) penutup melingkar.
- KISAH NYATA: (1) hook titik balik dengan "story" atau "footage" yang diberi lingkaran sorot; (2) latar masalah
  dengan taruhan bernada dramatis ("satu goresan kecil saja bisa membunuh setengah kota"); (3) momen "aha" saat
  penemuan; (4) dampak besar ("barchart" atau "counter" yang faktual); (5) pelajaran penutup yang menyambung ke
  kalimat pertama.
BUNYI MOMEN PUNCAK ("sfx"): efek suara TIDAK dipakai untuk tiap kata atau tiap label. Hanya satu bunyi di momen puncak
adegan "mechanism" atau "cutaway", dan bunyinya HARUS cocok dengan kejadian yang tampil. Pilihan: "clank" (logam
beradu, pengunci lepas), "hiss" (desis udara atau tekanan), "zap" (listrik), "thud" (hantaman atau dentum berat),
"sizzle" (panas, api, menggoreng), "bubble" (cairan, gelembung, mendidih), "ding" (selesai atau berhasil), "bell"
(momen sejarah), "impact" (kejutan umum). Kosongkan ("") kalau tidak ada kejadian yang pas. Jangan memakai bunyi yang
sama di dua adegan berturutan.
{SIM_GUIDE}
VISUAL NYATA (WAJIB, ini yang paling penting): penonton harus MELIHAT persis apa yang sedang diucapkan.
Untuk SETIAP adegan selain "footage" isi dua kolom:
- "subject": 1 sampai 3 kata BAHASA INGGRIS untuk benda, hewan, orang, atau kendaraan utama yang disebut di
  kalimat itu (contoh: "escalator", "cat", "car", "key", "elephant", "doctor"). Kosongkan ("") kalau tidak ada
  satu benda utama (misalnya hanya angka atau gagasan).
- "art": daftar berisi 1 deskripsi gambar BAHASA INGGRIS (maksimal 25 kata) tentang adegan kartun 3D yang
  memperlihatkan persis isi kalimat itu. Deskripsi tiap adegan HARUS berbeda dari adegan lain (sudut, benda, atau
  tindakan berbeda). Mulai dengan benda utamanya yang nyata dan dikenal (contoh: "An airplane
  window with rounded corners, close-up, cabin wall around it"). Tulis hal yang bisa dipotret, BUKAN gagasan abstrak
  (hindari kata seperti "concept", "force", "stress", "energy"). Boleh ada tokoh kartun atau orang. Untuk cara kerja
  benda, gambarkan potongan melintang bagian dalamnya. Jangan minta teks atau huruf.
- "subject" harus benda yang disebut di kalimat ADEGAN ITU SENDIRI, bukan benda topik besar. Kalau topiknya
  pesawat, adegan jendela memakai "window", adegan retakan memakai "crack" atau "glass", adegan kaca berlapis
  memakai "glass", adegan sayap memakai "wing". DILARANG memakai subject yang sama di lebih dari 2 adegan dalam
  satu video dan dilarang di dua adegan berturutan. Pakai kata benda umum yang mudah ditemukan di perpustakaan
  model 3D (satu kata Inggris, bukan istilah teknik).
Setiap momen klimaks atau kejutan diberi satu kalimat pendek yang menghentak (animasi otomatis memberi getaran
dan kilat di momen itu).

SEMUA VISUAL BERUPA ANIMASI 3D: setiap adegan selain "footage" otomatis ditampilkan sebagai animasi 3D. Pakai tipe
"footage" paling banyak SATU adegan (misalnya hook berupa rekaman nyata), sisanya pilih tipe animasi supaya seluruh
video berupa simulasi 3D.

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
- "mechanism": animasi yang MEMPERLIHATKAN cara kerja suatu benda sehingga penonton paham tanpa membaca.
               PRIORITAS UTAMA untuk topik cara kerja benda dan banyak topik sains. Isi "mechanism" dengan
               salah satu di bawah ini, dan isi "items" berisi 3 sampai 4 nama bagian BERURUTAN sesuai
               daftar bagian-nya (ganti dengan nama bagian benda yang sebenarnya, maksimal 2 kata per label,
               "value" boleh kosong). Kalau bendanya TIDAK ada di daftar berikut (contoh: sabuk pengaman, kunci pintu,
               kamera), isi "mechanism": "" dan WAJIB menulis "sim" 3D yang lengkap untuk benda itu; jangan ganti ke
               tipe lain:
                 "katrol_lift" (lift, derek, katrol): bagian 1 kabin, 2 tali baja, 3 pemberat, 4 katrol
                 "roda_gigi" (jam, mesin, sepeda): 1 gigi penggerak, 2 gigi perantara, 3 gigi keluaran
                 "piston" (mesin, pompa, rem hidrolik): 1 piston, 2 silinder, 3 poros engkol
                 "tuas" (gunting, jungkat-jungkit, pembuka botol): 1 titik tumpu, 2 beban, 3 gaya tekan
                 "aliran" (pipa, semprotan, sayap pesawat): 1 pipa lebar, 2 penyempitan, 3 aliran cepat
                 "panas" (rice cooker, kompor, oven): 1 sumber panas, 2 isi yang dipanaskan, 3 sensor suhu, 4 uap
                 "rangkaian" (lampu, charger, saklar): 1 baterai, 2 saklar, 3 lampu, 4 aliran listrik
                 "tekanan" (ban, kompresor, suntikan, balon): 1 tutup atau piston, 2 partikel gas, 3 pengukur tekanan
                 "nozel_bensin" (nozel SPBU, pompa otomatis berhenti sendiri): 1 gagang, 2 lubang udara, 3 ruang hampa, 4 pengunci
                 "roda_kerucut" (kereta api, rel, belok tanpa setir): 1 roda kerucut, 2 rel, 3 sisi besar
                 "eskalator" (eskalator, travelator): 1 roda penggerak tangga, 2 roda pegangan, 3 anak tangga, 4 pegangan tangan
                 "kunci_silinder" (kunci pintu, gembok): 1 pin atas, 2 pin bawah, 3 pegas, 4 anak kunci
                 "sprinkler" (sprinkler gedung, alarm kebakaran): 1 kepala sprinkler, 2 sumbat katup, 3 tabung kaca
                 "venturi" (karburator, semprotan, parfum, sayap): 1 celah sempit, 2 pipa hisap, 3 tekanan turun
                 "eddy_current" (rem magnet, rem kereta cepat): 1 roda, 2 magnet, 3 arus pusar
                 "jembatan" (jembatan gantung, kabel baja, bendungan): 1 jalan, 2 menara, 3 kabel baja
                 "airbag" (airbag, sensor tabrakan): 1 sensor benturan, 2 pemicu, 3 kantong udara
                 "mesin_ice" (mesin mobil, motor bensin): 1 piston, 2 poros engkol, 3 busi, 4 klep
- "question" : tanda tanya merah besar yang berdenyut, untuk adegan hook atau pembongkar mitos yang melawan akal
               sehat (contoh: "REL KAKU, KOK NGGAK ANJLOK?"). "title" berisi kalimat tanya singkat dan "points"
               berisi 1 teks pendek di bawah tanda tanya (maksimal 5 kata).
- "compare"  : sebelum dan sesudah, atau dua hal yang dibandingkan. Isi "items" dengan TEPAT 2 item
               berbentuk {{"label": "judul sisi maksimal 2 kata, misalnya Sebelum / Sesudah / Dulu / Kini",
               "value": "penjelasan maksimal 8 kata"}}.
Pakai "counter" dan "barchart" HANYA kalau angkanya benar-benar faktual, jangan mengarang angka.
Pakai "timeline" hanya kalau memang ada urutan waktu. Hindari kartu teks dan diagram kotak-kotak ("flow", "mindmap") kecuali terpaksa: penonton cepat bosan melihat
teks muncul bergantian. Utamakan visual yang bergerak dan konkret ("mechanism", "cutaway", "microscale",
"story", "gauge"), dan pakai "footage" paling banyak 2 adegan (adegan pembuka dan satu lagi).
Pakai campuran minimal 4 tipe yang berbeda.
PILIH GAYA ANIMASI SESUAI KATEGORI: kategori "CARA KERJA" utamakan "cutaway" (minimal 2 adegan) ditambah
"mechanism"; kategori "FAKTA SAINS" utamakan "microscale" (minimal 1 adegan) ditambah "gauge", "barchart" atau
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
  "description": "Deskripsi singkat 2-3 kalimat. Lalu 2 sampai 3 hashtag topik (contoh #Sains #CaraKerja). JANGAN pakai #Shorts.",
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
      "sound": "mesin",
      "sfx": "clank",
      "subject": "elevator",
      "art": ["cutaway cross-section of an elevator shaft showing steel ropes, pulley and heavy counterweight"]
    }}
  ]
}}
"""

SIM_GUIDE = """SIMULASI 3D ("sim"): untuk setiap adegan bertipe "mechanism" atau "cutaway" tulis "sim", yaitu adegan 3D sungguhan
yang bergerak sesuai cara kerja benda. Satuan kira-kira meter, sumbu y ke atas, kamera melihat titik tengah dari
depan. Seluruh benda harus muat dalam kotak sekitar 10 lebar x 10 tinggi. Isi "sim":
- "objects": maksimal 14 benda: {"id","shape","pos":[x,y,z],"size","color":"#rrggbb","material","label"}.
  shape: box (size lebar,tinggi,tebal), cylinder dan tube/pipa berongga (size radius,tinggi,0; sumbunya vertikal,
  putar dengan "rot":[90,0,0] untuk mendatar), sphere (radius), cone, torus (radius besar,radius kecil), gear
  (radius,tebal,jumlah gigi), plate, rope (tali: "link":["idA","idB"], "linkOff":[[x,y,z],[x,y,z]]).
  material: metal, glass (tembus pandang, untuk dinding atau tabung), liquid, glow, rubber, plastic.
  "label" (maksimal 3 kata) hanya untuk bagian penting, muncul berurutan.
- "motions": {"target":id,"kind":"move","to":[x,y,z],"t0":0..1,"t1":0..1} (bergerak dari pos ke "to"),
  {"kind":"spin","axis":"y","speed":putaran per detik}, {"kind":"pulse","speed":..},
  {"kind":"color","color":"#rrggbb","t0","t1"} (berubah warna, contoh jadi merah saat klimaks pada t0 sekitar 0.62).
- "flows": aliran partikel bercahaya sepanjang jalur: {"path":[[x,y,z],...],"color","count","size","speed","t0","t1"}
  (cairan oranye, udara biru muda, listrik biru, panas oranye).
- "cutaway": true untuk membelah benda supaya bagian dalam terlihat. "cam": {"dist":16-22,"height":2-3,"orbit":0.8-1.3}.
Susun supaya sebab-akibat terlihat jelas dan klimaks terjadi di sekitar t=0.62 (benda bergerak, warna berubah, aliran
berhenti). Contoh lift: shaft (box glass), pulley (cylinder rot [90,0,0], spin), cab dan cw (box) bergerak
berlawanan lewat "move", dua rope dari pulley ke cab dan cw. Adegan lain: "sim": null."""


GROQ_KEY = os.getenv("GROQ_API_KEY") or ""
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY") or ""
# Penyedia cadangan (gratis) yang memakai format OpenAI: (nama, alamat, key, daftar model)
BACKUP_PROVIDERS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions", GROQ_KEY,
     [m for m in [os.getenv("GROQ_MODEL"), "openai/gpt-oss-120b", "llama-3.3-70b-versatile",
                  "meta-llama/llama-4-scout-17b-16e-instruct", "qwen/qwen3-32b", "openai/gpt-oss-20b"] if m]),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions", CEREBRAS_KEY,
     [m for m in [os.getenv("CEREBRAS_MODEL"), "gpt-oss-120b", "llama-3.3-70b", "qwen-3-32b", "llama3.1-8b"] if m]),
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
        "max_tokens": 8192,
        "response_format": {"type": "json_object"},
    }
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"  # model penalaran jangan menghabiskan jatah token untuk berpikir
    res = requests.post(url, headers=headers, json=body, timeout=90)
    if res.status_code == 400 and "response_format" in res.text:
        body.pop("response_format")  # model ini tidak mendukung mode JSON
        res = requests.post(url, headers=headers, json=body, timeout=90)
    if res.status_code == 400 and "reasoning_effort" in res.text:
        body.pop("reasoning_effort")
        res = requests.post(url, headers=headers, json=body, timeout=90)
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code} {res.text[:200]}")
    return res.json()["choices"][0]["message"]["content"]


def available_models(url, key):
    """Daftar model yang benar-benar bisa dipakai key ini (kosong kalau gagal ditanyakan)."""
    try:
        res = requests.get(url.rsplit("/chat/completions", 1)[0] + "/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if res.status_code == 200:
            return {x.get("id") for x in res.json().get("data", []) if x.get("id")}
    except Exception:
        pass
    return set()


def build_text_sources(prompt):
    """Daftar sumber penulis naskah berurutan: Gemini dulu, lalu cadangan gratis.
    Tiap item: (nama, fungsi yang mengembalikan teks JSON)."""
    sources = []
    if GEMINI_KEY and GEMINI_KEY != "ISI_KEY_DI_SINI":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_KEY)
        config = types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0,
                                             http_options=types.HttpOptions(timeout=75000))
        for model_name in GEMINI_MODELS:
            sources.append((
                f"Gemini {model_name}",
                lambda mn=model_name: client.models.generate_content(model=mn, contents=prompt, config=config).text,
            ))
    for name, url, key, models in BACKUP_PROVIDERS:
        if not key:
            continue
        have = available_models(url, key)
        if have:
            usable = [x for x in models if x in have]
            if not usable:
                usable = [x for x in sorted(have) if any(w in x for w in ("gpt-oss", "llama", "qwen"))
                          and not any(w in x for w in ("guard", "whisper", "tts", "embed", "prompt"))][:3]
            skipped = [x for x in models if x not in usable]
            if skipped:
                info(f"  -> {name}: model {', '.join(skipped)} tidak tersedia untuk key ini, dilewati.")
            models = usable
        for model_name in models:
            sources.append((
                f"{name} {model_name}",
                lambda u=url, k=key, mn=model_name: call_openai_style(u, k, mn, prompt),
            ))
    return sources


GREETINGS = ("halo", "hai", "hay", "selamat datang", "kali ini", "hari ini kita", "apa kabar", "teman-teman")
DRAFT_SCENE_KEYS = ("lines", "title", "type", "tone", "points", "items", "number", "unit", "footage_query",
                    "keywords", "variant", "mood", "weather", "sound", "mechanism", "sfx", "sim", "art", "subject")


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
        "seperti aturan di atas (jumlah adegan 8 sampai 10, total ucapan 150 sampai 175 kata).\n"
        "Periksa dan perbaiki satu per satu:\n"
        "1. Hook: apakah 3 detik pertama membuat orang berhenti scroll? Kalau datar, ganti dengan fakta "
        "mengejutkan atau peringatan yang lebih tajam. Tanpa sapaan.\n"
        "2. Rasa penasaran: apakah ada pertanyaan yang baru terjawab di akhir? Pastikan jawaban tidak bocor di awal.\n"
        "3. Titik balik di tengah video yang berlawanan dengan dugaan penonton.\n"
        "4. Paling banyak 3 angka di seluruh ucapan (satu angka per kalimat, tidak berdekatan). Kalau lebih, buang yang kurang penting dan ganti dengan perbandingan benda akrab. Jangan menumpuk istilah teknik.\n"
        "5. Hapus kalimat pengisi; setiap kalimat harus membawa informasi baru. Total ucapan 150 sampai 175 kata, tanpa dialog dua orang.\n"
        "6. CEK FAKTA: perbaiki atau hapus klaim yang tidak pasti benar. Jangan mengarang angka; kalau ragu "
        "pakai \"sekitar\" atau buang klaimnya.\n"
        "7. Obrolan Shela dan Flay terdengar natural dan lucu-ringan, bukan membaca teks.\n"
        "8. Penutup menyambung ke hook atau mengajak penonton berkomentar.\n"
        "9. Pilih tipe adegan, footage_query, dan keywords yang paling pas untuk tiap kalimat. Ganti kartu teks "
        "(\"flow\", \"mindmap\") dengan animasi konkret (\"mechanism\", \"cutaway\", \"microscale\", \"story\") bila bisa.\n"
        "10. Pastikan kalimat terakhir tersambung secara tata bahasa dengan kalimat pertama (seamless loop).\n"
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
            if not (6 <= len(better["scenes"]) <= 10 and 110 <= words <= 215):
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


def upgrade_sims(data, base_prompt):
    """Adegan yang masih memakai animasi 3D cadangan umum diminta dibuatkan animasi 3D khusus bendanya."""
    todo = [sc for sc in data["scenes"] if sc.get("sim_generic")][:3]
    if not todo:
        return data
    info(f"  -> Membuat animasi 3D khusus untuk {len(todo)} adegan...")
    for sc in todo:
        labels = [str(i.get("label") or "") for i in (sc.get("items") or []) if isinstance(i, dict)]
        ask = (
            "Kamu perancang animasi 3D sains. Topik video: " + str(data.get("title")) + ". Adegan: " + str(sc.get("title"))
            + ". Narasi adegan: " + str(sc.get("narration")) + ". Bagian yang diberi label: " + ", ".join(labels) + ".\n\n"
            + SIM_GUIDE + "\n\nTulis HANYA JSON {\"sim\": {...}} untuk adegan ini: bentuk benda aslinya dari beberapa benda 3D "
            "sederhana, dan gerak yang memperlihatkan SEBAB-AKIBAT cara kerjanya (klimaks sekitar t=0.62). Pakai label "
            "bagian yang diberikan."
        )
        dead = set()
        for name, call in build_text_sources(ask):
            if name in dead:
                continue
            try:
                got = extract_json(call())
                sim = sim_presets.clean_sim(got.get("sim") if "sim" in got else got)
                if sim is None:
                    raise ValueError("spesifikasi 3D tidak layak")
                sc["sim"], sc["sim_generic"] = sim, False
                info(f"     adegan \"{sc.get('title')}\": animasi 3D khusus dibuat ({name})")
                break
            except Exception as e:
                msg = str(e)
                if any(x in msg for x in ("404", "NOT_FOUND", "401", "403")):
                    dead.add(name)
                info(f"     {name} dilewati: {msg[:80]}")
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
    started = time.time()
    waits = (25, 45, 70)  # jeda antar putaran (detik); total paling lama sekitar 8 menit
    for round_no in range(1, len(waits) + 2):
        for name, call in sources:
            if name in dead:
                continue
            # model yang sedang sibuk dicoba 2 kali saja, lalu pindah ke sumber berikutnya
            for attempt in (1, 2):
                try:
                    data = extract_json(call())
                    validate_content(data)
                    info(f"  -> Naskah dibuat dengan {name}")
                    return upgrade_sims(polish_script(data, prompt), prompt)
                except Exception as e:
                    last_error = e
                    message = str(e)
                    if any(x in message for x in ("404", "NOT_FOUND", "401", "403", "invalid_api_key", "model_not_found")):
                        info(f"  -> {name} tidak bisa dipakai ({message[:90]}), mencoba sumber lain...")
                        dead.add(name)
                        break
                    if "429" in message:
                        info(f"  -> {name} kena batas pemakaian gratis, pindah ke sumber lain.")
                        break
                    info(f"  -> Percobaan {attempt}/2 dengan {name} gagal: {message[:130]}")
                    time.sleep(3 * attempt)
        if len(dead) >= len(sources):
            break
        if round_no <= len(waits):
            wait = waits[round_no - 1]
            info(f"  -> Semua sumber sedang sibuk. Menunggu {wait} detik lalu mencoba lagi (putaran {round_no + 1}/{len(waits) + 1})...")
            time.sleep(wait)
    raise RuntimeError(
        "Semua penulis naskah gagal setelah beberapa putaran (Gemini sibuk dan cadangan kena batas atau tidak tersedia). "
        "Coba lagi 10 sampai 30 menit lagi, atau isi CEREBRAS_API_KEY di .env sebagai cadangan tambahan. "
        f"Kesalahan terakhir: {last_error}"
    )


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


def enforce_loop(scenes):
    """Penutup yang mengulang kata-kata pembuka terdengar gagap saat video berputar. Kata ulangan di ujung dibuang."""
    try:
        first = scenes[0]["lines"][0]["text"].split()[:4]
        last_line = scenes[-1]["lines"][-1]
        norm = lambda ws: [w.strip(".,!?;:\"'").lower() for w in ws]
        words = last_line["text"].split()
        key = norm(first)
        for n in range(min(len(key), 4), 1, -1):
            if len(words) > n and norm(words[-n:]) == key[:n]:
                last_line["text"] = " ".join(words[:-n]).rstrip(" ,")
                scenes[-1]["narration"] = " ".join(l["text"] for l in scenes[-1]["lines"])
                break
    except Exception:
        pass


def validate_content(data):
    for key in ("title", "description", "tags", "scenes"):
        if key not in data:
            raise ValueError(f"JSON dari Gemini kekurangan kolom '{key}'.")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) < 3:
        raise ValueError("Jumlah adegan terlalu sedikit.")
    if not isinstance(data["tags"], list):
        data["tags"] = [str(data["tags"])]

    scenes = []
    for raw in data["scenes"][:10]:
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
        elif scene_type == "mechanism":
            items = [
                {"label": clean_text(it.get("label"), 24), "value": clean_text(it.get("value"), 40)}
                for it in (raw.get("items") or [])
                if isinstance(it, dict) and clean_text(it.get("label"), 24)
            ][:4]
            if len(items) < 2:
                scene_type, items = "flow", []
        elif scene_type == "question" and not points:
            scene_type = "flow"
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
        mechanism = str(raw.get("mechanism") or "").strip().lower()
        mood = str(raw.get("mood") or "").strip().lower()
        weather = str(raw.get("weather") or "").strip().lower()
        keywords = [clean_text(k, 30) for k in (raw.get("keywords") or []) if str(k).strip()][:3]
        art_raw = raw.get("art")
        if isinstance(art_raw, str):
            art_raw = [art_raw]
        art = [clean_text(a, 320) for a in (art_raw or []) if isinstance(a, str) and len(str(a).strip()) > 12][:2]
        subject = clean_text(str(raw.get("subject") or ""), 40).lower()
        sfx_raw = str(raw.get("sfx") or "").strip().lower()
        sim = None
        sim_generic = False
        if scene_type in ("mechanism", "cutaway"):
            labels_for_sim = [str(i.get("label") or "") for i in (items or []) if isinstance(i, dict)]
            sim = sim_presets.clean_sim(raw.get("sim"))
            if sim is None:
                guess = mechanism if mechanism in MECHANISMS else ""
                guess = guess or sim_presets.guess_preset(
                    " ".join([str(raw.get("title") or "")] + [str(ln.get("text") or "") for ln in (raw.get("lines") or []) if isinstance(ln, dict)] + [str(raw.get("narration") or "")]))
                spec = sim_presets.preset_sim(guess, labels_for_sim) if guess else None
                sim = sim_presets.clean_sim(spec) if spec else None
                if sim is None:
                    sim = sim_presets.clean_sim(sim_presets.generic_sim(labels_for_sim))
                    sim_generic = True
        if sim is None and scene_type != "footage":
            sim = sim_scenes.scene_sim({
                "type": scene_type, "title": clean_text(raw.get("title"), 40), "points": points, "items": items,
                "number": number, "unit": clean_text(raw.get("unit"), 40) or "", "weather": weather,
            })
        scenes.append({
            "sim": sim,
            "sim_generic": sim_generic,
            "sfx": sfx_raw if sfx_raw in KEY_SOUNDS else "",
            "art": art,
            "subject": subject,
            "variant": variant if variant in ("device", "ground") else "device",
            "mechanism": mechanism if mechanism in MECHANISMS else "",
            "mood": mood if mood in MOODS else "tegang",
            "weather": weather if weather in WEATHERS else "cerah",
            "keywords": keywords,
            "narration": narration,
            "lines": lines,
            "sound": sound if sound in AMBIENCES else ("mesin" if mechanism in ("katrol_lift", "roda_gigi", "piston", "roda_kerucut") else "air" if mechanism in ("aliran", "nozel_bensin") else "hening"),
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
    for scene in scenes:
        if scene["type"] == "footage" and not scene.get("footage_query"):
            scene["type"] = "mindmap" if len(scene["points"]) >= 2 else "flow"
    # cadangan: adegan tanpa kueri footage memakai kueri giliran bicara pertamanya yang punya kueri
    for scene in scenes:
        if not scene.get("footage_query"):
            scene["footage_query"] = next((l["footage_query"] for l in scene["lines"] if l.get("footage_query")), "")

    enforce_loop(scenes)
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
                for w in align_words(words, line["text"], line["speaker"] if DIALOG else "narator", scene.get("keywords") or ()):
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
        if scene["type"] != "footage":
            continue  # hanya adegan footage yang memakai rekaman asli; adegan lain memakai animasi sendiri
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


ART_TYPES = None  # semua jenis adegan selain footage boleh punya gambar AI


def fetch_art_images(scenes):
    """Beri tiap adegan visual yang sesuai isinya: model 3D gratis kalau ada (Poly Pizza), kalau tidak ada
    gambar kartun 3D buatan AI. Yang gagal tetap memakai animasi 3D bawaan. Mengembalikan daftar kredit model.
    Matikan gambar AI dengan ART=off dan model 3D dengan MODEL3D=off di .env."""
    credits = set()
    art_on = os.getenv("ART", "on").strip().lower() != "off"
    model_key = os.getenv("POLYPIZZA_KEY", "").strip() if os.getenv("MODEL3D", "on").strip().lower() != "off" else ""
    for name in os.listdir(PUBLIC_DIR):
        if re.fullmatch(r"art_\d+_\d+\.(png|jpg)", name):
            os.remove(os.path.join(PUBLIC_DIR, name))
    todo = [(i, sc) for i, sc in enumerate(scenes) if sc["type"] != "footage" or not sc.get("video")]
    data_types = ("counter", "barchart", "timeline", "compare", "gauge")  # angka tetap tampil sebagai 3D data
    todo = [(i, sc) for i, sc in todo if (sc.get("subject") or sc.get("art")) and sc["type"] not in data_types]
    if not todo:
        return credits
    key = GEMINI_KEY if GEMINI_KEY and GEMINI_KEY != "ISI_KEY_DI_SINI" else ""
    if not model_key:
        info("  -> POLYPIZZA_KEY belum diisi di .env: model 3D dilewati, dipakai gambar kartun 3D AI.")
    info("  -> Menyiapkan visual tiap adegan (model 3D / gambar kartun 3D), bisa beberapa menit...")
    n_model, n_art, failed = 0, 0, 0
    used = []
    seen_art = set()
    for i, sc in todo:
        if model_key and sc.get("subject"):
            path, credit = models3d.fetch_model(sc["subject"], PUBLIC_DIR, model_key, info)
            # model yang sama jangan dipakai berturutan atau lebih dari dua kali: pakai gambar kartun sebagai gantinya
            if path and (used.count(path) >= 2 or (used and used[-1] == path)):
                info(f"  -> Model '{sc['subject']}' sudah sering dipakai, adegan ini memakai gambar kartun 3D.")
                path = None
            if path:
                used.append(path)
                sc["model"] = path
                n_model += 1
                if credit:
                    credits.add(credit)
                continue
        if art_on and sc.get("art"):
            sig = sc["art"][0].lower()[:40]
            if sig in seen_art:  # deskripsi gambar kembar dengan adegan lain: pakai animasi 3D bawaan saja
                continue
            seen_art.add(sig)
            path = os.path.join(PUBLIC_DIR, f"art_{i}_0.jpg")
            if ai_art.make_image(sc["art"][0], path, key, info):
                sc["art_urls"] = [f"art_{i}_0.jpg"]
                n_art += 1
            else:
                failed += 1
            time.sleep(2)
    # adegan tanpa visual meminjam visual adegan lain (adegan terakhir meminjam adegan pertama supaya video berputar mulus)
    have = [sc for _, sc in todo if sc.get("model") or sc.get("art_urls")]
    if have:
        for i, sc in enumerate(scenes):
            if sc["type"] in data_types or sc.get("model") or sc.get("art_urls") or sc.get("video") or sc.get("sim"):
                continue  # adegan yang sudah punya animasi 3D sendiri tidak meminjam (supaya tidak ada gambar kembar)
            src = have[0] if i == len(scenes) - 1 else min(have, key=lambda h: abs(scenes.index(h) - i))
            for k in ("model", "art_urls"):
                if src.get(k):
                    sc[k] = src[k]
    info(f"  -> Visual: {n_model} model 3D, {n_art} gambar kartun 3D" + (f", {failed} gagal (diganti animasi 3D bawaan)." if failed else "."))
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


def generate_voice_gemini(scenes, wav_path):
    """Seluruh naskah dibacakan sekali oleh Gemini TTS, lalu waktu tiap kata dicari dari jeda napasnya."""
    import natural_voice as nv

    info("[2/5] Membuat suara narator natural (Gemini TTS)...")
    tokens, owners = [], []
    for i, sc in enumerate(scenes):
        for j, line in enumerate(sc["lines"]):
            toks = line["text"].split()
            tokens += toks
            owners += [(i, j)] * len(toks)
    script_text = " ".join(" ".join(l["text"] for l in sc["lines"]) for sc in scenes)

    audio, pauses = nv.make_voice(GEMINI_KEY, GEMINI_TTS_MODELS, GEMINI_VOICE, script_text, TTS_STYLE, log=info)
    audio_seconds = len(audio) / nv.SAMPLE_RATE
    times = nv.align_words(tokens, audio_seconds, pauses)

    words, pos = [], 0
    for i, sc in enumerate(scenes):
        for j, line in enumerate(sc["lines"]):
            n = len(line["text"].split())
            raw = [{"word": tokens[pos + k], "start": times[pos + k][0], "end": times[pos + k][1]} for k in range(n)]
            line["start"] = round(max(0.0, raw[0]["start"] - 0.05), 2)
            line["end"] = round(raw[-1]["end"] + 0.1, 2)
            who = line["speaker"] if DIALOG else "narator"
            words += align_words(raw, line["text"], who, sc.get("keywords") or ())
            pos += n

    duration = round(audio_seconds + 0.3, 2)  # akhir dibuat rapat supaya video berulang terasa menyambung
    for i, sc in enumerate(scenes):
        first = sc["lines"][0]["start"]
        sc["start"] = 0.0 if i == 0 else round(max(scenes[i - 1]["lines"][-1]["end"], first - 0.08), 2)
    for i, sc in enumerate(scenes):
        sc["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else duration
    nv.write_wav(wav_path, audio)
    return words, duration


async def generate_voices(scenes):
    """Pilih pembuat suara. Hasil: (kata-kata, durasi, nama file suara)."""
    for name in ("voice.mp3", "voice.wav"):
        path = os.path.join(PUBLIC_DIR, name)
        if os.path.exists(path):
            os.remove(path)
    if TTS_MODE != "edge" and GEMINI_KEY and GEMINI_KEY != "ISI_KEY_DI_SINI":
        try:
            words, duration = generate_voice_gemini(scenes, os.path.join(PUBLIC_DIR, "voice.wav"))
            info("  -> Suara: Gemini TTS")
            return words, duration, "voice.wav"
        except Exception as e:
            info(f"  -> Suara Gemini tidak bisa dipakai ({str(e)[:160]}). Memakai Edge-TTS sebagai cadangan.")
    words, duration = await generate_scene_voices(scenes, os.path.join(PUBLIC_DIR, "voice.mp3"))
    info("  -> Suara: Edge-TTS")
    return words, duration, "voice.mp3"


def render_remotion_video(words, scenes, duration, theme_index=0, music=None, bg_seed=0, audio_file="voice.mp3"):
    info("[4/5] Menjalankan Remotion (membuat video beranimasi)...")
    npm = shutil.which("npm")
    npx = shutil.which("npx")
    if not npm or not npx:
        raise RuntimeError("Node.js belum terpasang. Unduh dari https://nodejs.org lalu jalankan ulang.")

    # Pasang paket Remotion otomatis kalau belum ada
    if not os.path.isdir(os.path.join(REMOTION_DIR, "node_modules", "@remotion", "three")):
        info("  -> Pertama kali: memasang paket Remotion (butuh beberapa menit)...")
        run_command([npm, "install", "--no-audit", "--no-fund"], REMOTION_DIR)

    os.makedirs(OUT_DIR, exist_ok=True)
    output_mp4 = os.path.join(OUT_DIR, "shorts_final.mp4")
    if os.path.exists(output_mp4):
        os.remove(output_mp4)

    props = {
        "audioUrl": audio_file,
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
                "mechanism": s.get("mechanism", ""),
                "mood": s.get("mood", "tegang"),
                "weather": s.get("weather", "cerah"),
                **({"sfx": s["sfx"]} if s.get("sfx") else {}),
                **({"sim": s["sim"]} if s.get("sim") else {}),
                **({"video": s["video"], "videoSeconds": s.get("video_seconds") or 0} if s.get("video") else {}),
                **({"clips": s["clips"]} if s.get("clips") else {}),
                **({"artUrls": s["art_urls"]} if s.get("art_urls") else {}),
                **({"model": s["model"]} if s.get("model") else {}),
            }
            for s in scenes
        ],
        "words": words,
        "durationInSeconds": duration,
        "themeIndex": theme_index,
        "bgSeed": bg_seed,
        "sfxMap": pick_sfx_map(),
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
    has_sim = any(sc.get("sim") for sc in props["scenes"])
    if has_sim:
        cmd.append("--gl=" + (os.getenv("GL_MODE") or "angle"))  # animasi 3D butuh WebGL
    try:
        run_command(cmd, REMOTION_DIR)
    except Exception as e:
        if not has_sim:
            raise
        info(f"  -> Render dengan animasi 3D gagal ({str(e)[:100]}). Mengulang tanpa 3D (animasi 2D bawaan)...")
        for sc in props["scenes"]:
            sc.pop("sim", None)
            if sc.get("type") == "mechanism" and not sc.get("mechanism"):
                sc["type"] = "flow"
                sc["points"] = [str(i.get("label") or "") for i in (sc.get("items") or [])][:4] or sc.get("points") or ["Cara kerja"]
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        run_command([c for c in cmd if not c.startswith("--gl=")], REMOTION_DIR)

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
        props["layout"] = pick_thumb_layout()
        bg = render_thumb_background(scenes)
        if bg:
            props["bg"] = bg
        else:
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

    # #Shorts tidak diperlukan YouTube (video tegak pendek otomatis jadi Shorts) dan membuat judul terlihat seperti spam
    title = re.sub(r"\s*#shorts\b", "", content_data["title"], flags=re.I).strip()
    description = re.sub(r"\s*#shorts\b", "", content_data["description"], flags=re.I).strip()

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
        words, duration, audio_file = asyncio.run(generate_voices(data["scenes"]))
        info(f"  -> Durasi video: {duration} detik, {len(words)} kata")

        credits = fetch_stock_videos(data["scenes"])
        model_credits = fetch_art_images(data["scenes"])
        if credits:
            data["description"] += "\n\nVideo latar: " + ", ".join(sorted(credits))
        if model_credits:
            data["description"] += "\n\nModel 3D: " + "; ".join(sorted(model_credits))
        final_video = render_remotion_video(
            words, data["scenes"], duration, data["theme_index"], data.get("music"), data.get("bg_seed", 0), audio_file
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
