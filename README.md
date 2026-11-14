# AI YouTube Agent

Agen ini membuat video YouTube Shorts sendiri, dari cari topik sampai diunggah:

1. Gemini memilih topik (cara kerja benda, fakta sains, atau cerita sejarah) dan menulis naskah.
2. Edge-TTS mengubah naskah jadi suara Bahasa Indonesia, gratis, plus waktu tiap kata.
3. Gemini juga menentukan visual tiap adegan (diagram alur, mind map, atau angka yang menghitung naik), dan Pixabay atau Pexels (gratis, opsional) memberi video latar yang bergerak.
4. Remotion menyatukan semuanya dengan suara dan teks kinetik jadi video, dengan latar berwarna yang terus bergerak.
5. Video diunggah ke YouTube.

## Isi videonya

- Jenis adegan: diagram alur, peta pikiran, angka yang menghitung naik, garis waktu sejarah, grafik batang, dan perbandingan sebelum-sesudah. Gemini memilih yang paling cocok untuk tiap bagian cerita.
- Tema warna (pelangi, neon, senja, hutan, samudra, emas, kosmik) dipilih Gemini sesuai suasana topik.
- Suara dibuat per adegan dengan kecepatan dan nada yang berbeda (semangat, santai, misterius, tegas) supaya tidak monoton. Pengaturannya ada di `TONES` di `main_agent.py`.
- Efek suara (bunyi saat kartu muncul, desiran antar adegan, dentang saat angka selesai) dibuat sendiri dan bebas hak cipta. Matikan dengan menulis `SFX=off` di `.env`.
- Obrolan dua suara: Shela (cewek, yang bertanya dan kaget) dan Flay (cowok, yang menjelaskan). Subtitle muncul kata demi kata persis saat diucapkan, dengan label nama pembicara. Mau satu narator saja? Tulis `DIALOG=off` di `.env`. Suaranya bisa diganti lewat `VOICE_SHELA` dan `VOICE_FLAY`.
- Rekaman asli: adegan pembuka (hook) memakai video nyata dari Pixabay atau Pexels, dan adegan lain memakai video itu sebagai latar yang jelas terlihat. Ini butuh `PIXABAY_API_KEY` di `.env`. Tanpa key, videonya tetap jadi tapi hanya memakai latar animasi.
- Adegan jam kecepatan: jarum naik dramatis untuk membandingkan angka (misalnya tekanan ban mobil lawan ban pesawat).
- Tema warna dipilih agen sendiri sesuai kategori topik dan tidak pernah mengulang tema dari 3 video terakhir (riwayatnya di `riwayat_tema.json`). Ada tema sepia bernuansa foto tua untuk kisah sejarah.
- Animasi sesuai jenis topik: potongan melintang tembus pandang (X-ray) dengan panah arah gerak untuk "cara kerja benda" (ada versi bawah tanah dengan lapisan tanah dan mesin bor), zoom dari benda utuh ke tingkat mikro dengan getaran dan slow motion untuk "fakta sains", dan ilustrasi buku cerita dengan karakter berekspresi, cuaca, serta kamera bergeser dan zoom ke wajah untuk "kisah nyata".
- Footage berganti per kalimat sesuai isi ucapannya (misalnya uji tabrak, lalu pabrik kaca, lalu close-up pecahan kaca), bukan satu video dari awal sampai akhir.
- Hook: kalimat pertama dibuat menghentak (tanpa sapaan), diawali dentuman. Kata kunci di subtitle berwarna kuning dan membesar, dan tiap teks baru diberi bunyi kecil.
- Jeda napas di suara dipotong otomatis supaya tempo padat. Matikan dengan `TRIM_BREATH=off` di `.env` kalau hasilnya terasa terlalu rapat.
- Latar animasi punya 6 gaya yang diacak, jadi tiap video dan tiap adegan terlihat berbeda.
- Suara latar sesuai kejadian (angin, gesekan ban, benturan, deru mesin, air) ditambah musik latar buatan sendiri (misterius, semangat, atau tenang). Musik bisa dimatikan dengan `BGM=off`. Mau pakai musikmu sendiri? Taruh `bgm.mp3` di `video_engine/public`.
- Thumbnail dibuat otomatis berukuran tegak 9:16 (`video_engine/out/thumbnail.jpg`) dan dipasang saat unggah. Kalau gagal dipasang, biasanya karena channel belum diverifikasi nomor teleponnya di YouTube, dan videonya tetap terunggah.

