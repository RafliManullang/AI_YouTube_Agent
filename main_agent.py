"""
AI YouTube Agent
Alur kerja: naskah dan storyboard -> TTS dan waktu kata -> ilustrasi AI + jangkar Vision
-> koreografi Remotion -> unggah ke YouTube.

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
from pathlib import Path
from datetime import datetime, timedelta, timezone

import requests

import asset_generator
import pacing
import render_worker
import svg_composer

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

SESSION_PATH = Path(BASE_DIR) / "cache" / "last_session.json"

END_PAD = 1.5  # detik jeda setelah suara selesai (45 bingkai pada 30 fps)


def split_keys(*values):
    """Satu variabel .env boleh berisi beberapa key dipisah koma (kunci1,kunci2,kunci3). Hasil: daftar unik tanpa nilai kosong atau contoh."""
    out = []
    for v in values:
        for k in re.split(r"[,;\s]+", v or ""):
            k = k.strip().strip('"').strip("'")
            if k and k != "ISI_KEY_DI_SINI" and k not in out:
                out.append(k)
    return out


GEMINI_KEYS = split_keys(os.getenv("GEMINI_API_KEY"), os.getenv("GOOGLE_API_KEY"))
GEMINI_KEY = GEMINI_KEYS[0] if GEMINI_KEYS else ""  # key pertama dipakai untuk suara (TTS) dan pemeriksa visual
PEXELS_KEY = os.getenv("PEXELS_API_KEY") or ""  # opsional: video latar gratis dari Pexels
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY") or ""  # opsional: video latar gratis dari Pixabay
# Kalau model pertama tidak tersedia, agen otomatis mencoba yang berikutnya
GEMINI_MODELS = [
    m for m in [
        os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        "gemini-3.6-flash",
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
TOPIC_HINT = ""  # topik yang diminta pengguna; dipakai untuk mencocokkan animasi bawaan

SCENE_TYPES = ("flow", "mindmap", "counter", "timeline", "barchart", "compare", "gauge", "footage",
               "cutaway", "microscale", "story", "mechanism")
MECHANISMS = ("katrol_lift", "roda_gigi", "piston", "tuas", "aliran", "panas", "rangkaian", "tekanan",
              "nozel_bensin", "roda_kerucut", "eskalator", "kunci_silinder", "sprinkler", "venturi",
              "eddy_current", "jembatan", "airbag", "mesin_ice", "ball_socket", "capillary", "pressure_leak", "jangkar_rantai", "sosrobahu",
              "mobil_dongkrak", "jembatan_geser", "loop_induksi", "bimetal", "setrika", "aliran_listrik", "panas_berlebih")
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
             "riser", "beep", "screech", "chain", "swell", "creak")
KEY_SOUNDS = ("clank", "hiss", "zap", "thud", "sizzle", "bubble", "ding", "impact", "glitch", "riser", "bell",
              "chain", "swell", "creak")
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
MICRO_CAUSAL_RULE = (
    "KERANGKA WAJIB, ALUR SINEMATIK 4 BABAK (urut, tanpa selipan sejarah, nama penemu, tahun, atau fakta umum yang memutus gambar; "
    "semua kalimat membahas benda yang sedang tampil). Persen di bawah adalah bagian dari total durasi ucapan; tampilan layar berganti otomatis mengikuti urutan adegan:\n"
    "  BABAK 1, CONTEXT HOOK (adegan pertama saja, sekitar 0-12%, tampilan: wujud luar benda utuh di tempat aslinya): sebut benda apa ini dan di mana ia bekerja, "
    "lalu ajukan paradoks fisika (contoh: \"Benda sekecil kelingking ini menahan tekanan 2 ton tanpa baut pengunci.\"). Penonton langsung tahu bendanya.\n"
    "  BABAK 2, X-RAY DIVE-IN (1 sampai 2 adegan, sekitar 12-30%, tampilan: kamera menembus cangkang luar): jawab rasa penasaran \"apa isi di dalam benda ini\", "
    "perkenalkan MAKSIMAL 3 komponen inti yang saling bersentuhan, sebut satu per satu.\n"
    "  BABAK 3, CORE MECHANISM DAN TRIGGER (sekitar 30-90%, tampilan: bagian demi bagian di dalam mesin): jelaskan runtut, mulai dari kondisi normal "
    "(gaya tekanan, pegas, atau arus menahan komponen di posisinya), lalu satu pemicu dari luar dan rantai reaksinya: A mendorong B, B membuka celah C, "
    "fluida atau arus D mengalir. SETIAP kalimat wajib punya subjek berupa komponen fisik yang menggerakkan komponen lain. "
    "Boleh SATU perumpamaan benda sehari-hari: satu adegan tersendiri di babak ini yang kalimatnya diawali kata \"Ibarat\" (tampilannya berganti ke gambar perumpamaan).\n"
    "  BABAK 4, RESOLUTION DAN ZOOM-OUT (adegan terakhir saja, sekitar 90-100%, tampilan: kembali ke benda utuh): komponen kembali ke posisi semula, "
    "benda utuh menyelesaikan tugasnya, lalu kalimat pancingan penutup.\n"
    "Bagi 8 sampai 10 adegan ke dalam keempat babak itu sesuai urutan dan persentasenya. Dilarang membahas sejarah atau statistik di tengah penjelasan mekanis. "
    "Tulis semua angka dengan angka (290, 2 ton), bukan dengan huruf."
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
        cands = props.get("mechScenes") or []
        if not cands:
            return None
        sc = cands[min(2, len(cands) - 1)]
        frame = min(sc["endFrame"] - 1, sc["triggerFrame"] + 18)
        props["clean"] = True
        with open(os.path.join(REMOTION_DIR, "thumb_bg_props.json"), "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        cmd = [shutil.which("npx"), "remotion", "still", "src/index.ts", "ShortsComp", out,
               "--props=thumb_bg_props.json", f"--frame={frame}", "--image-format=jpeg", "--jpeg-quality=88"]
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
    STRUCTURE_RULE = MICRO_CAUSAL_RULE
    return f"""
Kamu adalah scriptwriter YouTube Shorts edukasi berbahasa Indonesia, gaya Kok Bisa / Veritasium.
{topic_rule}
{avoid}

