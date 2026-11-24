"""Penulis kanvas mekanis: AI menulis SATU komponen React/SVG khusus untuk topik video ini (GeneratedMechanism.tsx: tiga tampilan Exterior, Analogy, Cutaway).

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
import time
from pathlib import Path

RETRY_PAUSE = 6  # detik jeda sebelum mengulang penulisan kanvas
GEN_REL = os.path.join("src", "generated", "GeneratedMechanism.tsx")

STUB = '''// Berkas ini DITULIS ULANG oleh agen di setiap video (svg_composer.py). Isi di bawah hanya cadangan kosong
// supaya proyek tetap bisa dikompilasi sebelum agen pernah berjalan.
import React from "react";

export interface ViewProps { trig: number; sceneIndex: number; local: number; mode: string; focus: string; forceLevel: number; isDamaged: boolean }
export const ANCHORS: Record<string, { x: number; y: number }> = { whole: { x: 540, y: 830 } };
export const CAMERA: { scale: number; anchor: string }[] = [{ scale: 1, anchor: "whole" }];
export const LABEL_ANCHORS: string[] = [];
export const DETAIL_ANCHOR = "whole";
export const Exterior: React.FC<ViewProps> = () => <g />;
export const Analogy: React.FC<ViewProps> = () => <g />;
export const Cutaway: React.FC<ViewProps> = () => <g />;
'''

VIEW_IFACE = '''
export interface ViewProps { trig: number; sceneIndex: number; local: number; mode: string; focus: string; forceLevel: number; isDamaged: boolean }
'''

ALLOWED_IMPORTS = ("react", "remotion", "../components/MechanicalPrimitives", "../components/hud")

# Ringkasan kontrak renderer dan skills/.../references/yukngulikin-golden-style.md.
# Jangan sertakan markdown mentah atau contoh TSX; sisakan ruang untuk semua adegan.
CANVAS_BRIEF = """Tulis satu file GeneratedMechanism.tsx lengkap, hanya kode. Ekspor interface ViewProps { trig:number; sceneIndex:number; local:number; mode:string; focus:string; forceLevel:number; isDamaged:boolean }.
Ekspor const Exterior, Analogy, Cutaway bertipe React.FC<ViewProps>, masing-masing mengembalikan <g> pada koordinat dunia yang sama. Exterior menutupi Cutaway; Analogy menggambar perumpamaan fisik, bukan mesin utama. Panggung mengatur opacity, kamera, teks, label, HUD dan latar; jangan gambar ulang.
Ekspor const ANCHORS (nama -> {x,y}, whole di 540,830, komponen berbeda titik), CAMERA (array {scale,anchor}, satu per adegan), LABEL_ANCHORS (string[]), DETAIL_ANCHOR (nama jangkar detail).
Kanvas 1080x1920; objek besar di X100..980 Y400..1320. Gunakan minimal 6 <path> berkurva dan 4 panggilan interpolate/interpolateColors/spring, inputRange selalu naik. Gerak deterministik mengikuti frame dan trig. Impor hanya react, remotion, ../components/MechanicalPrimitives atau ../components/hud. Tanpa aset luar, jaringan, acak, timer atau hook state/effect.
Gaya potongan teknis: kontur gelap, sorot komponen aktif, tampilkan sebab dan akibat geraknya. Kamera dari benda utuh ke detail lalu mundur."""

STANDARD_STYLE = """Ringkasan gaya: kontur #0f172a 3.5px bersudut bulat, gradasi tiga stop dan pantulan cahaya. Gambar lingkungan fisik serta saluran yang tersambung ke tepi. Analogi memakai arah gaya yang sama. Redupkan bagian nonfokus; saat beban naik, lengkungkan bentuk sekaligus ubah warna/kecepatan. Pertahankan perubahan kondisi antaradegan. Gunakan forceLevel dan isDamaged untuk reaksi lokal. Tersedia CoilSpring, PipeChannel, PistonCylinder, GearWheel, FlexDiaphragm, CurvedArrow dan ParticleFX di MechanicalPrimitives."""