## Tahap 7: video ~1 menit yang lebih natural

- Narator tunggal (default). Dialog Shela dan Flay tidak lagi dipakai supaya hook tidak terbuang untuk basa-basi. Mau dialog lagi? Tulis `DIALOG=on` di `.env`.
- Suara natural lewat Gemini TTS (key Gemini yang sama, satu permintaan untuk seluruh naskah supaya intonasinya mengalir). Pilihan suara: `GEMINI_VOICE` (bawaan Puck), model: `GEMINI_TTS_MODEL`. Kalau gagal atau kuota habis, otomatis pindah ke Edge-TTS. Paksa Edge-TTS dengan `TTS=edge`. Butuh paket `numpy` (`pip install -r requirements.txt`).
- Animasi simulasi cara kerja (adegan `mechanism`): lift (kabin, tali baja, katrol, pemberat), roda gigi, piston dan poros engkol, tuas, aliran pipa menyempit, pemanas dan konveksi, rangkaian listrik, serta tekanan gas. Bagian benda diberi label yang muncul berurutan dengan bunyi kecil. Footage hanya dipakai di adegan `footage`.
- Naskah ~60 detik, padat, dibuka dengan visual konkret dan premis yang bikin penasaran, ditutup dengan kalimat yang menyambung ke kalimat pembuka supaya video terasa berulang mulus.
- Judul tidak lagi memakai `#Shorts`.

## Tahap 9: animasi 3D dan efek suara yang rapi

- **Animasi 3D sungguhan** (three.js di dalam Remotion): benda 3D berlogam dan kaca, tali, roda gigi, aliran partikel bercahaya, kamera yang mengitari benda dan mendekat di klimaks, serta label bagian yang menempel pada benda. Penulis naskah menyusun adegan 3D untuk TIAP topik (kolom `sim`), jadi animasinya khusus topik itu. Kalau susunannya tidak layak, dipakai animasi 3D bawaan (lift, roda gigi, piston, aliran pipa, rangkaian listrik, pemanas, nozel bensin), lalu animasi 2D.
- Kalau render 3D gagal di komputermu, agen otomatis mengulang tanpa 3D. Mode WebGL bisa diganti lewat `GL_MODE` di `.env` (bawaan `angle`). Render 3D lebih lama dari 2D, terutama tanpa kartu grafis.
- Ilustrasi AI (`ART`): adegan animasi bisa memakai gambar potongan benda buatan AI (Gemini gambar atau Pollinations). Matikan dengan `ART=off`.
- **Efek suara**: bunyi per kata, per label, dan per frasa subtitle dihapus total. Efek suara hanya di dentuman hook, pergantian adegan, dan satu momen puncak tiap animasi. Jenis bunyinya dipilih sesuai kejadian lewat kolom `sfx` (clank, hiss, zap, thud, sizzle, bubble, ding, bell, impact).
- Setiap bunyi punya 4 variasi, dan agen mencatat pilihannya di `riwayat_sfx.json` supaya video berikutnya memakai variasi yang berbeda. Bunyi baru: zap, thud, sizzle, bubble, bell (`python tools/buat_sfx.py`).
- Pertama kali setelah pembaruan ini, agen memasang paket baru (`three`) otomatis, butuh beberapa menit.

## Tahap 8: storyboard dan efek sinematik

- Kerangka adegan per kategori (hook, taruhan, bagian rahasia, proses, klimaks, fakta, penutup melingkar) sekarang ada di instruksi naskah.
- Momen klimaks animasi cara kerja: gerakan melambat sebentar (slow motion), layar bergetar, kilat putih, dan bunyi denting atau desis. Kamera juga bergeser dan memperbesar perlahan.
- Animasi baru: nozel bensin (lubang udara tertutup bensin lalu pengunci lepas) dan roda kereta kerucut (roda bergeser ke sisi besar saat belok). Aliran dibuat bercahaya.
- Adegan baru `question`: tanda tanya merah besar yang berdenyut untuk hook yang melawan akal sehat.
- Adegan cerita sejarah: pinggiran gelap (vignette), zoom pelan ala Ken Burns, transisi glitch kilas balik, dan detak jam halus.
- Efek suara baru (dibuat sendiri): klik, denting logam, desis, detak jam, glitch (`python tools/buat_sfx.py`).

## Naskah yang lebih menarik dan tahan gangguan

