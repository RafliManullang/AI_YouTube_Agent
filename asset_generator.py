"""Storyboard hybrid: satu palet per topik, gambar raster untuk anatomi, JSON untuk gerak."""
import base64
import hashlib
import io
import json
import math
import os
import re
import time

import requests
from huggingface_hub import InferenceClient
from PIL import Image, ImageOps

VIEWS = {"01_exterior": "exterior", "02_analogy": "analogy", "03_cutaway": "cutaway", "04_closeup": "closeup"}
MODES = {"exterior": "Full object working in its real environment",
         "analogy": "An everyday physical analogy in a warm studio scene",
         "cutaway": "Technical cross-section showing distinct internal parts on a deep slate blueprint background",
         "closeup": "Extreme macro cutaway of the critical moving component"}
MASTER_STYLE_PROMPT = ("Studio-quality cel-shaded technical illustration, bold dark navy outlines (#0f172a), "
                       "crisp vector shadows and dimensional highlights. One centered subject, vertical 9:16. "
                       "Keep top 20% and bottom 25% clear. NO typography, text, labels, letters, numbers or watermark.")
PALETTES = ("amber, cyan and coral", "teal, burnt orange and cream", "cobalt, brass and vermilion")


def topic_seed(title):
    return int.from_bytes(hashlib.sha256(title.encode()).digest()[:4], 'big') % 2147483646


def build_image_prompt(subject, view, seed, retry=False):
    return (f"{subject}. {MODES[view]}. {MASTER_STYLE_PROMPT} Shared palette: {PALETTES[seed % len(PALETTES)]}."
            + (" Clean blank surfaces. Absolutely zero typography or markings." if retry else ""))


def validate_assets(spec):
    if not isinstance(spec, list) or len(spec) not in (3, 4):
        raise ValueError('Storyboard membutuhkan 3–4 assets.')
    found = {}
    for item in spec:
        if not isinstance(item, dict):
            raise ValueError('Spesifikasi aset bukan objek.')
        key = item.get('id')
        if not isinstance(key, str) or key not in VIEWS or VIEWS[key] != item.get('view_type') or key in found:
            raise ValueError('ID atau view_type aset tidak valid.')
        if not isinstance(item.get('prompt'), str) or not item['prompt'].strip():
            raise ValueError(f'Deskripsi visual {key} kosong.')
        found[key] = {'id': key, 'view_type': VIEWS[key], 'prompt': item['prompt'].strip()[:500]}
    if not set(list(VIEWS)[:3]) <= found.keys():
        raise ValueError('Aset exterior, analogy dan cutaway wajib ada.')
    return [found[k] for k in VIEWS if k in found]


def clear_assets(directory):
    # Hanya PNG milik generator ini; jangan hapus aset lain milik pengguna.
    for key in VIEWS:
        (directory / f'{key}.png').unlink(missing_ok=True)


