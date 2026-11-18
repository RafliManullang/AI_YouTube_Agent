# GOLDEN REFERENCE: STANDAR VISUAL CHANNEL @YUKNGULIKIN

Acuan kualitas: channel pertama pembuat proyek ini, @yukngulikin (https://youtube.com/@yukngulikin). Ambil PRINSIPNYA, bukan
cetakan topik-per-topik: setiap video WAJIB terasa sekelas "Cara Kerja Sayap Pesawat 300 Ton" dari segi gaya objek, ritme gerak,
dan kejelasan HUD-nya, meskipun topiknya berbeda-beda.

## 1. Palet & gaya objek (cel-shaded technical toon)

- Garis tepi (stroke) semua bodi: `#0f172a`, ketebalan `3.5px`, `strokeLinejoin="round"`. Jangan garis tipis atau tanpa stroke.
- Shading pakai `linearGradient` 3-stop dengan pantulan cahaya (specular highlight) yang jelas di satu sisi -- bukan warna flat,
  dan bukan efek neon glow melayang di atas latar hitam kosong.
- Lingkungan ikut hidup: benda tidak pernah berdiri di atas latar beku. Garis jalan/landasan/permukaan ikut bergeser pelan, dan
  aliran udara/cairan di sekitarnya bergerak dengan kepala panah (`markerEnd="url(#flowArrow)"`, sudah disediakan sistem).

## 2. Komposisi layar & HUD kuantitatif

- Pojok kiri atas: pertanyaan hook singkat (3-4 kata, kata kunci warna `#f97316`) hanya di beberapa detik pertama -- di proyek ini
  sudah ditangani sistem (`HeaderQuestion`, hilang otomatis sebelum label mesin muncul), AI tidak perlu menggambar ulang.
- Kartu klaim fisika dengan sumber (`sumber: produsen asli / standar resmi`) -- di proyek ini sudah ditangani sistem
  (`CitationBadge`), AI tidak perlu menggambar ulang.
- Indikator beban/gaya (Segmented Force Bar): kalau topik melibatkan beban, tekanan, atau gaya yang bisa diukur, gambar sendiri
  di dalam Cutaway berupa 4 balok kecil bertumpuk (hijau -> oranye) yang menyala bertahap mengikuti `trig` (1 balok di trig rendah,
  4 balok saat trig mendekati 1), ditempel langsung di sebelah komponen yang menahan beban itu, plus angka besar beban
  (contoh: "300 TON", "12 BAR") di sampingnya. Jangan dipaksakan kalau topiknya tidak punya besaran beban yang jelas.
- Miskonsepsi (tanda silang merah `#ef4444` di atas komponen saat narasi bilang "bukan/tanpa/tidak ada") -- sudah ditangani sistem
  lewat `negationFrame` (`MisconceptionCross`), AI tidak perlu menggambar ulang, cukup pastikan `ANCHORS` punya titik yang tepat.
- Kaca pembesar (magnifier) di detail mikro saat aksi puncak -- sudah ditangani sistem lewat `DETAIL_ANCHOR`, AI cukup memastikan
  `DETAIL_ANCHOR` menunjuk titik yang paling kecil dan paling penting untuk diperbesar.

## 3. Ritme gerak & urutan adegan

- Adegan pembuka: wujud utuh benda bekerja di lingkungan aslinya (bukan di ruang kosong).
- Adegan analogi: perumpamaan fisik sehari-hari (contoh: tangan miring dijulurkan ke luar jendela mobil yang melaju) dengan garis
  vektor sudut dan arah aliran yang SAMA logikanya dengan benda utama, supaya penonton menyambungkan dua hal itu sendiri.
- Adegan bedah (X-ray/cutaway): latar teknis gelap kebiruan untuk bagian dalam, komponen yang sedang tidak dibahas diredupkan ke
  opacity 0.35 (lihat aturan sorotan fokus di prompt utama), dan deformasi bentuk (lengkung, tertekan, memuai) memakai kurva
  Bezier nyata saat komponen menahan beban -- bukan sekadar berubah ukuran kotak.
- Adegan penutup: zoom-out kembali ke benda utuh di lingkungannya, menutup lingkaran cerita.

Yang DIAMBIL dari referensi ini: prinsip gaya objek, cara HUD menjelaskan angka, dan ritme bedah-lalu-kembali-utuh di atas.
Yang TIDAK diambil: urutan shot persis, posisi teks persis, atau topik videonya -- itu menyesuaikan topik yang diminta user.
