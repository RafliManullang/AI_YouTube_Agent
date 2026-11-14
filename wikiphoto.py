"""Foto asli bebas pakai dari Wikimedia Commons (tanpa kunci, gratis).

Dipakai untuk adegan 'story' (kisah nyata) supaya muncul foto dokumentasi sungguhan di bingkai polaroid.
Hanya foto berlisensi terbuka (domain publik, CC0, CC BY, CC BY-SA) yang diambil; nama pembuat foto
dicantumkan di deskripsi video. Kalau tidak ketemu yang cocok, adegan memakai gambar kartun/animasi 3D."""

import html
import os
import re

import requests

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "AIYouTubeAgent/1.0 (https://github.com/RafliManullang/AI_YouTube_Agent; educational)"}
OK_LICENSE = ("cc0", "public domain", "pd", "cc by", "cc-by")
STOP = {"the", "of", "in", "a", "an", "and", "at", "on", "for", "to"}


def _words(text):
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOP and len(w) > 2]


def _strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch_photo(query, public_dir, index, log=print):
    """Cari satu foto asli untuk kata kunci Inggris. Hasil: (nama_file, kredit) atau (None, None)."""
    query = (query or "").strip()
    if not query:
        return None, None
    try:
        res = requests.get(API, headers=HEADERS, timeout=30, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query + " filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": 10, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": 900})
        if res.status_code != 200:
            log(f"  -> Foto asli '{query}' tidak ditemukan ({res.status_code}).")
            return None, None
        pages = list((res.json().get("query") or {}).get("pages", {}).values())
        key = _words(query)
        best = None
        for pg in sorted(pages, key=lambda p: p.get("index", 99)):
            info = (pg.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            lic = (meta.get("LicenseShortName", {}).get("value") or "").lower()
            if not any(lic.startswith(x) or x in lic for x in OK_LICENSE) or "nc" in lic.split() or "-nc" in lic:
                continue
            if info.get("mime") not in ("image/jpeg", "image/png") or (info.get("width") or 0) < 500:
                continue
            title = (pg.get("title") or "").lower()
            desc = _strip((meta.get("ImageDescription") or {}).get("value")).lower()
            hit = sum(1 for w in set(key) if w in title or w in desc)
            if key and hit < max(1, (len(set(key)) + 1) // 2):
                continue  # foto harus benar-benar memuat kata kunci (cegah foto asal-asalan)
            best = (info, meta, pg)
            break
        if not best:
            log(f"  -> Foto asli untuk '{query}' tidak ada yang cocok.")
            return None, None
        info, meta, pg = best
        url = info.get("thumburl") or info.get("url")
        img = requests.get(url, headers=HEADERS, timeout=60)
        if img.status_code != 200 or len(img.content) < 5000:
            return None, None
        name = f"photo_{index}.jpg"
        with open(os.path.join(public_dir, name), "wb") as f:
            f.write(img.content)
        artist = _strip((meta.get("Artist") or {}).get("value")) or "tidak diketahui"
        lic = (meta.get("LicenseShortName") or {}).get("value") or ""
        credit = f"{pg.get('title', '').replace('File:', '')} oleh {artist[:60]} ({lic}), Wikimedia Commons"
        log(f"  -> Foto asli ditemukan untuk '{query}'.")
        return name, credit
    except Exception as e:
        log(f"  -> Foto asli '{query}' gagal diambil ({str(e)[:60]}).")
        return None, None
