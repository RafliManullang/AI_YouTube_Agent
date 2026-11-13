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