Pecah video menjadi 8 sampai 10 ADEGAN berurutan. Setiap adegan punya ucapan dan visual beranimasi.
PANJANG NASKAH WAJIB antara 105 sampai 118 kata (maksimal mutlak 120 kata) agar durasi bicara tidak melebihi 55 detik dan kalimat
penutup tuntas sebelum video berakhir. Naskah padat, langsung ke inti, dan alurnya
runtut dari awal sampai akhir.
{style_rule}
HOOK 3 DETIK PERTAMA (paling penting): kalimat pertama WAJIB langsung menghentak, maksimal 12 kata, berupa
fakta mengejutkan, peringatan, atau premis yang memancing penasaran dan menyebut benda konkretnya (contoh:
"Di balik dinding lift ini ada balok besi seberat mobil. Kamu naik, dia turun. Buat apa?" atau "Jangan pernah
pakai kaca rumah untuk mobil, ini akibatnya!"). Visual adegan pertama sudah memperlihatkan benda itu di detik
ke-0. DILARANG membuka dengan sapaan (halo, hai, selamat datang), basa-basi,
"kali ini kita bahas", atau percakapan santai bernada datar. Kalimat pertama DILARANG diawali kata sambung (karena, dan, tapi, jadi, lalu,
makanya, soalnya, sebab): harus kalimat utuh yang bisa berdiri sendiri. Visual adegan pertama harus langsung
memperlihatkan inti masalahnya, bukan pemandangan umum.
NAMA BENDA WAJIB DI AWAL (supaya penonton awam langsung tahu benda apa yang dibahas dalam 1-2 detik pertama): salah satu dari
3-5 kata pertama kalimat pembuka WAJIB menyebut nama benda/alatnya secara konkret (contoh: "Di dalam mesin cuci piring...",
"Pentil ban motor itu...", "Saat kamu menekan tombol flush..."). DILARANG membuka dengan kalimat abstrak yang belum menyebut
bendanya ("Air panas meluncur di dalam mesin...", "Sesuatu bergerak cepat di balik logam...").
SATU ALAT, SATU ANATOMI (dilarang mencampur bagian dari dua alat berbeda yang mirip tapi beda fungsi): kalau topiknya mesin cuci
PIRING, komponennya rak piring, baling-baling semprot, pemanas air, filter saringan -- BUKAN drum berputar (itu milik mesin cuci
BAJU). Pastikan setiap nama komponen yang disebut benar-benar bagian asli dari benda yang sedang dibahas, bukan tertukar dari
benda sejenis yang berbeda.
DILARANG NARATOR MEMBACA ARAHAN KAMERA: kalimat narasi TIDAK BOLEH berisi kalimat yang menjelaskan apa yang dilakukan tampilan/
kamera itu sendiri, seperti "Kamera menembus...", "Visual menampilkan...", "Layar memperlihatkan...", "Mari kita lihat lebih
dekat...". Narator hanya boleh berbicara tentang BENDA dan KEJADIAN FISIKnya, bukan tentang gambar/videonya.
ALUR CERITA: ikuti KERANGKA WAJIB di bawah (rantai sebab-akibat mikro). Angka cukup satu atau dua yang paling mengejutkan, dan hanya
kalau angka itu menjelaskan gaya atau ukuran komponen yang sedang tampil, dengan perbandingan benda akrab ("seberat mobil").
Perumpamaan paling banyak satu adegan pendek berawalan "Ibarat", di babak 3. Jangan menyelipkan sejarah atau titik balik "Tapi tunggu".
PENUTUP MELINGKAR (seamless loop): kalimat terakhir adalah PERTANYAAN PANCINGAN pendek (maksimal 10 kata)
yang dijawab langsung oleh kalimat pembuka saat video berulang. JANGAN mengulang kata-kata pembuka di penutup
(pengulangan kata terdengar seperti gagap). Contoh: pembuka "Tiga pesawat hancur di udara gara-gara jendela
kotak." dan penutup "Jadi, apa jadinya kalau jendela pesawat berbentuk kotak?". Contoh lain: pembuka "Karena
di baliknya ada balok besi seberat mobil." dan penutup "Lalu kenapa lift tidak pernah jatuh?".
{STRUCTURE_RULE}

STORYBOARD HYBRID: rencanakan 3–4 ilustrasi berulang dari satu topik, tanpa kode atau teks di gambar.
assets: ID/view_type wajib 01_exterior/exterior, 02_analogy/analogy, 03_cutaway/cutaway; opsional 04_closeup/closeup.
Isi prompt singkat dalam bahasa Inggris, spesifik ke alat/perumpamaan dalam naskah. Cutaway wajib memperlihatkan
komponen fisik yang dibahas. Gunakan exterior di awal dan akhir, analogy untuk satu adegan "Ibarat", cutaway untuk
bedah inti dan closeup opsional di klimaks. Setiap scene: asset_id, component (nama bagian yang ditunjuk),
camera (fromScale/toScale 1..2.2, focusX/focusY 0..1), overlay (type flow_arrows/heat_pulse/badge_only,
direction up/down/left/right, targetX 0..1080, targetY 0..1920, label singkat, accentColor #rrggbb).
Isi items dengan 1–2 nama komponen nyata, type mechanism, trigger satu kata persis dari narasi untuk sinkronisasi aksi.
BUNYI MOMEN PUNCAK ("sfx"): hanya satu bunyi di momen puncak adegan, harus cocok dengan kejadiannya. Pilihan: "clank" (logam beradu),
"hiss" (desis udara), "zap" (listrik), "thud" (hantaman berat), "sizzle" (panas), "bubble" (cairan), "ding" (berhasil), "bell"
(momen sejarah), "impact" (kejutan), "chain" (rantai), "swell" (tekanan besar), "creak" (derit struktur). Kosongkan ("") kalau tidak
ada kejadian yang pas. Jangan memakai bunyi yang sama di dua adegan berturutan.
TEMPO PADAT: kalimat pendek, tanpa pengantar bertele-tele, tanpa pengulangan. Setiap kalimat membawa informasi baru. Adegan terakhir
penutup singkat yang bikin orang ingin menonton ulang. Ucapan hanya berisi kalimat yang diucapkan: tanpa instruksi panggung,
tanpa emoji, tanpa tanda bintang, tanpa hashtag.
LARANGAN KLISE: jangan memakai "Tapi tunggu", "bayangkan kamu", "rahasianya adalah", "inilah rahasia". Judul adegan spesifik
pada isi (contoh: "Gigi spider", bukan "Penjelasan"), maksimal 4 kata.
BAHASA LISAN NYATA, BUKAN KARANGAN PUITIS: tulis seperti bercerita ke teman, bukan seperti narasi dokumenter yang dibuat-buat. Boleh
pakai penghubung santai sesekali ("pernah perhatiin", "nah", "makanya", "jadi gini"). DILARANG KERAS kalimat puitis atau metafora yang
salah secara fisika/tidak masuk akal kalau dibayangkan sungguhan (contoh yang DILARANG: "desis halus yang menyejukkan aliran udara",
"tarian cahaya di balik roda gigi") -- setiap kalimat harus menjelaskan gerakan atau sebab-akibat yang benar-benar terjadi pada bendanya,
bukan menghias. Kalimat penutup DILARANG berupa ajakan menebak yang murahan ("coba tebak apa yang terjadi selanjutnya", "menurutmu apa
yang akan dipotong berikutnya") -- penutup harus pertanyaan pancingan yang jawabannya adalah kalimat pembuka (lihat PENUTUP MELINGKAR).
DILARANG KERAS kalimat pancingan komentar murahan di penutup ("menurutmu kenapa?", "tulis di komentar", "komen di bawah") --
pertanyaan pancingan PENUTUP MELINGKAR sudah cukup sebagai penutup, jangan ditambah ajakan komentar generik.
"keywords" berisi 1 sampai 3 kata kunci terpenting dari ucapan adegan itu, ditulis persis seperti yang diucapkan.
"sound" adalah suara latar adegan, pilih satu: "angin", "gesekan", "benturan", "mesin", "air", atau "hening".
"music" adalah musik latar seluruh video: "misterius", "semangat", atau "tenang".
"tone" adalah gaya suara narator pada adegan itu: "semangat", "santai", "misterius", atau "tegas". Variasikan.
"category" salah satu dari: "CARA KERJA", "FAKTA SAINS", "KISAH NYATA".
"thumbnail_text" adalah 2 sampai 4 kata huruf besar yang memancing penasaran, boleh diakhiri tanda tanya, tanpa emoji.

LATAR DAN LAPISAN LAYAR:
"environment" pilih SATU sesuai tempat benda bekerja: "outdoor_motion" (kendaraan, transportasi, aerodinamika), "domestic_room" (alat rumah
tangga, elektronik rumah, korek, setrika, AC, regulator, detektor), "industrial_pipe" (pompa, katup air, konstruksi, bendungan, listrik),
"micro_circuit" (chip, sensor, baterai, sinyal, gelombang), "anatomical_fluid" (medis, tubuh manusia, biologi, kimia), "deep_pressure"
(kapal selam, hidrolik berat, antariksa).
"hook_question" adalah kalimat tanya pendek 3 sampai 6 kata yang tampil besar di layar selama 12 detik pertama (contoh "Kok bisa mati sendiri?",
"Apa yang menahan?"), senada dengan kalimat pembuka. "hook_highlight" berisi 1 sampai 2 kata dari kalimat tanya itu yang diberi warna.
"claim" adalah SATU klaim fisik berangka yang DIUCAPKAN di naskah beserta lembaga sumbernya, contoh {{"source": "SAE", "text": "±290 km/jam"}}.
Isi hanya kalau kamu YAKIN angka dan sumbernya benar (lembaga nyata seperti SAE, IEEE, BSN, FAA, NASA, WHO). Kalau ragu, kosongkan
keduanya. Dilarang mengarang sumber.
Per adegan (boleh kosong): "load" adalah beban atau tekanan yang ditahan komponen dan diucapkan di adegan itu (contoh "2 TON"); "force" adalah
label panah gaya (contoh "4x tekanan") kalau adegan itu membahas kenaikan tekanan, suhu, kecepatan, atau tegangan. Kosongkan kalau
angkanya tidak diucapkan di adegan itu.

Keluarkan HANYA JSON murni dengan format persis ini:
{{
  "title": "Judul menarik maksimal 60 karakter",
  "description": "Deskripsi singkat 2-3 kalimat. Lalu 2 sampai 3 hashtag topik (contoh #Sains #CaraKerja). JANGAN pakai #Shorts.",
  "tags": ["sains", "teknologi", "carakerja", "shorts", "edukasi"],
  "category": "CARA KERJA",
  "thumbnail_text": "KOK BISA JATUH?",
  "music": "misterius",
  "environment": "domestic_room",
  "hook_question": "Kok bisa mati sendiri?",
  "hook_highlight": "mati sendiri",
  "claim": {{"source": "", "text": ""}},
  "assets": [{{"id":"01_exterior","view_type":"exterior","prompt":"subject in its environment"}},
             {{"id":"02_analogy","view_type":"analogy","prompt":"everyday analogy"}},
             {{"id":"03_cutaway","view_type":"cutaway","prompt":"cross-section and named internal parts"}}],
  "scenes": [
    {{
      "asset_id":"01_exterior", "component":"nama bagian",
      "camera":{{"fromScale":1,"toScale":1.18,"focusX":0.5,"focusY":0.5}},
      "overlay":{{"type":"badge_only","label":"BENDA UTUH"}},
      "lines": [{{"speaker": "flay", "text": "Kalimat yang diucapkan."}}],
      "title": "Judul adegan",
      "type": "mechanism",
      "tone": "semangat",
      "items": [{{"label": "bagian benda", "value": ""}}],
      "keywords": ["kata kunci"],
      "trigger": "kata",
      "sound": "mesin",
      "sfx": "clank",
      "load": "",
      "force": ""
    }}
  ]
}}
"""


GROQ_KEYS = split_keys(os.getenv("GROQ_API_KEY"))
CEREBRAS_KEYS = split_keys(os.getenv("CEREBRAS_API_KEY"))
# Penyedia cadangan (gratis) yang memakai format OpenAI: (nama, alamat, key, daftar model)
BACKUP_PROVIDERS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions", GROQ_KEYS,
     [m for m in [os.getenv("GROQ_MODEL"), "openai/gpt-oss-120b", "openai/gpt-oss-20b"] if m]),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions", CEREBRAS_KEYS,
     [m for m in [os.getenv("CEREBRAS_MODEL"), "gpt-oss-120b", "llama-3.3-70b", "qwen-3-32b", "llama3.1-8b"] if m]),
]


def call_openai_style(url, key, model, prompt, raw=False):
    """Panggil penyedia berformat OpenAI (Groq, Cerebras) dan kembalikan teks jawabannya."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Kamu menjawab HANYA dengan kode yang diminta, tanpa penjelasan." if raw else "Kamu menjawab HANYA dengan satu objek JSON yang valid, tanpa teks lain."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6 if raw else 0.9,
        "max_tokens": 3500 if url.startswith("https://api.groq.com/") else (16000 if raw else 8192),
    }
    if not raw:
        body["response_format"] = {"type": "json_object"}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"  # model penalaran jangan menghabiskan jatah token untuk berpikir
    res = requests.post(url, headers=headers, json=body, timeout=240 if raw else 120)
    if res.status_code == 400 and "response_format" in res.text:
        body.pop("response_format")  # model ini tidak mendukung mode JSON
        res = requests.post(url, headers=headers, json=body, timeout=120)
    if res.status_code == 400 and "reasoning_effort" in res.text:
        body.pop("reasoning_effort")
        res = requests.post(url, headers=headers, json=body, timeout=120)
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code} {res.text[:200]}")
    return res.json()["choices"][0]["message"]["content"]


_MODEL_CACHE = {}
_SKIP_LOGGED = set()


def available_models(url, key):
    """Daftar model yang benar-benar bisa dipakai key ini (kosong kalau gagal ditanyakan). Hasil disimpan supaya tidak ditanyakan berulang."""
    if (url, key) in _MODEL_CACHE:
        return _MODEL_CACHE[(url, key)]
    _MODEL_CACHE[(url, key)] = got = _fetch_models(url, key)
    return got


def _fetch_models(url, key):
    try:
        res = requests.get(url.rsplit("/chat/completions", 1)[0] + "/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if res.status_code == 200:
            return {x.get("id") for x in res.json().get("data", []) if x.get("id")}
    except Exception:
        pass
    return set()


_WAIT_PATTERNS = (
    r"try again in\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)\s*s",
    r"retry in\s*(\d+(?:\.\d+)?)\s*s",
    r"retryDelay['\\\" :]*(\d+(?:\.\d+)?)s",
)
_BUSY_MARKS = ("429", "503", "504", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE", "overloaded", "timed out", "Timeout", "rate limit")
_FATAL_MARKS = ("404", "NOT_FOUND", "401", "403", "413", "invalid_api_key", "model_not_found")
_COOLDOWN = {}  # nama sumber -> waktu (time.time) sampai boleh dicoba lagi


def parse_wait_seconds(message):
    """Baca 'try again in 7.5s' / 'retry in 12s' / '1m3.2s' dari pesan galat. None kalau tidak ada."""
    msg = str(message or "")
    for pat in _WAIT_PATTERNS:
        m = re.search(pat, msg, re.I)
        if m:
            nums = [x for x in m.groups() if x]
            try:
                if len(nums) == 2:
                    return float(nums[0]) * 60 + float(nums[1])
                return float(nums[0])
            except ValueError:
                pass
    return None


def unavailable(exc):
    status = getattr(exc, "code", None)
    if status is not None:
        return str(status) == "503"
    return bool(re.match(r"(?:503\b|UNAVAILABLE\b)", str(exc), re.I))


def call_llm_with_smart_wait(name, fn, tries=3, log=None, rotate_on_503=False):
    """Panggil satu sumber LLM dengan jeda cerdas:
    - 404 / key salah / 413 (terlalu besar): langsung dilempar, jangan diulang.
    - 429: kalau server bilang cukup tunggu <= 25 detik, tunggu sebentar lalu ulang; kalau lebih lama, langsung pindah sumber lain
      (key berikutnya) dan sumber ini diistirahatkan sampai waktunya.
    - 503 / 504 / timeout: tunggu sesuai petunjuk server, kalau tidak ada 10 detik x (percobaan + 1), lalu ulang."""
    log = log or info
    until = _COOLDOWN.get(name, 0)
    if until > time.time():
        raise RuntimeError(f"429 {name} masih istirahat {int(until - time.time())} detik")
    last = None
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            if rotate_on_503 and unavailable(e):
                raise  # coba key berikutnya tanpa menunggu di key yang sama
            last = e
            msg = str(e)
            if any(x in msg for x in _FATAL_MARKS) and "429" not in msg:
                raise
            busy = any(x in msg for x in _BUSY_MARKS)
            if not busy:
                raise
            hint = parse_wait_seconds(msg)
            is_quota = "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate limit" in msg.lower()
            if is_quota and (hint is None or hint > 25):
                _COOLDOWN[name] = time.time() + (hint if hint else 60)
                raise
            if attempt >= tries - 1:
                raise
            wait = (hint + 1.5) if hint is not None else 10 * (attempt + 1)
            wait = min(wait, 40)
            log(f"     {name} sibuk, menunggu {wait:.0f} detik lalu mencoba lagi ({attempt + 2}/{tries})...")
            time.sleep(wait)
    raise last


class CanvasSources:
    """Daftar yang bisa diulang untuk revisi, tetapi tidak menawarkan key model yang sudah sibuk."""
    def __init__(self, sources, blocked):
        self.sources = sources
        self.blocked = blocked

    def __iter__(self):
        for name, call in self.sources:
            if name.partition(" #")[0] not in self.blocked:
                yield name, call


def llm_callers(raw=False):
    """Bangun klien sekali; breaker dibagi semua key/putaran per sesi kanvas."""
    gem = []
    blocked = set()
    if GEMINI_KEYS:
        from google import genai
        from google.genai import types

        options = types.HttpOptions(timeout=240000 if raw else 120000)
        if raw:
            options.retry_options = types.HttpRetryOptions(attempts=1)
        clients = [genai.Client(api_key=k, http_options=options) for k in GEMINI_KEYS]
        last_busy_key = {}

        def gemini_call(prompt, model, index, config, name):
            try:
                text = call_llm_with_smart_wait(name, lambda: clients[index].models.generate_content(
                    model=model, contents=prompt, config=config).text, rotate_on_503=raw)
            except Exception as exc:
                if raw and unavailable(exc):
                    if model in last_busy_key and last_busy_key[model] != index:
                        blocked.add(f"Gemini {model}")
                        info(f"  -> {model}: dua key berturut-turut 503; lewati model selama sesi kanvas.")
                    last_busy_key[model] = index
                else:
                    last_busy_key.pop(model, None)
                raise
            last_busy_key.pop(model, None)
            return text

        for model in dict.fromkeys(GEMINI_MODELS):
            params = {"temperature": 0.6 if raw else 1.0}
            if not raw:
                params["response_mime_type"] = "application/json"
            elif model.startswith("gemini-3") and "flash" in model:
                params["thinking_config"] = types.ThinkingConfig(thinking_level="LOW")
            elif model.startswith("gemini-2.5-flash"):
                params["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            config = types.GenerateContentConfig(**params)
            for ki in range(len(clients)):
                tag = f" #{ki + 1}" if len(clients) > 1 else ""
                name = f"Gemini {model}{tag}"
                gem.append((name, lambda p, m=model, i=ki, cfg=config, n=name: gemini_call(p, m, i, cfg, n)))
    backups = []
    providers = list(BACKUP_PROVIDERS)
    if raw:
        providers.append(("OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
                          split_keys(os.getenv("OPENROUTER_API_KEY")),
                          [os.getenv("OPENROUTER_MODEL") or "openrouter/free"]))
    for name, url, keys, models in providers:
        if not keys:
            continue
        have = available_models(url, keys[0]) if name != "OpenRouter" else set()
        if have:
            usable = [x for x in models if x in have]
            if not usable:
                usable = [x for x in sorted(have) if any(w in x for w in ("gpt-oss", "llama", "qwen"))
                          and not any(w in x for w in ("guard", "whisper", "tts", "embed", "prompt"))][:3]
            skipped = [x for x in models if x not in usable]
            if skipped and (name, tuple(skipped)) not in _SKIP_LOGGED:
                _SKIP_LOGGED.add((name, tuple(skipped)))
                info(f"  -> {name}: model {', '.join(skipped)} tidak tersedia untuk key ini, dilewati.")
            models = usable
        for model_name in dict.fromkeys(models):
            for ki, key in enumerate(keys):
                tag = f" #{ki + 1}" if len(keys) > 1 else ""
                source = f"{name} {model_name}{tag}"
                backups.append((
                    source, lambda p, u=url, k=key, mn=model_name, n=source: call_llm_with_smart_wait(
                        n, lambda: call_openai_style(u, k, mn, p, raw)),
                ))
    ordered = (gem + backups) if (raw or os.getenv("TEXT_FIRST", "groq").strip().lower() == "gemini") else (backups + gem)
    return CanvasSources(ordered, blocked) if raw else ordered


def build_text_sources(prompt, raw=False):
    return [(n, lambda f=f: f(prompt)) for n, f in llm_callers(raw)]


GREETINGS = ("halo", "hai", "hay", "selamat datang", "kali ini", "hari ini kita", "apa kabar", "teman-teman")
HYBRID_SCENE_KEYS = ("asset_id", "component", "camera", "overlay")
DRAFT_SCENE_KEYS = HYBRID_SCENE_KEYS + ("lines", "title", "type", "tone", "points", "items", "number", "unit", "footage_query",
                    "keywords", "variant", "mood", "weather", "sound", "mechanism", "sfx", "sim", "art", "subject", "photo", "trigger", "load", "force")


def polish_script(data, base_prompt):
    """Putaran editor: naskah pertama ditulis ulang oleh editor supaya hook lebih kuat, ada titik balik,
    angka yang mudah dibayangkan, dan faktanya dicek. Kalau gagal, naskah pertama dipakai apa adanya."""
    if os.getenv("EDITOR", "on").strip().lower() == "off":
        return data
    info("  -> Editor sedang menyempurnakan naskah (hook, titik balik, angka, cek fakta)...")
    draft = {k: data[k] for k in ("assets", "title", "description", "tags", "category", "thumbnail_text", "music", "environment", "hook_question", "hook_highlight", "claim") if k in data}
    draft["scenes"] = [{k: sc[k] for k in DRAFT_SCENE_KEYS if k in sc} for sc in data["scenes"]]
    editor_prompt = (
        "===== TUGAS KAMU: EDITOR NASKAH VIDEO SHORTS BAHASA INDONESIA =====\n"
        "Pertahankan daftar assets dan koreografi hybrid tiap adegan; cocokkan component dengan bagian yang diucapkan. "
        "kiasan jangan diterjemahkan harfiah; tipe \"footage\" tidak dipakai; kosongkan \"art\" dan \"photo\".\n"
        "Di bawah ini ada DRAF naskah. Kamu editor video viral yang sangat kritis. Tulis ulang "
        "draf itu menjadi versi yang jauh lebih menarik, dengan TOPIK YANG SAMA dan FORMAT JSON YANG SAMA PERSIS "
        "seperti DRAF (semua kolom tiap adegan tetap ada; jumlah adegan 8 sampai 10, total ucapan 105 sampai 118 kata, maksimal mutlak 120).\n"
        "Periksa dan perbaiki satu per satu:\n"
        "1. Hook: apakah 3 detik pertama membuat orang berhenti scroll? Kalau datar, ganti dengan fakta "
        "mengejutkan atau peringatan yang lebih tajam. Tanpa sapaan.\n"
        "2. Rasa penasaran: apakah ada pertanyaan yang baru terjawab di akhir? Pastikan jawaban tidak bocor di awal.\n"
        "3. Titik balik di tengah video yang berlawanan dengan dugaan penonton.\n"
        "4. Paling banyak 3 angka di seluruh ucapan (satu angka per kalimat, tidak berdekatan). Kalau lebih, buang yang kurang penting dan ganti dengan perbandingan benda akrab. Jangan menumpuk istilah teknik.\n"
        "5. Hapus kalimat pengisi; setiap kalimat harus membawa informasi baru. Total ucapan 105 sampai 118 kata (maksimal mutlak 120), tanpa dialog dua orang.\n"
        "6. CEK FAKTA: perbaiki atau hapus klaim yang tidak pasti benar. Jangan mengarang angka; kalau ragu "
        "pakai \"sekitar\" atau buang klaimnya.\n"
        "7. Obrolan Shela dan Flay terdengar natural dan lucu-ringan, bukan membaca teks.\n"
        "8. Penutup menyambung ke hook atau mengajak penonton berkomentar.\n"
        "9. Pilih tipe adegan dan keywords yang paling pas untuk tiap kalimat. Ganti kartu teks "
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
            if not (6 <= len(better["scenes"]) <= 10 and 90 <= words <= 135):
                raise ValueError(f"hasil editor tidak wajar ({len(better['scenes'])} adegan, {words} kata)")
            if any(first.startswith(g) for g in GREETINGS):
                raise ValueError("hasil editor masih dibuka dengan sapaan")
            info(f"  -> Naskah disempurnakan oleh editor ({name})")
            return better
        except Exception as e:
            message = str(e)
            if any(x in message for x in ("404", "NOT_FOUND", "401", "403", "413", "invalid_api_key", "model_not_found")):
                dead.add(name)
            info(f"  -> Editor ({name}) dilewati: {message[:100]}")
    if os.getenv("ALLOW_UNEDITED", "off").strip().lower() == "on":
        info("  -> Tahap editor tidak berhasil, memakai naskah pertama (ALLOW_UNEDITED=on).")
        return data
    raise RuntimeError("Tahap Editor tidak berhasil di semua sumber. Video tidak dirender dengan naskah mentah; mengulang dengan sumber lain.")


def research_and_write(forced_topic=None):
    global TOPIC_HINT
    TOPIC_HINT = forced_topic or ""
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
                    return polish_script(data, prompt)
                except Exception as e:
                    last_error = e
                    message = str(e)
                    if any(x in message for x in ("404", "NOT_FOUND", "401", "403", "413", "invalid_api_key", "model_not_found")):
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


def fix_opener(scenes):
    """Kalimat pertama tidak boleh diawali kata sambung (terdengar menggantung saat video dibuka)."""
    try:
        line = scenes[0]["lines"][0]
        words = line["text"].split()
        if len(words) > 3 and words[0].strip(",.").lower() in ("karena", "dan", "tapi", "jadi", "lalu", "makanya", "soalnya", "sebab"):
            rest = " ".join(words[1:])
            line["text"] = rest[0].upper() + rest[1:]
            scenes[0]["narration"] = " ".join(l["text"] for l in scenes[0]["lines"])
    except Exception:
        pass


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


ENV_TYPES = ("outdoor_motion", "domestic_room", "industrial_pipe", "micro_circuit", "anatomical_fluid", "deep_pressure")
ENV_HINTS = {
    "outdoor_motion": ("mobil", "motor", "kendaraan", "pesawat", "roda", "rem ", "jalan", "kereta", "ban ", "aerodinamika", "sayap", "kapal", "sepeda", "jembatan"),
    "domestic_room": ("setrika", "korek", "regulator", "gas", "ac ", "kulkas", "kompor", "detektor", "rumah", "dapur", "pentil", "kunci", "lampu", "toilet", "kipas", "mesin cuci", "printer", "struk", "kasir", "kertas", "fotokopi", "mesin jahit", "jam", "gunting"),
    "industrial_pipe": ("pompa", "katup", "pipa", "bendungan", "konstruksi", "turbin", "pabrik", "crane", "lift", "bor", "gergaji mesin", "rumput", "kabel listrik"),
    "micro_circuit": ("chip", "sensor", "baterai", "sinyal", "gelombang", "prosesor", "transistor", "wifi", "layar", "kamera", "ponsel", "laser", "magnet"),
    "anatomical_fluid": ("tubuh", "jantung", "darah", "otot", "medis", "sel ", "paru", "mata", "otak", "tulang", "kimia", "vaksin", "obat"),
    "deep_pressure": ("kapal selam", "hidrolik", "antariksa", "roket", "vakum", "laut", "selam", "tekanan tinggi", "satelit", "dalam air"),
}


def _numbers_in(label, narration):
    """Angka pada label HUD harus benar-benar diucapkan di naskah; kalau ada angka yang tidak muncul, label dibuang."""
    nums = re.findall(r"\d+(?:[.,]\d+)?", label or "")
    return all(n in narration for n in nums) if nums else True


def pick_environment(raw, text):
    raw = str(raw or "").strip().lower()
    if raw in ENV_TYPES:
        return raw
    low = " " + text.lower() + " "
    scores = {k: sum(low.count(w) for w in ws) for k, ws in ENV_HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "domestic_room"  # default netral; industrial_pipe dulu sering salah muncul di topik non-pipa


def finish_screen_fields(data):
    """Rapikan environment, kalimat tanya pembuka, dan klaim berangka. Klaim hanya dipakai kalau angkanya memang diucapkan di naskah."""
    script = data["full_script"]
    data["environment"] = pick_environment(data.get("environment"), data["title"] + " " + script)
    q = clean_text(data.get("hook_question"), 60)
    if len(q.split()) > 7:  # terlalu panjang untuk judul besar di layar: pakai teks thumbnail
        q = ""
    if not q:
        t = str(data.get("thumbnail_text") or "").strip()
        q = t.capitalize() if t.endswith("?") else ""
    if q:
        q = " ".join(q.split()[:7]).rstrip(" .!")
        if not q.endswith("?"):
            q += "?"
    data["hook_question"] = q
    qwords = {re.sub(r"[^a-z0-9]", "", w.lower()) for w in q.split()}
    hl = [w for w in clean_text(data.get("hook_highlight"), 40).split() if re.sub(r"[^a-z0-9]", "", w.lower()) in qwords]
    data["hook_highlight"] = " ".join(hl[:2])
    cl = data.get("claim") if isinstance(data.get("claim"), dict) else {}
    source, text = clean_text(cl.get("source"), 30), clean_text(cl.get("text"), 24)
    spoken = script.replace(",", ".")
    nums = re.findall(r"\d+(?:[.,]\d+)?", text)
    ok = bool(source and text and nums and all(n.replace(",", ".") in spoken for n in nums))
    data["claim"] = {"source": source, "text": text} if ok else {"source": "", "text": ""}


def validate_content(data):
    data["assets"] = asset_generator.validate_assets(data.get("assets"))
    for key in ("title", "description", "tags", "scenes"):
        if key not in data:
            raise ValueError(f"JSON dari Gemini kekurangan kolom '{key}'.")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) < 3:
        raise ValueError("Jumlah adegan terlalu sedikit.")
    if not isinstance(data["tags"], list):
        data["tags"] = [str(data["tags"])]

    spoken = 0
    for raw in data["scenes"][:10]:
        for ln in (raw.get("lines") or []) if isinstance(raw, dict) else []:
            spoken += len(str((ln or {}).get("text", "")).split()) if isinstance(ln, dict) else 0
    if spoken > 135:
        raise ValueError(f"Naskah terlalu panjang ({spoken} kata); batas 120 kata supaya kalimat terakhir tidak terpotong.")

    scenes = []
    for raw in data["scenes"][:10]:
        lines = clean_lines(raw)
        narration = " ".join(l["text"] for l in lines)
        if len(narration.split()) < 4:
            continue
        items = [
            {"label": clean_text(it.get("label"), 24), "value": ""}
            for it in (raw.get("items") or [])
            if isinstance(it, dict) and clean_text(it.get("label"), 24)
        ][:2]
        title = clean_text(raw.get("title"), 40) or "Tahukah kamu"
        tone = raw.get("tone") if raw.get("tone") in TONES else None
        sound = str(raw.get("sound") or "").strip().lower()
        keywords = [clean_text(k, 30) for k in (raw.get("keywords") or []) if str(k).strip()][:3]
        sfx_raw = str(raw.get("sfx") or "").strip().lower()
        load = clean_text(raw.get("load"), 18).upper()
        force = clean_text(raw.get("force"), 24)
        if not _numbers_in(load, narration):
            load = ""
        if not _numbers_in(force, narration):
            force = ""
        scenes.append({
            **{k: raw[k] for k in HYBRID_SCENE_KEYS if k in raw},
            "load": load,
            "force": force,
            "sfx": sfx_raw if sfx_raw in KEY_SOUNDS else "",
            "trigger": clean_text(raw.get("trigger"), 30).lower(),
            "keywords": keywords,
            "narration": narration,
            "lines": lines,
            "sound": sound if sound in AMBIENCES else "hening",
            "title": title,
            "type": "mechanism",
            "tone": tone,
            "points": [i["label"] for i in items] or [title],
            "items": items,
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

    fix_opener(scenes)
    enforce_loop(scenes)
    data["scenes"] = scenes
    data["full_script"] = " ".join(s["narration"] for s in scenes)
    if len(data["full_script"].split()) < 20:
        raise ValueError("Naskah terlalu pendek.")
    data["title"] = clean_text(data["title"], 80)
    finish_screen_fields(data)

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

    duration = round(offset + END_PAD, 2)  # jeda di akhir supaya kalimat terakhir tidak terpotong
    for i, scene in enumerate(scenes):
        scene["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else duration
    return all_words, duration


# ========================================================
# 4. VIDEO LATAR GRATIS (PEXELS, OPSIONAL)
# ========================================================
def run_command(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def trim_voice_tail(audio, rate, keep=0.22, fade=0.12):
    """Buang hening panjang di ujung suara (supaya video berulang menyambung rapat) dan beri fade halus
    di ujung terakhir supaya kata penutup tidak terdengar terpotong."""
    try:
        import numpy as np
        a = np.asarray(audio)
        floor = 0.02 * max(1e-9, float(np.max(np.abs(a))))
        loud = np.nonzero(np.abs(a.astype("float32")) > floor)[0]
        if len(loud) == 0:
            return audio
        end = min(len(a), int(loud[-1]) + int(keep * rate))
        out = a[:end].astype("float32").copy()
        n = min(len(out), int(fade * rate))
        out[-n:] *= np.linspace(1.0, 0.0, n)
        return out.astype(a.dtype)
    except Exception:
        return audio


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
    audio = trim_voice_tail(audio, nv.SAMPLE_RATE)
    audio_seconds = len(audio) / nv.SAMPLE_RATE
    pauses = [p for p in pauses if (p[0] if isinstance(p, (tuple, list)) else p) < audio_seconds]
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

    duration = round(audio_seconds + END_PAD, 2)  # jeda di akhir supaya kalimat terakhir tidak terpotong
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


def vision_caller():
    """Fungsi (prompt, [png]) -> teks memakai Gemini penglihat; None kalau tidak ada kunci Gemini (pemeriksaan visual dilewati)."""
    if not GEMINI_KEY or GEMINI_KEY == "ISI_KEY_DI_SINI":
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None
    client = genai.Client(api_key=GEMINI_KEY)

    def call(prompt, images):
        parts = [types.Part.from_bytes(data=b, mime_type="image/png") for b in images] + [prompt]
        config = types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json",
                                             http_options=types.HttpOptions(timeout=90000))
        last = None
        for model_name in dict.fromkeys(filter(None, [os.getenv("VISION_MODEL"), *GEMINI_MODELS, "gemini-2.5-flash"])):
            try:
                return client.models.generate_content(model=model_name, contents=parts, config=config).text
            except Exception as e:  # coba model berikutnya
                last = e
        raise RuntimeError(str(last)[:120] if last else "tidak ada model Gemini")
    return call


def _norm_word(w):
    return re.sub(r"[^a-z0-9]", "", str(w or "").lower())


def render_timings(scenes, words, duration):
    timings = svg_composer.build_timings(scenes, words)
    timings[0]["startFrame"] = 0
    timings[-1]["endFrame"] = max(timings[-1]["endFrame"], int(round(float(duration) * 30)))
    return timings


def render_remotion_video(words, scenes, duration, theme_index=0, music=None, bg_seed=0, audio_file="voice.mp3", screen=None, timings=None, *, hybrid):
    info("[4/5] Menjalankan Remotion (membuat video beranimasi)...")
    npm = shutil.which("npm")
    npx = shutil.which("npx")
    if not npm or not npx:
        raise RuntimeError("Node.js belum terpasang. Unduh dari https://nodejs.org lalu jalankan ulang.")

    # Pasang paket Node yang belum ada (termasuk paket baru setelah git pull)
    render_worker.ensure_deps(REMOTION_DIR, info)

    os.makedirs(OUT_DIR, exist_ok=True)
    output_mp4 = os.path.join(OUT_DIR, "shorts_final.mp4")
    if os.path.exists(output_mp4):
        os.remove(output_mp4)

    props = {
        "audioUrl": audio_file,
        "scenes": [
            {
                "type": "mechanism",
                "title": s["title"],
                "points": s["points"],
                "items": s.get("items") or [],
                "start": s["start"],
                "end": s["end"],
                "sound": s.get("sound", "hening"),
                **({"sfx": s["sfx"]} if s.get("sfx") else {}),
            }
            for s in scenes
        ],
        "words": words,
        "durationInSeconds": duration,
        "themeIndex": theme_index,
        "bgSeed": bg_seed,
        "environmentType": (screen or {}).get("environment") or "domestic_room",
        "hookQuestion": (screen or {}).get("hook_question") or "",
        "hookHighlight": (screen or {}).get("hook_highlight") or "",
        **({"claim": screen["claim"]} if (screen or {}).get("claim", {}).get("text") else {}),
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

    props["mechScenes"] = timings or render_timings(scenes, words, duration)
    props["hybrid"] = hybrid

    # Semua data wajib lolos skema Zod, lalu render berjalan dengan pemulihan otomatis (render_worker.py)
    render_worker.render(props, output_mp4, REMOTION_DIR, None, info)

    if not os.path.exists(output_mp4) or os.path.getsize(output_mp4) < 10_000:
        raise RuntimeError("Video hasil render tidak ditemukan atau rusak.")
    normalize_loudness(output_mp4)
    return output_mp4


def normalize_loudness(path):
    """Samakan keras suara video ke standar YouTube (sekitar -14 LUFS) supaya tidak terdengar pelan.
    Kalau gagal, video asli tetap dipakai. Matikan dengan LOUDNORM=off di .env."""
    if os.getenv("LOUDNORM", "on").strip().lower() == "off":
        return
    tmp = path + ".norm.mp4"
    prefix = ffmpeg_prefix()
    if not prefix:
        return
    try:
        cmd = prefix + ["-y", "-i", path, "-c:v", "copy", "-af", "loudnorm=I=-13:TP=-1.5:LRA=9",
                                 "-c:a", "aac", "-b:a", "192k", "-ar", "44100", tmp]
        subprocess.run(cmd, check=True, capture_output=True, cwd=REMOTION_DIR)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 10_000:
            os.replace(tmp, path)
            info("  -> Keras suara disamakan ke standar YouTube.")
    except Exception as e:
        info(f"  -> Penyamaan keras suara dilewati ({str(e)[:60]}).")
        if os.path.exists(tmp):
            os.remove(tmp)


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
def save_session(session):
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    pending = SESSION_PATH.with_suffix(".tmp")
    with pending.open("w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False)
    pending.replace(SESSION_PATH)


def prepare_session(resume, topic):
    if resume:
        try:
            session = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            data = session["data"]
            if session["version"] != 1 or not data["scenes"]:
                raise ValueError("format tidak sesuai")
            if "voice" in session:
                voice = session["voice"]
                if (voice["audio_file"] not in ("voice.mp3", "voice.wav") or not voice["words"]
                        or voice["duration"] <= 0 or len(voice["timings"]) != len(data["scenes"])):
                    raise ValueError("data TTS tidak lengkap")
                if (Path(PUBLIC_DIR) / voice["audio_file"]).stat().st_size == 0:
                    raise ValueError("audio kosong")
        except (OSError, KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Checkpoint/audio tidak dapat dipakai: {exc}. Mulai ulang tanpa --resume.") from exc
        info(f"  -> Melanjutkan sesi: {data['title']}")
    else:
        data = research_and_write(topic)
        pacing.tag_urgency(data["scenes"])
        session = {"version": 1, "data": data}
        save_session(session)
        asset_generator.clear_assets(Path(PUBLIC_DIR) / "assets")
        info(f"  -> Topik dipilih: {data['title']} ({len(data['scenes'])} adegan)")
        info(f"  -> Tema warna: {THEME_NAMES[data['theme_index']]}")

    if "voice" not in session:
        os.makedirs(PUBLIC_DIR, exist_ok=True)
        words, duration, audio_file = asyncio.run(generate_voices(data["scenes"]))
        session["voice"] = {"audio_file": audio_file, "duration": duration, "words": words,
                            "timings": render_timings(data["scenes"], words, duration)}
        save_session(session)
    return data, session["voice"]


def prepare_hybrid(data, voice):
    spec, shots = asset_generator.storyboard(data, voice["timings"])
    components = list(dict.fromkeys(s["component"] for s in shots if s["asset_id"] == "03_cutaway"))
    cache = data.setdefault("hybrid_cache", {})
    client = None
    if GEMINI_KEY:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
    asset_map, anchors = asset_generator.generate_scene_assets(
        spec, Path(PUBLIC_DIR) / "assets", data["title"], components, cache,
        lambda: save_session({"version": 1, "data": data, "voice": voice}), client, vision_caller(), info)
    asset_generator.apply_anchors(shots, anchors)
    return {"assetMap": asset_map, "shots": shots}


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Agent")
    parser.add_argument("--resume", action="store_true", help="Lanjutkan checkpoint terakhir tanpa mengulang tahap yang sudah selesai")
    parser.add_argument("--tanpa-upload", action="store_true", help="Buat video saja, jangan diunggah")
    parser.add_argument("--unggah-saja", action="store_true",
                        help="Unggah video yang sudah jadi (hasil terakhir) tanpa membuat video baru")
    parser.add_argument("--jadwal", default=None, metavar="JAM",
                        help="Jam tayang di YouTube (WIB), contoh: 13:00. Video diunggah dulu, tayang otomatis di jam itu")
    parser.add_argument("--topik", "--topic", dest="topik", default=None, help="Tentukan topik sendiri (kalau kosong, dipilih acak)")
    parser.add_argument(
        "--privasi", default=PRIVACY, choices=["private", "unlisted", "public"],
        help="Status video di YouTube (bawaan: private)",
    )
    args = parser.parse_args()
    if args.resume and (args.topik or args.unggah_saja):
        parser.error("--resume tidak dapat digabung dengan --topik atau --unggah-saja")

    try:
        publish_at = next_publish_time(args.jadwal) if args.jadwal else None

        if args.unggah_saja:
            if not os.path.exists(VIDEO_PATH) or os.path.getsize(VIDEO_PATH) < 10_000:
                raise RuntimeError("Belum ada video jadi. Buat dulu dengan: jalankan_agen.bat --tanpa-upload")
            notes = load_video_notes()
            info(f"Mengunggah video yang sudah jadi: {notes['title']}")
            upload_video(VIDEO_PATH, notes, args.privasi, publish_at)
            return

        data, voice = prepare_session(args.resume, args.topik)
        words, duration, audio_file = voice["words"], voice["duration"], voice["audio_file"]
        info(f"  -> Durasi video: {duration} detik, {len(words)} kata")

        info("[3/5] Menyiapkan ilustrasi hybrid dan mencari jangkar komponen...")
        hybrid = prepare_hybrid(data, voice)
        final_video = render_remotion_video(
            words, data["scenes"], duration, data["theme_index"], data.get("music"), data.get("bg_seed", 0), audio_file,
            {k: data.get(k) for k in ("environment", "hook_question", "hook_highlight", "claim")}, timings=voice["timings"], hybrid=hybrid
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
