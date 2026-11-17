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
1. DILARANG BENTUK SLIDE ATAU INFOGRAFIS: tidak ada grafik batang, tabung VS, bola bernomor 1-2-3, speedometer, tanda tanya besar, kartu teks, judul bab, atau daftar poin. Layar adalah SATU benda utuh. Teks hanya boleh berupa label nama komponen yang diambil dari `labels` adegan aktif. Dilarang menulis teks lain (angka, kalimat, judul) yang kamu karang sendiri.
2. BENTUK HARUS BENAR SECARA FISIKA: gambar bendanya seperti aslinya (roda gigi harus punya gigi yang saling bertaut, pegas berbentuk pegas, pipa berongga, aliran dengan panah). Dilarang memakai bola/lingkaran polos untuk mewakili benda yang bukan bola. Kalau ada perbandingan (misalnya lintasan panjang vs pendek), gambarkan dengan panjang garis yang BENAR: yang lebih panjang harus tampak lebih panjang.
3. TIGA LAPIS:
   - Lapis 1 (cangkang luar): siluet bodi asli benda, `fill="rgba(30,41,59,0.35)"`, `stroke="#475569"`, `strokeWidth={3}`, supaya penonton langsung mengenali bendanya sejak frame pertama.
   - Lapis 1B (FrontCoverShell, penutup depan bodi luar): bodi luar benda yang utuh dan tertutup (logam, karet, tekstur ulir luar, leher). Di adegan 0 penutup ini solid (opacity 1.0) dan menutupi isi dalam. Saat masuk adegan pembedahan komponen dalam (sceneIndex >= 1) penutup memudar ke opacity 0 dengan `spring` dimulai tepat di frame awal adegan itu (atau frame kata "memotong/membedah/dalamnya"), seperti dinding depan yang terbelah. Bagian dalam sudah ada dan bergerak pelan di belakang penutup sejak frame 0, hanya tertutup.
   - Lapis 2 (bagian dalam yang bergerak): minimal 5 komponen mekanis yang relevan dengan naskah. SETIAP komponen bergerak secara matematis dari `frame` (`rotate(frame*k)`, `Math.sin(frame/...)`, `interpolate`, `spring`, strokeDashoffset untuk aliran). Gerak idle berjalan terus dari frame 0.
   - Lapis 3 (label penunjuk): lihat aturan 8. Maksimal 2 label per adegan.
4. SATU KANVAS, KAMERA BERKELANJUTAN DENGAN JANGKAR:
   - Benda tidak pernah dihapus atau diganti saat `sceneIndex` berganti. Bagian yang tidak dibahas boleh meredup (opacity 0.45) tapi tetap tergambar.
   - Di awal file (di luar komponen) WAJIB ada kamus `COMPONENT_ANCHORS` berisi titik pusat pasti (x, y) setiap komponen yang kamu gambar, misalnya `const COMPONENT_ANCHORS = { whole: {x:540,y:820}, pin: {x:540,y:520}, spring: {x:540,y:780} }`. Gambar tiap komponen persis di koordinat jangkarnya (satu sumber kebenaran, jangan menulis angka koordinat yang berbeda di tempat lain). Wajib ada jangkar `whole` untuk tampilan benda utuh.
   - Tabel kamera untuk SETIAP adegan (jangan pakai modulo): `CAMERA = [{ scale, anchor: "nama jangkar" }, ...]`. Pindah dari kamera adegan sebelumnya ke adegan sekarang dengan satu `spring` (progres 0..1) dari frame mulai adegan; skala dan koordinat jangkar keduanya di-interpolasi dengan progres yang sama.
   - Fungsi kamera (CameraRig) WAJIB mengunci jangkar tepat di pusat layar (540, 820): bungkus seluruh gambar benda dengan `<g transform={`translate(540 820) scale(${s}) translate(${-ax} ${-ay})`}>` dengan (ax, ay) = jangkar hasil interpolasi, s = skala hasil interpolasi. Dilarang memakai `transform-origin` tetap. Skala zoom-in 1.4 sampai 2.4, zoom-out adegan pembuka dan penutup skala 1 dengan jangkar `whole`.
