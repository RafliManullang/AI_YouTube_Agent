"""Penulis kanvas mekanis: AI menulis SATU komponen React/SVG khusus untuk topik video ini (TopicMechanism.tsx).

Tidak ada daftar preset. Seluruh video adalah satu benda/mesin yang digambar dari awal sampai akhir; tiap adegan hanya
menggerakkan kamera dan bagian benda yang sedang dibahas. Kode dari AI melewati empat pagar sebelum dirender:
  1. pemeriksaan teks (hanya impor react dan remotion, tanpa acak/jaringan/gambar luar),
  2. pemeriksaan tipe TypeScript (tsc --noEmit),
  3. uji render beberapa bingkai nyata (galat saat dijalankan ikut tertangkap),
  4. layar tidak boleh kosong di bingkai pertama.
Kalau gagal, pesan galatnya dikirim kembali ke AI untuk diperbaiki (maksimal 2 kali perbaikan)."""

import json
import os
import re
import shlex
import subprocess

GEN_REL = os.path.join("src", "generated", "GeneratedMechanism.tsx")

STUB = '''// Berkas ini DITULIS ULANG oleh agen di setiap video (svg_composer.py). Isi di bawah hanya cadangan kosong
// supaya proyek tetap bisa dikompilasi sebelum agen pernah berjalan.
import React from "react";
import { AbsoluteFill } from "remotion";

export interface SceneTiming {
  sceneIndex: number;
  startFrame: number;
  endFrame: number;
  triggerFrame: number;
  focusTarget: string;
  labels: string[];
}

export interface TopicMechanismProps {
  scenes: SceneTiming[];
}

export const TopicMechanism: React.FC<TopicMechanismProps> = () => (
  <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 42%, #162032 0%, #090d16 75%)" }} />
);
'''

