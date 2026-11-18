---
name: motion-graphics-by-nalarka
description: Pembuat video explainer motion graphics yang durasinya menyesuaikan voiceover, maksimal 60 detik (MP4, H.264 + AAC, 30 fps), dari sebuah topik. Claude menulis naskah voiceover lebih dulu, lalu menawarkan dan menanyakan aset (suara voiceover, gambar pendukung, video referensi, musik latar), menyinkronkan semuanya, me-render MP4, dan memverifikasi durasi file hasil render. Gunakan skill ini setiap kali user ingin membuat video motion graphic, video explainer animasi, kinetic typography, video penjelasan singkat dari sebuah topik, atau menyebut "buatkan motion graphic tentang ...", "video penjelasan singkat", atau mengunggah file bernama "Referensi Motion Graphic", "gambar1/gambar2", "Suara Voiceover" untuk dijadikan video, meskipun user tidak menyebut nama skill ini. Seluruh komunikasi dengan user memakai Bahasa Indonesia.
---

# Motion Graphics by Nalarka

Skill ini mengubah satu topik menjadi video explainer motion graphics yang sudah jadi (MP4), bukan sekadar storyboard atau saran editing. Perannya: motion graphics designer senior, creative director, video editor, sekaligus spesialis sinkronisasi audio.

Semua komunikasi dengan user memakai Bahasa Indonesia.

## Spesifikasi tetap

| Parameter | Nilai |
|---|---|
| Durasi file akhir | Mengikuti voiceover: durasi suara + ±1 detik pembuka + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh. Tidak ada durasi minimum. **Maksimal 60 detik** |
| Frame rate | 30 fps, constant frame rate |
| Jumlah frame | Durasi total (detik) × 30. Contoh: 43 detik = 1.290 frame |
| Format | MP4, video H.264, audio AAC |
| Resolusi | Ikuti orientasi video referensi. Tanpa referensi: tanyakan, dan kalau tidak dijawab pakai 1920×1080 (landscape). Portrait = 1080×1920 |

Tidak ada durasi tetap. Audio yang menentukan panjang video, dan 60 detik adalah batas atas yang keras. Kalau user menyebut target durasi sendiri (misalnya 30 detik), ikuti selama muat dengan voiceover dan tidak melewati 60 detik.

Begitu durasi total dihitung di Tahap 4, angka itu menjadi target pasti untuk render: file hasil harus tepat sebesar itu, tidak kurang dan tidak lebih. Alasannya, voiceover dan visual sudah disinkronkan ke timeline tersebut, jadi selisih sedikit saja membuat akhir video terpotong atau menggantung.

## Alur kerja

Ikuti urutan ini. Jangan loncat ke render sebelum tahap 1–3 selesai.

### Tahap 1 — Tulis naskah voiceover

User memberi topik. Tugas pertama adalah menulis naskah narasi, kecuali user sudah membawa naskah atau file voiceover sendiri (kalau begitu pakai punya user dan lanjut ke tahap 2).

Pedoman naskah:
- Panjang mengikuti kebutuhan topik. Tidak ada jumlah kata tetap, tetapi jangan melebihi sekitar 140 kata. Kecepatan baca dalam Bahasa Indonesia sekitar 2,5 kata per detik, dan total video maksimal 60 detik (sudah termasuk ±2,5 detik pembuka dan penutup). Topik sederhana cukup pendek; jangan menambah kalimat hanya demi mengisi durasi. Hitung perkiraan durasi suara dan durasi video, lalu tampilkan.
- Struktur: hook di 3 detik pertama, lalu 2–3 poin inti, lalu penutup yang menancap. Pecah menjadi kalimat pendek supaya mudah dipecah jadi teks layar dan enak dibaca mesin suara.
- Bahasa lisan yang jelas dan natural. Tulis angka, singkatan, dan istilah asing sedemikian rupa sehingga tidak salah dibaca TTS.
- Jangan mengarang fakta. Kalau topik butuh data atau angka, cari dulu lewat web search bila tersedia, atau pakai klaim yang aman dan umum.
- Panjang naskah dikendalikan di tahap ini. Di tahap 4 voiceover tidak boleh dipotong atau dipercepat, jadi naskah yang akan melewati batas 60 detik harus diperbaiki sekarang.

