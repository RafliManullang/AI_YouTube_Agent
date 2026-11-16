"""Lima komponen primitif fisika yang berlaku untuk topik sains apa pun.

Kalau agen tidak punya animasi khusus untuk sebuah topik, adegan WAJIB memakai salah satu primitif ini
(bukan benda acak seperti headphone, jembatan, atau mobil). Label di layar 100% berasal dari naskah (items), tidak ada yang tertulis mati."""

import re

import sim_presets

IDS = ("ParticleFlow", "WaveInterference", "PressureChamber", "HeatTransfer", "MechanicalTrigger")

KEYS = {
    "ParticleFlow": ("ion", "partikel", "arus", "listrik", "elektron", "gas", "aliran", "cairan", "muatan", "radiasi", "alfa",
                     "radioaktif", "mengalir", "molekul", "udara", "americium", "plasma"),
    "WaveInterference": ("suara", "gelombang", "sinyal", "radio", "sirine", "bunyi", "nada", "frekuensi", "getar", "alarm", "bising", "nyaring"),
    "PressureChamber": ("tekanan", "ruang", "tabung", "kompres", "wadah", "sensor", "detektor", "asap", "tertutup", "uap", "balon", "kaleng", "memadat"),
    "HeatTransfer": ("panas", "suhu", "kalor", "bimetal", "muai", "dingin", "termostat", "api", "membara", "hangat", "pemanas", "lebur"),
    "MechanicalTrigger": ("pegas", "palu", "pukul", "tombol", "pemicu", "tuas", "klik", "benturan", "piezo", "menekan", "pengunci", "jatuh", "ketuk"),
}
ROTATION = ("ParticleFlow", "PressureChamber", "MechanicalTrigger", "HeatTransfer", "WaveInterference")
MAX_USES = 2


def choose(text, uses, index=0):
    """Primitif yang paling cocok dengan kata-kata adegan; yang sudah dipakai dua kali dilewati."""
    t = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())
    scored = sorted(((sum(t.count(w) for w in KEYS[p]), -uses.get(p, 0), -ROTATION.index(p), p) for p in IDS), reverse=True)
    for score, _, _, p in scored:
        if score > 0 and uses.get(p, 0) < MAX_USES:
            return p
    for k in range(len(ROTATION)):
        p = ROTATION[(index + k) % len(ROTATION)]
        if uses.get(p, 0) < MAX_USES:
            return p
    return ROTATION[index % len(ROTATION)]


def sim_for(pid, labels=(), hook=False, text=""):
    """Spesifikasi simulasi dari satu primitif. Label hanya dari naskah. hook=True: tampil sebagai potongan melintang (cangkang tembus pandang)."""
    props = {}
    if pid == "ParticleFlow":
        props = {"shell": "disc" if hook else "box"}
    elif pid == "WaveInterference":
        props = {"mode": "noise" if ("bising" in text.lower() and "lawan" not in text.lower() and "terbalik" not in text.lower()) else "interference"}
    elif pid == "MechanicalTrigger":
        props = {"shell": "box" if hook else "none"}
    labels = [str(x).strip() for x in labels if str(x).strip()][:3]
    spec = {"cam": {"dist": 25 if pid != "MechanicalTrigger" else 22, "height": 1.0, "orbit": 0.0, "target": [0, 0, 0]},
            "components": [{"id": pid, "pos": [0, 0, 0], "props": props, "labels": labels}],
            "objects": [], "motions": [], "flows": []}
    return sim_presets.clean_sim(spec)
