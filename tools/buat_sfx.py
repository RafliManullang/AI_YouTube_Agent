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


def save(name, signal, peak=0.9):
    signal = np.asarray(signal, dtype=np.float64)
    top = np.max(np.abs(signal)) or 1.0
    data = (signal / top * peak * 32767).astype(np.int16)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, f"{name}.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())


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
    print("Efek suara tersimpan di", os.path.abspath(OUT))