DEBUG_DIR = Path(__file__).resolve().parent / "cache"

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
    """Pemeriksaan KERAS saja: hanya hal yang pasti membuat render rusak. Selera gambar ditangani auto-perbaikan dan peringatan."""
    errs = []
    if len(code) < 1200:
        errs.append("kode terlalu pendek untuk tiga tampilan mekanis yang utuh")
    if len(code) > 60000:
        errs.append("kode terlalu panjang (maksimal 60000 karakter)")
    for mod in re.findall(r"from\s+['\"]([^'\"]+)['\"]", code):
        if mod not in ALLOWED_IMPORTS:
            errs.append(f"impor '{mod}' dilarang; hanya 'react', 'remotion', '../components/MechanicalPrimitives', '../components/hud'")
    for pat, msg in FORBIDDEN:
        if re.search(pat, code):
            errs.append(msg)
    if not re.search(r"export\s+const\s+Cutaway\b", code):
        errs.append("tidak ada `export const Cutaway` (tampilan potongan dalam wajib ada)")
    if not re.search(r"export\s+const\s+Exterior\b", code):
        errs.append("tidak ada `export const Exterior` (bodi luar benda)")
    if not re.search(r"export\s+const\s+ANCHORS\b", code) or not re.search(r"export\s+const\s+CAMERA\b", code):
        errs.append("wajib ekspor `ANCHORS` dan `CAMERA` (satu baris kamera tiap adegan)")
    for m in re.finditer(r"interpolate\(\s*[^,\[\]]+,\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", code):
        if float(m.group(1)) >= float(m.group(2)):
            errs.append(f"interpolate dengan inputRange [{m.group(1)}, {m.group(2)}] tidak naik ketat dan akan membuat render crash")
            break
    # Gerbang kepadatan visual (semantic density gate): tolak kode yang cuma gambar kotak/lingkaran kaku dan diam,
    # supaya yang lolos pasti punya siluet berkurva dan benar-benar bergerak di beberapa properti, bukan cuma satu.
    path_count = len(re.findall(r"<path\b", code))
    if path_count < 6:
        errs.append(
            f"hanya {path_count} tag <path> (minimal 6) -- bentuknya kemungkinan cuma <rect>/<circle> kaku, bukan siluet "
            "kurva benda asli; bodi utama dan komponen dalam wajib digambar pakai <path> berkurva (gunakan siluet nyata)"
        )
    motion_calls = len(re.findall(r"\b(?:interpolate(?:Colors)?|spring)\s*\(", code))
    if motion_calls < 4:
        errs.append(
            f"hanya {motion_calls} pemanggilan interpolate()/spring() -- gambarnya kemungkinan nyaris statis; animasikan "
            "lebih banyak properti berbeda (posisi, rotasi, warna, bukaan) supaya gerak terasa hidup"
        )
    return errs


def soft_warnings(code):
    """Catatan kualitas yang TIDAK membuang satu panggilan AI; hanya dicetak ke log."""
    w = []
    if len(re.findall(r"<(?:g|path|rect|circle|ellipse|CoilSpring|PipeChannel|PistonCylinder|GearWheel|FlexDiaphragm)\b", code)) < 12:
        w.append("gambar sedikit bentuk")
    if not re.search(r"useCurrentFrame\s*\(", code):
        w.append("tidak ada gerak dari useCurrentFrame")
    grads = re.findall(r"<linearGradient\b.*?</linearGradient>", code, re.S)
    if sum(1 for g in grads if g.count("<stop") >= 3) < 2:
        w.append("gradasi logam kurang dari 2")
    if "<text" in code:
        w.append("ada elemen <text> (seharusnya tanpa teks)")
    return w


_FULL_RECT = re.compile(r"<rect\b[^>]*?(?:width\s*=\s*\{?[\"']?1080[\"']?\}?[^>]*?height\s*=\s*\{?[\"']?1920|height\s*=\s*\{?[\"']?1920[\"']?\}?[^>]*?width\s*=\s*\{?[\"']?1080)[^>]*?/>", re.S)
_CSS_BG = re.compile(r"\bbackground(?:Color)?\s*:\s*(?:\"[^\"]*\"|'[^']*'|`[^`]*`)\s*,?")
_TEXT_EL = re.compile(r"<text\b[^>]*?(?:/>|>.*?</text>)", re.S)


def autofix(code):
    """Perbaiki dengan kode (bukan menyuruh AI menulis ulang): buang latar layar penuh, CSS background, teks karangan, dan <svg> bersarang."""
    code = _FULL_RECT.sub("", code)
    code = _CSS_BG.sub("", code)
    code = _TEXT_EL.sub("", code)
    body_start = code.find("export const")
    if body_start > 0:
        head, body = code[:body_start], code[body_start:]
        body = re.sub(r"<svg\b[^>]*>", "<g>", body)
        body = body.replace("</svg>", "</g>")
        code = head + body
    return code