- Alur cerita dirancang supaya orang menonton sampai habis: hook menghentak, taruhan, penjelasan dengan analogi, titik balik di tengah, angka gila yang mudah dibayangkan, jawaban yang memuaskan, lalu penutup yang menyambung ke awal.
- Setelah naskah pertama jadi, ada tahap editor: naskah ditulis ulang untuk memperkuat hook, titik balik, dan angka, sekaligus mengecek fakta. Kalau tahap ini gagal, naskah pertama tetap dipakai. Matikan dengan `EDITOR=off` di `.env`.
- Kalau Gemini sedang sibuk (error 503), agen otomatis pindah ke penulis cadangan gratis: Groq lalu Cerebras. Isi `GROQ_API_KEY` dan/atau `CEREBRAS_API_KEY` di `.env`. Gemini tetap dipakai lebih dulu.

## Persiapan sekali saja

1. Pasang Python dan Node.js.
2. Salin `.env.example` menjadi `.env`, lalu isi `GEMINI_API_KEY` (ambil gratis di Google AI Studio).
3. Untuk unggah otomatis, taruh file `client_secret.json` dari Google Cloud (YouTube Data API v3, jenis aplikasi Desktop) di folder ini. Saat pertama kali jalan, browser akan terbuka untuk minta izin.

## Cara menjalankan

Klik dua kali `jalankan_agen.bat`. Untuk uji coba tanpa unggah, buka terminal di folder ini lalu ketik:

```
jalankan_agen.bat --tanpa-upload
```

Kalau videonya sudah kamu tonton dan bagus, unggah video yang itu juga (tanpa membuat video baru) dengan:

```
jalankan_agen.bat --unggah-saja
```

Alurnya jadi hemat: buat dengan `--tanpa-upload`, tonton, lalu `--unggah-saja`. Jangan membuat video baru di antaranya, karena video lama akan tertimpa. Judul dan deskripsinya tersimpan otomatis di `video_engine/out/catatan_video.json`.

Supaya video tayang tepat jam tertentu tanpa komputermu harus menyala saat itu, pakai `--jadwal`. Video diunggah dulu, lalu YouTube sendiri yang menayangkannya (jam WIB):

```
jalankan_agen.bat --jadwal 13:00
jalankan_agen.bat --unggah-saja --jadwal 19:30
```

Pilihan lain: `--topik "cara kerja lift gedung"` untuk menentukan topik sendiri, dan
`--privasi unlisted` atau `--privasi public` untuk mengubah status video.

## Hal yang perlu diketahui

- Satu kali jalan butuh sekitar 2 sampai 4 menit.
- Video latar (opsional): daftar gratis di pixabay.com, buka pixabay.com/api/docs setelah login untuk melihat key-nya, lalu isi `PIXABAY_API_KEY` di `.env`. Pexels (`PEXELS_API_KEY`) juga didukung kalau pendaftarannya sudah dibuka lagi. Kalau kosong atau gagal, video tetap jadi dengan latar animasi bawaan. Nama sumber video otomatis ditulis di deskripsi YouTube.
- Musik latar (opsional): taruh file musik bebas hak cipta bernama `bgm.mp3` di folder `video_engine/public`. Otomatis dipakai dengan volume pelan.
- Video hasil ada di `video_engine/out/shorts_final.mp4`.
- Status bawaan video adalah `private` supaya hasil pertama bisa dicek dulu. Untuk langsung publik, isi `YOUTUBE_PRIVACY=public` di file `.env`, atau jalankan dengan `--privasi public`.
- Jangan pernah mengunggah `.env`, `client_secret.json`, atau `token.json` ke GitHub.

## Tahap 10: semua adegan 3D + thumbnail beragam

- Semua jenis adegan (angka, grafik batang, garis waktu, ukuran, aliran, peta ide, perbandingan, kisah, skala kecil, pertanyaan) kini digambar sebagai animasi 3D asli, lengkap dengan tulisan 3D. Rekaman stok maksimal 1 adegan per video.
- Benda yang belum dikenal (misalnya sabuk pengaman) dibuatkan model 3D oleh AI. Kalau gagal, dipakai model bawaan berdasarkan kata kunci.
- Thumbnail: ada 5 tata letak yang bergantian (tidak sama dengan dua video terakhir, riwayat di `riwayat_thumb.json`). Latarnya diambil dari gambar 3D bersih video itu sendiri.
- Render 3D lebih lambat. Kalau bermasalah, atur `GL_MODE` di `.env` (mis. `egl` atau `swiftshader`).

