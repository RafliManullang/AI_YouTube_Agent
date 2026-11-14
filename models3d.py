"""Model 3D gratis (hewan, orang, kendaraan, mesin, benda sehari-hari) dari Poly Pizza.

Perlu kunci gratis: daftar di https://poly.pizza lalu buat kunci di halaman Settings > API,
tulis di file .env sebagai POLYPIZZA_KEY=... Tanpa kunci, bagian ini dilewati dan agen memakai
gambar kartun 3D buatan AI. Semua model berlisensi CC0 atau CC-BY; yang CC-BY dicantumkan di deskripsi."""

import os
import re

import requests

API = "https://api.poly.pizza/v1.1/search/"


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "model"


def fetch_model(subject, public_dir, key, log=print):
    """Cari dan unduh satu model 3D (.glb) untuk kata kunci Inggris. Hasil: (nama_file, kredit) atau (None, None)."""
    subject = (subject or "").strip()
    if not subject or not key:
        return None, None
    folder = os.path.join(public_dir, "models")
    os.makedirs(folder, exist_ok=True)
    # satu benda utama = satu model sepanjang video ("cruise ship" dan "sailing ship" memakai kapal yang sama)
    name = f"{_slug(subject.split()[-1])}.glb"
    path = os.path.join(folder, name)
    credit_path = path + ".txt"
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        credit = open(credit_path, encoding="utf-8").read().strip() if os.path.exists(credit_path) else ""
        return f"models/{name}", credit
    try:
        res = requests.get(API + requests.utils.quote(subject), params={"Limit": 8},
                           headers={"x-auth-token": key}, timeout=30)
        if res.status_code != 200:
            log(f"  -> Model 3D '{subject}' tidak ditemukan ({res.status_code}).")
            return None, None
        results = res.json().get("results") or []
        # utamakan model yang judulnya memuat kata kunci
        # hanya terima model yang judulnya memuat kata kunci (kalau tidak, hasilnya sering ngawur: pisau untuk "tinta")
        words = [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in subject.lower().split() if len(w) >= 3]
        results = [r for r in results if any(w in str(r.get("Title", "")).lower() for w in words)]
        # buang model yang jelas beda benda (pemanas ruangan untuk "iron", dsb.)
        bad = ("heater", "radiator", "fireplace", "man", "golem", "ore", "ingot", "bar")
        results = [r for r in results if not any(b in re.findall(r"[a-z]+", str(r.get("Title", "")).lower()) and b not in words for b in bad)]
        for r in results:
            url = r.get("Download")
            if not url:
                continue
            dl = requests.get(url, timeout=90)
            if dl.status_code == 200 and len(dl.content) > 2000 and dl.content[:4] == b"glTF":
                with open(path, "wb") as f:
                    f.write(dl.content)
                creator = (r.get("Creator") or {}).get("Username") if isinstance(r.get("Creator"), dict) else r.get("Creator")
                lic = str(r.get("Licence") or r.get("License") or "")
                credit = ""
                if "0" not in lic.split()[-1:] and "cc0" not in lic.lower():
                    credit = f'"{r.get("Title", subject)}" oleh {creator or "kreator"} via Poly Pizza ({lic or "CC-BY"})'
                with open(credit_path, "w", encoding="utf-8") as f:
                    f.write(credit)
                return f"models/{name}", credit
    except Exception as e:
        log(f"  -> Model 3D '{subject}' gagal diunduh: {str(e)[:80]}")
    return None, None