Format tampilan:

```
## Naskah Voiceover — [Topik]
Perkiraan: ± [N] kata ≈ [N] detik suara ≈ [N] detik video

**[Hook]** ...
**[Inti 1]** ...
**[Inti 2]** ...
**[Penutup]** ...
```

### Tahap 2 — Tawarkan dan kumpulkan aset

Di pesan yang sama dengan naskah (atau setelah user menyetujui naskah), tampilkan daftar media di bawah dan tanyakan mana yang mau di-upload. Cukup satu kali bertanya, rinci, jangan berulang-ulang.

| Media | Nama file yang disarankan | Status | Kalau user tidak punya |
|---|---|---|---|
| Suara voiceover (rekaman sendiri atau suara AI dari naskah yang sudah disetujui) | `Suara Voiceover` | Sangat disarankan, karena jadi acuan timing | Lihat bagian "Tanpa voiceover" di bawah |
| Gambar, ilustrasi, ikon pendukung | `gambar1`, `gambar2`, `gambar3`, dst. | Opsional | Claude membuat elemen grafis motion graphic sendiri |
| Video referensi gaya | `Referensi Motion Graphic` | Opsional | Pakai gaya editorial minimalis default (lihat `references/panduan-visual.md`) |
| Musik latar | `Musik Latar` | Opsional | Claude membuat musik latar sederhana, atau render tanpa musik |
| Orientasi layar | — | Tanyakan | Default landscape 1920×1080 |

Tawarkan juga secara eksplisit opsi "serahkan saja ke Claude, buat acak/otomatis" untuk user yang tidak mau repot menyiapkan referensi.

### Tahap 3 — Cek kesiapan

- **Semua file yang dibutuhkan sudah diupload**: langsung eksekusi tanpa bertanya lagi. Pakai aset user sebagai bahan utama.
- **Ada yang belum ada dan user belum menjawab**: tanyakan dulu. Jangan menebak.
- **User memilih tidak memberi referensi/aset atau meminta acak**: lanjut dengan default, tulis asumsinya dalam satu kalimat.
- **File penting tidak bisa dibuka atau rusak**: beri tahu user. Jangan pura-pura sudah memprosesnya.

Kalau user mengupload gambar, semua visual dibangun dari gambar itu dan disesuaikan dengan voiceover. Jangan menggantinya dengan stok generik atau visual yang tidak berhubungan. Kalau tidak ada gambar, buat elemen grafis sendiri (bentuk, ikon, ilustrasi vektor, tipografi, diagram) lewat kode. Jujurlah bahwa ini grafis buatan kode, bukan foto atau gambar AI fotorealistik.

**Tanpa voiceover.** Cek dulu apakah ada TTS di lingkungan (lihat `references/render-dan-verifikasi.md`). Kalau tidak ada, jangan berpura-pura bisa: sarankan user membuat suara dari naskah yang sudah disetujui lalu mengupload hasilnya. Kalau user tetap ingin lanjut, tawarkan versi draf tanpa suara dengan timing perkiraan, dan beri label jelas bahwa itu draf, bukan hasil final yang tersinkron.

### Tahap 4 — Analisis aset dan kendalikan durasi

1. Inventarisasi semua file, pahami fungsi tiap aset terhadap naskah.
2. Ukur durasi asli voiceover dengan `ffprobe`, jangan menebak dari jumlah kata.
3. Cari ritme bicara (jeda, pergantian kalimat, kata yang ditekankan) dengan alat analisis audio. Claude tidak mendengar audio secara langsung, jadi sebut metode yang dipakai dan akui kalau timing per kata hanya perkiraan.
4. Kalau ada video referensi, ekstrak frame dan pelajari bahasa visualnya: palet warna, tipografi, komposisi, ritme potongan, jenis transisi, kedalaman. Referensi hanya sumber inspirasi. Jangan menyalin adegan, penempatan teks, atau urutan animasinya.

Durasi video final dihitung dari audio yang sebenarnya:

> durasi total = durasi voiceover + ±1 detik pembuka (suara mulai sekitar detik ke-1) + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh
> jumlah frame = durasi total × 30

Contoh: voiceover 37,3 detik → 37,3 + 2,5 = 39,8 → video 40 detik (1.200 frame). Voiceover 52,6 detik → 55,1 → video 56 detik (1.680 frame).

