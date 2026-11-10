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


if __name__ == "__main__":
    save("pop", pop())
    save("whoosh", whoosh(), peak=0.7)
    save("ding", ding(), peak=0.8)
    save("tick", tick(), peak=0.7)
    print("Efek suara tersimpan di", os.path.abspath(OUT))
