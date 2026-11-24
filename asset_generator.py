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


EXTERIOR_PROMPT = ("Clean 2D cel-shaded technical illustration of {subject}, isolated on a solid dark slate "
                   "studio background, centered, full object visible, bold dark navy outlines, "
                   "no text, no scenery, no cave, no fantasy background")


STYLE_ANCHOR = ("Style anchor for every image in this video: solid dark slate studio background (#1e293b), "
                "bold dark navy cel-shaded ink outlines, one warm light from the upper left, the main object "
                "always in its exact same signature color in every scene, clean modern educational look. "
                "Never a brick wall, stone wall, cave, orange circle backdrop, or scenery.")


def exterior_prompt(subject):
    return EXTERIOR_PROMPT.format(subject=str(subject).strip()) + " " + STYLE_ANCHOR


def _story_image(data, directory, cache, checkpoint, clients, vision, log, key, subject):
    """Satu gambar bercerita dengan prompt terkunci + cek Vision; kandidat lama dari cache dipakai ulang."""
    path = directory / f'{key}.png'
    record = cache.setdefault(key, {})
    png = path.read_bytes() if path.exists() else b''
    if png and hashlib.sha256(png).hexdigest() == record.get('sha256'):
        return f'assets/{key}.png'
    seed = topic_seed(data['title'] + key)
    log(f'  -> Membuat gambar cerita {key}...')
    png = generate_picture(exterior_prompt(subject), seed, clients, log)
    if vision:
        for attempt in (1, 2):
            try:
                answer = vision(f"Apakah gambar ini jelas menampilkan {subject} tanpa latar aneh? "
                                'Jawab JSON saja: {"ok": boolean}', [png])
                import json as _json
                ok = _json.loads(answer[answer.find('{'):answer.rfind('}') + 1]).get('ok')
            except Exception as exc:
                log(f'  -> Cek Vision {key} dilewati ({str(exc)[:80]}).')
                break
            if ok or attempt == 2:
                break
            log(f'  -> Vision menolak {key}; membuat ulang satu kali...')
            png = generate_picture(exterior_prompt(subject) + ' Show the whole object clearly.', seed + 1, clients, log)
    pending = path.with_suffix('.tmp')
    pending.write_bytes(png)
    pending.replace(path)
    record.update(sha256=hashlib.sha256(png).hexdigest())
    checkpoint()
    return f'assets/{key}.png'


def generate_story_images(data, directory, cache, checkpoint, clients=(), vision=None, log=print):
    """3 gambar bercerita: hook aksi (benda bekerja), analogi, dan payoff (hasil akhir)."""
    directory.mkdir(parents=True, exist_ok=True)
    by_id = {a.get('id'): a for a in data.get('assets') or [] if isinstance(a, dict)}
    title = data['title']
    analogy_scene = next((s for s in data['scenes'] if 'ibarat' in (s.get('narration') or '').lower()
                          or 'analogi' in (s.get('title') or '').lower()), None)
    analogy_subject = (by_id.get('02_analogy') or {}).get('prompt') or (
        analogy_scene['narration'] if analogy_scene else title + ' everyday analogy')
    return {
        'exterior': _story_image(data, directory, cache, checkpoint, clients, vision, log, '01_exterior',
                                 (by_id.get('01_exterior') or {}).get('prompt') or
                                 title + ', together in ONE frame with the real object it acts on, positioned '
                                 'against that target and actively starting its real job on it - the interaction '
                                 'between the two objects clearly visible, never the object alone on an empty floor'),
        'analogy': _story_image(data, directory, cache, checkpoint, clients, vision, log, '02_analogy', analogy_subject),
        'payoff': _story_image(data, directory, cache, checkpoint, clients, vision, log, '03_payoff',
                               (by_id.get('04_closeup') or {}).get('prompt') or
                               title + ', the SAME object and the SAME target together in one frame, the job fully '
                               'finished and the final result unmistakable (raised, opened, pressed or filled to '
                               'its final state) - never the target alone without the object that caused it'),
    }


