"""
Membuat tiga musik latar sederhana (bebas hak cipta) untuk video.
Hasilnya sudah ikut tersimpan di video_engine/public/bgm, jadi file ini hanya perlu dijalankan
kalau kamu ingin mengubah musiknya:  python tools/buat_musik.py   (butuh: pip install numpy)

Tiga suasana: misterius (pelan dan gelap), semangat (ceria dan cepat), tenang (santai).
"""
import os
import wave

import numpy as np

SR = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "video_engine", "public", "bgm")


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def smooth(x, w):
    return np.convolve(x, np.ones(w) / w, mode="same")


def tone_saw(freq, seconds, detune=0.004):
    t = np.arange(int(SR * seconds)) / SR
    out = np.zeros_like(t)
    for d in (-detune, 0, detune):
        out += 2 * ((t * freq * (1 + d)) % 1.0) - 1
    return out / 3


def pad(notes, seconds):
    """Nada panjang yang lembut: gergaji disetel sedikit berbeda lalu dihaluskan."""
    n = int(SR * seconds)
    sig = np.zeros(n)
    for note in notes:
        sig += smooth(tone_saw(midi(note), seconds), 18)
    env = np.minimum(1, np.arange(n) / (SR * 0.5)) * np.minimum(1, (n - np.arange(n)) / (SR * 0.6))
    return sig / len(notes) * env


def pluck(note, seconds=0.5):
    t = np.arange(int(SR * seconds)) / SR
    f = midi(note)
    sig = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3 * f * t)
    return sig * np.exp(-t * 7)


def bass(note, seconds):
    t = np.arange(int(SR * seconds)) / SR
    f = midi(note)
    env = np.minimum(1, t / 0.01) * np.exp(-t * 2.2)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) * env


def kick():
    t = np.arange(int(SR * 0.28)) / SR
    freq = 110 * np.exp(-t * 22) + 42
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 11)


def hat(rng, length=0.05):
    t = np.arange(int(SR * length)) / SR
    noise = rng.standard_normal(len(t))
    return (noise - smooth(noise, 4)) * np.exp(-t * 70)


def clap(rng):
    t = np.arange(int(SR * 0.18)) / SR
    noise = rng.standard_normal(len(t))
    return smooth(noise, 3) * np.exp(-t * 26)


def put(buf, sig, at_seconds, gain=1.0):
    i = int(at_seconds * SR)
    if i >= len(buf):
        return
    end = min(len(buf), i + len(sig))
    buf[i:end] += sig[: end - i] * gain


def echo(sig, delay_seconds, feedback, times):
    out = sig.copy()
    d = int(delay_seconds * SR)
    for k in range(1, times + 1):
        out[d * k:] += sig[: len(sig) - d * k] * (feedback ** k)
    return out


def build(bpm, bars, chords, bass_notes, arp_steps, arp_notes, drums, pad_gain, arp_gain, seed):
    """Satu lagu: akor panjang, bass, petikan nada, dan ketukan. Panjangnya pas sehingga bisa diulang."""
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    total = bars * 4 * beat
    music = np.zeros(int(SR * total))
    for bar in range(bars):
        idx = bar % len(chords)
        start = bar * 4 * beat
        put(music, pad(chords[idx], 4 * beat), start, pad_gain)
        # bass pada tiap ketukan kuat
        root = bass_notes[idx]
        for b in (0, 2):
            put(music, bass(root, 2 * beat), start + b * beat, 0.5)
        # petikan nada naik turun
        steps = 4 * arp_steps
        for s in range(steps):
            note = arp_notes[idx][s % len(arp_notes[idx])]
            put(music, pluck(note), start + s * (4 * beat / steps), arp_gain)
        # ketukan
        if drums in ("tegang", "ceria"):
            for b in range(4):
                if drums == "ceria" or b % 2 == 0:
                    put(music, kick(), start + b * beat, 0.55)
            for b in range(8):
                put(music, hat(rng), start + b * beat / 2 + beat / 4 if drums == "tegang" else start + b * beat / 2, 0.16)
            if drums == "ceria":
                put(music, clap(rng), start + beat, 0.25)
                put(music, clap(rng), start + 3 * beat, 0.25)
        elif drums == "santai":
            put(music, kick(), start, 0.4)
            put(music, kick(), start + 2.5 * beat, 0.3)
            for b in range(4):
                put(music, hat(rng, 0.04), start + b * beat + beat / 2, 0.1)
    # gema halus, lalu bagian ekor dilipat ke awal supaya sambungan tidak terdengar
    wet = echo(music, beat * 0.75, 0.38, 3)
    tail = wet[len(music):]
    wet = wet[: len(music)]
    wet[: len(tail)] += tail[: len(wet)]
    return wet


def save(name, sig):
    sig = np.asarray(sig, dtype=np.float64)
    sig = sig - np.mean(sig)
    sig = sig / (np.max(np.abs(sig)) or 1) * 0.8
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, f"{name}.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((sig * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    # misterius: A minor, pelan, ketukan tipis di sela-sela
    save("misterius", build(
        bpm=96, bars=8,
        chords=[[57, 60, 64], [53, 57, 60], [50, 53, 57], [52, 56, 59]],
        bass_notes=[33, 29, 26, 28],
        arp_steps=2,
        arp_notes=[[69, 72, 76, 72], [65, 69, 72, 69], [62, 65, 69, 65], [64, 68, 71, 68]],
        drums="tegang", pad_gain=0.9, arp_gain=0.35, seed=1))
    # semangat: C mayor, cepat dan ceria
    save("semangat", build(
        bpm=124, bars=8,
        chords=[[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]],
        bass_notes=[36, 31, 33, 29],
        arp_steps=2,
        arp_notes=[[72, 76, 79, 76], [71, 74, 79, 74], [72, 76, 81, 76], [69, 72, 77, 72]],
        drums="ceria", pad_gain=0.55, arp_gain=0.4, seed=2))
    # tenang: santai, akor lembut
    save("tenang", build(
        bpm=82, bars=8,
        chords=[[55, 59, 62, 66], [52, 55, 59, 62], [57, 60, 64, 67], [50, 54, 57, 60]],
        bass_notes=[31, 28, 33, 26],
        arp_steps=1,
        arp_notes=[[74, 71, 67, 71], [71, 67, 64, 67], [76, 72, 69, 72], [69, 66, 62, 66]],
        drums="santai", pad_gain=0.9, arp_gain=0.3, seed=3))
    print("Musik latar tersimpan di", os.path.abspath(OUT))
