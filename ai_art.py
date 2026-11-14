"""Gambar kartun 3D buatan AI untuk adegan animasi.

Urutan sumber (semuanya gratis, yang pertama berhasil dipakai):
1. Gemini gambar (pakai key Gemini yang sama), kalau jatah gratisnya ada.
2. Pollinations (tanpa key).
Kalau semuanya gagal, adegan memakai animasi gambar-kode bawaan (Mechanisms.tsx)."""

import base64
import os
import random
import time
import urllib.parse

import requests

STYLE = (
    "Stylized 3D cartoon render in a modern animated-movie style, vertical 9:16 composition, soft studio lighting, "
    "vivid colors, smooth rounded shapes, subject large and centered with clear readable action that shows exactly "
    "the described scene, simple colorful gradient background, NO text, NO letters, NO watermark. Scene: "
)
GEMINI_IMAGE_MODELS = [
    m for m in [os.getenv("GEMINI_IMAGE_MODEL"), "gemini-2.5-flash-image", "gemini-2.0-flash-preview-image-generation"] if m
]


def _gemini_image(api_key, prompt, path, log):
    for model in GEMINI_IMAGE_MODELS:
        try:
            res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["IMAGE"],
                        "imageConfig": {"aspectRatio": "9:16"},
                    },
                },
                timeout=120,
            )
            if res.status_code != 200:
                log(f"  -> Gambar Gemini ({model}) tidak tersedia: {res.status_code}")
                continue
            for part in res.json()["candidates"][0]["content"]["parts"]:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(inline["data"]))
                    return True
        except Exception as e:
            log(f"  -> Gambar Gemini ({model}) gagal: {str(e)[:80]}")
    return False


def _pollinations(prompt, path, seed, log):
    url = (
        "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
        + f"?width=720&height=1280&nologo=true&model=flux&seed={seed}"
    )
    for attempt in (1, 2):
        try:
            res = requests.get(url, timeout=150)
            if res.status_code == 200 and res.headers.get("content-type", "").startswith("image") and len(res.content) > 8000:
                with open(path, "wb") as f:
                    f.write(res.content)
                return True
            log(f"  -> Pollinations percobaan {attempt}: {res.status_code}")
        except Exception as e:
            log(f"  -> Pollinations percobaan {attempt} gagal: {str(e)[:80]}")
        time.sleep(6)
    return False


def make_image(prompt, path, gemini_key="", log=print):
    full = STYLE + prompt
    seed = random.randrange(1, 10**6)
    if gemini_key and _gemini_image(gemini_key, full, path, log):
        return True
    return _pollinations(full, path, seed, log)
