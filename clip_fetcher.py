import os
import re
from pathlib import Path
import requests

STOPWORDS = {
    "photorealistic", "vertical", "shot", "close", "closeup", "wide", "cinematic",
    "light", "lighting", "camera", "slow", "push", "zoom", "pan", "the", "and",
    "with", "from", "inside", "showing", "view", "angle", "high", "resolution",
    "detailed", "realistic", "bright", "dark", "ultra", "macro", "scene", "video",
}


def clear_clips(clips_dir: Path):
    """Hapus klip sisa topik sebelumnya agar tidak terpakai di video baru."""
    if not clips_dir.exists():
        return
    for p in clips_dir.iterdir():
        if p.is_file() and p.name.startswith("scene_"):
            try:
                p.unlink()
            except OSError:
                pass


def _has_clip(clips_dir: Path, scene_id: str) -> bool:
    for ext in (".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg"):
        p = clips_dir / f"{scene_id}{ext}"
        if p.exists() and p.stat().st_size > 10_000:
            return True
    return False


def _build_queries(prompt: str, title: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", prompt.lower())
    picked = [w for w in words if len(w) > 2 and w not in STOPWORDS]
    candidates = []
    if len(picked) >= 2:
        candidates.append(" ".join(picked[:2]))
    for w in picked[:3]:
        candidates.append(w)
    if title:
        t_words = [w for w in re.findall(r"[a-zA-Z]+", title.lower()) if len(w) > 2]
        if t_words:
            candidates.append(" ".join(t_words[:2]))
    candidates.extend(["water flow", "engineering machine", "science technology"])
    seen, out = set(), []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _download(url: str, out_path: Path) -> bool:
    res = requests.get(url, timeout=90)
    res.raise_for_status()
    if len(res.content) < 10_000:
        return False
    out_path.write_bytes(res.content)
    return True


def _fetch_pexels(queries: list[str], out_path: Path, pexels_key: str, used_ids: set) -> str:
    headers = {"Authorization": pexels_key}
    for orient in ("portrait", None):
        for q in queries:
            params = {"query": q, "per_page": 5}
            if orient:
                params["orientation"] = orient
            res = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=30)
            if res.status_code != 200:
                raise RuntimeError(f"Pexels {res.status_code}: {res.text[:100]}")
            for vid in res.json().get("videos") or []:
                vid_id = f"pexels_{vid.get('id')}"
                if vid_id in used_ids:
                    continue
                files = [f for f in vid.get("video_files") or [] if f.get("file_type") == "video/mp4" and f.get("link")]
                files.sort(key=lambda f: abs((f.get("width") or 0) - 720))
                if files and _download(files[0]["link"], out_path):
                    used_ids.add(vid_id)
                    return q
    return ""


def _fetch_pixabay(queries: list[str], out_path: Path, pixabay_key: str, used_ids: set) -> str:
    for q in queries:
        res = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": pixabay_key, "q": q, "per_page": 5},
            timeout=30,
        )
        if res.status_code != 200:
            raise RuntimeError(f"Pixabay {res.status_code}: {res.text[:100]}")
        for hit in res.json().get("hits") or []:
            hit_id = f"pixabay_{hit.get('id')}"
            if hit_id in used_ids:
                continue
            vids = hit.get("videos") or {}
            url = (vids.get("medium") or vids.get("small") or vids.get("large") or {}).get("url")
            if url and _download(url, out_path):
                used_ids.add(hit_id)
                return q
    return ""


def fill_clips(scenes: list, clips_dir: Path, log=print):
    """Isi semua klip yang belum ada di video_engine/public/clips/ secara otomatis."""
    clips_dir.mkdir(parents=True, exist_ok=True)
    pexels_key = (os.getenv("PEXELS_API_KEY") or "").strip()
    pixabay_key = (os.getenv("PIXABAY_API_KEY") or "").strip()

    if not pexels_key and not pixabay_key:
        log("  -> PEXELS_API_KEY dan PIXABAY_API_KEY kosong di .env.")
        return

    log("[3/5] Mengunduh klip otomatis dari Pexels/Pixabay...")
    used_ids = set()
    for i, sc in enumerate(scenes):
        scene_id = sc.get("id") or f"scene_{i + 1:02d}"
        if _has_clip(clips_dir, scene_id):
            continue
        queries = _build_queries(sc.get("visualPrompt") or "", sc.get("title") or "")
        out_path = clips_dir / f"{scene_id}.mp4"
        matched = ""

        if pexels_key and not matched:
            try:
                matched = _fetch_pexels(queries, out_path, pexels_key, used_ids)
                if matched:
                    log(f"  -> {scene_id}.mp4 diunduh via Pexels ({matched})")
            except Exception as e:
                log(f"  -> Pexels error ({scene_id}): {str(e)[:90]}")

        if pixabay_key and not matched:
            try:
                matched = _fetch_pixabay(queries, out_path, pixabay_key, used_ids)
                if matched:
                    log(f"  -> {scene_id}.mp4 diunduh via Pixabay ({matched})")
            except Exception as e:
                log(f"  -> Pixabay error ({scene_id}): {str(e)[:90]}")

        if not matched:
            log(f"  -> Gagal mengunduh {scene_id}.")
