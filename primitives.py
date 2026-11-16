"""Primitif fisika yang berlaku untuk banyak topik sains, dipilih sesuai BIDANG topiknya.

Bidang mekanika benda padat (mobil, poros, sendi, bantalan, batang): poros dan sendi, bantalan bola, batang kaku vs fleksibel, dan
pemicu pegas-palu. Bidang fluida, gas, listrik, dan gelombang: partikel mengalir, gelombang, ruang bertekanan, dan panas.
Komponen satu bidang tidak dipakai di bidang lain. Label di layar 100% berasal dari naskah (items)."""

import re

import sim_presets

FLUID_IDS = ("ParticleFlow", "WaveInterference", "PressureChamber")
SOLID_IDS = ("RotatingShaftAndJoint", "BallBearingCage", "RigidVsFlexibleRod")
IDS = FLUID_IDS + ("HeatTransfer", "MechanicalTrigger") + SOLID_IDS

KEYS = {
    "ParticleFlow": ("ion", "partikel", "arus", "listrik", "elektron", "gas", "aliran", "cairan", "muatan", "radiasi", "alfa",
                     "radioaktif", "mengalir", "molekul", "udara", "americium", "plasma"),
    "WaveInterference": ("suara", "gelombang", "sinyal", "radio", "sirine", "bunyi", "nada", "frekuensi", "getar", "alarm", "bising", "nyaring"),
    "PressureChamber": ("tekanan", "ruang", "tabung", "kompres", "wadah", "sensor", "detektor", "asap", "tertutup", "uap", "balon", "kaleng", "memadat"),
    "HeatTransfer": ("panas", "suhu", "kalor", "bimetal", "muai", "dingin", "termostat", "api", "membara", "hangat", "pemanas", "lebur"),
    "MechanicalTrigger": ("pegas", "palu", "pukul", "tombol", "pemicu", "tuas", "klik", "benturan", "piezo", "menekan", "pengunci", "jatuh", "ketuk"),
    "RotatingShaftAndJoint": ("poros", "putar", "memutar", "sendi", "kardan", "engsel", "tekuk", "belok", "meliuk", "roda", "penggerak", "kemudi", "puntir", "sudut", "derajat", "transmisi"),
    "BallBearingCage": ("bola", "bantalan", "bearing", "mangkuk", "alur", "cincin", "presisi", "bergeser", "miring", "lekuk"),
    "RigidVsFlexibleRod": ("kaku", "patah", "retak", "fleksibel", "lentur", "beban", "kuat", "rapuh", "baja", "batang", "terpuntir"),
}
SOLID_WORDS = ("poros", "roda", "mobil", "baja", "sendi", "bantalan", "bearing", "engsel", "gigi", "rem", "mesin", "otomotif", "batang",
               "torsi", "kemudi", "setir", "kopling", "transmisi", "kardan", "puntir", "tuas", "tekuk", "patah", "rangka", "suspensi",
               "bola baja", "mangkuk", "ban ", "sasis", "pegas", "engkol", "piston", "bor", "baut", "las", "jembatan", "beton", "gir")
FLUID_WORDS = ("udara", "gas", "cairan", "asap", "uap", "ion", "listrik", "arus", "muatan", "elektron", "suara", "gelombang", "sinyal",
               "radio", "partikel", "fluida", "air ", "tekanan", "radioaktif", "sirine", "tegangan", "magnet", "cahaya", "laser")
ROT_SOLID = ("RotatingShaftAndJoint", "BallBearingCage", "RigidVsFlexibleRod", "MechanicalTrigger", "HeatTransfer")
ROT_FLUID = ("ParticleFlow", "PressureChamber", "WaveInterference", "MechanicalTrigger", "HeatTransfer")
MAX_USES = 2


def _count(words, t):
    return sum(t.count(w) for w in words)


def domain_of(text):
    """"mekanika" (benda padat) atau "fluida" (gas, cairan, listrik, gelombang), dari seluruh teks video."""
    t = (text or "").lower()
    return "mekanika" if _count(SOLID_WORDS, t) > _count(FLUID_WORDS, t) else "fluida"


def _allowed(domain, scene_text):
    t = (scene_text or "").lower()
    base = list(ROT_SOLID if domain == "mekanika" else ROT_FLUID)
    # komponen bidang lain hanya boleh kalau kalimat adegan itu sendiri jelas membicarakannya (2 kata kunci atau lebih)
    other = FLUID_IDS if domain == "mekanika" else SOLID_IDS
    for p in other:
        own = _count(KEYS[p], t)
        mine = _count(SOLID_WORDS if domain == "mekanika" else FLUID_WORDS, t)
        if own >= 2 and own > mine:
            base.append(p)
    return base


def choose(text, uses, index=0, domain="fluida"):
    """Primitif paling cocok dengan kata di adegan, hanya dari komponen yang sesuai bidang topik; maksimal 2 kali pakai."""
    t = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())
    allowed = _allowed(domain, t)
    scored = sorted(((_count(KEYS[p], t), -uses.get(p, 0), -allowed.index(p), p) for p in allowed), reverse=True)
    for score, _, _, p in scored:
        if score > 0 and uses.get(p, 0) < MAX_USES:
            return p
    rot = ROT_SOLID if domain == "mekanika" else ROT_FLUID
    for k in range(len(rot)):
        p = rot[(index + k) % len(rot)]
        if uses.get(p, 0) < MAX_USES:
            return p
    return rot[index % len(rot)]


def sim_for(pid, labels=(), hook=False, text=""):
    """Spesifikasi simulasi dari satu primitif. Label hanya dari naskah. hook=True: potongan melintang (cangkang tembus pandang)."""
    low = (text or "").lower()
    props = {}
    if pid == "ParticleFlow":
        props = {"shell": "disc" if hook else "box"}
    elif pid == "WaveInterference":
        props = {"mode": "noise" if ("bising" in low and "lawan" not in low and "terbalik" not in low) else "interference"}
    elif pid == "MechanicalTrigger":
        props = {"shell": "box" if hook else "none"}
    elif pid in SOLID_IDS:
        m = re.search(r"(\d{1,2})\s*(?:derajat|°)", low)
        if m:
            props = {"tilt": min(60, max(5, int(m.group(1))))}
    labels = [str(x).strip() for x in labels if str(x).strip()][:3]
    spec = {"cam": {"dist": 25 if pid not in ("MechanicalTrigger",) else 22, "height": 1.0, "orbit": 0.0, "target": [0, 0, 0]},
            "components": [{"id": pid, "pos": [0, 0, 0], "props": props, "labels": labels}],
            "objects": [], "motions": [], "flows": []}
    return sim_presets.clean_sim(spec)
