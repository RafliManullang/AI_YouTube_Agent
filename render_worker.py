"""Pekerja render dengan pemulihan otomatis.

Sebelum render panjang berjalan:
  1. Pemeriksaan kode TypeScript (dry-run, tanpa menghasilkan berkas). Kesalahan dicetak jelas, tapi tidak menghentikan render
     karena bundler Remotion kadang tetap berhasil.
  2. Data wajib lolos gerbang Zod (schema_gate).
Saat render gagal, galat dibaca lalu dipilih tindakan pemulihan yang sesuai, dan render diulang:
  - ditolak skema        -> perbaiki data otomatis lalu validasi ulang
  - WebGL / GPU bermasalah -> ganti mode GL (angle -> swangle -> swiftshader)
  - kehabisan memori     -> render satu bingkai pada satu waktu (concurrency 1)
  - model 3D macet       -> buang model 3D luar dari adegan
  - animasi 3D gagal     -> ganti adegan 3D jadi kartu 2D bawaan
  - masih gagal          -> buang semua visual tambahan (gambar, klip, model) sebagai langkah terakhir
Bentuk dan gerak tidak ditulis oleh LLM (lihat director.py), jadi 'self-healing' di sini memperbaiki lingkungan dan data, bukan karangan kode."""

import json
import os
import shutil
import subprocess
import threading

import schema_gate

GL_LADDER = ["angle", "swangle", "swiftshader"]


def typecheck(remotion_dir, log=print):
    """Dry-run pemeriksaan tipe. Hasil: True kalau bersih."""
    tsc = os.path.join(remotion_dir, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        return True
    try:
        res = subprocess.run([tsc, "--noEmit", "-p", "."], cwd=remotion_dir, capture_output=True, text=True, timeout=240)
    except Exception as e:
        log(f"  -> Pemeriksaan kode dilewati ({str(e)[:60]}).")
        return True
    if res.returncode == 0:
        return True
    errs = [l for l in (res.stdout or "").splitlines() if "error TS" in l][:5]
    log("  -> Pemeriksaan kode menemukan masalah (render tetap dicoba):\n     " + "\n     ".join(errs))
    return False


def _run(cmd, cwd):
    """Jalankan perintah, tampilkan keluaran langsung, dan simpan ekornya untuk dibaca saat gagal."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    tail = []

    def pump():
        for line in proc.stdout:
            print(line, end="", flush=True)
            tail.append(line)
            if len(tail) > 400:
                del tail[:100]

    th = threading.Thread(target=pump, daemon=True)
    th.start()
    code = proc.wait()
    th.join(timeout=5)
    return code, "".join(tail)[-20000:]


def diagnose(output):
    """Baca galat render dan tentukan tindakan pemulihan."""
    low = (output or "").lower()
    if "ditolak skema" in low:
        return "schema"
    if any(k in low for k in ("heap out of memory", "enomem", "sigkill", "out of memory", "std::bad_alloc")):
        return "memory"
    if any(k in low for k in ("webgl", "angle", "gl context", "creating webgl", "swiftshader")):
        return "gl"
    if "delayrender" in low or "timed out" in low or "timeout" in low:
        return "timeout"
    return "generic"


def _strip_models(props):
    n = 0
    for sc in props["scenes"]:
        if sc.pop("model", None):
            n += 1
    return n


def _strip_3d(props):
    n = 0
    for sc in props["scenes"]:
        if sc.pop("sim", None):
            n += 1
            if sc.get("type") == "mechanism" and not sc.get("mechanism"):
                sc["type"] = "flow"
                sc["points"] = [str(i.get("label") or "") for i in (sc.get("items") or [])][:4] or sc.get("points") or ["Cara kerja"]
    return n


def _strip_extras(props):
    for sc in props["scenes"]:
        for k in ("model", "artUrls", "clips", "video", "videoSeconds", "sim"):
            sc.pop(k, None)
        if sc.get("type") in ("mechanism", "footage"):
            sc["type"] = "flow"
            sc["points"] = sc.get("points") or [sc.get("title") or "Cara kerja"]


def render(props, output_mp4, remotion_dir, callers=None, log=print, max_attempts=5):
    """Validasi, lalu render dengan tangga pemulihan. Mengembalikan jalur video; melempar RuntimeError bila semua gagal."""
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("Node.js belum terpasang. Unduh dari https://nodejs.org lalu jalankan ulang.")
    typecheck(remotion_dir, log)
    props_path = os.path.join(remotion_dir, "render_props.json")
    gl_step, concurrency, done = 0, None, set()
    last_out = ""

    for attempt in range(1, max_attempts + 1):
        props = schema_gate.validate_or_repair(props, remotion_dir, callers, log)  # data mentah tidak pernah langsung ke render
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        cmd = [npx, "remotion", "render", "src/index.ts", "ShortsComp", output_mp4, "--props=render_props.json"]
        if any(sc.get("sim") or sc.get("model") for sc in props["scenes"]):
            cmd.append("--gl=" + (os.getenv("GL_MODE") or GL_LADDER[gl_step]))
        if concurrency:
            cmd.append(f"--concurrency={concurrency}")
        code, last_out = _run(cmd, remotion_dir)
        if code == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 10_000:
            if attempt > 1:
                log(f"  -> Render berhasil setelah pemulihan otomatis (percobaan {attempt}).")
            return output_mp4

        kind = diagnose(last_out)
        log(f"  -> Render gagal (percobaan {attempt}/{max_attempts}), jenis masalah: {kind}.")
        if kind == "memory" and "memory" not in done:
            concurrency, _ = 1, done.add("memory")
            log("     Pemulihan: render satu bingkai pada satu waktu.")
        elif kind == "gl" and gl_step < len(GL_LADDER) - 1 and not os.getenv("GL_MODE"):
            gl_step += 1
            log(f"     Pemulihan: ganti mode GL ke {GL_LADDER[gl_step]}.")
        elif kind == "timeout" and "models" not in done and _strip_models(props):
            done.add("models")
            log("     Pemulihan: model 3D luar dibuang dari adegan.")
        elif "3d" not in done and _strip_3d(props):
            done.add("3d")
            log("     Pemulihan: animasi 3D diganti kartu 2D bawaan.")
        elif "extras" not in done:
            done.add("extras")
            _strip_extras(props)
            log("     Pemulihan terakhir: semua visual tambahan dibuang, memakai kartu 2D bawaan.")
        else:
            break
    raise RuntimeError("Render gagal setelah pemulihan otomatis. Galat terakhir:\n" + (last_out or "")[-800:])
