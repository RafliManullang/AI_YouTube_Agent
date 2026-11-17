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
import time

RETRY_PAUSE = 6  # detik jeda sebelum mengulang penulisan kanvas
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
  mode?: "konteks" | "xray" | "blueprint";
  negationFrame?: number;
  hud?: { load?: string; force?: string };
}

export interface TopicMechanismProps {
  scenes: SceneTiming[];
}

export const TopicMechanism: React.FC<TopicMechanismProps> = () => <AbsoluteFill />;
'''

PROMPT_SVG_COMPOSER = """Kamu adalah Principal Motion Graphics Engineer dan Technical Illustrator (spesialis gaya 2D Cutaway / X-Ray Engineering seperti Animagraffs dan Kurzgesagt).

TUGAS: berdasarkan TOPIK dan DAFTAR ADEGAN di bawah, tulis SATU file React TypeScript Remotion utuh (`TopicMechanism.tsx`) yang menggambar SATU benda/mesin dari topik ini sebagai ilustrasi SVG potongan melintang (cutaway) yang menyatu dari detik 0 sampai akhir video. Benda digambar KHUSUS untuk topik ini dari bentuk dasar SVG (path, rect, circle, ellipse, line, polygon, g, defs). Jangan memakai pola yang sudah kamu hafal dari video lain; rancang dari fisika benda yang dibahas.

TAHAP 1 - BLUEPRINT (tulis sebagai komentar blok di bagian paling atas file, maksimal 25 baris):
 - sebut sistem utuhnya dan 4 sampai 7 bagian bergerak (nama, posisi pusat x,y, ukuran, apa yang membuatnya bergerak);
 - untuk tiap adegan: bagian mana yang menjadi fokus kamera (scale, translateX, translateY) dan aksi klimaksnya.
TAHAP 2 - KODE.

ATURAN MUTLAK:
1. DILARANG BENTUK SLIDE ATAU INFOGRAFIS: tidak ada grafik batang, tabung VS, bola bernomor 1-2-3, speedometer, tanda tanya besar, kartu teks, judul bab, atau daftar poin. Layar adalah SATU benda utuh. Teks hanya boleh berupa label nama komponen yang diambil dari `labels` adegan aktif, ditambah teks di dalam komponen HUD (aturan 19) yang datanya diberikan sistem. Dilarang menulis teks lain (angka, kalimat, judul) yang kamu karang sendiri.
2. BENTUK HARUS BENAR SECARA FISIKA: gambar bendanya seperti aslinya (roda gigi harus punya gigi yang saling bertaut, pegas berbentuk pegas, pipa berongga, aliran dengan panah). Dilarang memakai bola/lingkaran polos untuk mewakili benda yang bukan bola. Kalau ada perbandingan (misalnya lintasan panjang vs pendek), gambarkan dengan panjang garis yang BENAR: yang lebih panjang harus tampak lebih panjang.
3. TIGA LAPIS:
   - Lapis 1 (cangkang luar): siluet bodi asli benda, `fill="rgba(30,41,59,0.35)"`, `stroke="#475569"`, `strokeWidth={3}`, supaya penonton langsung mengenali bendanya sejak frame pertama.
   - Lapis 1B (FrontCoverShell, penutup depan bodi luar): bodi luar benda yang utuh dan tertutup (logam, karet, tekstur ulir luar, leher). Pada `mode === "konteks"` penutup solid (opacity 1.0) dan menutupi isi dalam. Saat `mode` menjadi `"xray"` penutup memudar dengan `spring` dimulai tepat di `startFrame` adegan itu sampai opacity 0.25 (transparan, isi dalam terlihat), dan tetap 0.25 selama `"blueprint"`. Saat `mode` kembali `"konteks"` (penutup akhir) penutup menutup lagi sampai opacity 1. Bagian dalam sudah ada dan bergerak pelan di belakang penutup sejak frame 0.
   - Lapis 2 (bagian dalam yang bergerak): minimal 5 komponen mekanis yang relevan dengan naskah. SETIAP komponen bergerak secara matematis dari `frame` (`rotate(frame*k)`, `Math.sin(frame/...)`, `interpolate`, `spring`, strokeDashoffset untuk aliran). Gerak idle berjalan terus dari frame 0.
   - Lapis 3 (label penunjuk): lihat aturan 7 dan 12. Maksimal 2 label per adegan.
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
   - viewBox utama `0 0 1080 1920`. Area aman gambar utama: X 100..980, Y 380..1280. Area Y 1290..1920 harus bersih (tempat subtitle di 68% tinggi layar), dan area Y 0..380 dipakai kalimat tanya pembuka serta kotak klaim. Latar layar disediakan sistem: svg WAJIB transparan (lihat aturan 21).
   - Warna kontras tinggi di atas latar gelap (biru #38bdf8, oranye #f59e0b, merah #ef4444, hijau #22c55e, abu logam #94a3b8), bagian aktif diberi `filter="url(#glow)"`.
7. LABEL ANTI-TERPOTONG (HUD LAYAR, DI LUAR KAMERA):
   - Callout label DILARANG berada di dalam `<g>` yang terkena `transform` kamera (translate/scale). Gambar benda di dalam satu `<g transform=...>` kamera. Lalu gambar SEMUA label di grup terpisah SESUDAH grup kamera, tanpa transform kamera, sehingga ukuran dan posisi kotak tidak ikut membesar dan tidak keluar layar saat zoom.
   - Posisi titik target di layar dihitung dengan nilai kamera yang sama dengan grup kamera: `sx = 540 + (cx - ax) * s`, `sy = 820 + (cy - ay) * s`, dengan (cx, cy) koordinat komponen, (ax, ay) jangkar kamera hasil interpolasi, dan s skala kamera. Beri nama hasilnya `screenTargetX = sx` dan `screenTargetY = sy`. Garis penunjuk WAJIB berujung tepat di titik itu (`<line x1={screenTargetX} y1={screenTargetY} .../>`) dan taruh titik bulat kecil `<circle cx={screenTargetX} cy={screenTargetY} r={6} />` di titik tersebut, supaya garis selalu menempel pada komponen walau kamera zoom-in atau bergeser (garis yang menunjuk ruang kosong dianggap salah). Kotak label diletakkan di sisi kiri atau kanan titik itu, lalu posisinya DIJEPIT dengan `Math.min(Math.max(x, 180), 900 - lebarKotak)`. Kotak harus selalu penuh terlihat, X 180..900, Y 380..1270.
   - Lebar kotak = jumlah karakter * 15 + 40. Teks label HANYA nama komponen dari `labels`, huruf kapital, maksimal 3 kata dan 22 karakter (contoh "PIN TENGAH", "PEGAS ULIR", "SEGEL KARET"). DILARANG memotong atau menyalin potongan kalimat narasi. Kalau `labels` kosong, jangan tulis label apa pun.
8. URUTAN SEBAB-AKIBAT:
   - Alat pemicu dari luar (kepala pompa, jari, pelatuk, tangan, piston) digambar DI DALAM layar (Y 200..420, tidak pernah di Y < 150) dan bergerak turun atau maju sampai menempel pada komponen SEBELUM komponen itu bergerak. Urutannya: alat bergerak (triggerProgress 0 sampai 0.35), komponen terdorong (0.2 sampai 0.7), baru aliran muncul.
   - Aliran udara/cairan/listrik melewati celah HANYA tampil (opacity > 0) sesudah katup atau pin benar-benar membuka celah (`triggerProgress > 0.35`). Opacity aliran = `interpolate(triggerProgress, [0.35, 0.6], [0, 1], clamp)`. Sebelum itu celah tertutup rapat dan aliran tidak boleh terlihat menembus penutup.
   - Adegan pengandaian negatif ("tanpa komponen ini", "seandainya tidak ada"): komponen yang dibahas menjadi transparan tipis (opacity 0.15) dan tampilkan panah oranye (#f59e0b) yang melesat keluar lewat ujung lubang. Adegan seperti ini harus punya gerak yang terlihat sejak awal adegan, tidak boleh diam.
9. BENTUK LUWES, BUKAN KAKU:
   - Pegas: `<path>` kurva Bezier (perintah C atau S) membentuk lilitan bulat, atau tumpukan elips setengah, dengan `strokeLinejoin="round"` dan `strokeLinecap="round"`, `strokeWidth` 6, gradasi metalik (linearGradient abu terang ke abu gelap). Dilarang `<polyline>` zig-zag bersudut lancip. Saat pegas tertekan, jarak lilitan dirapatkan, bukan garis dipotong.
   - Dinding selongsong punya bibir dudukan katup (valve seat) yang menyempit di bagian yang menahan katup, bukan dua balok lurus. Ulir luar digambar sebagai garis melingkar sejajar (bukan duri miring). Semua pipa, pegas, dan garis aliran memakai `strokeLinejoin="round"` dan `strokeLinecap="round"`.
   - Ruang bertekanan berisi 12 sampai 15 partikel bulat kecil (`<circle>`, r 3..6) yang bergerak naik-turun lewat `Math.sin(frame * 0.1 + i)`, memantul tepat di bawah permukaan segel/penutup (tidak menembusnya). Panah gaya menyentuh permukaan yang ditekan, bukan melayang di ruang kosong.
   - Saat adegan klimaks, partikel di ruang bertekanan bergerak ke arah celah yang terbuka.
10. KEDALAMAN 2.5D DAN MATERIAL (DILARANG TERLIHAT DATAR):
   - Setiap batang, selongsong, pin, pipa, dan silinder memakai `<linearGradient>` dengan MINIMAL 3 titik warna `<stop>`: tepi gelap, pantulan terang di tengah (specular highlight), tepi bayangan. Contoh logam: #475569 (0%), #e2e8f0 (45%), #334155 (100%). Kaca/cairan memakai biru transparan dengan highlight putih. Dilarang mengisi komponen dengan satu warna solid. Semua gradasi tetap dibungkus garis tepi tegas (aturan 17).
   - Tiap komponen yang bergerak diberi garis highlight tipis di sisi atas/kiri (`stroke="#ffffff" strokeOpacity={0.35} strokeWidth={2}`) dan bayangan gelap di belakangnya (`<filter id="shadow">` dengan `<feDropShadow dx="6" dy="8" stdDeviation="6" floodColor="#000" floodOpacity="0.55"/>`) supaya bagian dalam mesin tampak bertumpuk dan punya kedalaman ruang. Komponen yang lebih dalam digambar lebih dulu dan sedikit lebih gelap.
   - Fluida, gas, atau listrik yang berubah kondisi (tekanan rendah ke tinggi, dingin ke panas) mengubah WARNA secara halus lewat `interpolateColors(progress, [0, 1], ["#38bdf8", "#f97316"])` (impor dari 'remotion'), bukan berganti warna mendadak. Kondisi rendah = biru, kondisi tinggi = oranye menyala.
11. TATA LETAK PENUH LAYAR (DILARANG MENGUMPUL DI ATAS):
   - Di kamera `whole` (skala 1), seluruh sistem benda harus mengisi area X 120..960 dan Y 380..1280: lebar sistem minimal 75% dari 840, tinggi minimal 60% dari 900, titik tengahnya sekitar (540, 830). Dilarang menaruh benda hanya di setengah atas layar sementara setengah bawah kosong, dan dilarang membuat komponen kecil-kecil seperti ikon (komponen inti minimal 160 px pada skala 1).
   - Saat kamera zoom-in, komponen yang dibahas harus utuh terlihat (tidak terpotong tepi layar) dan berukuran sedikitnya 40% lebar layar. Pilih skala zoom supaya komponen beserta tetangganya yang bersentuhan masih muat di X 60..1020.
   - Sistem yang rumit (rem kereta, mesin, jaringan pipa) disederhanakan menjadi SATU rantai utama dari kiri ke kanan atau atas ke bawah yang terdiri dari 4 sampai 6 komponen besar. Dilarang menaruh komponen yang tidak pernah dibahas narasi.
   - Setiap komponen yang disebut di narasi harus punya bentuk yang bisa dikenali (silinder, piston, pegas, katup, roda, pipa berongga), bukan kotak polos atau ikon.
12. PENEMPATAN LABEL: kotak label tidak boleh menutupi komponen yang ditunjuk atau komponen lain. Letakkan kotak label di ruang kosong, minimal 70 px dari tepi gambar komponen itu, dengan garis penunjuk pendek. Dua label dalam satu adegan tidak boleh saling berpotongan atau berjarak kurang dari 80 px.
13. JALUR ALIRAN KONTINU DAN LOGIKA KATUP:
   - Kalau ada aliran (gas, cairan, udara, arus listrik, atau gaya), `<path>` aliran WAJIB kontinu dari titik masuk (inlet), melewati ruang tengah, sampai berbelok masuk ke pipa atau jalur keluar (outlet). Dilarang garis aliran yang berhenti menabrak dinding buntu.
   - Saat katup, bola, atau saklar menutup jalur (shutoff/terkunci), aliran di sisi keluar (downstream) WAJIB berhenti total (opacity 0), dan partikel atau aliran hanya boleh menumpuk di sisi sebelum penutup (upstream).
14. NOL KOMPONEN DIAM (ZERO STATIC PARTS):
   - Dilarang menggambar komponen internal (pegas kedua, membran diafragma, roda gigi pendamping, jarum indikator) yang membeku sepanjang video.
   - Setiap komponen internal diberi gerak mikro (secondary motion) dengan `Math.sin(frame * 0.08)` atau bereaksi terhadap perubahan tekanan atau gerak komponen utama.
15. LARANGAN IKON MIKRO DI PINGGIR LAYAR (FOKUS MAKRO):
   - Dilarang menggambar objek pemicu (robekan selang, percikan api, benturan) berukuran kecil (kurang dari 60 px) di tepi layar.
   - Kalau adegan membahas kerusakan atau reaksi di bagian pinggir alat, masukkan koordinat bagian itu ke `COMPONENT_ANCHORS` lalu arahkan kamera zoom-in (`scale` 1.5 atau lebih) tepat ke titik itu supaya terlihat jelas dan dramatis.
16. PENGAMAN RUNTIME BINGKAI 0 (ANTI-CRASH REACT DAN REMOTION):
   - Elemen `<svg>` utama WAJIB persis `viewBox="0 0 1080 1920"`.
   - Jangkar kamera diambil dari nama pada tabel `CAMERA`, selalu dengan cadangan: `const A = (name: string) => COMPONENT_ANCHORS[name] ?? COMPONENT_ANCHORS.whole ?? { x: 540, y: 820 };`. Dilarang membaca `.x` atau `.y` dari hasil pencarian kamus tanpa cadangan, dan dilarang memakai `focusTarget` (itu judul adegan, bukan nama jangkar) sebagai kunci kamus.
   - Definisikan satu pembantu di atas dan pakai di mana-mana: `const clampOpt = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const; const lerp = (v: number, a: number, b: number, c: number, d: number) => interpolate(v, [a, Math.max(a + 1, b)], [c, d], clampOpt);`. Dilarang memanggil `interpolate` dengan inputRange yang `a >= b` (misalnya `[0, 0]` saat startFrame sama dengan triggerFrame).
   - `scenes` bisa kosong atau memuat frame di luar semua adegan: pakai `const active = scenes.find(...) ?? scenes[scenes.length - 1]`, lalu cadangan `active?.labels ?? []`, `active?.sceneIndex ?? 0`. Indeks tabel `CAMERA` selalu dijepit `Math.min(Math.max(i, 0), CAMERA.length - 1)`.
   - Ekspor `export const TopicMechanism` sekaligus `export default TopicMechanism;`.
17. GAYA CEL-SHADED TECHNICAL ILLUSTRATION (STANDAR STUDIO ANIMASI EDUKASI):
   - SETIAP komponen benda memakai garis tepi gelap tegas: `stroke="#0f172a" strokeWidth={3.5} strokeLinejoin="round" strokeLinecap="round"`. Garis tepi ini yang membuat gambar kode terlihat seperti ilustrasi studio, bukan kotak mentah. Tulis konstanta `const INK = "#0f172a";` dan pakai di mana-mana.
   - Warna fungsional (tetap, jangan diganti): bodi atau cangkang pasif netral (#cbd5e1, #94a3b8, #475569); komponen penggerak utama (pegas, pin, katup, roda gigi) hangat kontras (#f59e0b kuning emas atau #ef4444 merah); aliran energi, fluida, gaya: biru sian #38bdf8 untuk kondisi normal, dingin, atau masuk, oranye menyala #f97316 untuk tekanan tinggi, panas, atau bahaya, hijau #22c55e untuk kondisi terkunci, aman, atau gaya angkat.
18. ALUR SINEMATIK 4 BABAK (WAJIB UNTUK SEMUA TOPIK; ikuti `mode` tiap adegan; benda yang sama tetap ada, hanya penyajiannya berubah):
   - Babak 1, adegan 0 (`"konteks"`, EXTERIOR HOOK): dari frame pertama render bodi luar benda secara UTUH dan SOLID di tengah layar, jelas bentuk aslinya, lengkap dengan konteks tempat benda bekerja di atas latar lingkungan milik sistem (nosel menempel di lubang tangki, setrika di atas kain, pompa di rumah pompa, bodi mesin cuci dengan tabung kaca bundar). Penutup depan solid, kamera `whole` skala 1. DILARANG langsung menampilkan diagram dalam tanpa memperlihatkan wujud utuh benda di adegan pertama.
   - Babak 2, adegan dengan `"xray"` (X-RAY DIVE-IN): kamera melakukan zoom-in tajam (skala 1.8 sampai 2.4) menembus bodi luar ke arah komponen internal utama, dengan spring halus dari `startFrame`; bodi luar memudar sampai opacity 0.25 dan komponen internal utama mulai bergerak jelas. Ini menjawab rasa penasaran "apa isi di dalam benda ini". Latar sistem berganti ke cetak biru.
   - Babak 3, adegan dengan `"blueprint"` (CORE MECHANICS): kamera berpindah bergantian ke komponen internal yang sedang dibahas narasi (pakai jangkar `COMPONENT_ANCHORS` yang spesifik), penutup tetap 0.25. Panah gaya HUD (aturan 19) muncul sesuai data adegan, dan Lingkaran Pembesar (Magnifier Inset) muncul dengan `spring` di pojok kanan bawah: pusat X=800, Y=1150, radius 140, bingkai putih `stroke="#ffffff" strokeWidth={6}` plus garis tepi INK, isinya DIPOTONG `<clipPath>` bulat dan menampilkan zoom 3x pada bagian terkecil yang sedang beraksi (celah 1 mm, bola gotri, membran, ujung pin). Cara: tulis bagian kecil itu sebagai komponen fungsi sendiri (mis. `SmallPart`), panggil dua kali: sekali di gambar utama dan sekali di dalam lingkaran dengan `transform="translate(800 1150) scale(3) translate(-px -py)"` (px, py = jangkar bagian itu). Lingkaran pembesar digambar di grup HUD, di luar grup kamera.
   - Babak 4, adegan terakhir (`"konteks"`, RESOLUTION AND ZOOM-OUT): kamera zoom-out ke skala 1 jangkar `whole` melewati cangkang transparan, bodi luar menutup kembali sampai opacity 1, dan benda ditampilkan utuh sedang menyelesaikan tugasnya (gerak idle yang puas, aliran normal kembali), sebagai penutup yang tuntas.
   - Latar layar penuh disediakan sistem (lihat aturan 21). Jangan menggambar latar sendiri.
19. HUD FISIKA (komponen siap pakai; JANGAN menggambar panah angka atau ikon beban sendiri). Impor persis: `import { SegmentedForceArrow, LoadWeightBadge, MisconceptionCross } from "../components/hud";` dan gambar di grup HUD SESUDAH grup kamera (koordinat layar, hitung dengan rumus aturan 7):
   - `<SegmentedForceArrow x={} y={} direction="up" | "down" | "left" | "right" label={scene.hud.force} level={triggerProgress} />`: panah gaya 4 balok yang menyala bertahap; panggil HANYA di adegan yang `hud.force`-nya terisi. `level` = `triggerProgress` (0 sampai 1). Letakkan di dekat komponen yang gayanya naik, arah sesuai arah gaya. Label panah berada 44 px di bawah pangkalnya, jadi untuk panah `up` pangkal (y) harus di Y 1190 atau lebih kecil supaya label tidak menabrak subtitle di Y 1306.
   - `<LoadWeightBadge value={scene.hud.load} x={} y={} />`: ikon beban merah-oranye; panggil HANYA di adegan yang `hud.load`-nya terisi; letakkan di atas atau di samping komponen yang menahan beban itu.
   - `<MisconceptionCross active={frame >= scene.negationFrame} since={scene.negationFrame} x={} y={} />`: silang merah; panggil HANYA di adegan yang `negationFrame >= 0`, letakkan di atas bagian yang dibantah narasi.
   - Teks HUD datang dari `scene.hud` dan `scene.negationFrame` pada `scenes` (lihat interface). Dilarang mengarang nilai sendiri. Kalau datanya kosong, komponen itu tidak dipanggil. Kotak klaim berangka di kiri atas, kalimat tanya pembuka, dan subtitle dibuat sistem: JANGAN digambar.
20. FISIKA MIKRO (benda harus terasa hidup dan bereaksi terhadap gaya):
   - Deformasi elastis: setiap komponen yang menahan beban atau tekanan (membran, sayap, pelat, ban, pegas, selang) melengkung dengan kurva Bezier `Q` atau `C` yang titik kontrolnya bergeser mengikuti `triggerProgress`. Dilarang komponen elastis yang tetap kaku saat menerima gaya.
   - Efek kontak: setiap kali dua komponen berbenturan, katup menutup rapat, atau tekanan bocor, munculkan 6 sampai 8 partikel kecil (lingkaran atau garis pendek) yang memancar keluar dari titik kontak dengan arah `i * 2 * Math.PI / 7`. Jarak, skala, dan opacity partikel dihitung dengan `interpolate` dari `frame - triggerFrame` (0 sampai 20 frame, memudar).
21. LATAR DAN LAPISAN LAYAR MILIK SISTEM:
   - Sistem sudah menggambar latar bergerak sesuai topik (atau latar cetak biru saat mode blueprint) di belakang gambarmu. `<svg>` utama WAJIB transparan: dilarang `<rect>` seukuran layar, dilarang `background` atau `backgroundColor` CSS, dilarang `<AbsoluteFill style={{ background }}>`.
   - Sistem juga menggambar kalimat tanya pembuka (kiri atas, 12 detik pertama), kotak klaim (kiri atas, setelah 12 detik), dan subtitle (di 68% tinggi layar). Jangan menaruh bagian penting benda di Y < 380 atau Y > 1290.
22. SIAP DIPAKAI: komponen WAJIB diekspor tepat seperti ini, dan interface WAJIB ada persis:
```tsx
export interface SceneTiming {
  sceneIndex: number;
  startFrame: number;
  endFrame: number;
  triggerFrame: number; // frame absolut saat kata pemicu diucapkan
  focusTarget: string;
  labels: string[];
  mode?: "konteks" | "xray" | "blueprint"; // tampilan adegan (aturan 18)
  negationFrame?: number; // frame kata penyangkal, -1 kalau tidak ada
  hud?: { load?: string; force?: string }; // data HUD adegan (aturan 19)
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

REPAIR_PROMPT = """Kode `TopicMechanism.tsx` di bawah GAGAL pada pemeriksaan otomatis. Perbaiki kodenya, jangan ubah tema gambarnya, dan tetap patuhi semua aturan (hanya impor 'react', 'remotion', dan '../components/hud'; SVG viewBox 0 0 1080 1920, tanpa Math.random, ekspor `TopicMechanism`, `SceneTiming`, `TopicMechanismProps`, benda terlihat dan bergerak sejak frame 0).

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
        if mod not in ("react", "remotion", "../components/hud"):
            errs.append(f"impor '{mod}' dilarang; hanya 'react', 'remotion', dan '../components/hud'")
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
    for m in re.finditer(r"interpolate\(\s*[^,\[\]]+,\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", code):
        if float(m.group(1)) >= float(m.group(2)):
            errs.append(f"interpolate dengan inputRange [{m.group(1)}, {m.group(2)}] tidak naik ketat dan akan membuat render crash")
            break
    if "#0f172a" not in code or not re.search(r"strokeWidth\s*=\s*\{?\s*3\.5", code):
        errs.append("gaya cel-shaded: komponen wajib bergaris tepi stroke=\"#0f172a\" strokeWidth={3.5} strokeLinejoin=\"round\"")
    if re.search(r"<rect\b[^>]*width\s*=\s*\{?[\"']?1080[\"']?\}?[^>]*height\s*=\s*\{?[\"']?1920", code) or \
            re.search(r"\bbackground(Color)?\s*:\s*[\"'`](?!transparent)", code):
        errs.append("dilarang menggambar latar layar penuh (rect 1080x1920 atau CSS background); latar disediakan sistem, svg harus transparan")
    if "clipPath" not in code:
        errs.append("wajib ada Lingkaran Pembesar (magnifier) dengan <clipPath> bulat untuk mode blueprint")
    if '"blueprint"' not in code or '"xray"' not in code:
        errs.append("wajib menangani alur 4 babak: mode \"konteks\", \"xray\", dan \"blueprint\" (aturan 18)")
    if "COMPONENT_ANCHORS" not in code:
        errs.append("wajib ada kamus COMPONENT_ANCHORS (koordinat pasti tiap komponen) dan kamera yang mengunci jangkar di pusat layar")
    grads = re.findall(r"<linearGradient\b.*?</linearGradient>", code, re.S)
    if sum(1 for g in grads if g.count("<stop") >= 3) < 2:
        errs.append("wajib minimal 2 <linearGradient> dengan 3 titik warna <stop> atau lebih (efek logam 3D: tepi gelap, pantulan terang, tepi bayangan)")
    if re.search(r"<polyline", code):
        errs.append("dilarang <polyline> zig-zag; gambar pegas dengan <path> kurva Bezier")
    return errs


def fix_viewbox(code):
    """Paksa <svg> utama memakai viewBox 0 0 1080 1920 (hanya tag <svg pertama), tanpa membuang satu panggilan AI hanya karena ukurannya beda."""
    m = re.search(r"<svg\b[^>]*>", code, re.S)
    if not m:
        return code
    tag = m.group(0)
    new = re.sub(r"\sviewBox\s*=\s*(\"[^\"]*\"|'[^']*'|\{[^}]*\})", "", tag)
    new = new.replace("<svg", '<svg viewBox="0 0 1080 1920"', 1)
    return code[:m.start()] + new + code[m.end():]


def normalize(code):
    """Pembersih otomatis: viewBox, export default, impor react, dan interface wajib."""
    code = fix_viewbox(code)
    if "TopicMechanism" in code and not re.search(r"export\s+default\s+TopicMechanism", code):
        code = code.rstrip() + "\nexport default TopicMechanism;\n"
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
  mode?: "konteks" | "xray" | "blueprint";
  negationFrame?: number;
  hud?: { load?: string; force?: string };
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
Kalau TIDAK LOLOS, tuliskan perbaikan koordinat SVG pada kode TopicMechanism.tsx.
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
            f"tampilan (mode) = {tm['mode']} | label yang boleh ditulis = {tm['labels']} | fokus = \"{tm['focusTarget']}\" | "
            f"HUD = {tm['hud'] or 'tidak ada'} | kata penyangkal di frame = {tm['negationFrame'] if tm['negationFrame'] >= 0 else 'tidak ada'}"
        )
    return "\n".join(rows)


NEGATION_WORDS = ("bukan", "bukanlah", "tanpa", "jangan")


def view_mode(index, count, start_fraction):
    """Empat babak: adegan 0 benda utuh (konteks), 12-30% menembus cangkang (xray), 30-90% mekanisme inti (blueprint), penutup kembali ke benda utuh."""
    if index == 0 or (index == count - 1 and count >= 5):
        return "konteks"
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
        out.append({
            "mode": view_mode(i, n, float(s["start"]) / total_end),
            "negationFrame": int(round(float(neg["start"]) * fps)) if neg is not None else -1,
            "hud": hud,
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
        log(f"  -> Kanvas percobaan {attempt}/{attempts} belum lolos: {errors[0][:260]}")
        if attempt < attempts:
            time.sleep(RETRY_PAUSE)  # beri jeda supaya batas token per menit (429) pulih
    raise RuntimeError("Kanvas mekanis buatan AI tidak lolos pemeriksaan setelah perbaikan otomatis: " + "; ".join(errors[:3]))
