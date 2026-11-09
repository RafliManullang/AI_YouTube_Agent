# AI YouTube Agent

Agen ini membuat video YouTube Shorts sendiri, dari cari topik sampai diunggah:

1. Gemini memilih topik (cara kerja benda, fakta sains, atau cerita sejarah) dan menulis naskah.
2. Edge-TTS mengubah naskah jadi suara Bahasa Indonesia, gratis, plus waktu tiap kata.
3. Pollinations membuat 3 gambar visual bergaya infografis 3D.
4. Remotion menyatukan gambar, suara, dan teks kinetik jadi video.
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

Pilihan lain: `--topik "cara kerja lift gedung"` untuk menentukan topik sendiri, dan
`--privasi unlisted` atau `--privasi public` untuk mengubah status video.

## Hal yang perlu diketahui

- Satu kali jalan butuh sekitar 3 sampai 5 menit, karena gambar gratis dibatasi 1 gambar tiap 45 detik.
- Kalau gambar gagal dibuat, agen memakai gambar cadangan supaya video tetap jadi.
- Video hasil ada di `video_engine/out/shorts_final.mp4`.
- Status bawaan video adalah `private`. Proyek Google Cloud yang belum diverifikasi oleh YouTube memang hanya boleh mengunggah video privat.
- Jangan pernah mengunggah `.env`, `client_secret.json`, atau `token.json` ke GitHub.
