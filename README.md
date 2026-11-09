# AI YouTube Agent

Agen ini membuat video YouTube Shorts sendiri, dari cari topik sampai diunggah:

1. Gemini memilih topik (cara kerja benda, fakta sains, atau cerita sejarah) dan menulis naskah.
2. Edge-TTS mengubah naskah jadi suara Bahasa Indonesia, gratis, plus waktu tiap kata.
3. Gemini juga menentukan visual tiap adegan (diagram alur, mind map, atau angka yang menghitung naik), dan Pixabay atau Pexels (gratis, opsional) memberi video latar yang bergerak.
4. Remotion menyatukan semuanya dengan suara dan teks kinetik jadi video, dengan latar berwarna yang terus bergerak.
5. Video diunggah ke YouTube.

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

Pilihan lain: `--topik "cara kerja lift gedung"` untuk menentukan topik sendiri, dan
`--privasi unlisted` atau `--privasi public` untuk mengubah status video.

## Hal yang perlu diketahui

- Satu kali jalan butuh sekitar 2 sampai 4 menit.
- Video latar (opsional): daftar gratis di pixabay.com, buka pixabay.com/api/docs setelah login untuk melihat key-nya, lalu isi `PIXABAY_API_KEY` di `.env`. Pexels (`PEXELS_API_KEY`) juga didukung kalau pendaftarannya sudah dibuka lagi. Kalau kosong atau gagal, video tetap jadi dengan latar animasi bawaan. Nama sumber video otomatis ditulis di deskripsi YouTube.
- Musik latar (opsional): taruh file musik bebas hak cipta bernama `bgm.mp3` di folder `video_engine/public`. Otomatis dipakai dengan volume pelan.
- Video hasil ada di `video_engine/out/shorts_final.mp4`.
- Status bawaan video adalah `private` supaya hasil pertama bisa dicek dulu. Untuk langsung publik, isi `YOUTUBE_PRIVACY=public` di file `.env`, atau jalankan dengan `--privasi public`.
- Jangan pernah mengunggah `.env`, `client_secret.json`, atau `token.json` ke GitHub.
