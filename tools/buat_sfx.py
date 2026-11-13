"""
Membuat efek suara sederhana (bebas hak cipta) untuk video.
Hasilnya sudah ikut tersimpan di video_engine/public/sfx, jadi file ini hanya perlu dijalankan
kalau kamu ingin mengubah bunyinya:  python tools/buat_sfx.py   (butuh: pip install numpy)
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "video_engine", "public", "sfx")


AMBIENT = ("wind", "rumble", "water")  # suara latar berulang tidak diberi variasi


def _write(name, signal, peak):
    signal = np.asarray(signal, dtype=np.float64)
    top = np.max(np.abs(signal)) or 1.0
    data = (signal / top * peak * 32767).astype(np.int16)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, f"{name}.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())


def _resample(signal, factor):
    # factor > 1 = lebih tinggi dan lebih pendek, factor < 1 = lebih rendah dan lebih panjang
    n = max(8, int(len(signal) / factor))
    return np.interp(np.linspace(0, len(signal) - 1, n), np.arange(len(signal)), signal)


def save(name, signal, peak=0.9):
    """Simpan efek utama, lalu tiga variasi (b, c, d) dengan nada dan warna berbeda
    supaya efek yang sama tidak terdengar persis sama terus."""
    signal = np.asarray(signal, dtype=np.float64)
    _write(name, signal, peak)
    if name in AMBIENT:
        return
    _write(name + "_b", _resample(signal, 0.8), peak)
    _write(name + "_c", _resample(signal, 1.28), peak * 0.95)
    soft = _resample(signal, 1.08)
    soft = np.convolve(soft, np.ones(5) / 5, mode="same")  # sedikit lebih lembut
    _write(name + "_d", soft, peak)


def t_axis(seconds):
    return np.linspace(0, seconds, int(SR * seconds), endpoint=False)


def smooth(noise, window):
    kernel = np.ones(window) / window
    return np.convolve(noise, kernel, mode="same")


def pop():
    # bunyi "plop" pendek: nada turun cepat
    t = t_axis(0.16)
    freq = 900 * np.exp(-t * 14) + 260
    phase = 2 * np.pi * np.cumsum(freq) / SR
    env = np.exp(-t * 26)
    return np.sin(phase) * env


def whoosh():
    # desiran: derau yang makin terang lalu meredup
    rng = np.random.default_rng(7)
    t = t_axis(0.55)
    noise = rng.standard_normal(len(t))
    dark = smooth(noise, 60)
    bright = smooth(noise, 6)
    mix = np.clip(t / 0.3, 0, 1)
    sound = dark * (1 - mix) + bright * mix
    env = np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 2
    return sound * env


def ding():
    # lonceng kecil: dua nada harmonis yang meredup pelan
    t = t_axis(0.9)
    env = np.exp(-t * 5.5)
    return (np.sin(2 * np.pi * 1320 * t) + 0.5 * np.sin(2 * np.pi * 1980 * t) + 0.25 * np.sin(2 * np.pi * 2640 * t)) * env


def tick():
    # ketukan pendek
    t = t_axis(0.05)
    env = np.exp(-t * 90)
    return np.sin(2 * np.pi * 2100 * t) * env


def make_loop(signal, fade_seconds=0.4):
    """Sambung ujung ke awal dengan bauran halus supaya bunyi bisa diputar berulang tanpa putus."""
    n = int(SR * fade_seconds)
    body = signal[:-n].copy()
    ramp = np.linspace(0, 1, n)
    body[:n] = body[:n] * ramp + signal[-n:] * (1 - ramp)
    return body


def band(noise, low_window, high_window):
    """Derau yang hanya menyisakan nada menengah (selisih dua perataan)."""
    return smooth(noise, low_window) - smooth(noise, high_window)


def wind():
    # desau angin: derau gelap yang kerasnya naik turun pelan (bisa diulang)
    rng = np.random.default_rng(11)
    t = t_axis(4.4)
    noise = rng.standard_normal(len(t))
    base = band(noise, 14, 220)
    swell = 0.65 + 0.35 * np.sin(2 * np.pi * 0.5 * t) * np.sin(2 * np.pi * 0.25 * t + 1)
    return make_loop(base * swell, 0.4)


def rumble():
    # deru mesin rendah: tiga nada rendah ditambah derau gelap (bisa diulang)
    rng = np.random.default_rng(5)
    t = t_axis(3.4)
    tone = np.sin(2 * np.pi * 36 * t) + 0.7 * np.sin(2 * np.pi * 54 * t) + 0.4 * np.sin(2 * np.pi * 72.5 * t)
    grit = smooth(rng.standard_normal(len(t)), 40) * 6
    wobble = 0.8 + 0.2 * np.sin(2 * np.pi * 5 * t)
    return make_loop((tone + grit) * wobble, 0.4)


def water():
    # gemericik air: derau menengah dengan gelembung kecil (bisa diulang)
    rng = np.random.default_rng(23)
    t = t_axis(3.4)
    base = band(rng.standard_normal(len(t)), 5, 40) * 1.4
    for _ in range(46):
        start = rng.uniform(0, 3.0)
        freq = rng.uniform(500, 1600)
        idx = int(start * SR)
        bt = t_axis(0.07)
        bubble = np.sin(2 * np.pi * (freq + 9000 * bt) * bt) * np.exp(-bt * 55) * rng.uniform(0.2, 0.6)
        base[idx: idx + len(bt)] += bubble[: len(base) - idx]
    return make_loop(base, 0.4)


def screech():
    # decit ban: nada tinggi bergetar dengan derau gesekan
    rng = np.random.default_rng(3)
    t = t_axis(1.15)
    freq = 1250 + 160 * np.sin(2 * np.pi * 9 * t) - 220 * t
    phase = 2 * np.pi * np.cumsum(freq) / SR
    tone = np.sign(np.sin(phase)) * 0.35 + np.sin(phase * 2) * 0.3 + np.sin(phase * 3) * 0.15
    hiss = (rng.standard_normal(len(t)) - smooth(rng.standard_normal(len(t)), 5)) * 0.45
    env = np.clip(t / 0.05, 0, 1) * np.clip((1.15 - t) / 0.4, 0, 1)
    return (tone + hiss) * env


def impact():
    # benturan: dentuman rendah ditambah letupan derau
    rng = np.random.default_rng(9)
    t = t_axis(0.9)
    freq = 120 * np.exp(-t * 7) + 38
    thud = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 6)
    crack = smooth(rng.standard_normal(len(t)), 3) * np.exp(-t * 38) * 0.9
    return thud * 1.3 + crack


def beep():
    # bip pendek ala alat ukur
    t = t_axis(0.16)
    env = np.clip(t / 0.01, 0, 1) * np.clip((0.16 - t) / 0.03, 0, 1)
    return (np.sin(2 * np.pi * 1000 * t) + 0.3 * np.sin(2 * np.pi * 2000 * t)) * env


def riser():
    # naik tegang: nada dan derau yang makin tinggi lalu berhenti mendadak
    rng = np.random.default_rng(13)
    t = t_axis(1.6)
    freq = 180 + 1500 * (t / 1.6) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR)
    air = band(rng.standard_normal(len(t)), 4, 30) * 2.2
    env = (t / 1.6) ** 1.6
    return (tone * 0.6 + air * 0.8) * env


def click():
    # klik mekanis: dua ketukan logam sangat pendek
    rng = np.random.default_rng(31)
    t = t_axis(0.09)
    a = np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 130)
    b = np.zeros(len(t))
    k = int(0.028 * SR)
    b[k:] = (np.sin(2 * np.pi * 1700 * t[: len(t) - k]) + smooth(rng.standard_normal(len(t) - k), 2)) * np.exp(-t[: len(t) - k] * 110)
    return a + 0.8 * b


def clank():
    # denting logam: beberapa nada tak harmonis yang meredup
    rng = np.random.default_rng(37)
    t = t_axis(0.55)
    env = np.exp(-t * 11)
    tone = sum(np.sin(2 * np.pi * f * t) * w for f, w in ((410, 1.0), (687, 0.7), (1130, 0.5), (1873, 0.3)))
    hit = smooth(rng.standard_normal(len(t)), 2) * np.exp(-t * 90)
    return tone * env + hit * 1.2


def hiss():
    # desis tekanan udara: derau terang yang naik lalu turun cepat
    rng = np.random.default_rng(41)
    t = t_axis(0.7)
    noise = rng.standard_normal(len(t)) - smooth(rng.standard_normal(len(t)), 8)
    env = np.clip(t / 0.05, 0, 1) * np.exp(-t * 4.5)
    return noise * env


def tock():
    # detak jam yang lebih rendah dari tick
    t = t_axis(0.09)
    return np.sin(2 * np.pi * 760 * t) * np.exp(-t * 55)


def glitch():
    # gangguan digital singkat: potongan derau dan nada lompat
    rng = np.random.default_rng(43)
    t = t_axis(0.3)
    freq = np.where((t * 40).astype(int) % 2 == 0, 540, 1380) + (t * 40).astype(int) % 3 * 210
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(freq) / SR)) * 0.4
    gate = ((t * 55).astype(int) % 3 != 0).astype(float)
    return (tone + rng.standard_normal(len(t)) * 0.35) * gate * np.exp(-t * 6)


def zap():
    # sengatan listrik: nada tinggi bergetar dengan derau pendek
    rng = np.random.default_rng(53)
    t = t_axis(0.35)
    buzz = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.5 + np.sin(2 * np.pi * (1800 + 900 * np.sin(2 * np.pi * 30 * t)) * t) * 0.5
    crack = rng.standard_normal(len(t)) * np.exp(-t * 40)
    return (buzz * np.exp(-t * 9) + crack) * np.clip(t / 0.004, 0, 1)


def thud():
    # hantaman berat: dentum rendah
    t = t_axis(0.5)
    f = 95 * np.exp(-t * 6) + 38
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def sizzle():
    # mendesis panas: derau tajam berkilau
    rng = np.random.default_rng(59)
    t = t_axis(0.9)
    n = rng.standard_normal(len(t))
    n = n - smooth(n, 4)
    crackle = (rng.random(len(t)) > 0.997) * rng.standard_normal(len(t)) * 3
    return (n * 0.6 + crackle) * np.exp(-t * 3) * np.clip(t / 0.03, 0, 1)


def bubble():
    # gelembung naik: nada menanjak pendek beberapa kali
    t = t_axis(0.8)
    out = np.zeros(len(t))
    for start, base in ((0.0, 420), (0.18, 520), (0.33, 380), (0.5, 600)):
        m = t >= start
        u = t[m] - start
        out[m] += np.sin(2 * np.pi * np.cumsum(base * (1 + 3.5 * u)) / SR) * np.exp(-u * 24)
    return out


def bell():
    # lonceng kecil: nada bening yang panjang
    t = t_axis(1.1)
    return sum(np.sin(2 * np.pi * f * t) * w for f, w in ((880, 1.0), (1760, 0.45), (2637, 0.25))) * np.exp(-t * 4.2)


if __name__ == "__main__":
    save("pop", pop())
    save("whoosh", whoosh(), peak=0.7)
    save("ding", ding(), peak=0.8)
    save("tick", tick(), peak=0.7)
    save("wind", wind(), peak=0.8)
    save("rumble", rumble(), peak=0.8)
    save("water", water(), peak=0.8)
    save("screech", screech(), peak=0.7)
    save("impact", impact(), peak=0.9)
    save("beep", beep(), peak=0.6)
    save("riser", riser(), peak=0.7)
    save("click", click(), peak=0.8)
    save("clank", clank(), peak=0.8)
    save("hiss", hiss(), peak=0.6)
    save("tock", tock(), peak=0.7)
    save("glitch", glitch(), peak=0.6)
    save("zap", zap(), peak=0.7)
    save("thud", thud(), peak=0.9)
    save("sizzle", sizzle(), peak=0.6)
    save("bubble", bubble(), peak=0.6)
    save("bell", bell(), peak=0.6)
    print("Efek suara tersimpan di", os.path.abspath(OUT))
