"""AI Director: pengawas independen antara penulis naskah dan pembuat video.

Tahap 1 Penulis naskah (research_and_write + editor)  -> naskah dan rencana visual tiap adegan.
Tahap 2 Director (berkas ini)                          -> memeriksa akurasi visual, tumpang tindih, dan angka; memerintahkan perbaikan.
Tahap 3 Pembuat video (render_remotion_video)         -> menerjemahkan rencana yang sudah disetujui ke props Remotion.
Catatan: tahap 3 tidak menulis kode oleh LLM. Bentuk dan gerak datang dari pustaka terverifikasi (sim_library dan
src/components/library), sehingga tidak ada kode karangan yang bisa rusak atau salah bentuk."""

import json
import re

import metaphors
import sim_library
import sim_presets
import topic_lock

VALID_TYPES = ("flow", "mindmap", "counter", "timeline", "barchart", "compare", "gauge", "footage",
               "cutaway", "microscale", "story", "mechanism")
FIXABLE_TYPES = ("flow", "mindmap", "cutaway", "microscale")  # adegan teks datar yang boleh diganti animasi
MAX_NUMBERS = 3


def _numbers(text):
    return re.findall(r"\d+(?:[.,]\d+)?", text or "")


def check(data):
    """Pemeriksaan pasti (tanpa LLM). Hasil: daftar masalah {scene, problem, fix}."""
    issues = []
    scenes = data.get("scenes") or []
    total_numbers = sum(len(_numbers(sc.get("narration"))) for sc in scenes)
    if total_numbers > MAX_NUMBERS:
        issues.append({"scene": None, "problem": f"{total_numbers} angka di ucapan (batas {MAX_NUMBERS})", "fix": None})
    prev_visual = None
    for i, sc in enumerate(scenes):
        text = f"{sc.get('title', '')} {sc.get('narration', '')}"
        want, _ = metaphors.match(text)
        guess = want or sim_presets.guess_preset(text)
        # 1. benda yang disebut punya animasi terverifikasi, tetapi adegan memakai visual lain
        if guess and not sc.get("sim_preset") and sc.get("type") in FIXABLE_TYPES + ("mechanism",):
            issues.append({"scene": i, "problem": f"naskah menyebut benda berpreset '{guess}' tetapi visualnya bukan itu", "fix": ("set_preset", guess)})
        # 2. model/gambar luar dipakai padahal ada animasi terverifikasi untuk bendanya
        if guess and (sc.get("model") or sc.get("art_urls")) and not sc.get("sim_preset"):
            issues.append({"scene": i, "problem": f"visual luar dipakai untuk benda berpreset '{guess}'", "fix": ("set_preset", guess)})
        # 3. visual kembar berturutan
        visual = sc.get("model") or (tuple(sc.get("art_urls") or []) or None) or sc.get("subject")
        if visual and visual == prev_visual:
            issues.append({"scene": i, "problem": "visual sama dengan adegan sebelumnya", "fix": ("clear_visual", None)})
        prev_visual = visual
        # 4. tumpang tindih: terlalu banyak label dalam animasi
        sim = sc.get("sim") or {}
        n_labels = sum(1 for o in sim.get("objects", []) if o.get("label")) + sum(len(c.get("labels") or []) for c in sim.get("components", []))
        if n_labels > 4:
            issues.append({"scene": i, "problem": f"{n_labels} label, label akan tumpang tindih", "fix": ("trim_labels", 4)})
    return issues


def _apply(data, issue):
    i, fix = issue.get("scene"), issue.get("fix")
    if i is None or not fix or i >= len(data["scenes"]):
        return False
    sc = data["scenes"][i]
    action, value = fix
    if action == "set_preset" and value:
        labels = [str(x.get("label") or "") for x in (sc.get("items") or []) if isinstance(x, dict)]
        spec = sim_presets.preset_sim(value, labels)
        sim = sim_presets.clean_sim(spec) if spec else None
        if not sim:
            return False
        sc["sim"], sc["sim_preset"], sc["sim_generic"] = sim, True, False
        sc["preset_name"] = value
        sc["subject"] = ""
        sc["type"] = "mechanism"
        for k in ("model", "art_urls", "video", "clips"):
            sc.pop(k, None)
        return True
    if action == "clear_visual":
        for k in ("model", "art_urls"):
            sc.pop(k, None)
        sc["subject"] = ""
        return True
    if action == "trim_labels":
        sim = sc.get("sim") or {}
        seen = 0
        for o in sim.get("objects", []):
            if o.get("label"):
                seen += 1
                if seen > value:
                    o.pop("label", None)
        return True
    return False