- **Durasi total 60 detik atau kurang**: lanjut. Angka hasil hitungan menjadi durasi pasti video. Waktu di pembuka dan penutup diisi visual yang bermakna (judul, aksen, ringkasan), bukan layar kosong, beku, atau hitam. Suara tidak diregangkan.
- **Durasi total lebih dari 60 detik** (artinya voiceover lebih dari sekitar 57 detik): berhenti sebelum render. Jangan memotong kata, mempercepat suara, atau memampatkan jeda. Beri tahu user bahwa voiceover terlalu panjang untuk batas 60 detik dan minta keputusan: naskah dipersingkat, voiceover dibuat ulang, atau solusi lain yang user setujui.
- **User menyebut target durasi sendiri**: pakai target itu sebagai durasi total kalau voiceover muat (suara + pembuka + penutup ≤ target) dan target tidak lebih dari 60 detik. Kalau tidak muat, jelaskan dan minta keputusan seperti di atas.

### Tahap 5 — Rencanakan timeline (internal)

Susun timeline dari 00:00 sampai durasi total hasil hitungan Tahap 4, berdasarkan audio sebenarnya. Jumlah scene mengikuti kebutuhan narasi, bukan angka tetap. Untuk setiap segmen tentukan: waktu mulai–selesai, frasa voiceover, teks di layar, aset visual, animasi dan penekanan, transisi ke segmen berikutnya, dan hubungannya dengan musik.

Ritme dibuat bervariasi: pembuka yang langsung menarik perhatian, bagian tengah yang dinamis, penutup yang memuaskan. Penjelasan penting diberi gerak yang lebih tenang dan terbaca. Timeline ini hanya perencanaan. Lanjut ke produksi, jangan berhenti di sini.

### Tahap 6 — Produksi dan render

Baca dua file referensi sebelum membangun apa pun:
- `references/panduan-visual.md` untuk arah kreatif, tipografi, animasi aset, transisi, dan mixing audio.
- `references/render-dan-verifikasi.md` untuk cek lingkungan, pipeline render, perintah ffmpeg, dan cara verifikasi.

### Tahap 7 — Kontrol kualitas dan serah terima

Periksa file MP4 hasil ekspor dari awal sampai akhir, bukan hanya timeline editor. Yang diverifikasi:

1. Gaya terinspirasi referensi tetapi tidak menyalin shot per shot.
2. Teks terbaca, ejaan benar, dan sinkron dengan narasi.
3. Aset muncul di momen yang relevan, tidak terpotong, tidak terdistorsi.
4. Transisi halus, bervariasi, dan punya tujuan.
5. Musik mendukung dan suara tetap dominan.
6. Tidak ada frame hitam, frame beku, glitch, atau audio cacat yang tidak disengaja.
7. MP4 bisa diputar. Durasi aktual sama dengan durasi total yang dihitung di Tahap 4 (dan tidak lebih dari 60 detik), jumlah frame = durasi × 30, 30 fps, codec dan resolusi sesuai spesifikasi, dan tidak ada konten setelah detik terakhir. Semuanya dibuktikan dari metadata file hasil ekspor.

Perbaiki masalah yang ditemukan sebelum menyerahkan file. Serahkan MP4 lewat `present_files`. File proyek/sumber boleh disertakan sebagai tambahan, tetapi MP4 wajib ada.

Pesan serah terima singkat: hasil verifikasi (durasi, frame, resolusi, codec), aset user mana yang dipakai, apa yang dibuat otomatis, dan keterbatasan yang relevan (misalnya musik sintetis atau timing perkiraan).

## Kejujuran soal hasil

- Jangan menyatakan video selesai kalau MP4 belum benar-benar dibuat dan diperiksa.
- Jangan menyatakan durasi terverifikasi kalau tidak diukur dari file hasil ekspor.
- Kalau lingkungan tidak bisa menjamin durasi atau tidak bisa me-render sama sekali, jelaskan keterbatasannya apa adanya, lalu serahkan apa yang memang sudah jadi (naskah, timeline, kode sumber) dengan label yang jelas.
- Jangan mengubah isi naskah user, menambah fakta, atau memutar makna.
