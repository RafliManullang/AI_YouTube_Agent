"""Irama video: setiap adegan diberi tingkat kepentingan (urgency), lalu tingkat itu mengatur kecepatan potongan dan perpindahan.

  high   = hook dan momen kejutan: potongan visual sekitar 1,5 detik, perpindahan cepat dan tegas.
  normal = penjelasan inti: potongan 3 sampai 4 detik, perpindahan biasa.
  low    = penutup / jeda napas: potongan paling longgar, perpindahan lembut.
"""

import re

HIGH_WORDS = ("bahaya", "jangan", "rahasia", "ternyata", "meledak", "terbakar", "hancur", "mematikan", "tiba-tiba", "gawat")
BREATH_WORDS = ("jadi", "intinya", "karena itu", "makanya", "ternyata", "tapi")

CUT_SECONDS = {"high": 1.5, "normal": 3.5, "low": 4.0}
TRANSITION = {
    "high": {"kind": "whip", "seconds": 0.15},
    "normal": {"kind": "fade", "seconds": 0.25},
    "low": {"kind": "fade", "seconds": 0.4},
}
HOOK_SECONDS = 3.0


def tag_urgency(scenes):
    """Beri tag urgency tiap adegan: hook = high, kalimat kejutan = high, penutup = low, selebihnya normal."""
    last = len(scenes) - 1
    for i, sc in enumerate(scenes):
        text = (sc.get("narration") or " ".join(sc.get("points") or [])).lower()
        if i == 0:
            level = "high"
        elif i == last:
            level = "low"
        elif any(w in text for w in HIGH_WORDS) and len(text.split()) <= 26:
            level = "high"
        else:
            level = "normal"
        sc["urgency"] = level
        sc["transition"] = dict(TRANSITION[level])
    return scenes


def cut_seconds(scene):
    return CUT_SECONDS.get(scene.get("urgency") or "normal", 3.5)


def split_plan(plan, scene, variants):
    """Pecah potongan footage yang terlalu panjang menurut urgency adegan. plan = [[kueri, mulai, selesai], ...].
    variants(kueri) -> daftar kueri serupa, supaya potongan hasil pecahan tidak memakai klip yang sama."""
    seg = cut_seconds(scene)
    out = []
    for query, a, b in plan:
        n = int((b - a) // (seg * 1.35))
        if n <= 0:
            out.append([query, a, b])
            continue
        pieces = n + 1
        step = (b - a) / pieces
        alts = variants(query) or [query]
        for k in range(pieces):
            out.append([alts[k % len(alts)] if k else query, round(a + k * step, 2), round(a + (k + 1) * step, 2)])
    return out[: 4 if scene.get("urgency") == "high" else 3]


def key_sentence_pauses(scene):
    """Kalimat penting (kata penghubung atau tanda tanya di ujung) mendapat jeda napas mikro 0,18 detik di naskah suara.
    Hasil: daftar indeks baris yang diberi jeda."""
    marks = []
    for i, line in enumerate(scene.get("lines") or []):
        text = str(line.get("text") or "").strip().lower()
        if scene.get("urgency") == "high":
            continue  # hook dibuat rapat tanpa jeda
        if text.endswith("?") or any(re.match(rf"^{w}\b", text) for w in BREATH_WORDS):
            marks.append(i)
    return marks
