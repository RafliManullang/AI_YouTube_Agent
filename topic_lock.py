"""Kunci topik: benda di layar harus benda yang memang dibahas topiknya.

Masalah yang dicegah: topik pemantik korek, tetapi layar menampilkan rangkaian lampu dan baterai, atau kompor dan oven.
Cara kerja (semua pasti, tanpa menebak):
  1. detect()      mengenali topik terkunci dari judul dan naskah.
  2. enforce()     tiap adegan: benda di luar daftar dibuang atau diganti animasi resmi topik itu. Kalau ada AI yang
                   bisa ditanya, AI diminta memilih ulang HANYA dari daftar resmi (hukuman: pilihan di luar daftar ditolak).
  3. dedupe()      animasi yang sama tidak dipakai dua kali dalam satu video (awal dan akhir tidak kembar lagi).
  4. continuity()  urutan sebab-akibat: tahap animasi tidak boleh melompat mundur atau keluar dari rantai topik."""

import json

import sim_presets

LOCKS = (
    {
        "name": "headphone",
        "triggers": ("headphone", "earphone", "peredam bising", "noise cancelling", "peredam suara", "headset"),
        "min_hits": 2,
        # jika aset khusus tidak ada, hanya gelombang suara yang boleh tampil (bukan benda acak)
        "chain": ("gelombang_bising", "gelombang_suara"),
        "stage_words": {
            "gelombang_bising": ("bising", "mesin", "suara luar", "mikrofon", "menangkap", "penangkap", "desing"),
            "gelombang_suara": ("interferensi", "destruktif", "terbalik", "lawan", "hening", "meredam", "saling", "menghilang", "membunuh"),
        },
        "subjects_ok": ("headphone", "earphone", "headset", "wave", "sound"),
        "banned": ("microphone", "mic", "speaker", "chip", "circuit", "goat", "bus", "train", "radio", "guitar", "piano", "mikrofon",
                   "kambing", "mask", "weapon", "gun", "monster", "sword", "oven", "stove", "fridge"),
        "banned_presets": ("aliran_listrik", "panas_berlebih", "setrika", "bimetal", "mesin_ice", "pemantik_pegas", "pemantik_kristal", "pemantik_api"),
    },
    {
        "name": "pemantik",
        "triggers": ("korek", "pemantik", "lighter", "piezo"),
        "min_hits": 2,
        # rantai sebab-akibat, berurutan: tombol+pegas -> palu menghantam kristal -> gas terbakar
        "chain": ("pemantik_pegas", "pemantik_kristal", "pemantik_api"),
        "stage_words": {
            "pemantik_pegas": ("tombol", "pegas", "pengunci", "palu", "tekan"),
            "pemantik_kristal": ("kristal", "kuarsa", "piezo", "muatan", "tegangan", "benturan", "hantam", "atom"),
            "pemantik_api": ("api", "gas", "butana", "percik", "nyala", "bakar"),
        },
        "subjects_ok": ("lighter", "spring", "crystal", "quartz", "flame", "fire", "spark", "gas", "butane", "hammer", "button"),
        "banned": ("stove", "oven", "cooker", "kitchen", "lamp", "bulb", "light bulb", "battery", "switch", "fridge",
                   "microwave", "kompor", "oven", "lampu", "baterai", "saklar", "circuit", "rangkaian"),
        "banned_presets": ("aliran_listrik", "panas_berlebih", "setrika", "bimetal", "mesin_ice"),
    },
)


def detect(data, forced_topic=""):
    text = " ".join([forced_topic or "", data.get("title", "")] + [f"{s.get('title', '')} {s.get('narration', '')}" for s in data.get("scenes", [])]).lower()
    for lock in LOCKS:
        hits = sum(text.count(t) for t in lock["triggers"])
        if hits >= lock["min_hits"] or any(t in (forced_topic or "").lower() or t in data.get("title", "").lower() for t in lock["triggers"]):
            return lock
    return None


