import os
import re
from pathlib import Path
import requests

STOPWORDS = {
    "photorealistic", "vertical", "9:16", "shot", "close-up", "closeup", "close", "up", "wide",
    "cinematic", "light", "lighting", "camera", "slow", "push-in", "zoom", "pan",
    "of", "the", "a", "an", "in", "on", "at", "with", "and", "to", "from", "inside",
    "showing", "view", "angle", "high", "resolution", "detailed", "realistic",
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
        if p.exists() and p.stat().st_size > 1000:
            return True
    return False


def _short_query(prompt: str, fallback: str) -> str:
    words = re.findall(r"[a-zA-Z]+", prompt.lower())
    picked = [w for w in words if len(w) > 2 and w not in STOPWORDS]
    return " ".join(picked[:3]) if picked else fallback


def _fetch_fal(prompt: str, out_path: Path, fal_key: str) -> bool:
    model = os.getenv("FAL_MODEL", "fal-ai/flux/dev").strip()
    url = f"https://fal.run/{model}"
    res = requests.post(
        url,
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json={"prompt": prompt, "image_size": "portrait_16_9", "num_images": 1},
        timeout=120,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Fal {res.status_code}: {res.text[:120]}")
    images = res.json().get("images") or []
    if not images:
        return False
    img_res = requests.get(images[0]["url"], timeout=60)
    img_res.raise_for_status()
    out_path.write_bytes(img_res.content)
    return True


def _fetch_gemini_image(prompt: str, out_path: Path, api_key: str) -> bool:
    from google import genai
    from google.genai import types

    model = os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-002").strip()
    client = genai.Client(api_key=api_key)
    res = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="9:16",
            output_mime_type="image/png",
        ),
    )
    if not res.generated_images:
        return False
    out_path.write_bytes(res.generated_images[0].image.image_bytes)
    return True


def _fetch_pexels(query: str, out_path: Path, pexels_key: str) -> bool:
    res = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": pexels_key},
        params={"query": query, "orientation": "portrait", "per_page": 3},
        timeout=30,
    )
    res.raise_for_status()
    for vid in res.json().get("videos") or []:
        files = [f for f in vid.get("video_files") or [] if f.get("file_type") == "video/mp4"]
        files.sort(key=lambda f: abs((f.get("width") or 0) - 720))
        if files:
            dl = requests.get(files[0]["link"], timeout=90)
            dl.raise_for_status()
            out_path.write_bytes(dl.content)
            return True
    return False


def _fetch_pixabay(query: str, out_path: Path, pixabay_key: str) -> bool:
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": pixabay_key, "q": query, "per_page": 3},
        timeout=30,
    )
    res.raise_for_status()
    for hit in res.json().get("hits") or []:
        vids = hit.get("videos") or {}
        url = (vids.get("medium") or vids.get("small") or {}).get("url")
        if url:
            dl = requests.get(url, timeout=90)
            dl.raise_for_status()
            out_path.write_bytes(dl.content)
            return True
    return False


def fill_clips(scenes: list, clips_dir: Path, log=print):
    """Isi semua klip yang belum ada di video_engine/public/clips/ secara otomatis."""
    clips_dir.mkdir(parents=True, exist_ok=True)
    fal_key = (os.getenv("FAL_KEY") or "").strip()
    gemini_key = ((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").split(",")[0]).strip()
    pexels_key = (os.getenv("PEXELS_API_KEY") or "").strip()
    pixabay_key = (os.getenv("PIXABAY_API_KEY") or "").strip()

    if not any((fal_key, gemini_key, pexels_key, pixabay_key)):
        log("  -> Tidak ada API key visual (FAL_KEY / GEMINI_API_KEY / PEXELS_API_KEY / PIXABAY_API_KEY) di .env.")
        return

    log("[3/5] Mengisi klip visual otomatis untuk setiap adegan...")
    for i, sc in enumerate(scenes):
        scene_id = sc.get("id") or f"scene_{i + 1:02d}"
        if _has_clip(clips_dir, scene_id):
            continue
        prompt = sc.get("visualPrompt") or sc.get("title") or "science mechanism"
        query = _short_query(prompt, sc.get("title") or "science")
        ok = False

        if fal_key and not ok:
            try:
                ok = _fetch_fal(prompt, clips_dir / f"{scene_id}.png", fal_key)
                if ok:
                    log(f"  -> {scene_id}.png dibuat via Fal.ai")
            except Exception as e:
                log(f"  -> Fal gagal untuk {scene_id}: {str(e)[:90]}")

        if gemini_key and gemini_key != "ISI_KEY_DI_SINI" and not ok:
            try:
                ok = _fetch_gemini_image(prompt, clips_dir / f"{scene_id}.png", gemini_key)
                if ok:
                    log(f"  -> {scene_id}.png dibuat via Gemini Imagen")
            except Exception as e:
                log(f"  -> Gemini Imagen dilewati untuk {scene_id}: {str(e)[:90]}")

        if pexels_key and not ok:
            try:
                ok = _fetch_pexels(query, clips_dir / f"{scene_id}.mp4", pexels_key)
                if ok:
                    log(f"  -> {scene_id}.mp4 diunduh via Pexels ({query})")
            except Exception as e:
                log(f"  -> Pexels gagal untuk {scene_id}: {str(e)[:90]}")

        if pixabay_key and not ok:
            try:
                ok = _fetch_pixabay(query, clips_dir / f"{scene_id}.mp4", pixabay_key)
                if ok:
                    log(f"  -> {scene_id}.mp4 diunduh via Pixabay ({query})")
            except Exception as e:
                log(f"  -> Pixabay gagal untuk {scene_id}: {str(e)[:90]}")

        if not ok:
            log(f"  -> Gagal mengisi {scene_id} dari semua sumber.")
