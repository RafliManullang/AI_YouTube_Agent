"""Storyboard hybrid: satu palet per topik, gambar raster untuk anatomi, JSON untuk gerak."""
import hashlib
import io
import json
import math
import os
import re
from urllib.parse import quote

import requests
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


def picture_bytes(raw):
    with Image.open(io.BytesIO(raw)) as im:
        if im.width >= im.height or im.width < 256 or im.width * im.height > 24_000_000:
            raise ValueError('Provider tidak mengembalikan ilustrasi potret yang sesuai.')
        # Vision dan Remotion harus melihat crop yang persis sama.
        canvas = ImageOps.fit(im.convert('RGB'), (1080, 1920), method=Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        canvas.save(buf, format='PNG')
        return buf.getvalue()


def generate_picture(prompt, seed, client, log):
    # Gemini Developer API tidak menerima seed untuk Imagen. Gunakan palet yang sama;
    # Flux di bawah juga mendapat seed numerik.
    if client is not None:
        try:
            result = client.models.generate_images(model=os.getenv('IMAGEN_MODEL') or 'imagen-4.0-generate-001',
                prompt=prompt, config={'number_of_images': 1, 'aspect_ratio': '9:16'})
            return picture_bytes(result.generated_images[0].image.image_bytes)
        except Exception as exc:
            log(f'  -> Imagen gagal ({type(exc).__name__}); mencoba Flux.')
    token = os.getenv('POLLINATIONS_API_KEY')
    endpoint = 'https://gen.pollinations.ai/image/' if token else 'https://image.pollinations.ai/prompt/'
    res = requests.get(endpoint + quote(prompt, safe=''), timeout=90,
                       headers={'Authorization': f'Bearer {token}'} if token else {},
                       params={'width': 1080, 'height': 1920, 'model': 'flux', 'nologo': 'true', 'seed': seed})
    res.raise_for_status()
    return picture_bytes(res.content)


def locate(vision, png, components):
    if not vision:
        raise RuntimeError('Vision untuk validasi cutaway membutuhkan GEMINI_API_KEY. Lanjutkan dengan --resume.')
    prompt = ('Cari titik tengah komponen berikut pada gambar: ' + json.dumps(components, ensure_ascii=False) +
              '. Abaikan komponen yang tidak terlihat, jangan menebak. JSON saja: '
              '{"has_garbled_text":boolean,"anchors":{"nama persis":[x,y]}}. '
              'x,y ternormalisasi 0..1 dari kiri atas. Tandai teks/huruf/angka tercetak yang bocor.')
    obj = json.loads(vision(prompt, [png]))
    if not isinstance(obj, dict) or type(obj.get('has_garbled_text')) is not bool or not isinstance(obj.get('anchors'), dict):
        raise ValueError('JSON Vision tidak valid; ulangi dengan --resume.')
    anchors = {}
    for name in components:
        xy = obj['anchors'].get(name)
        if isinstance(xy, list) and len(xy) == 2 and all(type(v) in (int, float) and 0 <= v <= 1 for v in xy):
            anchors[name] = xy
    return {'has_garbled_text': obj['has_garbled_text'], 'anchors': anchors}


def generate_scene_assets(spec, directory, title, components, cache, checkpoint, client=None, vision=None, log=print):
    """Checkpoint dipanggil setelah setiap kandidat dan keputusan Vision, sebelum tahap berikutnya."""
    spec = validate_assets(spec)
    directory.mkdir(parents=True, exist_ok=True)
    seed = topic_seed(title)
    asset_map = cache.setdefault('assetMap', {})
    records = cache.setdefault('images', {})
    if vision is None and not records.get('03_cutaway', {}).get('vision'):
        raise RuntimeError('GEMINI_API_KEY diperlukan untuk memeriksa cutaway. Gunakan --resume setelah key siap.')
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
                png = generate_picture(build_image_prompt(item['prompt'], view, seed, bool(attempt)), seed + attempt, client, log)
                pending = path.with_suffix('.tmp')
                pending.write_bytes(png)
                pending.replace(path)
                record.update(sha256=hashlib.sha256(png).hexdigest(), attempt=attempt)
                record.pop('vision', None)
                checkpoint()  # Vision gagal? Pertahankan kandidat tanpa membayar gambar lagi.
            if view == 'cutaway' and 'vision' not in record:
                record['vision'] = locate(vision, png, components)
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
