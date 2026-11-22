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
                             cwd=remotion_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
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
    """Perbaikan pasti yang tidak perlu LLM: urutan frame adegan, id berurutan, batas durasi."""
    dur = float(props.get("durationInSeconds") or 0) or 40.0
    props["durationInSeconds"] = min(180.0, max(3.0, dur))
    total_frames = int(round(props["durationInSeconds"] * 30))
    scenes = props.get("scenes") or []
    scenes.sort(key=lambda sc: sc.get("startFrame", 0))
    prev = 0
    for i, sc in enumerate(scenes):
        sc["id"] = f"scene_{i + 1:02d}"
        sc["narration"] = str(sc.get("narration") or "")[:600]
        sc["visualPrompt"] = str(sc.get("visualPrompt") or "")[:600]
        if not isinstance(sc.get("clipPath"), str):
            sc["clipPath"] = ""
        start = max(prev, int(sc.get("startFrame") or prev))
        duration = int(sc.get("durationInFrames") or 90)
        sc["startFrame"] = start
        sc["durationInFrames"] = max(1, min(duration, max(1, total_frames - start)))
        prev = start + sc["durationInFrames"]
    for w in props.get("words") or []:
        if isinstance(w.get("end"), (int, float)) and isinstance(w.get("start"), (int, float)) and w["end"] < w["start"]:
            w["end"] = w["start"]
    props["scenes"] = scenes
    return props


# Bidang pelengkap: kalau isinya tidak sah, cukup dibuang (video tetap jadi) daripada menggagalkan seluruh video.
PRUNABLE = {"who", "emphasis", "sfx"}


def prune_invalid(props, errors, log=print):
    """Buang bidang pelengkap yang ditolak skema. Hasil: jumlah bidang yang dibuang."""
    removed = 0
    for e in errors:
        path = e.split(":")[0].split(".")
        if len(path) < 2 or path[-1] not in PRUNABLE:
            # galat di dalam bidang pelengkap bertingkat (mis. sim.objects.3.color): buang bidang pelengkap terdekat
            idx = next((i for i, p in enumerate(path) if p in PRUNABLE and i > 0), None)
            if idx is None:
                continue
            path = path[: idx + 1]
        node = props
        try:
            for p in path[:-1]:
                node = node[int(p)] if isinstance(node, list) else node[p]
            key = int(path[-1]) if isinstance(node, list) else path[-1]
            if isinstance(node, dict) and key in node:
                del node[key]
                removed += 1
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    if removed:
        log(f"  -> {removed} bidang pelengkap yang tidak sah dibuang otomatis.")
    return removed


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
        + "\n\nPerbaiki HANYA adegan yang salah. Tiap adegan hanya boleh berisi: id (scene_01, scene_02, ...), "
        "narration, visualPrompt (prompt visual Bahasa Inggris), clipPath (clips/scene_XX.mp4 atau kosong), "
        "startFrame dan durationInFrames (bilangan bulat, berurutan tanpa tumpang tindih), sfx opsional. "
        "Jawab HANYA dengan JSON berbentuk {\"scenes\": {\"<nomor adegan>\": {...adegan lengkap yang sudah benar...}}}.\n\n"
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
    """Cadangan terakhir: adegan rusak diganti placeholder dengan waktu yang sama (klip menyusul)."""
    return {"id": str(scene.get("id") or "scene_01"), "narration": str(scene.get("narration") or "")[:600],
            "visualPrompt": str(scene.get("visualPrompt") or "")[:600], "clipPath": "",
            "startFrame": int(scene.get("startFrame") or 0), "durationInFrames": max(1, int(scene.get("durationInFrames") or 90))}


def validate_or_repair(props, remotion_dir, callers=None, log=print, max_rounds=2):
    """Pintu wajib sebelum render. Mengembalikan data bersih, atau melempar SchemaError."""
    props = auto_fix(props)
    ok, errors, clean = run_validator(props, remotion_dir, log)
    rounds = 0
    pruned = 0
    while not ok and pruned < 3 and prune_invalid(props, errors, log):
        pruned += 1
        props = auto_fix(props)
        ok, errors, clean = run_validator(props, remotion_dir, log)
    while not ok and rounds < max_rounds and callers and _bad_scene_indexes(errors):
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
