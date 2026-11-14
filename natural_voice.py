"""Suara narator yang lebih natural lewat Gemini TTS (gratis dengan key Gemini yang sama).

Seluruh naskah dibacakan dalam SATU permintaan supaya intonasinya mengalir seperti orang bercerita.
Karena Gemini TTS tidak memberi waktu tiap kata, waktunya dicari sendiri dari jeda napas di rekaman:
jeda yang terdeteksi dicocokkan dengan tanda baca di naskah, lalu kata-kata dibagi di antara jeda itu.
Kalau ada yang gagal, main_agent.py otomatis memakai Edge-TTS sebagai cadangan."""

import base64
import io
import re
import time
import wave

import requests

SAMPLE_RATE = 24000
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

FRAME = 0.01  # detik per bingkai analisis
PAUSE_MIN = 0.09  # hening minimal yang dianggap jeda (detik)
PAUSE_MAX = 0.38  # jeda lebih panjang dari ini dipersingkat supaya tempo padat
LEAD = 0.04
TAIL = 0.32  # ujung suara diberi ruang supaya suku kata terakhir yang pelan tidak terpotong


def _np():
    import numpy as np  # diimpor di sini supaya kalau numpy tidak ada, cukup jatuh ke Edge-TTS

    return np


# --------------------------------------------------------------------
# Meminta suara dari Gemini
# --------------------------------------------------------------------
def _pcm_from_response(data):
    parts = data["candidates"][0]["content"]["parts"]
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            raw = base64.b64decode(inline["data"])
            if raw[:4] == b"RIFF":
                with wave.open(io.BytesIO(raw), "rb") as w:
                    if w.getsampwidth() != 2:
                        raise RuntimeError("Format suara tidak didukung.")
                    rate, ch, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
            else:
                mime = inline.get("mimeType") or inline.get("mime_type") or ""
                m = re.search(r"rate=(\d+)", mime)
                rate, ch, pcm = int(m.group(1)) if m else SAMPLE_RATE, 1, raw
            return pcm, rate, ch
    raise RuntimeError("Jawaban tidak berisi suara.")


def request_speech(api_key, model, voice, text, timeout=180):
    """Satu permintaan suara. Hasil: array float32 mono 24 kHz."""
    np = _np()
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    res = requests.post(
        API_URL.format(model=model),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code} {res.text[:200]}")
    pcm, rate, ch = _pcm_from_response(res.json())
    x = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(len(x) * SAMPLE_RATE / rate)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


# --------------------------------------------------------------------
# Merapikan rekaman: potong hening awal/akhir, persingkat jeda panjang
# --------------------------------------------------------------------
def tidy_audio(x):
    """Hasil: (rekaman rapi, daftar jeda [(mulai, selesai)] dalam detik pada rekaman rapi)."""
    np = _np()
    n = int(SAMPLE_RATE * FRAME)
    k = len(x) // n
    if k < 20:
        raise RuntimeError("Rekaman terlalu pendek.")
    env = np.sqrt((x[: k * n].reshape(k, n) ** 2).mean(axis=1))
    thr = max(0.01, 0.06 * float(np.percentile(env, 95)))
    speech = env > thr
    idx = np.where(speech)[0]
    if len(idx) == 0:
        raise RuntimeError("Rekaman tidak berisi suara.")
    first = max(0, int(idx[0]) - int(LEAD / FRAME))
    soft = np.where(env > max(0.004, 0.02 * float(np.percentile(env, 95))))[0]  # ambang rendah untuk ujung kata pelan
    last = min(k, int(max(idx[-1], soft[-1] if len(soft) else idx[-1])) + int(TAIL / FRAME))

    # runs: urutan (apakah_hening, bingkai_awal, bingkai_akhir)
    runs = []
    i = first
    while i < last:
        j = i
        while j < last and speech[j] == speech[i]:
            j += 1
        runs.append([bool(not speech[i]), i, j])
        i = j
    # hening pendek di tengah kata dianggap bagian dari bicara
    min_pause = int(PAUSE_MIN / FRAME)
    max_pause = int(PAUSE_MAX / FRAME)
    pieces = []
    pauses = []
    cursor = 0.0
    for kind, a, b in runs:
        length = b - a
        is_pause = kind and length >= min_pause and a > first and b < last
        if is_pause and length > max_pause:
            half = max_pause // 2
            seg = np.concatenate([x[a * n : (a + half) * n], x[(b - (max_pause - half)) * n : b * n]])
            length = max_pause
        else:
            seg = x[a * n : b * n]
        if is_pause:
            pauses.append((cursor, cursor + length * FRAME))
        pieces.append(seg)
        cursor += length * FRAME
    out = np.concatenate(pieces).astype(np.float32)
    fade = int(0.006 * SAMPLE_RATE)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out, pauses


# --------------------------------------------------------------------
# Mencari waktu tiap kata dari jeda napas
# --------------------------------------------------------------------
def _syllables(token):
    word = re.sub(r"[^a-zA-Z0-9]", "", token).lower()
    if not word:
        return 1
    if word.isdigit():
        return max(1, len(word)) * 1.5
    return max(1, len(re.findall(r"[aiueo]+", word)))