def normalize(code):
    """Pembersih otomatis: auto-perbaikan, impor react, ViewProps, dan ekspor cadangan agar panggung tidak pernah crash karena hal kecil."""
    code = autofix(code)
    if not re.search(r"import\s+React\b|import\s+\*\s+as\s+React", code):
        code = 'import React from "react";\n' + code
    if not re.search(r"interface\s+ViewProps\b|type\s+ViewProps\b", code):
        code += VIEW_IFACE
    if not re.search(r"export\s+const\s+ANCHORS\b", code):
        code += '\nexport const ANCHORS: Record<string, { x: number; y: number }> = { whole: { x: 540, y: 830 } };\n'
    if not re.search(r"export\s+const\s+CAMERA\b", code):
        code += '\nexport const CAMERA: { scale: number; anchor: string }[] = [{ scale: 1, anchor: "whole" }];\n'
    if not re.search(r"export\s+const\s+LABEL_ANCHORS\b", code):
        code += '\nexport const LABEL_ANCHORS: string[] = [];\n'
    if not re.search(r"export\s+const\s+DETAIL_ANCHOR\b", code):
        code += '\nexport const DETAIL_ANCHOR = "whole";\n'
    if re.search(r"export\s+const\s+Cutaway\b", code) and not re.search(r"export\s+const\s+Analogy\b", code):
        code += "\nexport const Analogy = Cutaway;\n"  # tanpa tampilan analogi, adegan analogi memakai potongan dalam
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
    """Bingkai uji: awal, satu bingkai sesudah pemicu untuk SETIAP jenis tampilan yang dipakai (luar, analogi, sinar-X, cetak biru), dan dekat akhir."""
    frames = [0]
    seen = set()
    for t in timings:
        m = t.get("mode", "konteks")
        if m not in seen:
            seen.add(m)
            frames.append(min(total_frames - 1, t["triggerFrame"] + 12))
    frames.append(max(0, total_frames - 6))
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


_ERR_KEY = re.compile(r"(TypeError|ReferenceError|RangeError|SyntaxError|Error:|inputRange|is not defined|Cannot read|undefined)", re.I)


