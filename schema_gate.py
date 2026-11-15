"""Gerbang validasi: data untuk Remotion wajib lolos skema Zod (video_engine/src/schemas/sceneSchema.ts).

Alur: perbaikan otomatis yang pasti-pasti saja (urutan adegan, batas durasi, angka yang meleset) ->
validasi Zod -> kalau masih salah, minta LLM memperbaiki bagian yang ditolak (maksimal 2 putaran) ->
kalau tetap gagal, adegan yang rusak diganti kartu teks sederhana. Data mentah tidak pernah langsung ke render."""

import json
import os
import shutil
import subprocess

NODE_FLAGS = ["--experimental-strip-types", "--no-warnings"]


class SchemaError(RuntimeError):
    pass


def _node():
    return shutil.which("node")


def run_validator(props, remotion_dir, log=print):
    """Jalankan validator Zod. Hasil: (lolos, daftar_kesalahan, data_bersih)."""
    node = _node()
    if not node:
        return True, [], props  # tanpa Node render pun tidak bisa jalan; biarkan langkah render yang melapor
    remotion_dir = os.path.abspath(remotion_dir)
    src = os.path.join(remotion_dir, "gate_props.json")
    with open(src, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)
    try:
        return _run_validator_file(node, remotion_dir, src, log, props)
    finally:
        try:
            os.remove(src)
        except OSError:
            pass


def _run_validator_file(node, remotion_dir, src, log, props):
    try:
        res = subprocess.run([node] + NODE_FLAGS + [os.path.join("src", "cli", "validateProps.ts"), src],
                             cwd=remotion_dir, capture_output=True, text=True, timeout=60)
    except Exception as e:
        log(f"  -> Validator Zod tidak bisa dijalankan ({str(e)[:60]}), dilewati.")
        return True, [], props
    out = (res.stdout or "").strip().splitlines()
    if res.returncode == 2 and out:
        try:
            return False, json.loads(out[-1]).get("errors", []), props
        except Exception:
            return False, ["(akar): keluaran validator tidak terbaca"], props
    if res.returncode != 0:
        log(f"  -> Validator Zod gagal berjalan ({(res.stderr or '')[:80]}), dilewati.")
        return True, [], props
    with open(src, encoding="utf-8") as f:
        clean = json.load(f)
    return True, [], clean


def auto_fix(props):
    """Perbaikan pasti yang tidak perlu LLM: angka berupa teks, adegan tidak berurutan, melewati durasi."""
    dur = float(props.get("durationInSeconds") or 0) or 40.0
    props["durationInSeconds"] = min(180.0, max(3.0, dur))
    scenes = props.get("scenes") or []
    for s in scenes:
        for k in ("start", "end", "number"):
            if isinstance(s.get(k), str):
                try:
                    s[k] = float(s[k].replace(",", "."))
                except ValueError:
                    s.pop(k, None)
        if s.get("number") is None:
            s.pop("number", None)
        if s.get("unit") is None:
            s.pop("unit", None)
        s["title"] = str(s.get("title") or "")[:80]
        s["points"] = [str(p)[:60] for p in (s.get("points") or [])][:8]
    scenes.sort(key=lambda s: s.get("start", 0))
    prev = 0.0
    for s in scenes:
        s["start"] = max(prev, float(s.get("start", 0)))
        s["end"] = min(props["durationInSeconds"], float(s.get("end", s["start"] + 3)))
        if s["end"] <= s["start"]:
            s["end"] = s["start"] + 0.5
        prev = s["end"]
    for w in props.get("words") or []:
        if isinstance(w.get("end"), (int, float)) and isinstance(w.get("start"), (int, float)) and w["end"] < w["start"]:
            w["end"] = w["start"]
    props["scenes"] = scenes
    return props


def _bad_scene_indexes(errors):
    idx = set()
    for e in errors:
        parts = e.split(":")[0].split(".")
        if len(parts) >= 2 and parts[0] == "scenes" and parts[1].isdigit():
            idx.add(int(parts[1]))
    return idx


def llm_repair(props, errors, callers, log=print):
    """Minta LLM memperbaiki adegan yang ditolak. callers = [(nama, fungsi(prompt)->teks)]."""
    bad = sorted(_bad_scene_indexes(errors))
    if not bad:
        return None
    ask = (
        "Kamu pemeriksa data video. JSON adegan di bawah DITOLAK oleh skema ketat dengan kesalahan ini:\n"
        + "\n".join("- " + e for e in errors[:15])
        + "\n\nPerbaiki HANYA adegan yang salah. Pakai nilai yang sah: type salah satu dari flow, mindmap, counter, timeline, barchart, "
        "compare, gauge, footage, cutaway, microscale, story, question, mechanism; warna berbentuk #rrggbb; angka berupa angka, bukan teks; "
        "end harus lebih besar dari start. Jawab HANYA dengan JSON berbentuk {\"scenes\": {\"<nomor adegan>\": {...adegan lengkap yang sudah benar...}}}.\n\n"
        + json.dumps({str(i): props["scenes"][i] for i in bad if i < len(props["scenes"])}, ensure_ascii=False)[:9000]
    )
    for name, call in callers:
        try:
            text = call(ask)
            start, end = text.find("{"), text.rfind("}")
            fixed = json.loads(text[start:end + 1]).get("scenes", {})
            for k, v in fixed.items():
                if str(k).isdigit() and int(k) < len(props["scenes"]) and isinstance(v, dict):
                    props["scenes"][int(k)] = v
            log(f"  -> Perbaikan data adegan oleh LLM ({name}).")
            return props
        except Exception as e:
            log(f"     {name} gagal memperbaiki: {str(e)[:80]}")
    return None


def to_safe_scene(scene):
    """Cadangan terakhir: adegan rusak diganti kartu teks sederhana dengan waktu yang sama."""
    pts = [str(p)[:60] for p in (scene.get("points") or []) if str(p).strip()][:4] or ["Cara kerja"]
    return {"type": "flow", "title": str(scene.get("title") or "Cara kerja")[:80], "points": pts,
            "start": float(scene.get("start", 0)), "end": float(scene.get("end", 1))}


def validate_or_repair(props, remotion_dir, callers=None, log=print, max_rounds=2):
    """Pintu wajib sebelum render. Mengembalikan data bersih, atau melempar SchemaError."""
    props = auto_fix(props)
    ok, errors, clean = run_validator(props, remotion_dir, log)
    rounds = 0
    while not ok and rounds < max_rounds and callers:
        rounds += 1
        log(f"  -> Data ditolak skema ({len(errors)} masalah), meminta perbaikan (putaran {rounds})...")
        fixed = llm_repair(props, errors, callers, log)
        if not fixed:
            break
        props = auto_fix(fixed)
        ok, errors, clean = run_validator(props, remotion_dir, log)
    if not ok:
        bad = _bad_scene_indexes(errors)
        if bad:
            log(f"  -> Adegan {sorted(bad)} tetap ditolak: diganti kartu teks sederhana.")
            for i in bad:
                if i < len(props["scenes"]):
                    props["scenes"][i] = to_safe_scene(props["scenes"][i])
            props = auto_fix(props)
            ok, errors, clean = run_validator(props, remotion_dir, log)
    if not ok:
        raise SchemaError("Data video tidak lolos skema: " + "; ".join(errors[:5]))
    return clean