def generate_exterior(data, directory, cache, checkpoint, clients=(), vision=None, log=print):
    """Hanya 01_exterior: wujud benda asli untuk babak pembuka/penutup mode modular.

    Prompt dikunci ke latar studio bersih. Bila Vision tersedia, gambar ditanya ya/tidak
    ("apakah ini jelas {topik} tanpa latar aneh?"); jawaban tidak memicu maksimal 1 regenerasi.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / '01_exterior.png'
    record = cache.setdefault('exterior', {})
    png = path.read_bytes() if path.exists() else b''
    if png and hashlib.sha256(png).hexdigest() == record.get('sha256'):
        return 'assets/01_exterior.png'
    item = next((a for a in data.get('assets') or [] if isinstance(a, dict) and a.get('id') == '01_exterior'), None)
    subject = (item or {}).get('prompt') or data['title']
    seed = topic_seed(data['title'])
    log('  -> Membuat gambar benda asli (01_exterior)...')
    png = generate_picture(exterior_prompt(subject), seed, clients, log)
    if vision:
        for attempt in (1, 2):
            try:
                answer = vision(f"Apakah gambar ini jelas menampilkan {data['title']} tanpa latar aneh? "
                                'Jawab JSON saja: {"ok": boolean}', [png])
                import json as _json
                ok = _json.loads(answer[answer.find('{'):answer.rfind('}') + 1]).get('ok')
            except Exception as exc:
                log(f'  -> Cek Vision gambar pembuka dilewati ({str(exc)[:80]}).')
                break
            if ok:
                break
            if attempt == 2:
                log('  -> Vision tetap menolak gambar pembuka; memakai kandidat terakhir.')
                break
            log('  -> Vision menolak gambar pembuka (bukan bendanya / latar aneh); membuat ulang satu kali...')
            png = generate_picture(exterior_prompt(subject) + ' Show the whole object clearly.', seed + 1, clients, log)
    pending = path.with_suffix('.tmp')
    pending.write_bytes(png)
    pending.replace(path)
    record.update(sha256=hashlib.sha256(png).hexdigest())
    checkpoint()
    return 'assets/01_exterior.png'


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


STORYBOARD_STYLE = ("Cel-shaded educational explainer illustration, bold dark navy ink outlines, warm orange "
                    "and teal palette, soft daylight, clean simple environment that fits the scene (sky, runway, "
                    "room, road or workshop), vertical 9:16 composition with the subject large in frame. "
                    "Keep the main object's design and signature colors identical in every scene of this video. "
                    "Simple bold graphic arrows are allowed only to show force or flow direction. "
                    "Absolutely no text, letters, numbers, logos, labels or watermark anywhere in the image.")


def storyboard_prompt(visual, topic):
    """Prompt storyboard satu adegan: ilustrasi spesifik kalimat itu, gaya disatukan STORYBOARD_STYLE."""
    subject = str(visual or "").strip() or f"the main subject of '{topic}' in action"
    return f"{subject}. The video is about: {topic} - keep its design consistent with that subject. {STORYBOARD_STYLE}"


def generate_storyboard_images(data, directory, cache, checkpoint, clients=(), vision=None, log=print):
    """Satu ilustrasi layar penuh per adegan (gaya storyboard channel edukasi): sb_00.png, sb_01.png, ...

    Cache sha256 per adegan supaya --resume tidak membayar generate ulang; cek Vision maksimal
    1 regenerasi per adegan. Adegan yang gagal total memakai gambar adegan sebelumnya agar
    jumlah gambar selalu sama dengan jumlah adegan (sinkron ke indeks adegan tidak bergeser).
    """
    directory.mkdir(parents=True, exist_ok=True)
    out = []
    for i, scene in enumerate(data["scenes"]):
        key = f"sb_{i:02d}"
        path = directory / f"{key}.png"
        record = cache.setdefault(key, {})
        png = path.read_bytes() if path.exists() else b""
        if png and hashlib.sha256(png).hexdigest() == record.get("sha256"):
            out.append(f"assets/{key}.png")
            continue
        subject = storyboard_prompt(scene.get("visual"), data["title"])
        log(f"  -> Membuat storyboard adegan {i + 1}/{len(data['scenes'])}: {scene.get('title', '')[:40]}")
        try:
            png = generate_picture(subject, topic_seed(data["title"] + key), clients, log)
            if vision:
                for attempt in (1, 2):
                    try:
                        answer = vision(f"Apakah gambar ini jelas menampilkan adegan berikut tanpa teks/huruf/angka: {scene.get('visual') or scene.get('title', '')}? "
                                        'Jawab JSON saja: {"ok": boolean}', [png])
                        import json as _json
                        ok = _json.loads(answer[answer.find("{"):answer.rfind("}") + 1]).get("ok")
                    except Exception as exc:
                        log(f"  -> Cek Vision {key} dilewati ({str(exc)[:80]}).")
                        break
                    if ok or attempt == 2:
                        break
                    log(f"  -> Vision menolak {key}; membuat ulang satu kali...")
                    png = generate_picture(subject + " Show the action more clearly, larger subject.", topic_seed(data["title"] + key) + 1, clients, log)
            pending = path.with_suffix(".tmp")
            pending.write_bytes(png)
            pending.replace(path)
            record.update(sha256=hashlib.sha256(png).hexdigest())
            checkpoint()
            out.append(f"assets/{key}.png")
        except Exception as exc:
            if not out:
                raise
            log(f"  -> Storyboard adegan {i + 1} gagal ({str(exc)[:100]}); memakai gambar adegan sebelumnya.")
            out.append(out[-1])
    return out
