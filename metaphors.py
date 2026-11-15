"""Mesin perumpamaan visual: mengubah konsep sains yang abstrak menjadi gambaran yang mudah dicerna orang awam.

Kamus ini dipakai di tiga tempat:
 1. sim_library.KEYWORDS: kata di naskah otomatis diarahkan ke animasi 3D perumpamaannya (bukan teks atau latar merah polos).
 2. build_prompt: LLM diberi daftar perumpamaan supaya naskah dan pilihan visualnya selaras.
 3. Director: memeriksa adegan yang menyebut konsep abstrak tetapi visualnya tidak menggambarkannya."""

# (nama preset 3D, kata pemicu di naskah, perumpamaan visual dalam bahasa sederhana)
METAPHORS = (
    ("aliran_listrik", ("arus listrik", "listrik mengalir", "aliran listrik", "elektron", "arus mengalir"),
     "titik biru bercahaya yang melaju cepat di dalam pipa bening dari sumber listrik menuju lampu"),
    ("panas_berlebih", ("panas berlebih", "terlalu panas", "membara", "overheat", "makin panas", "suhu naik"),
     "logam yang memerah menyala dengan partikel panas naik dan getaran udara di atasnya"),
    ("bimetal", ("bimetal", "bimetallic", "keping logam", "kuningan dan besi", "kuningan memuai", "memuai dan melengkung"),
     "dua lapis logam pipih berbeda warna yang melengkung saat dipanaskan dan lurus saat dingin"),
    ("setrika", ("setrika", "tapak setrika"),
     "setrika bening yang memperlihatkan tapak, elemen pemanas, dan keping pengatur suhu di dalamnya"),
)


def keyword_table():
    """Format yang dipakai guess_preset: ((preset, (kata, ...)), ...)."""
    return tuple((name, words) for name, words, _ in METAPHORS)


def match(text):
    """Cari perumpamaan yang cocok dengan teks. Hasil: (preset, deskripsi) atau ('', '')."""
    t = (text or "").lower()
    for name, words, desc in METAPHORS:
        if any(w in t for w in words):
            return name, desc
    return "", ""


def prompt_guide():
    """Daftar perumpamaan untuk LLM."""
    lines = [f'- bila naskah membahas "{words[0]}": pakai animasi "{name}" ({desc})' for name, words, desc in METAPHORS]
    return "PERUMPAMAAN VISUAL (jangan diterjemahkan harfiah, jangan hanya teks atau latar merah polos):\n" + "\n".join(lines)