## Tahap 11: pembuka lebih menghentak, angka lebih sedikit, penutup menyambung

- 3 detik pertama: zoom-in cepat, getaran, kilatan putih, bunyi desing lalu dentuman.
- Angka dibatasi maksimal 3 di seluruh ucapan, satu per kalimat, supaya penonton tidak kewalahan.
- Kalimat terakhir otomatis diakhiri dengan kata-kata pembuka (video berulang terasa satu kalimat yang berputar).

## Tahap 12: perpustakaan animasi 3D siap pakai

Sembilan animasi 3D bawaan ditambahkan di `sim_library.py`: eskalator (roda tangga dan roda pegangan beda kecepatan), kunci silinder (pin dan pegas), sprinkler (tabung kaca pecah di 68°C), efek venturi, rem magnet (arus pusar), roda kereta kerucut, jembatan gantung, airbag, dan mesin pembakaran (piston, klep, busi). Dipakai otomatis kalau naskah menyebut bendanya dan AI tidak membuat model 3D sendiri.

## Tahap 13: visual yang sesuai isi kalimat

Tiap adegan (selain angka) kini memperlihatkan persis apa yang diucapkan. AI menulis dua hal per adegan: `subject` (benda, hewan, atau orang utama, dalam bahasa Inggris) dan `art` (deskripsi adegan kartun 3D). Urutannya:
1. Model 3D asli gratis dari Poly Pizza (`models3d.py`, perlu `POLYPIZZA_KEY` di `.env`). Model berputar, bergerak, dan memutar animasi bawaannya. Kredit pembuat otomatis masuk ke deskripsi video.
2. Kalau tidak ada modelnya: gambar kartun 3D buatan AI (Gemini atau Pollinations) yang digerakkan.
3. Kalau keduanya gagal: animasi 3D bawaan (`sim_*.py`).
Adegan angka, grafik, dan garis waktu tetap berupa 3D data.

## Tahap 14: perbaikan dari video Tahap 13

- Gambar kartun AI: deskripsi adegan kini ditaruh di depan perintah (dulu gaya di depan, hasilnya gambar abstrak warna-warni). AI diminta menulis benda nyata yang bisa dipotret, bukan gagasan abstrak.
- Kata `subject` dibuat konsisten antar adegan supaya model 3D yang sama dipakai (tidak berganti pesawat tiap adegan).
- Model 3D lebih besar dan naik ke tengah layar, label jadi tag tanpa garis, lantai oval diganti cincin tipis.
- Adegan tanpa visual meminjam visual adegan lain; adegan terakhir memakai visual adegan pertama (video berputar mulus). Tidak ada lagi adegan yang hanya berisi judul.
- Alat ukur 3D lebih besar.

## Tahap 15: variasi dan perbaikan dari video kedua

- Kerangka cerita bergiliran (6 macam: mitos lawan fakta, detektif, hitung mundur, andai tidak ada, bedah langkah demi langkah, orang di baliknya), tidak sama dengan dua video terakhir (`riwayat_alur.json`). Kata klise ("Tapi tunggu", "analogi", dll.) dilarang.
- Penutup berputar kini berupa pertanyaan pancingan yang dijawab kalimat pembuka. Kata pembuka tidak lagi diulang di akhir (terdengar gagap).
- `subject` model 3D harus benda di kalimat adegan itu sendiri; satu model tidak boleh dipakai berturutan atau lebih dari dua kali, sisanya memakai gambar kartun 3D.
- Cincin kuning di belakang subtitle dihapus, tag yang sama dengan judul disembunyikan, teks perbandingan tidak berhimpit.

## Tahap 16: perapihan dari video "paper cut"

- Klip stok kini diperpanjang sampai klip berikutnya, jadi tidak ada layar kosong di tengah adegan pembuka.
- Teks perbandingan dan grafik batang berdiri di depan lantai (dulu tenggelam di bawah lantai transparan) dan berwarna putih terang.
- Transisi antar adegan dipersingkat (0,25 detik) supaya judul tidak bertumpuk.
- Adegan yang sudah punya animasi 3D tidak lagi meminjam gambar adegan lain; deskripsi gambar yang kembar dilewati.
- Adegan angka: cincin dan keterangan dirapikan agar tidak menimpa judul.

## Tahap 17: ujung suara