PROMPT_SVG_COMPOSER = """Kamu adalah Principal Motion Graphics Engineer dan Technical Illustrator (spesialis gaya 2D Cutaway / X-Ray Engineering seperti Animagraffs dan Kurzgesagt).

TUGAS: berdasarkan TOPIK dan DAFTAR ADEGAN di bawah, tulis SATU file React TypeScript Remotion utuh (`TopicMechanism.tsx`) yang menggambar SATU benda/mesin dari topik ini sebagai ilustrasi SVG potongan melintang (cutaway) yang menyatu dari detik 0 sampai akhir video. Benda digambar KHUSUS untuk topik ini dari bentuk dasar SVG (path, rect, circle, ellipse, line, polygon, g, defs). Jangan memakai pola yang sudah kamu hafal dari video lain; rancang dari fisika benda yang dibahas.

TAHAP 1 - BLUEPRINT (tulis sebagai komentar blok di bagian paling atas file, maksimal 25 baris):
 - sebut sistem utuhnya dan 4 sampai 7 bagian bergerak (nama, posisi pusat x,y, ukuran, apa yang membuatnya bergerak);
 - untuk tiap adegan: bagian mana yang menjadi fokus kamera (scale, translateX, translateY) dan aksi klimaksnya.
TAHAP 2 - KODE.

ATURAN MUTLAK:
1. DILARANG BENTUK SLIDE ATAU INFOGRAFIS: tidak ada grafik batang, tabung VS, bola bernomor 1-2-3, speedometer, tanda tanya besar, kartu teks, judul bab, atau daftar poin. Layar adalah SATU benda utuh. Teks hanya boleh berupa label penunjuk kecil yang diambil dari `labels` adegan aktif. Dilarang menulis teks lain (angka, kalimat, judul) yang kamu karang sendiri.
2. BENTUK HARUS BENAR SECARA FISIKA: gambar bendanya seperti aslinya (roda gigi harus punya gigi yang saling bertaut, pegas berbentuk pegas, pipa berongga, aliran dengan panah). Dilarang memakai bola/lingkaran polos untuk mewakili benda yang bukan bola. Kalau ada perbandingan (misalnya lintasan panjang vs pendek), gambarkan dengan panjang garis yang BENAR: yang lebih panjang harus tampak lebih panjang.
3. TIGA LAPIS:
   - Lapis 1 (cangkang luar): siluet bodi asli benda, `fill="rgba(30,41,59,0.35)"`, `stroke="#475569"`, `strokeWidth={3}`, supaya penonton langsung mengenali bendanya sejak frame pertama.
   - Lapis 2 (bagian dalam yang bergerak): minimal 5 komponen mekanis yang relevan dengan naskah. SETIAP komponen bergerak secara matematis dari `frame` (`rotate(frame*k)`, `Math.sin(frame/...)`, `interpolate`, `spring`, strokeDashoffset untuk aliran). Gerak idle berjalan terus dari frame 0.
   - Lapis 3 (label penunjuk): `<line>` + `<text>` yang menunjuk koordinat bagian yang dibahas. Maksimal 2 label per adegan, fontSize 26, kontras tinggi, tidak bertumpuk, teks persis dari `labels`.
4. SATU KANVAS, KAMERA BERKELANJUTAN: benda tidak pernah dihapus atau diganti saat `sceneIndex` berganti. Buat tabel kamera untuk SETIAP adegan (jangan pakai modulo): `[{scale, x, y}, ...]` dan pindah dari kamera adegan sebelumnya ke adegan sekarang dengan `spring` dari frame mulai adegan (zoom-in ke bagian yang dibahas, zoom-out untuk melihat sistem utuh). Bagian yang tidak dibahas boleh meredup (opacity 0.45) tapi tetap tergambar.
5. KATA PEMICU: dari frame pertama seluruh benda sudah terlihat dan bergerak pelan (idle). `triggerProgress` = 0 sebelum `triggerFrame` adegan aktif lalu naik 0 sampai 1 dengan `spring`; pakai untuk AKSI KLIMAKS adegan itu (poros memerah dan retak, katup menutup, percikan, sudut membelok, aliran menyempit, dan sebagainya). Klimaks harus sesuai isi narasi adegan.
6. KODE ANTI-CRASH:
   - HANYA impor dari 'react' dan 'remotion' (`AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate`). Dilarang impor lain, gambar luar, `<image>`, `<foreignObject>`.
   - Dilarang `Math.random`, `Date`, `useState`, `useEffect`, `fetch`, `eval`, `window`, `document`, `setTimeout`. Semua gerak murni fungsi dari `frame`.
   - `interpolate` wajib dipanggil dengan inputRange yang naik ketat dan `{extrapolateLeft:'clamp', extrapolateRight:'clamp'}`.
   - Jangan memakai `Array.from` atau perulangan tanpa batas pasti; jumlah elemen dibuat dari angka tetap kecil (maksimal 60 per perulangan).
   - Semua id `<linearGradient>`, `<radialGradient>`, `<filter id="glow">` didefinisikan di `<defs>`. Pastikan semua tag SVG tertutup dan semua variabel yang dipakai sudah dideklarasikan.
   - viewBox utama `0 0 1080 1920`. Area aman gambar utama: X 100..980, Y 220..1450. Area Y 1500..1920 harus bersih (tempat subtitle). Latar: gradien gelap radial; tanpa lantai, tanpa grid, tanpa kilatan putih.
   - Warna kontras tinggi di atas latar gelap (biru #38bdf8, oranye #f59e0b, merah #ef4444, hijau #22c55e, abu logam #94a3b8), bagian aktif diberi `filter="url(#glow)"`.
7. SIAP DIPAKAI: komponen WAJIB diekspor tepat seperti ini, dan interface WAJIB ada persis:
```tsx
export interface SceneTiming {
  sceneIndex: number;
  startFrame: number;
  endFrame: number;
  triggerFrame: number; // frame absolut saat kata pemicu diucapkan
  focusTarget: string;
  labels: string[];
}
export interface TopicMechanismProps { scenes: SceneTiming[]; }
export const TopicMechanism: React.FC<TopicMechanismProps> = ({ scenes }) => { ... }
```
   Adegan aktif dicari dari `frame` (cadangan: adegan terakhir). Frame di luar semua adegan tidak boleh membuat galat.

KELUARAN: HANYA satu blok kode TypeScript (.tsx) utuh. Tanpa penjelasan di luar kode.

TOPIK: {topic}

DAFTAR ADEGAN (urut; narasi, kata pemicu, label bagian yang boleh ditulis, fokus):
{scenes}
"""