def _weight(token):
    return _syllables(token) + 0.35


def align_words(tokens, duration, pauses):
    """Hasil: daftar (mulai, selesai) per kata. tokens = kata-kata naskah (lengkap dengan tanda baca)."""
    n = len(tokens)
    weights = [_weight(t) for t in tokens]
    cum = [0.0]
    for w in weights:
        cum.append(cum[-1] + w)
    total = cum[-1]

    # batas kalimat/frasa: setelah kata ke-i bila diakhiri tanda baca
    bounds = []
    for i, t in enumerate(tokens[:-1]):
        m = re.search(r"([.!?…]|[,;:])$", t)
        if m:
            bounds.append((i + 1, 0.5 if m.group(1) in ".!?…" else 0.24))
    span0, span1 = LEAD, max(LEAD + 0.1, duration - TAIL)

    # cocokkan jeda terdeteksi dengan batas (urutan tetap, boleh melewati yang tidak cocok)
    m_, p_ = len(bounds), len(pauses)
    INF = 1e9
    skip_pause, skip_bound = 0.9, 1.3
    dp = [[INF] * (p_ + 1) for _ in range(m_ + 1)]
    back = [[None] * (p_ + 1) for _ in range(m_ + 1)]
    dp[0][0] = 0.0
    for a in range(m_ + 1):
        for b in range(p_ + 1):
            cur = dp[a][b]
            if cur >= INF:
                continue
            if b < p_ and cur + skip_pause < dp[a][b + 1]:
                dp[a][b + 1] = cur + skip_pause
                back[a][b + 1] = (a, b, None)
            if a < m_ and cur + skip_bound < dp[a + 1][b]:
                dp[a + 1][b] = cur + skip_bound
                back[a + 1][b] = (a, b, None)
            if a < m_ and b < p_:
                idx, expect_len = bounds[a]
                expect_t = span0 + (cum[idx] / total) * (span1 - span0)
                center = (pauses[b][0] + pauses[b][1]) / 2
                cost = abs(center - expect_t) / 1.2 + abs((pauses[b][1] - pauses[b][0]) - expect_len) / 0.3
                if cur + cost < dp[a + 1][b + 1]:
                    dp[a + 1][b + 1] = cur + cost
                    back[a + 1][b + 1] = (a, b, (a, b))
    matches = {}
    a, b = m_, p_
    while (a, b) != (0, 0):
        pa, pb, pair = back[a][b]
        if pair is not None:
            matches[bounds[pair[0]][0]] = pauses[pair[1]]
        a, b = pa, pb

    # potong teks jadi bagian-bagian di antara jeda yang cocok
    cuts = sorted(matches)
    seg_words = []  # (kata_awal, kata_akhir_eksklusif, t_awal, t_akhir)
    start_idx, start_t = 0, span0
    for c in cuts:
        pause = matches[c]
        seg_words.append((start_idx, c, start_t, max(start_t + 0.05, pause[0])))
        start_idx, start_t = c, pause[1]
    seg_words.append((start_idx, n, start_t, max(start_t + 0.05, span1)))

    times = [None] * n
    for a_, b_, t0, t1 in seg_words:
        w_sum = cum[b_] - cum[a_]
        cursor = t0
        for i in range(a_, b_):
            d = (weights[i] / w_sum) * (t1 - t0)
            times[i] = (round(cursor, 3), round(cursor + d * 0.92, 3))
            cursor += d
    return times


# --------------------------------------------------------------------
# Satu langkah lengkap
# --------------------------------------------------------------------
def make_voice(api_key, models, voice, script_text, style, log=print):
    """Minta suara untuk seluruh naskah. Hasil: (rekaman float32 rapi, jeda). Melempar error kalau gagal."""
    words = len(script_text.split())
    expected = words / 2.6  # detik, perkiraan kasar
    last_error = None
    for model in models:
        for attempt, use_style in ((1, True), (2, True), (3, False)):
            prompt = f"{style}:\n{script_text}" if use_style and style else script_text
            try:
                x = request_speech(api_key, model, voice, prompt)
                seconds = len(x) / SAMPLE_RATE
                if seconds > expected * 1.9 + 3:
                    # biasanya karena petunjuk gaya ikut dibacakan
                    raise RuntimeError(f"suara terlalu panjang ({seconds:.0f} dtk untuk {words} kata)")
                if seconds < expected * 0.4:
                    raise RuntimeError(f"suara terlalu pendek ({seconds:.0f} dtk untuk {words} kata)")
                return tidy_audio(x)
            except Exception as e:
                last_error = e
                msg = str(e)
                log(f"  -> Suara Gemini ({model}) percobaan {attempt}/3 gagal: {msg[:120]}")
                if any(c in msg for c in ("404", "NOT_FOUND", "400", "401", "403")) and "terlalu" not in msg:
                    break  # model tidak ada atau key ditolak: coba model berikutnya
                time.sleep(4 * attempt)
    raise RuntimeError(f"Semua percobaan Gemini TTS gagal: {last_error}")


def write_wav(path, x):
    np = _np()
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