def prompt_guide(forced_topic):
    lock = detect({"scenes": []}, forced_topic)
    if not lock:
        return ""
    return (f"KUNCI TOPIK ({lock['name']}): kamu DILARANG memunculkan benda di luar topik ini. Animasi yang boleh dipakai hanya: "
            f"{', '.join(lock['chain'])} (urut sebab-akibat). \"subject\" hanya boleh salah satu dari: {', '.join(lock['subjects_ok'])}. "
            f"Dilarang keras: {', '.join(sorted(set(lock['banned'])))}. Pelanggaran akan ditolak otomatis dan adegan diganti.\n")


def _bad_subject(lock, text):
    t = (text or "").lower()
    return any(b in t for b in lock["banned"])


MAX_USES = 3  # satu animasi resmi boleh muncul paling banyak 3 kali, tiap kali dengan sudut kamera dan jarak berbeda


def _stage_by_position(lock, i, n, uses):
    p = lock["chain"][min(len(lock["chain"]) - 1, int(i / max(1, n) * len(lock["chain"])))]
    return p if uses.get(p, 0) < MAX_USES else None


def _stage_for(lock, sc, uses):
    """Tahap rantai yang paling cocok dengan narasi adegan; yang belum sering dipakai diutamakan."""
    text = f"{sc.get('title', '')} {sc.get('narration', '')}".lower()
    scored = [(sum(text.count(w) for w in lock["stage_words"][p]), -uses.get(p, 0), -i, p) for i, p in enumerate(lock["chain"])]
    for score, _, _, p in sorted(scored, reverse=True):
        if score > 0 and uses.get(p, 0) < MAX_USES:
            return p
    return None


def _variant_cam(sc, k):
    """Pemakaian ke-k dari animasi yang sama: kamera lebih dekat dan sudut lain, supaya tidak tampak kembar."""
    if k <= 0:
        return
    cam = (sc.get("sim") or {}).get("cam")
    if not isinstance(cam, dict):
        return
    cam["dist"] = round(float(cam.get("dist", 22)) * (1 - 0.22 * k), 2)
    cam["orbit"] = round(float(cam.get("orbit", 0.8)) + (1.1 if k % 2 else -1.1) * k, 2)
    tgt = list(cam.get("target") or [0, 0, 0])
    tgt[1] = round(tgt[1] + 0.5 * k, 2)
    cam["target"] = tgt
    sc["variant_k"] = k


def _llm_pick(lock, sc, call_sources, log):
    """Hukuman penolakan: AI diminta memilih ulang, jawaban di luar daftar resmi ditolak."""
    if not call_sources:
        return None
    ask = (f"Adegan video tentang {lock['name']}: judul \"{sc.get('title')}\", narasi \"{sc.get('narration')}\". Visual sebelumnya SALAH "
           f"karena di luar topik. Pilih SATU animasi dari daftar resmi: {', '.join(lock['chain'])}. Jawab HANYA JSON {{\"preset\": \"nama\"}}.")
    for name, call in call_sources:
        try:
            text = call(ask)
            got = json.loads(text[text.find("{"): text.rfind("}") + 1]).get("preset")
            if got in lock["chain"]:
                return got
        except Exception as e:
            log(f"     Pilih ulang ({name}) dilewati: {str(e)[:60]}")
    return None


def _set_preset(sc, name, variant=0):
    labels = [str(x.get("label") or "") for x in (sc.get("items") or []) if isinstance(x, dict)]
    spec = sim_presets.preset_sim(name, labels, defaults=True)  # topik terkunci: animasi memang khusus topiknya
    sim = sim_presets.clean_sim(spec) if spec else None
    if not sim:
        return False
    sc["sim"], sc["sim_preset"], sc["sim_generic"], sc["type"] = sim, True, False, "mechanism"
    sc["preset_name"] = name
    sc.pop("variant_k", None)
    _variant_cam(sc, variant)
    for k in ("model", "art_urls", "video", "clips", "art"):
        sc.pop(k, None)
    sc["subject"] = ""
    return True