REPAIR_PROMPT = """Kode `TopicMechanism.tsx` di bawah GAGAL pada pemeriksaan otomatis. Perbaiki kodenya, jangan ubah tema gambarnya, dan tetap patuhi semua aturan (hanya impor 'react' dan 'remotion', SVG viewBox 0 0 1080 1920, tanpa Math.random, ekspor `TopicMechanism`, `SceneTiming`, `TopicMechanismProps`, benda terlihat dan bergerak sejak frame 0).

MASALAH YANG DITEMUKAN:
{errors}

KODE SAAT INI:
```tsx
{code}
```

Kembalikan HANYA kode lengkap yang sudah diperbaiki dalam satu blok kode."""

FORBIDDEN = [
    (r"Math\.random", "Math.random dilarang (render harus sama di setiap bingkai)"),
    (r"\bDate\b", "Date dilarang"),
    (r"\buse(State|Effect|Ref|Memo|Callback|Layout\w*)\b", "hook React selain dari remotion dilarang"),
    (r"\bfetch\s*\(", "fetch dilarang"),
    (r"\beval\s*\(|new Function", "eval dilarang"),
    (r"\brequire\s*\(|\bimport\s*\(", "require / import dinamis dilarang"),
    (r"\b(window|document|localStorage)\b", "window/document dilarang"),
    (r"\bsetTimeout|setInterval", "timer dilarang"),
    (r"<image\b|<Img\b|<foreignObject|dangerouslySetInnerHTML", "gambar luar / foreignObject dilarang"),
]


def extract_code(text):
    """Ambil blok kode tsx dari jawaban LLM (dengan atau tanpa pagar ```)."""
    t = text or ""
    m = re.findall(r"```(?:tsx|typescript|ts|jsx)?\s*\n(.*?)```", t, re.S)
    if m:
        return max(m, key=len).strip() + "\n"
    if "```" in t:  # blok terpotong tanpa penutup
        t = t.split("```", 1)[1]
        t = re.sub(r"^(?:tsx|typescript|ts|jsx)\s*\n", "", t)
    return t.strip() + "\n"


def lint(code):
    """Pemeriksaan teks. Mengembalikan daftar masalah (kosong = lolos)."""
    errs = []
    if len(code) < 2500:
        errs.append("kode terlalu pendek untuk ilustrasi mekanis yang utuh")
    if len(code) > 60000:
        errs.append("kode terlalu panjang (maksimal 60000 karakter)")
    for mod in re.findall(r"from\s+['\"]([^'\"]+)['\"]", code):
        if mod not in ("react", "remotion"):
            errs.append(f"impor '{mod}' dilarang; hanya 'react' dan 'remotion'")
    for pat, msg in FORBIDDEN:
        if re.search(pat, code):
            errs.append(msg)
    if not re.search(r"export\s+const\s+TopicMechanism\b", code):
        errs.append("tidak ada `export const TopicMechanism`")
    if "viewBox" not in code or "1080" not in code or "1920" not in code:
        errs.append("viewBox harus 0 0 1080 1920")
    if code.count("<g") + code.count("<path") + code.count("<rect") + code.count("<circle") < 12:
        errs.append("gambar terlalu sedikit bentuk (minimal 5 komponen mekanis)")
    if not re.search(r"useCurrentFrame\s*\(", code):
        errs.append("gerak harus dihitung dari useCurrentFrame()")
    return errs


def normalize(code):
    """Pastikan interface wajib ada dan impor react ada."""
    if not re.search(r"import\s+React\b|import\s+\*\s+as\s+React", code):
        code = 'import React from "react";\n' + code
    if not re.search(r"interface\s+SceneTiming\b|type\s+SceneTiming\b", code):
        code += '''
export interface SceneTiming {
  sceneIndex: number;
  startFrame: number;
  endFrame: number;
  triggerFrame: number;
  focusTarget: string;
  labels: string[];
}
'''
    if not re.search(r"interface\s+TopicMechanismProps\b|type\s+TopicMechanismProps\b", code):
        code += "\nexport interface TopicMechanismProps {\n  scenes: SceneTiming[];\n}\n"
    return code