def _llm_review(data, call_sources, log):
    """Pengawas LLM: periksa akurasi ilmiah dan kecocokan visual. Hasil: daftar perbaikan yang aman dipakai."""
    rows = []
    for i, sc in enumerate(data["scenes"]):
        visual = "animasi terverifikasi" if sc.get("sim_preset") else ("model 3D: " + str(sc.get("subject")) if sc.get("model") else
                 ("gambar AI" if sc.get("art_urls") else ("animasi umum" if sc.get("sim") else "kartu teks")))
        rows.append({"scene": i, "type": sc.get("type"), "title": sc.get("title"), "narration": sc.get("narration"), "visual": visual})
    catalog = [n for n in sim_library.PRESET_NAMES]
    ask = (
        "Kamu AI Director, pengawas independen video sains Shorts. Periksa tiap adegan: (1) apakah visualnya akurat secara ilmiah dan "
        "memperlihatkan benda yang disebut narasi? (2) apakah ada adegan yang visualnya terlalu abstrak atau salah benda? "
        "(3) KESINAMBUNGAN: apakah benda di tiap adegan menyambung secara fisik dengan benda di adegan sebelumnya (sebab-akibat), "
        "bukan melompat ke benda asing? Adegan yang melompat ditandai action \"clear_visual\". "
        "Animasi terverifikasi yang tersedia: " + ", ".join(catalog) + ".\n"
        "Jawab HANYA JSON {\"fixes\": [{\"scene\": nomor, \"problem\": \"alasan singkat\", \"action\": \"set_preset\" atau \"set_type\" atau \"clear_visual\" atau \"ok\", "
        "\"value\": \"nama preset atau tipe adegan\"}]}. Hanya sertakan adegan yang benar-benar salah; kalau semua baik, fixes kosong.\n\n"
        + json.dumps(rows, ensure_ascii=False)[:9000]
    )
    for name, call in call_sources:
        try:
            text = call(ask)
            got = json.loads(text[text.find("{"): text.rfind("}") + 1])
            fixes = []
            for f in got.get("fixes", [])[:6]:
                idx, act, val = f.get("scene"), f.get("action"), str(f.get("value") or "")
                if not isinstance(idx, int) or not 0 <= idx < len(data["scenes"]):
                    continue
                if act == "set_preset" and val in sim_library.PRESET_NAMES:
                    fixes.append({"scene": idx, "problem": str(f.get("problem"))[:100], "fix": ("set_preset", val)})
                elif act == "clear_visual":
                    fixes.append({"scene": idx, "problem": str(f.get("problem"))[:100], "fix": ("clear_visual", None)})
                elif act == "set_type" and val in VALID_TYPES:
                    fixes.append({"scene": idx, "problem": str(f.get("problem"))[:100], "fix": ("set_type", val)})
            log(f"  -> Director ({name}) selesai memeriksa.")
            return fixes
        except Exception as e:
            log(f"     Director {name} dilewati: {str(e)[:80]}")
    return None


def review(data, call_sources=None, log=print, forced_topic=""):
    """Periksa naskah dan rencana visual, lalu perbaiki otomatis sebelum video dibuat. Selalu mengembalikan data."""
    issues = check(data)
    llm = _llm_review(data, call_sources, log) if call_sources else None
    if llm:
        issues += llm
    lock = topic_lock.detect(data, forced_topic)
    if lock:
        log(f"  -> Topik terkunci: {lock['name']} (hanya benda dan animasi resmi topik ini yang boleh tampil).")
        # saran perbaikan yang menarik animasi di luar topik tidak boleh dipakai
        issues = [i for i in issues if not (i.get("fix") and i["fix"][0] == "set_preset" and i["fix"][1] not in lock["chain"])]
    fixed = 0
    for issue in issues:
        if issue.get("fix") and issue["fix"][0] == "set_type":
            sc = data["scenes"][issue["scene"]]
            sc["type"] = issue["fix"][1]
            fixed += 1
        elif _apply(data, issue):
            fixed += 1
        if issue.get("problem"):
            log(f"     Director: adegan {issue['scene'] if issue.get('scene') is not None else '-'}: {issue['problem']}")
    if lock:
        fixed += topic_lock.enforce(data, lock, call_sources, log)
    fixed += topic_lock.domain_gate(data, forced_topic, lock, log)
    fixed += topic_lock.limit_charts(data, lock, log)
    fixed += topic_lock.dedupe(data, lock, log)
    if lock:
        fixed += topic_lock.continuity(data, lock, log)
    log(f"  -> Director: {len(issues)} catatan, {fixed} diperbaiki otomatis.")
    return data


def require_clean(data, forced_topic=""):
    """Gerbang akhir: kalau masih ada visual di luar topik terkunci, hentikan alur (jangan merender naskah rusak)."""
    lock = topic_lock.detect(data, forced_topic)
    if not lock:
        return
    left = []
    for i, sc in enumerate(data["scenes"]):
        blob = " ".join(str(x) for x in (sc.get("subject"), sc.get("art"), sc.get("preset_name"))).lower()
        if sc.get("sim_preset") and sc.get("preset_name") not in lock["chain"]:
            left.append(i)
        elif any(b in blob for b in lock["banned"]):
            left.append(i)
    if left:
        raise RuntimeError(f"AI Director: adegan {left} masih memuat benda di luar topik '{lock['name']}'. Render dibatalkan.")
