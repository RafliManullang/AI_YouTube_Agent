"""Tahap semi-otomatis: ekspor daftar klip yang dibutuhkan per adegan.

Sistem tidak lagi menyuruh LLM menggambar animasi. LLM hanya menulis naskah
dan prompt visual Bahasa Inggris per adegan. Pengguna membuat/mengkurasi klip
sendiri (tool AI video/gambar apa pun), menaruhnya di video_engine/public/clips/
dengan nama scene_01.mp4, scene_02.mp4, ... (atau .png/.jpg untuk adegan statis),
lalu menjalankan tahap 2 untuk merender.
"""

import html
from pathlib import Path

FPS = 30
CLIP_EXTS = (".mp4", ".png", ".jpg", ".jpeg", ".webp")


def clip_stem(index):
    return f"scene_{index + 1:02d}"


def find_clip(clips_dir, index):
    """Nama file klip untuk adegan index bila sudah ada di folder clips, else None."""
    clips_dir = Path(clips_dir)
    for ext in CLIP_EXTS:
        name = clip_stem(index) + ext
        if (clips_dir / name).is_file():
            return f"clips/{name}"
    return None


def build_clip_plan(scenes, clips_dir):
    """Rencana klip per adegan: frame mulai/durasi mengikuti timing TTS (start/end detik)."""
    plan = []
    for i, scene in enumerate(scenes):
        start = float(scene.get("start") or 0)
        end = float(scene.get("end") or start + 3)
        start_frame = int(round(start * FPS))
        duration = max(1, int(round(end * FPS)) - start_frame)
        plan.append({
            "sceneIndex": i,
            "id": clip_stem(i),
            "clipPath": find_clip(clips_dir, i) or "",
            "startFrame": start_frame,
            "durationInFrames": duration,
            "endFrame": start_frame + duration,
            "seconds": round(duration / FPS, 2),
        })
    if plan:
        plan[0]["startFrame"] = 0
    return plan


def missing_clips(plan):
    return [p for p in plan if not p["clipPath"]]


def write_storyboard(scenes, plan, out_dir, title=""):
    """Tulis storyboard.txt dan storyboard.html. Mengembalikan (txt_path, html_path)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"STORYBOARD — {title or 'Tanpa judul'}", ""]
    cards = []
    for scene, item in zip(scenes, plan):
        target = f"{item['id']}.mp4 (atau .png/.jpg)"
        lines += [
            f"[{item['id']}] {item['seconds']:.1f} detik — simpan sebagai: public/clips/{target}",
            f"Visual prompt (EN): {scene.get('visualPrompt') or ''}",
            f"Narasi: {scene.get('narration') or ''}",
            "",
        ]
        cards.append(
            "<section><h2>{} &middot; {:.1f}s &rarr; <code>public/clips/{}</code></h2>"
            "<p><strong>Visual prompt (EN):</strong> {}</p><p><em>{}</em></p></section>".format(
                html.escape(item["id"]), item["seconds"], html.escape(target),
                html.escape(scene.get("visualPrompt") or ""), html.escape(scene.get("narration") or "")))
    txt_path = out_dir / "storyboard.txt"
    html_path = out_dir / "storyboard.html"
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>Storyboard</title>"
        "<style>body{font-family:system-ui;max-width:760px;margin:2rem auto;padding:0 1rem}"
        "section{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}</style>"
        f"<h1>Storyboard — {html.escape(title or '')}</h1>" + "".join(cards),
        encoding="utf-8")
    return txt_path, html_path