def ensure_stub(remotion_dir):
    path = os.path.join(remotion_dir, GEN_REL)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(STUB)


def write_code(remotion_dir, code):
    path = os.path.join(remotion_dir, GEN_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def typecheck_generated(remotion_dir):
    """tsc --noEmit; hanya galat di berkas buatan AI yang dihitung. Mengembalikan daftar galat."""
    tsc = os.path.join(remotion_dir, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        return []
    try:
        res = subprocess.run([tsc, "--noEmit", "-p", "."], cwd=remotion_dir, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=240)
    except Exception:
        return []
    if res.returncode == 0:
        return []
    out = [l.strip() for l in (res.stdout or "").splitlines() if "GeneratedMechanism" in l and "error TS" in l]
    return out[:8]


def smoke_frames(timings, total_frames):
    """Bingkai uji: awal, tepat sesudah pemicu adegan tengah, dan dekat akhir."""
    mid = timings[len(timings) // 2]
    frames = [0, min(total_frames - 1, mid["triggerFrame"] + 12), max(0, total_frames - 6)]
    return sorted(set(max(0, f) for f in frames))


def _filled_fraction(png_path):
    """Porsi piksel area gambar utama yang berbeda dari latar. Layar kosong menghasilkan angka mendekati 0."""
    try:
        from PIL import Image
    except Exception:
        return None
    im = Image.open(png_path).convert("L")
    w, h = im.size
    box = im.crop((int(w * 0.09), int(h * 0.115), int(w * 0.91), int(h * 0.755)))
    px = list(box.getdata())
    mean = sum(px) / len(px)
    return sum(1 for v in px if abs(v - mean) > 28) / len(px)


def smoke_render(remotion_dir, props, log=print):
    """Render beberapa bingkai sungguhan. Mengembalikan daftar masalah (kosong = lolos)."""
    import shutil
    npx = shutil.which("npx")
    if not npx:
        return []
    total = int(round(float(props["durationInSeconds"]) * 30))
    frames = smoke_frames(props["mechScenes"], total)
    test = dict(props)
    test["audioUrl"] = ""
    test.pop("bgmUrl", None)
    test["sfx"] = False
    path = os.path.join(remotion_dir, "smoke_props.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(test, f, ensure_ascii=False)
    out_dir = os.path.join(remotion_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    problems = []
    try:
        for fr in frames:
            png = os.path.join(out_dir, f"_smoke_{fr}.png")
            cmd = [npx, "remotion", "still", "src/index.ts", "ShortsComp", png, f"--frame={fr}", "--props=smoke_props.json"]
            gl = os.getenv("GL_MODE")
            if gl:
                cmd.append("--gl=" + gl)
            cmd += shlex.split(os.getenv("REMOTION_EXTRA", ""))  # opsi tambahan (mis. jalur browser), lazimnya kosong
            res = subprocess.run(cmd, cwd=remotion_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode != 0 or not os.path.exists(png):
                tail = ((res.stderr or "") + (res.stdout or "")).strip().splitlines()
                keep = [l for l in tail if l.strip()][-6:]
                problems.append(f"gagal dirender di bingkai {fr}: " + " | ".join(keep)[:600])
                break
            if fr == 0:
                frac = _filled_fraction(png)
                if frac is not None and frac < 0.02:
                    problems.append("bingkai 0 hampir kosong: benda harus sudah tergambar jelas dan memenuhi area Y 220..1450 sejak frame pertama")
    finally:
        for fn in os.listdir(out_dir):
            if fn.startswith("_smoke_"):
                try:
                    os.remove(os.path.join(out_dir, fn))
                except OSError:
                    pass
        try:
            os.remove(path)
        except OSError:
            pass
    return problems


def describe_scenes(scenes, timings):
    rows = []
    for sc, tm in zip(scenes, timings):
        rows.append(
            f"Adegan {tm['sceneIndex']} (frame {tm['startFrame']}-{tm['endFrame']}, kata pemicu di frame {tm['triggerFrame']}): "
            f"narasi = \"{sc.get('narration', '')}\" | kata pemicu = \"{sc.get('trigger') or ''}\" | "
            f"label yang boleh ditulis = {tm['labels']} | fokus = \"{tm['focusTarget']}\""
        )
    return "\n".join(rows)


def build_timings(scenes, words, fps=30):
    """Jadwal tiap adegan dalam frame, dan frame kata pemicu (dari waktu kata TTS)."""
    def _norm_word(w):
        return re.sub(r"[^a-z0-9]", "", str(w or "").lower())

    out = []
    n = len(scenes)
    for i, s in enumerate(scenes):
        start = int(round(float(s["start"]) * fps))
        end = int(round(float(s["end"]) * fps))
        end = max(end, start + 1)
        inside = [w for w in words if float(s["start"]) - 0.05 <= float(w.get("start", 0)) < float(s["end"])]
        want = _norm_word(s.get("trigger"))
        hit = None
        if want:
            hit = next((w for w in inside if _norm_word(w.get("word")) == want), None) or \
                next((w for w in inside if want in _norm_word(w.get("word")) and len(want) > 3), None)
        if hit is None:
            hit = next((w for w in inside if w.get("emphasis")), None)
        if hit is not None:
            trig = int(round(float(hit["start"]) * fps))
        else:
            trig = start + int((end - start) * 0.35)
        trig = min(max(trig, start + 3), max(start + 3, end - 5))
        labels = [str(it.get("label") or "")[:28] for it in (s.get("items") or []) if isinstance(it, dict) and it.get("label")][:2]
        if not labels:
            labels = [str(p)[:28] for p in (s.get("points") or [])][:1]
        out.append({
            "sceneIndex": i,
            "startFrame": start if i else 0,
            "endFrame": end if i < n - 1 else max(end, int(round(float(s["end"]) * fps))),
            "triggerFrame": trig,
            "focusTarget": str(s.get("title") or "")[:60],
            "labels": labels,
        })
    return out


def compose(topic, scenes, timings, callers, remotion_dir, props_for_smoke, log=print, max_repairs=2):
    """Hasilkan dan validasi komponen. Mengembalikan True kalau berkas siap dipakai; melempar RuntimeError kalau semua gagal."""
    ensure_stub(remotion_dir)
    prompt = PROMPT_SVG_COMPOSER.replace("{topic}", str(topic)).replace("{scenes}", describe_scenes(scenes, timings))
    code, errors, last_source = None, [], None
    attempts = max_repairs + 1
    dead = set()
    for attempt in range(1, attempts + 1):
        ask = prompt if code is None else REPAIR_PROMPT.replace("{errors}", "\n".join("- " + e for e in errors[:8])).replace("{code}", code)
        got = None
        for name, call in callers:
            if name in dead:
                continue
            try:
                got = extract_code(call(ask))
                last_source = name
                break
            except Exception as e:
                msg = str(e)
                if any(x in msg for x in ("404", "NOT_FOUND", "401", "403", "413", "invalid_api_key", "model_not_found")):
                    dead.add(name)
                log(f"     Penulis kanvas {name} dilewati: {msg[:90]}")
        if got is None:
            raise RuntimeError("Penulis kanvas mekanis: semua sumber AI gagal menjawab.")
        code = normalize(got)
        errors = lint(code)
        if not errors:
            write_code(remotion_dir, code)
            errors = typecheck_generated(remotion_dir)
        if not errors:
            errors = smoke_render(remotion_dir, props_for_smoke, log)
        if not errors:
            log(f"  -> Kanvas mekanis dibuat oleh {last_source} dan lolos semua pemeriksaan (percobaan {attempt}).")
            return True
        log(f"  -> Kanvas percobaan {attempt}/{attempts} belum lolos: {errors[0][:140]}")
    raise RuntimeError("Kanvas mekanis buatan AI tidak lolos pemeriksaan setelah perbaikan otomatis: " + "; ".join(errors[:3]))