def clean_render_error(text):
    """Ambil pesan galat inti dari keluaran Remotion: buang baris tumpukan (`at ...`, node_modules) supaya AI tahu apa yang salah."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    useful = [l for l in lines if not l.startswith("at ") and "node_modules/" not in l and "node_modules\\" not in l]
    key = [l for l in useful if _ERR_KEY.search(l)]
    pick = key[:4] if key else (useful[-4:] or lines[-3:])
    seen, out = set(), []
    for l in pick:
        if l not in seen:
            seen.add(l)
            out.append(l[:260])
    return " | ".join(out)[:700]


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
        return clean_render_error((res.stderr or "") + "\n" + (res.stdout or "")) or "render gagal tanpa pesan galat"
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
    test["plainBg"] = True  # latar lingkungan dimatikan supaya "bingkai kosong" mengukur gambar AI saja
    test["clean"] = True
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
                    problems.append("bingkai 0 hampir kosong: benda harus sudah tergambar jelas dan memenuhi area Y 380..1280 sejak frame pertama")
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
Jawab TIDAK LOLOS (ok = false) kalau kamu menemukan SALAH SATU dari hal ini:
 1. Garis putus-putus label penunjuk (callout) menunjuk ke ruang kosong dan tidak menempel pada komponen mesin.
 2. Garis aliran fluida atau listrik menabrak dinding tertutup, atau tetap mengalir menembus katup yang sedang tertutup rapat.
 3. Ada komponen penting yang ukurannya terlalu kecil di pojok layar, atau terpotong batas kanvas.
Selain itu, TIDAK LOLOS juga kalau jelas terlihat: teks label terpotong, bagian benda bertumpuk parah sehingga tidak terbaca, kotak label menutupi komponen yang ditunjuk, benda hanya memenuhi separuh atas layar sementara bawahnya kosong, atau warna begitu gelap sehingga bagian penting nyaris tak terlihat.
Kalau tidak ada cacat jelas, jawab ok. Jangan mengada-ada demi terlihat teliti.
Kalau TIDAK LOLOS, tuliskan perbaikan koordinat atau ukuran pada kode GeneratedMechanism.tsx (tampilan Exterior, Analogy, atau Cutaway, tabel ANCHORS dan CAMERA).
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
        return parse_critique(request_canvas("Gemini visual", lambda p: vision(p, pngs), prompt, log))
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


def canvas_prompt(name, topic, scenes, timings, code=None, errors=()):
    compact = name.split()[0] == "Groq"
    limit = 4900 if compact else 6500
    brief = CANVAS_BRIEF + ("" if compact else "\n" + STANDARD_STYLE)
    brief += f"\nTopik: {str(topic)[:200]}\nAdegan: indeks | mode | frame awal-akhir/pemicu | fokus | label | narasi"
    if errors:
        brief += "\nPerbaiki masalah ini: " + "; ".join(map(str, errors[:5]))[:800]
    rows = []
    # Bagi anggaran merata agar adegan terakhir tidak hilang ketika narasi panjang.
    row_limit = min(320, (limit - len(brief) - 80) // max(1, len(scenes)) - 1)
    for sc, tm in zip(scenes, timings):
        row = (f"{tm['sceneIndex']} | {tm['mode']} | {tm['startFrame']}-{tm['endFrame']}/{tm['triggerFrame']} | "
               f"{tm['focusTarget'][:50]} | {', '.join(tm['labels'])} | {sc.get('narration', '')}")
        rows.append(row[:row_limit])
    prompt = brief + "\n" + "\n".join(rows)
    if code:
        revision = "\nKode untuk direvisi:\n" + code
        # Bila kode utuh tidak muat, regenerasi dari brief + diagnostik, bukan potongan TSX.
        prompt += revision if len(prompt + revision) <= limit else "\nTulis ulang file lengkap dari brief dan diagnostik di atas."
    return prompt


def request_canvas(name, call, prompt, log):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    header = f"{name} | Ukuran prompt kanvas: {len(prompt)} karakter"
    log(header)
    (DEBUG_DIR / "debug_last_prompt.txt").write_text(header + "\n\n" + prompt, encoding="utf-8")
    response_path = DEBUG_DIR / "debug_last_response.txt"
    response_path.write_text("Menunggu jawaban: " + name, encoding="utf-8")
    try:
        response = call(prompt) or ""
    except Exception as exc:
        response_path.write_text(f"{name}: tidak ada jawaban ({type(exc).__name__}). Lihat log terminal.", encoding="utf-8")
        raise
    response_path.write_text(response, encoding="utf-8")
    return response


NEGATION_WORDS = ("bukan", "bukanlah", "tanpa", "jangan")
# Pemeta kata kunci -> sinyal gerak (keyword-to-motion mapper): supaya animasi di Remotion selalu sinkron dengan apa
# yang SEDANG diucapkan narator di adegan itu, bukan cuma mengandalkan satu kata pemicu generik.
FORCE_WORDS = ("tekanan", "memadat", "menekan", "terjepit", "menahan", "beban", "berat", "mendorong", "tertekan")
DAMAGE_WORDS = ("bocor", "robek", "patah", "retak", "pecah", "rusak", "aus", "terkikis", "jebol")


ANALOGY_WORDS = ("ibarat", "bagaikan", "layaknya", "seperti", "mirip", "sama seperti")


def view_mode(index, count, start_fraction, narration=""):
    """Empat babak: adegan 0 benda utuh (konteks), awal menembus cangkang (xray), tengah mekanisme inti (blueprint),
    penutup kembali ke benda utuh. Adegan yang narasinya memuat perumpamaan ("ibarat", "seperti") SELALU memakai
    tampilan analogi tepat di adegan itu, di posisi durasi mana pun."""
    if index == 0 or (index == count - 1 and count >= 5):
        return "konteks"
    # Analogi dikunci ke adegan yang narasinya SENDIRI memuat kata perumpamaan,
    # di posisi durasi berapa pun - bukan slot persen yang bisa meleset dari ucapan narator.
    low = " " + str(narration or "").lower() + " "
    if any(f" {w} " in low for w in ANALOGY_WORDS):
        return "analogi"
    if start_fraction < 0.30:
        return "xray"
    if start_fraction < 0.90:
        return "blueprint"
    return "konteks"


def build_timings(scenes, words, fps=30):
    """Jadwal tiap adegan dalam frame, frame kata pemicu (dari waktu kata TTS), tampilan, dan data HUD."""
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
        neg = next((w for w in inside if _norm_word(w.get("word")) in NEGATION_WORDS), None)
        total_end = max(1.0, float(scenes[-1]["end"]))
        hud = {}
        if s.get("load"):
            hud["load"] = str(s["load"])[:20]
        if s.get("force"):
            hud["force"] = str(s["force"])[:26]
        narration_low = " " + str(s.get("narration", "")).lower() + " "
        force_level = 2.0 if any(f" {w}" in narration_low or f"{w} " in narration_low for w in FORCE_WORDS) else 1.0
        is_damaged = any(f" {w}" in narration_low or f"{w} " in narration_low for w in DAMAGE_WORDS)
        out.append({
            "mode": view_mode(i, n, float(s["start"]) / total_end, s.get("narration", "")),
            "negationFrame": int(round(float(neg["start"]) * fps)) if neg is not None else -1,
            "hud": hud,
            "sceneIndex": i,
            "startFrame": start if i else 0,
            "endFrame": end if i < n - 1 else max(end, int(round(float(s["end"]) * fps))),
            "triggerFrame": trig,
            "focusTarget": str(s.get("title") or "")[:60],
            "labels": labels,
            "forceLevel": force_level,
            "isDamaged": is_damaged,
        })
    seen = False
    for t in out:  # paling banyak satu adegan analogi; sisanya kembali ke mekanisme inti
        if t["mode"] == "analogi":
            if seen:
                t["mode"] = "blueprint"
            seen = True
    return out


def _check_all(code, remotion_dir, props):
    errors = lint(code)
    if not errors:
        write_code(remotion_dir, code)
        errors = typecheck_generated(remotion_dir)
    if not errors:
        errors = smoke_render(remotion_dir, props)
    return errors


def _vision_gate(code, callers, remotion_dir, props, vision, log, dead, make_prompt):
    """Gerbang visual: lihat tangkapan layar, kalau ada cacat jelas revisi kode SEKALI. Revisi dipakai hanya kalau lolos semua pemeriksaan kode."""
    log("  -> Pemeriksa visual melihat tangkapan layar sebelum render penuh...")
    issues = vision_critique(remotion_dir, props, vision, log)
    if not issues:
        log("     Tidak ada cacat visual yang jelas.")
        return code
    log(f"     Cacat visual: {issues[0][:130]}")
    for name, call in callers:
        if name in dead:
            continue
        try:
            revised = normalize(extract_code(request_canvas(name, call, make_prompt(name, code, issues), log)))
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
    """Hasilkan dan validasi tiga tampilan. Mengembalikan True kalau berkas siap dipakai; melempar RuntimeError kalau semua gagal.
    Penulisan kanvas dipanggil SEKALI kalau bisa: hal kecil diperbaiki oleh normalize(); model hanya dipanggil ulang untuk galat nyata."""
    ensure_stub(remotion_dir)
    def make_prompt(name, code, errors):
        return canvas_prompt(name, topic, scenes, timings, code, errors)

    code, errors, last_source = None, [], None
    attempts = max_repairs + 1
    dead = set()
    for attempt in range(1, attempts + 1):
        got = None
        for name, call in callers:
            if name in dead:
                continue
            try:
                got = extract_code(request_canvas(name, call, make_prompt(name, code, errors), log))
                last_source = name
                break
            except Exception as e:
                msg = str(e)
                if any(x in msg for x in ("404", "NOT_FOUND", "401", "403", "413", "invalid_api_key", "model_not_found", "tidak tersedia")):
                    dead.add(name)
                log(f"     Penulis kanvas {name} dilewati: {msg[:90]}")
        if got is None:
            raise RuntimeError("Penulis kanvas mekanis: semua sumber AI gagal menjawab.")
        code = normalize(got)
        errors = lint(code)
        if not errors:
            for note in soft_warnings(code):
                log(f"     Catatan (tidak menggagalkan): {note}")
            write_code(remotion_dir, code)
            errors = typecheck_generated(remotion_dir)
        if not errors:
            errors = smoke_render(remotion_dir, props_for_smoke, log)
        if not errors:
            log(f"  -> Kanvas mekanis dibuat oleh {last_source} dan lolos semua pemeriksaan (percobaan {attempt}).")
            if vision is not None:
                code = _vision_gate(code, callers, remotion_dir, props_for_smoke, vision, log, dead, make_prompt)
            return True
        log(f"  -> Kanvas percobaan {attempt}/{attempts} belum lolos: {errors[0][:260]}")
        if attempt < attempts:
            time.sleep(RETRY_PAUSE)
    raise RuntimeError("Kanvas mekanis buatan AI tidak lolos pemeriksaan setelah perbaikan otomatis: " + "; ".join(errors[:3]))