5. KATA PEMICU: dari frame pertama seluruh benda sudah terlihat dan bergerak pelan (idle). `triggerProgress` = 0 sebelum `triggerFrame` adegan aktif lalu naik 0 sampai 1 dengan `spring`; pakai untuk AKSI KLIMAKS adegan itu (poros memerah dan retak, katup menutup, percikan, sudut membelok, aliran menyempit, dan sebagainya). Klimaks harus sesuai isi narasi adegan.
6. KODE ANTI-CRASH:
   - HANYA impor dari 'react' dan 'remotion' (`AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate`). Dilarang impor lain, gambar luar, `<image>`, `<foreignObject>`.
   - Dilarang `Math.random`, `Date`, `useState`, `useEffect`, `fetch`, `eval`, `window`, `document`, `setTimeout`. Semua gerak murni fungsi dari `frame`.
   - `interpolate` wajib dipanggil dengan inputRange yang naik ketat dan `{extrapolateLeft:'clamp', extrapolateRight:'clamp'}`.
   - Jangan memakai `Array.from` atau perulangan tanpa batas pasti; jumlah elemen dibuat dari angka tetap kecil (maksimal 60 per perulangan).
   - Semua id `<linearGradient>`, `<radialGradient>`, `<filter id="glow">` didefinisikan di `<defs>`. Pastikan semua tag SVG tertutup dan semua variabel yang dipakai sudah dideklarasikan.
   - viewBox utama `0 0 1080 1920`. Area aman gambar utama: X 100..980, Y 220..1450. Area Y 1500..1920 harus bersih (tempat subtitle). Latar: gradien gelap radial; tanpa lantai, tanpa grid, tanpa kilatan putih.
   - Warna kontras tinggi di atas latar gelap (biru #38bdf8, oranye #f59e0b, merah #ef4444, hijau #22c55e, abu logam #94a3b8), bagian aktif diberi `filter="url(#glow)"`.
8. LABEL ANTI-TERPOTONG (HUD LAYAR, DI LUAR KAMERA):
   - Callout label DILARANG berada di dalam `<g>` yang terkena `transform` kamera (translate/scale). Gambar benda di dalam satu `<g transform=...>` kamera. Lalu gambar SEMUA label di grup terpisah SESUDAH grup kamera, tanpa transform kamera, sehingga ukuran dan posisi kotak tidak ikut membesar dan tidak keluar layar saat zoom.
   - Posisi titik target di layar dihitung dengan nilai kamera yang sama dengan grup kamera: `sx = 540 + (cx - ax) * s`, `sy = 820 + (cy - ay) * s`, dengan (cx, cy) koordinat komponen, (ax, ay) jangkar kamera hasil interpolasi, dan s skala kamera. Garis penunjuk berakhir di (sx, sy), kotak label diletakkan di sisi kiri atau kanan titik itu, lalu posisinya DIJEPIT dengan `Math.min(Math.max(x, 180), 900 - lebarKotak)`. Kotak harus selalu penuh terlihat, X 180..900, Y 240..1420.
   - Lebar kotak = jumlah karakter * 15 + 40. Teks label HANYA nama komponen dari `labels`, huruf kapital, maksimal 3 kata dan 22 karakter (contoh "PIN TENGAH", "PEGAS ULIR", "SEGEL KARET"). DILARANG memotong atau menyalin potongan kalimat narasi. Kalau `labels` kosong, jangan tulis label apa pun.
9. URUTAN SEBAB-AKIBAT:
   - Alat pemicu dari luar (kepala pompa, jari, pelatuk, tangan, piston) digambar DI DALAM layar (Y 200..420, tidak pernah di Y < 150) dan bergerak turun atau maju sampai menempel pada komponen SEBELUM komponen itu bergerak. Urutannya: alat bergerak (triggerProgress 0 sampai 0.35), komponen terdorong (0.2 sampai 0.7), baru aliran muncul.
   - Aliran udara/cairan/listrik melewati celah HANYA tampil (opacity > 0) sesudah katup atau pin benar-benar membuka celah (`triggerProgress > 0.35`). Opacity aliran = `interpolate(triggerProgress, [0.35, 0.6], [0, 1], clamp)`. Sebelum itu celah tertutup rapat dan aliran tidak boleh terlihat menembus penutup.
   - Adegan pengandaian negatif ("tanpa komponen ini", "seandainya tidak ada"): komponen yang dibahas menjadi transparan tipis (opacity 0.15) dan tampilkan panah oranye (#f59e0b) yang melesat keluar lewat ujung lubang. Adegan seperti ini harus punya gerak yang terlihat sejak awal adegan, tidak boleh diam.
10. BENTUK LUWES, BUKAN KAKU:
   - Pegas: `<path>` kurva Bezier (perintah C atau S) membentuk lilitan bulat, atau tumpukan elips setengah, dengan `strokeLinejoin="round"` dan `strokeLinecap="round"`, `strokeWidth` 6, gradasi metalik (linearGradient abu terang ke abu gelap). Dilarang `<polyline>` zig-zag bersudut lancip. Saat pegas tertekan, jarak lilitan dirapatkan, bukan garis dipotong.
   - Dinding selongsong punya bibir dudukan katup (valve seat) yang menyempit di bagian yang menahan katup, bukan dua balok lurus. Ulir luar digambar sebagai garis melingkar sejajar (bukan duri miring). Semua pipa, pegas, dan garis aliran memakai `strokeLinejoin="round"` dan `strokeLinecap="round"`.
   - Ruang bertekanan berisi 12 sampai 15 partikel bulat kecil (`<circle>`, r 3..6) yang bergerak naik-turun lewat `Math.sin(frame * 0.1 + i)`, memantul tepat di bawah permukaan segel/penutup (tidak menembusnya). Panah gaya menyentuh permukaan yang ditekan, bukan melayang di ruang kosong.
   - Saat adegan klimaks, partikel di ruang bertekanan bergerak ke arah celah yang terbuka.
11. KEDALAMAN 2.5D DAN MATERIAL (DILARANG TERLIHAT DATAR):
   - Setiap batang, selongsong, pin, pipa, dan silinder memakai `<linearGradient>` dengan MINIMAL 3 titik warna `<stop>`: tepi gelap, pantulan terang di tengah (specular highlight), tepi bayangan. Contoh logam: #475569 (0%), #e2e8f0 (45%), #334155 (100%). Kaca/cairan memakai biru transparan dengan highlight putih. Dilarang mengisi komponen dengan satu warna solid.
   - Tiap komponen yang bergerak diberi garis highlight tipis di sisi atas/kiri (`stroke="#ffffff" strokeOpacity={0.35} strokeWidth={2}`) dan bayangan gelap di belakangnya (`<filter id="shadow">` dengan `<feDropShadow dx="6" dy="8" stdDeviation="6" floodColor="#000" floodOpacity="0.55"/>`) supaya bagian dalam mesin tampak bertumpuk dan punya kedalaman ruang. Komponen yang lebih dalam digambar lebih dulu dan sedikit lebih gelap.
   - Fluida, gas, atau listrik yang berubah kondisi (tekanan rendah ke tinggi, dingin ke panas) mengubah WARNA secara halus lewat `interpolateColors(progress, [0, 1], ["#38bdf8", "#f97316"])` (impor dari 'remotion'), bukan berganti warna mendadak. Kondisi rendah = biru, kondisi tinggi = oranye menyala.
12. SIAP DIPAKAI: komponen WAJIB diekspor tepat seperti ini, dan interface WAJIB ada persis:
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
    if not re.search(r"strokeLinejoin\s*=\s*[\"{']+round", code):
        errs.append("pegas dan pipa wajib memakai strokeLinejoin=\"round\" dan strokeLinecap=\"round\"")
    if not re.search(r"FrontCover", code):
        errs.append("wajib ada komponen FrontCoverShell (penutup depan yang memudar saat masuk adegan pembedahan)")
    if "COMPONENT_ANCHORS" not in code:
        errs.append("wajib ada kamus COMPONENT_ANCHORS (koordinat pasti tiap komponen) dan kamera yang mengunci jangkar di pusat layar")
    grads = re.findall(r"<linearGradient\b.*?</linearGradient>", code, re.S)
    if sum(1 for g in grads if g.count("<stop") >= 3) < 2:
        errs.append("wajib minimal 2 <linearGradient> dengan 3 titik warna <stop> atau lebih (efek logam 3D: tepi gelap, pantulan terang, tepi bayangan)")
    if re.search(r"<polyline", code):
        errs.append("dilarang <polyline> zig-zag; gambar pegas dengan <path> kurva Bezier")
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


def render_still(remotion_dir, props_name, frame, png, timeout=300):
    """Render satu bingkai ke png. Mengembalikan None kalau berhasil, atau teks galat."""
    import shutil
    npx = shutil.which("npx")
    cmd = [npx, "remotion", "still", "src/index.ts", "ShortsComp", png, f"--frame={frame}", f"--props={props_name}"]
    gl = os.getenv("GL_MODE")
    if gl:
        cmd.append("--gl=" + gl)
    cmd += shlex.split(os.getenv("REMOTION_EXTRA", ""))  # opsi tambahan (mis. jalur browser), lazimnya kosong
    res = subprocess.run(cmd, cwd=remotion_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if res.returncode != 0 or not os.path.exists(png):
        tail = ((res.stderr or "") + (res.stdout or "")).strip().splitlines()
        return " | ".join([l for l in tail if l.strip()][-6:])[:600]
    return None


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
            err = render_still(remotion_dir, "smoke_props.json", fr, png)
            if err:
                problems.append(f"gagal dirender di bingkai {fr}: " + err)
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


VISION_PROMPT = """Kamu pemeriksa kualitas animasi infografis mekanis untuk video pendek vertikal (1080x1920). Di bawah ada {n} tangkapan layar dari video yang sama, berurutan: {desc}.
Abaikan subtitle putih besar di bagian bawah layar dan bayangan gelap di bawahnya; itu memang ada.
Periksa HANYA cacat yang jelas terlihat:
 a. teks label terpotong di tepi layar atau keluar layar,
 b. bagian benda saling bertumpuk parah sehingga tidak terbaca, atau menimpa label,
 c. layar terlalu kosong atau benda terlalu kecil (kurang dari separuh lebar layar) pada tangkapan yang seharusnya menampilkan benda,
 d. bagian benda keluar dari batas layar yang seharusnya utuh terlihat, atau posisinya miring tidak wajar,
 e. warna terlalu gelap sehingga bagian penting nyaris tak terlihat.
Kalau tidak ada cacat jelas, jawab ok. Jangan mengada-ada demi terlihat teliti.
Jawab HANYA JSON: {"ok": true atau false, "masalah": ["tangkapan ke-N: ..."], "perbaikan": ["perubahan koordinat atau ukuran SVG yang konkret, misalnya: geser kotak label PIN TENGAH ke x=300"]}"""


def vision_frames(timings, total_frames):
    """Tiga bingkai kunci: cangkang awal, saat pembedahan, dan aksi klimaks adegan di sepertiga akhir."""
    n = len(timings)
    f1 = 30
    f2 = timings[min(1, n - 1)]["startFrame"] + 25
    f3 = timings[min(n - 1, max(1, (n * 2) // 3))]["triggerFrame"] + 15
    out = []
    for f, name in ((f1, "benda utuh di awal"), (f2, "saat dibedah"), (f3, "aksi klimaks")):
        f = max(0, min(total_frames - 1, int(f)))
        if f not in [x[0] for x in out]:
            out.append((f, name))
    return out


def parse_critique(text):
    """Baca jawaban pemeriksa visual. Mengembalikan daftar masalah (kosong = tidak ada cacat atau jawaban tak terbaca)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except Exception:
        return []
    if data.get("ok") is True:
        return []
    issues = [str(x)[:220] for x in (data.get("masalah") or [])][:4]
    fixes = [str(x)[:220] for x in (data.get("perbaikan") or [])][:4]
    return ["Pemeriksa visual: " + x for x in issues] + ["Saran perbaikan: " + x for x in fixes]


def vision_critique(remotion_dir, props, vision, log=print):
    """Render 3 bingkai kunci (hanya beberapa detik), lalu minta model penglihat memeriksanya.
    Mengembalikan daftar masalah. Pemeriksaan ini bersifat penasihat: gangguan apa pun menghasilkan daftar kosong."""
    import shutil
    if not shutil.which("npx"):
        return []
    total = int(round(float(props["durationInSeconds"]) * 30))
    frames = vision_frames(props["mechScenes"], total)
    test = dict(props)
    test["audioUrl"] = ""
    test.pop("bgmUrl", None)
    test["sfx"] = False
    path = os.path.join(remotion_dir, "vision_props.json")
    out_dir = os.path.join(remotion_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    pngs = []
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False)
        for fr, _ in frames:
            png = os.path.join(out_dir, f"_vision_{fr}.png")
            if render_still(remotion_dir, "vision_props.json", fr, png, timeout=180):
                return []
            with open(png, "rb") as fh:
                pngs.append(fh.read())
        desc = "; ".join(f"tangkapan {i + 1} = {name} (bingkai {fr})" for i, (fr, name) in enumerate(frames))
        prompt = VISION_PROMPT.replace("{n}", str(len(pngs))).replace("{desc}", desc)
        return parse_critique(vision(prompt, pngs))
    except Exception as e:
        log(f"     Pemeriksaan visual dilewati: {str(e)[:100]}")
        return []
    finally:
        for fn in os.listdir(out_dir):
            if fn.startswith("_vision_"):
                try:
                    os.remove(os.path.join(out_dir, fn))
                except OSError:
                    pass
        try:
            os.remove(path)
        except OSError:
            pass


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
        labels = []
        for it in (s.get("items") or []):
            if isinstance(it, dict) and it.get("label"):
                lb = " ".join(str(it["label"]).split()[:3]).upper()[:22].strip()
                if lb:
                    labels.append(lb)
        labels = labels[:2]
        out.append({
            "sceneIndex": i,
            "startFrame": start if i else 0,
            "endFrame": end if i < n - 1 else max(end, int(round(float(s["end"]) * fps))),
            "triggerFrame": trig,
            "focusTarget": str(s.get("title") or "")[:60],
            "labels": labels,
        })
    return out


def _check_all(code, remotion_dir, props):
    errors = lint(code)
    if not errors:
        write_code(remotion_dir, code)
        errors = typecheck_generated(remotion_dir)
    if not errors:
        errors = smoke_render(remotion_dir, props)
    return errors


def _vision_gate(code, callers, remotion_dir, props, vision, log, dead):
    """Gerbang visual: lihat 3 tangkapan layar, kalau ada cacat jelas revisi kode SEKALI. Revisi dipakai hanya kalau lolos semua pemeriksaan kode."""
    log("  -> Pemeriksa visual melihat 3 tangkapan layar sebelum render penuh...")
    issues = vision_critique(remotion_dir, props, vision, log)
    if not issues:
        log("     Tidak ada cacat visual yang jelas.")
        return code
    log(f"     Cacat visual: {issues[0][:130]}")
    ask = REPAIR_PROMPT.replace("{errors}", "\n".join("- " + e for e in issues)).replace("{code}", code)
    for name, call in callers:
        if name in dead:
            continue
        try:
            revised = normalize(extract_code(call(ask)))
        except Exception as e:
            log(f"     Revisi visual oleh {name} dilewati: {str(e)[:80]}")
            continue
        if not _check_all(revised, remotion_dir, props):
            log(f"     Revisi visual oleh {name} lolos pemeriksaan dan dipakai.")
            return revised
        log("     Revisi visual belum lolos pemeriksaan kode, memakai versi sebelumnya.")
        break
    write_code(remotion_dir, code)  # pulihkan versi yang sudah lolos
    return code


def compose(topic, scenes, timings, callers, remotion_dir, props_for_smoke, log=print, max_repairs=2, vision=None):
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
            if vision is not None:
                code = _vision_gate(code, callers, remotion_dir, props_for_smoke, vision, log, dead)
            return True
        log(f"  -> Kanvas percobaan {attempt}/{attempts} belum lolos: {errors[0][:140]}")
    raise RuntimeError("Kanvas mekanis buatan AI tidak lolos pemeriksaan setelah perbaikan otomatis: " + "; ".join(errors[:3]))