def picture_bytes(raw, *, allow_square=False):
    with Image.open(io.BytesIO(raw)) as im:
        if im.width > im.height or (im.width == im.height and not allow_square) or im.width < 256 or im.width * im.height > 24_000_000:
            raise ValueError('Provider tidak mengembalikan ilustrasi potret yang sesuai.')
        # Vision dan Remotion harus melihat crop yang persis sama.
        canvas = ImageOps.fit(im.convert('RGB'), (1080, 1920), method=Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        canvas.save(buf, format='PNG')
        return buf.getvalue()


GEMINI_IMAGE_MODELS = (
    'gemini-3.1-flash-image', 'gemini-3.1-flash-lite-image',
    'gemini-2.5-flash-image', 'gemini-3-pro-image',
)
HF_DEFAULT_MODEL = 'black-forest-labs/FLUX.1-schnell'


def generate_with_gemini_image(client, prompt, model_name):
    from google.genai import types

    response = client.models.generate_content(
        model=model_name, contents=prompt,
        config=types.GenerateContentConfig(response_modalities=['IMAGE'],
                                          image_config=types.ImageConfig(aspect_ratio='9:16')),
    )
    for candidate in response.candidates or ():
        if not candidate.content:
            continue
        for part in candidate.content.parts or ():
            blob = part.inline_data
            if blob and blob.data and (not blob.mime_type or blob.mime_type.startswith('image/')):
                return blob.data
    raise ValueError('Gemini tidak mengembalikan data gambar.')


def generate_with_hf_flux(prompt, seed):
    token = os.getenv('HF_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Fallback Hugging Face tidak tersedia: HF_TOKEN belum diisi di .env.')
    model = os.getenv('HF_IMAGE_MODEL', '').strip() or HF_DEFAULT_MODEL
    client = InferenceClient(provider='auto', api_key=token, timeout=120)
    try:
        image = client.text_to_image(prompt, model=model, width=768, height=1344, seed=seed)
    except Exception as exc:
        # Jangan ulangi masalah token, kuota, atau jaringan dengan parameter yang sama.
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status not in (400, 422) and not (isinstance(exc, (ValueError, TypeError)) and
                any(p in str(exc).lower() for p in ('width', 'height', 'size', 'dimension', 'seed'))):
            raise
        image = client.text_to_image(prompt, model=model)
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    return buf.getvalue()


def generate_with_cloudflare_flux(prompt):
    account = os.getenv('CF_ACCOUNT_ID', '').strip()
    token = os.getenv('CF_API_TOKEN', '').strip()
    if not account or not token:
        raise RuntimeError('CF_ACCOUNT_ID / CF_API_TOKEN belum diisi di .env.')
    url = f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell'
    response = requests.post(url, headers={'Authorization': f'Bearer {token}'},
                             json={'prompt': prompt, 'steps': 4}, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if payload.get('success') is False or not (payload.get('result') or {}).get('image'):
        raise ValueError('Cloudflare tidak mengembalikan gambar.')
    return base64.b64decode(payload['result']['image'], validate=True)


def skip_gemini_image():
    return os.getenv('SKIP_GEMINI_IMAGE', '').strip() == '1'


def generate_picture(prompt, seed, clients, log):
    if os.getenv('CF_ACCOUNT_ID', '').strip() and os.getenv('CF_API_TOKEN', '').strip():
        try:
            return picture_bytes(generate_with_cloudflare_flux(prompt), allow_square=True)
        except Exception as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            log(f'  -> Cloudflare Workers AI gagal ({status or type(exc).__name__}); mencoba provider berikutnya.')
    if skip_gemini_image():
        log('  -> Gemini Image dilewati; memakai Hugging Face.')
        return picture_bytes(generate_with_hf_flux(prompt, seed), allow_square=True)
    # Baca override saat dipanggil: .env baru dimuat setelah modul ini diimpor.
    primary = os.getenv('IMAGE_MODEL', '').strip() or GEMINI_IMAGE_MODELS[0]
    models = dict.fromkeys((primary, *GEMINI_IMAGE_MODELS[1:]))
    for index, client in enumerate(clients, 1):
        for model in models:
            try:
                return picture_bytes(generate_with_gemini_image(client, prompt, model))
            except Exception as exc:
                detail = re.sub(r'AIza[\w-]+', '[redacted]', str(exc))
                log(f'  -> Gemini Image {model} (key #{index}) gagal: {type(exc).__name__}: {detail[:400]}')
    log('  -> Beralih ke Hugging Face.')
    return picture_bytes(generate_with_hf_flux(prompt, seed), allow_square=True)


def locate(vision, png, components):
    if not vision:
        raise RuntimeError('Vision tidak tersedia; periksa GEMINI_API_KEY dan SDK Gemini.')
    prompt = ('Cari titik tengah komponen berikut pada gambar: ' + json.dumps(components, ensure_ascii=False) +
              '. Abaikan komponen yang tidak terlihat, jangan menebak. JSON saja: '
              '{"has_garbled_text":boolean,"anchors":{"nama persis":[x,y]}}. '
              'x,y ternormalisasi 0..1 dari kiri atas. Tandai teks/huruf/angka tercetak yang bocor.')
    obj = json.loads(vision(prompt, [png]))
    if not isinstance(obj, dict) or type(obj.get('has_garbled_text')) is not bool or not isinstance(obj.get('anchors'), dict):
        raise ValueError('JSON Vision tidak valid.')
    anchors = {}
    for name in components:
        xy = obj['anchors'].get(name)
        if isinstance(xy, list) and len(xy) == 2 and all(type(v) in (int, float) and 0 <= v <= 1 for v in xy):
            anchors[name] = xy
    return {'has_garbled_text': obj['has_garbled_text'], 'anchors': anchors}


def generate_scene_assets(spec, directory, title, components, cache, checkpoint, clients=(), vision=None, log=print):
    """Checkpoint dipanggil setelah setiap kandidat dan keputusan Vision, sebelum tahap berikutnya."""
    spec = validate_assets(spec)
    directory.mkdir(parents=True, exist_ok=True)
    seed = topic_seed(title)
    asset_map = cache.setdefault('assetMap', {})
    records = cache.setdefault('images', {})
    generated = False
    for item in spec:
        key, view = item['id'], item['view_type']
        path = directory / f'{key}.png'
        record = records.setdefault(key, {})
        png = path.read_bytes() if path.exists() else b''
        if not png or hashlib.sha256(png).hexdigest() != record.get('sha256'):
            record.clear()
            asset_map.pop(key, None)
            png = b''
        while True:
            report = record.get('vision')
            rejected = report and report['has_garbled_text']
            if rejected and record['attempt'] >= 1:
                raise RuntimeError(f'{key}: Vision masih menemukan teks setelah satu regenerasi. Tinjau {path}.')
            if not png or rejected:
                attempt = int(bool(rejected))
                log(f'  -> Membuat {key} (seed {seed + attempt})')
                if generated:
                    time.sleep(2)  # hanya antar-generasi, bukan saat membaca checkpoint
                png = generate_picture(build_image_prompt(item['prompt'], view, seed, bool(attempt)), seed + attempt, clients, log)
                generated = True
                pending = path.with_suffix('.tmp')
                pending.write_bytes(png)
                pending.replace(path)
                record.update(sha256=hashlib.sha256(png).hexdigest(), attempt=attempt)
                record.pop('vision', None)
                checkpoint()  # Vision gagal? Pertahankan kandidat tanpa membayar gambar lagi.
            if view == 'cutaway' and 'vision' not in record:
                try:
                    record['vision'] = locate(vision, png, components)
                except Exception as exc:
                    detail = re.sub(r'AIza[\w-]+', '[redacted]', str(exc))
                    log(f'  -> Vision dilewati ({detail[:200]}), memakai koordinat bawaan. Teks gambar belum diperiksa.')
                    record['vision'] = {'anchors': {}, 'has_garbled_text': False, 'skipped': True}
                checkpoint()
                continue
            break
        relative = f'assets/{key}.png'
        if asset_map.get(key) != relative:
            asset_map[key] = relative
            checkpoint()
    return dict(asset_map), records['03_cutaway']['vision']['anchors']


def bounded(raw, default, lo, hi):
    if type(raw) not in (int, float) or not math.isfinite(raw):
        return default
    return max(lo, min(hi, raw))


def storyboard(data, timings):
    scenes = data['scenes']
    spec = data.get('assets')
    if not spec:  # migrasi checkpoint naskah pra-hybrid, tanpa mengulang TTS/editor
        analogy = next((s['narration'] for s,t in zip(scenes, timings) if t['mode'] == 'analogi'), data['title'])
        desc = [data['title'], analogy, data['title'] + ': ' + ', '.join(s['title'] for s in scenes)]
        spec = [dict(id=k, view_type=VIEWS[k], prompt=p) for k,p in zip(VIEWS, desc)]
    spec = validate_assets(spec)
    ids = {a['id'] for a in spec}
    shots = []
    for i, (s, t) in enumerate(zip(scenes, timings)):
        key = s.get('asset_id')
        if i in (0, len(scenes)-1):
            key = '01_exterior'
        elif t['mode'] == 'analogi':
            key = '02_analogy'
        elif not isinstance(key, str) or key not in ids:
            key = '03_cutaway'
        c = s.get('camera') if isinstance(s.get('camera'), dict) else {}
        o = s.get('overlay') if isinstance(s.get('overlay'), dict) else {}
        label = str(o.get('label') or next(iter(t['labels']), s['title']))[:32]
        shots.append({'asset_id': key, 'component': str(s.get('component') or label)[:60],
            'camera': {'fromScale': bounded(c.get('fromScale'), 1, 1, 2.2), 'toScale': bounded(c.get('toScale'), 1.25, 1, 2.2),
                       'focusX': bounded(c.get('focusX'), .5, 0, 1), 'focusY': bounded(c.get('focusY'), .5, 0, 1)},
            'overlay': {'label': label, 'type': o.get('type') if o.get('type') in ('heat_pulse','flow_arrows') else 'badge_only',
                        'direction': o.get('direction') if o.get('direction') in ('down','left','right') else 'up',
                        'accentColor': o['accentColor'] if re.fullmatch(r'#[0-9a-fA-F]{6}', str(o.get('accentColor'))) else '#38bdf8',
                        'targetX': bounded(o.get('targetX'), 540, 0, 1080), 'targetY': bounded(o.get('targetY'), 960, 0, 1920)}})
    return spec, shots


def apply_anchors(shots, anchors):
    for shot in shots:
        if shot['asset_id'] != '03_cutaway':
            continue
        point = anchors.get(shot['component'])
        x, y = point or (.5, .5)
        shot['camera'].update(focusX=x, focusY=y)
        shot['overlay'].update(targetX=x*1080, targetY=y*1920)
        if not point:  # Jangan menunjuk ruang kosong jika komponen tidak dikenali.
            shot['unlocated'] = True
            shot['overlay']['type'] = 'badge_only'