def _clear(sc):
    for k in ("model", "art_urls", "art", "sim", "video", "clips"):
        sc.pop(k, None)
    sc["subject"], sc["sim_preset"], sc["sim_generic"] = "", False, False
    sc.pop("preset_name", None)
    if sc.get("type") in ("mechanism", "cutaway", "microscale"):
        sc["type"] = "flow"


def enforce(data, lock, call_sources=None, log=print):
    """Buang atau ganti semua visual di luar topik. Hasil: jumlah adegan yang diperbaiki."""
    uses = {}
    for sc in data["scenes"]:
        if sc.get("preset_name") in lock["chain"] and sc.get("sim_preset"):
            uses[sc["preset_name"]] = uses.get(sc["preset_name"], 0) + 1
    fixed = 0
    for i, sc in enumerate(data["scenes"]):
        if sc.get("type") in ("counter", "barchart", "timeline", "compare", "gauge"):
            continue  # adegan data dan rekaman tidak membawa benda 3D
        subj = str(sc.get("subject") or "")
        art = " ".join(map(str, sc.get("art") or [])) if isinstance(sc.get("art"), list) else str(sc.get("art") or "")
        pre = sc.get("preset_name") or ""
        bad = (
            sc.get("type") == "footage"  # rekaman stok tidak dipakai: pembuka diganti animasi resmi topik
            or _bad_subject(lock, subj) or _bad_subject(lock, art)
            or (subj and not any(o in subj.lower() for o in lock["subjects_ok"]))
            or pre in lock["banned_presets"]
            or (sc.get("sim_preset") and pre not in lock["chain"])
        )
        if not bad:
            continue
        pick = _llm_pick(lock, sc, call_sources, log) or _stage_for(lock, sc, uses) or _stage_by_position(lock, i, len(data["scenes"]), uses)
        if pick and _set_preset(sc, pick, uses.get(pick, 0)):
            uses[pick] = uses.get(pick, 0) + 1
            log(f"     Kunci topik: adegan {i}: visual di luar topik '{lock['name']}' diganti animasi '{pick}'.")
        else:
            _clear(sc)
            log(f"     Kunci topik: adegan {i}: visual di luar topik dibuang.")
        fixed += 1
    return fixed


def dedupe(data, lock=None, log=print):
    """Animasi terverifikasi yang sama: tanpa kunci topik hanya boleh sekali; dengan kunci topik boleh sampai MAX_USES kali,
    dengan kamera berbeda. Kelebihannya diganti visual lain."""
    seen = {}
    fixed = 0
    for i, sc in enumerate(data["scenes"]):
        pre = sc.get("preset_name")
        if not pre or not sc.get("sim_preset"):
            continue
        if pre.startswith("prim:"):  # primitif fisika boleh dipakai ulang (maks 2x), dengan sudut kamera berbeda
            n = seen.get(pre, 0)
            if n and not sc.get("variant_k"):
                _variant_cam(sc, n)
            seen[pre] = n + 1
            continue
        n = seen.get(pre, 0)
        if n == 0:
            seen[pre] = 1
            continue
        if lock and pre in lock["chain"] and n < MAX_USES:
            if not sc.get("variant_k"):
                _set_preset(sc, pre, n)
            seen[pre] = n + 1
            log(f"     Anti-ulang: adegan {i}: animasi '{pre}' dipakai lagi dengan sudut kamera berbeda.")
        else:
            _clear(sc)
            log(f"     Anti-ulang: adegan {i}: animasi '{pre}' sudah dipakai, diganti visual lain.")
        fixed += 1
    return fixed


def continuity(data, lock, log=print):
    """Rantai sebab-akibat: tahap tidak boleh melompat mundur. Adegan yang melompat dilepas dari animasi tahapnya."""
    last = -1
    fixed = 0
    for i, sc in enumerate(data["scenes"]):
        pre = sc.get("preset_name")
        if pre not in lock["chain"] or not sc.get("sim_preset"):
            continue
        idx = lock["chain"].index(pre)
        if idx < last and not sc.get("variant_k"):
            _clear(sc)
            log(f"     Kesinambungan: adegan {i}: tahap '{pre}' melompat mundur, visual dilepas.")
            fixed += 1
        else:
            last = idx
    return fixed