Hening panjang di ujung suara narator dibuang (sisakan 0,22 detik) dan 0,12 detik terakhir diberi fade halus, supaya penutup tidak terdengar terpotong dan video berulang menyambung rapat.

## Tahap 18: perbaikan dari video pulpen

- Model 3D hanya diterima kalau judulnya memuat kata kunci (dulu pisau hijau muncul untuk "tinta" dan kristal biru untuk "cangkang logam").
- Tiga animasi 3D baru untuk mekanika mikro: `ball_socket` (bola berputar di soket mengalirkan tinta ke kertas), `capillary` (serat kertas menyerap cairan), `pressure_leak` (tekanan cairan dan bola penutup).
- Aturan baru: alat ukur dan penghitung hanya untuk besaran abstrak; ukuran fisik kecil dan gerakan benda ditampilkan sebagai adegan mekanisme yang memperlihatkan bendanya bergerak.
- Lantai tiap adegan berbeda (kisi, mengkilap, cincin, tanpa lantai) supaya latar tidak monoton.
- Ujung suara: ambang deteksi suara pelan diturunkan dan ruang akhir diperlebar (0,32 detik) supaya suku kata terakhir tidak terpotong.

## Tahap 19: jangkar, kisah inovasi, bahan logam, bunyi baru

- Stok video hanya untuk adegan pembuka. Adegan lain selalu animasi yang menjelaskan isinya (tidak ada lagi ubur-ubur sebagai pengisi).
- Satu benda utama memakai satu model 3D sepanjang video ("cruise ship" dan "sailing ship" tidak lagi berbeda).
- Empat animasi 3D baru: `jangkar_rantai` (potongan melintang dasar laut, rantai terseret di lumpur), `sosrobahu` (balok 480 ton diputar 90 derajat di atas minyak), `mobil_dongkrak` (kisah ide di garasi), `jembatan_geser` (tanjakan 6% jadi 1%).
- Bahan logam bertekstur (bintik, goresan), bahan `rust` untuk karat tipis, dan cahaya tepi (rim light) dua sisi.
- Batang grafik tumbuh dengan hentakan pegas; tulisan grafik batang tidak lagi berhimpit.
- Adegan kisah nyata tampil seperti foto polaroid arsip miring dengan selotip dan keterangan.
- Tiga efek bunyi baru yang cocok kejadiannya: `chain` (rantai), `swell` (berat air), `creak` (derit struktur). Dipakai otomatis oleh animasi yang sesuai.
- Panduan penulis naskah: kerangka "kisah inovasi" (contoh Sosrobahu dan jembatan berjalan Swiss).

## Tahap 20: perbaikan dari video sensor lampu merah

- Animasi 3D baru `loop_induksi`: potongan jalan, kawat tembaga berlilit di bawah aspal, mobil melintas, medan magnet berubah warna, sinyal naik ke kotak pengendali, lampu merah menjadi hijau.
- Grafik batang: tulisan di bawah batang dipecah dua baris dan jarak antar batang disesuaikan, angka naik bersamaan dengan tinggi batang.
- Perbaikan bug: benda yang akan berganti warna kini mulai dari warna awalnya (dulu langsung memakai warna akhir).
- Visual pinjaman: hanya adegan terakhir yang meminjam visual adegan pertama (untuk putaran mulus), dan tidak pernah berturutan dengan visual yang sama (dulu model kota yang sama tampil tiga adegan berurutan).
- Keras suara video disamakan ke standar YouTube (sekitar -14 LUFS) setelah render. Matikan dengan `LOUDNORM=off`.
- Warna latar: adegan bernomor ganjil memakai tema pendamping supaya video tidak satu warna.
- Kalimat pertama tidak boleh diawali kata sambung (karena, dan, tapi, dst.), dijaga di aturan naskah dan dibersihkan otomatis.
- Foto asli: adegan kisah nyata mencari foto dokumentasi berlisensi terbuka di Wikimedia Commons (tanpa kunci) dan menampilkannya di bingkai polaroid. Nama pembuat foto masuk ke deskripsi. Matikan dengan `PHOTO=off`. Kalau tidak ada yang cocok, dipakai gambar kartun atau animasi 3D.
- Air, lumpur, dan oli: aliran berbutir banyak, bergoyang dan berbeda ukuran, dengan bahan mengilap (air), kusam (lumpur), kental (oli). Jenis dibaca dari warna aliran.