TOPIC_FOR_DOMAIN = [""]


def _prim_scene(sc, i, n, uses, hook, data):
    import primitives
    text = f"{sc.get('title', '')} {sc.get('narration', '')}"
    labels = [str(x.get("label") or "") for x in (sc.get("items") or []) if isinstance(x, dict)]
    pid = primitives.choose(text, uses, i, primitives.domain_of(" ".join([str(data.get("title", ""))] + [f"{s.get('title','')} {s.get('narration','')}" for s in data["scenes"]]) + " " + (TOPIC_FOR_DOMAIN[0] or "")))
    sim = primitives.sim_for(pid, labels, hook=hook, text=text)
    if not sim:
        return False
    uses[pid] = uses.get(pid, 0) + 1
    sc["sim"], sc["sim_preset"], sc["sim_generic"], sc["type"] = sim, True, False, "mechanism"
    sc["preset_name"] = f"prim:{pid}"
    sc["subject"] = ""
    for k in ("model", "art_urls", "video", "clips", "art"):
        sc.pop(k, None)
    return True


def domain_gate(data, forced_topic="", lock=None, log=print):
    """Animasi bawaan di luar topiknya diganti primitif fisika umum; pembuka (detik 0 sampai 5) wajib simulasi mekanis,
    bukan tanda tanya atau kartu teks."""
    import sim_presets
    topic = f"{data.get('title', '')} {forced_topic or ''}"
    TOPIC_FOR_DOMAIN[0] = forced_topic or ""
    uses = {}
    for sc in data["scenes"]:
        if str(sc.get("preset_name", "")).startswith("prim:"):
            k = sc["preset_name"][5:]
            uses[k] = uses.get(k, 0) + 1
    fixed = 0
    n = len(data["scenes"])
    first = data["scenes"][0] if data["scenes"] else None
    if first and not (first.get("sim_preset") and first.get("type") in ("mechanism", "cutaway")) and first.get("type") not in ("counter", "gauge", "barchart"):
        if not (lock and first.get("preset_name") in lock["chain"]):
            if _prim_scene(first, 0, n, uses, True, data):
                fixed += 1
                log("     Pembuka: adegan 0 diganti simulasi mekanis (tanpa tanda tanya atau kartu teks).")
    for i, sc in enumerate(data["scenes"]):
        pre = sc.get("preset_name") or ""
        if pre and sc.get("sim_preset") and not pre.startswith("prim:") and not (lock and pre in lock["chain"]) and not sim_presets.domain_ok(pre, topic):
            if _prim_scene(sc, i, n, uses, (i == 0), data):
                fixed += 1
                log(f"     Topik: adegan {i}: animasi '{pre}' tidak cocok dengan topik, diganti primitif fisika.")
    return fixed


CHART_TYPES = ("barchart", "gauge", "timeline", "compare")


def limit_charts(data, lock=None, log=print):
    """Paling banyak SATU adegan grafik per video (utamakan barchart atau compare yang membandingkan angka). Sisanya diganti
    simulasi mekanis yang bendanya bergerak (derajat jadi benda miring, tahapan jadi aliran gerak), bukan speedometer atau bola 1-2-3."""
    idx = [i for i, s in enumerate(data["scenes"]) if s.get("type") in CHART_TYPES]
    if len(idx) <= 1:
        return 0
    keep = next((i for i in idx if data["scenes"][i]["type"] in ("barchart", "compare")), idx[0])
    uses = {}
    fixed = 0
    n = len(data["scenes"])
    for i in idx:
        if i == keep:
            continue
        sc = data["scenes"][i]
        if lock:
            pick = _stage_by_position(lock, i, n, {})
            ok = bool(pick) and _set_preset(sc, pick, 1)
        else:
            ok = _prim_scene(sc, i, n, uses, False, data)
        if ok:
            fixed += 1
            log(f"     Grafik dibatasi: adegan {i}: grafik '{sc.get('title')}' diganti simulasi mekanis.")
    return fixed
