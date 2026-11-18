# Render dan Verifikasi

Baca file ini sebelum membangun dan me-render. Semua perintah di bawah adalah contoh; sesuaikan nama file dengan aset user. Jangan menjalankan perintah yang bergantung pada tool yang belum dicek ada.

## Daftar isi
1. Cek lingkungan
2. Memilih pipeline render
3. Mengukur dan menganalisis voiceover
4. Menganalisis video referensi
5. Menyusun frame secara deterministik
6. Mixing audio dan ekspor
7. Verifikasi file hasil ekspor
8. Musik latar buatan sendiri
9. Jebakan umum

## 1. Cek lingkungan

Jalankan dulu, dan sesuaikan rencana dengan hasilnya:

```bash
ffmpeg -version | head -1; ffprobe -version | head -1
python3 -c "import PIL, numpy; print('PIL+numpy ok')"
node -v
fc-list | head -20          # font yang tersedia
which espeak-ng pico2wave   # TTS offline (kemungkinan besar tidak ada)
```

Catatan: jaringan sandbox dibatasi. `pip` dan `npm` bisa dipakai, tetapi Google Fonts dan unduhan model dari situs lain biasanya diblokir. Untuk font tambahan, coba paket npm `@fontsource/<nama-font>` atau font yang sudah ada di sistem. Versi ffmpeg memengaruhi opsi yang boleh dipakai (lihat bagian 6).

## 2. Memilih pipeline render

Prinsipnya: render setiap frame secara deterministik dari fungsi waktu `t = nomor_frame / 30`, lalu satukan dengan ffmpeg. Cara ini membuat jumlah frame pasti sama dengan durasi total × 30 dan animasi mudah disinkronkan dengan timeline.

| Pipeline | Cocok untuk | Syarat |
|---|---|---|
| Python (Pillow/numpy, opsional cairosvg atau skia-python) | Teks, bentuk, gambar user, mask, parallax; paling mudah dijamin jalan | PIL dan numpy |
| HTML/CSS/JS + browser headless (screenshot per frame) | Tipografi kompleks, SVG, CSS blur dan bayangan | Browser headless tersedia dan bisa dijalankan |
| Remotion / Node | Komposisi berbasis React | Node dan browser headless |
| Filtergraph ffmpeg / MoviePy | Komposisi sederhana | ffmpeg |

Pilih yang benar-benar berjalan di lingkungan ini. Kalau pipeline pilihan gagal, ganti ke yang lain dan jangan mengorbankan kualitas diam-diam. Kalau semuanya gagal, ikuti bagian "Kejujuran soal hasil" di SKILL.md.

Simpan frame sebagai `frames/00000.png` sampai `frames/01199.png`. Untuk mengurangi memori, bisa juga di-pipe langsung ke ffmpeg (`-f rawvideo -pix_fmt rgb24 -s WxH -r 30 -i -`).

## 3. Mengukur dan menganalisis voiceover

Durasi asli:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "Suara Voiceover.mp3"
```

Jeda dan batas kalimat (turunkan `noise` kalau rekaman bising):

```bash
ffmpeg -i "Suara Voiceover.mp3" -af silencedetect=noise=-35dB:d=0.25 -f null - 2>&1 | grep silence_
```

Timing per kata: kalau ada alat ASR/forced alignment yang benar-benar bisa dijalankan, pakai itu. Kalau tidak, bagi waktu menurut batas jeda hasil `silencedetect`, lalu distribusikan kata di dalam tiap frasa secara proporsional menurut jumlah suku kata atau huruf. Katakan kepada user bahwa timing per kata adalah perkiraan.

Kalau durasi total hasil hitungan (durasi voiceover + ±2,5 detik) melebihi 60 detik, berhenti dan tanya user (lihat Tahap 4 di SKILL.md).

Kalau user tidak punya voiceover dan TTS tidak tersedia, jangan mengarang suara. Sarankan user membuat suara dari naskah dan mengupload hasilnya. Kalau user minta draf tanpa suara, timing perkiraan boleh dihitung dari jumlah kata (sekitar 2,5 kata per detik), dengan label draf dan batas total tetap 60 detik.

## 4. Menganalisis video referensi

```bash
ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=nw=1 "Referensi Motion Graphic.mp4"
mkdir -p ref && ffmpeg -i "Referensi Motion Graphic.mp4" -vf "fps=2,scale=480:-1" ref/%03d.png
```

Lihat frame hasil ekstrak (bisa disusun jadi contact sheet) untuk membaca palet, tipografi, komposisi, dan ritme potongan. Ambil prinsipnya, bukan salinannya. Orientasi dan rasio layar referensi menjadi default orientasi output.

## 5. Menyusun frame secara deterministik

- Tulis satu fungsi `render(t)` yang menggambar seluruh frame dari waktu saja, tanpa state tersembunyi atau angka acak yang berubah tiap panggilan (pakai seed tetap).
- Definisikan fungsi easing (ease-out, ease-in-out, overshoot) dan pakai di semua animasi. Hindari gerak linear kecuali memang disengaja.
- Motion blur bisa disimulasikan dengan merata-ratakan beberapa sub-frame pada waktu yang sedikit berbeda.
- Pasang timeline dari tahap 5 sebagai data (daftar segmen dengan waktu mulai/selesai) supaya mudah disetel ulang.
- Render frame 0 sampai (jumlah frame − 1). Frame terakhir harus tetap berisi visual penutup yang jelas, bukan layar kosong.

## 6. Mixing audio dan ekspor

Durasi video mengikuti voiceover. Hitung dulu durasi total dan jumlah frame (aturannya ada di Tahap 4 SKILL.md: suara + ±1 detik pembuka + ±1,5 detik penutup, dibulatkan ke atas ke detik penuh):

```bash
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "Suara Voiceover.mp3")
DUR=$(awk -v v="$VO_DUR" 'BEGIN{t=v+2.5; d=int(t); if (d<t) d++; print d}')
FRAMES=$((DUR*30))
FADE_ST=$(awk -v d="$DUR" 'BEGIN{print d-2.5}')
echo "voiceover=$VO_DUR  total=$DUR detik  frame=$FRAMES"
[ "$DUR" -gt 60 ] && echo "MELEBIHI 60 DETIK: berhenti dan tanya user"
```

Pakai `$DUR` dan `$FRAMES` itu untuk seluruh render (jumlah frame yang digambar, timeline, dan ekspor). Voiceover digeser mulai di detik ke-1 (`adelay`), di-pad sampai akhir video, dan musik diloop lalu dipotong sepanjang video, diturunkan volumenya, di-duck saat ada suara, dan fade-out 2,5 detik di akhir.

Contoh lengkap (voiceover + musik):

```bash
ffmpeg -y -framerate 30 -i frames/%05d.png \
  -i "Suara Voiceover.mp3" \
  -stream_loop -1 -i "Musik Latar.mp3" \
  -filter_complex "\
[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,asetpts=PTS-STARTPTS,asplit=2[vo1][vo2];\
[2:a]atrim=0:$DUR,asetpts=PTS-STARTPTS,volume=0.35,afade=t=out:st=$FADE_ST:d=2.5[bg];\
[bg][vo1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck];\
[duck][vo2]amix=inputs=2:duration=longest:dropout_transition=0,volume=2,alimiter=limit=0.95[aout]" \
  -map 0:v -map "[aout]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 30 -frames:v $FRAMES \
  -c:a aac -b:a 192k -ar 48000 -t $DUR \
  -movflags +faststart "output.mp4"
```

Catatan:
- `amix` pada ffmpeg 6.x selalu menormalkan dengan membagi volume per jumlah input, makanya ada `volume=2` untuk mengembalikan level. Opsi `normalize=0` baru ada di ffmpeg 7.0 ke atas; pakai hanya kalau `ffmpeg -version` menunjukkan versi itu.
- Tanpa musik: hapus input musik dan cabang `[bg]`, lalu pakai `[1:a]adelay=1000:all=1,apad=whole_dur=$DUR,atrim=0:$DUR,afade=t=out:st=<DUR-0.5>:d=0.5[aout]` (hitung `DUR-0.5` dengan `awk` seperti `FADE_ST`).
- Tanpa voiceover (draf): gunakan hanya musik, dan beri label draf.
- Kalau yang diinput video mentah dan bukan urutan gambar, tetap paksa `-r 30` dan `-frames:v $FRAMES`.
- Kalau user menentukan target durasi sendiri, ganti nilai `DUR` dengan target itu (selama voiceover muat dan tidak lebih dari 60), lalu hitung `FRAMES` dan `FADE_ST` dengan rumus yang sama.

## 7. Verifikasi file hasil ekspor

Jangan mengandalkan durasi yang tampil di editor atau skrip. Ukur file MP4-nya:

```bash
# durasi container, codec, resolusi, fps, jumlah frame
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration,nb_frames -of default=nw=1 output.mp4

# hitung frame yang benar-benar terbaca (harus sama dengan $FRAMES)
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 output.mp4
```

Target: container ≈ `$DUR` detik (tepat sampai tiga angka desimal), `$FRAMES` frame video, 30 fps, H.264 + AAC, resolusi sesuai rencana. Encoder AAC menambah sedikit padding sehingga durasi stream audio bisa berbeda beberapa milidetik; yang dipakai sebagai bukti adalah durasi container dan jumlah frame video. Laporkan angka sebenarnya ke user. Kalau meleset, perbaiki dan ekspor ulang, jangan dibulatkan di laporan.

Deteksi masalah yang tidak disengaja:

```bash
# frame hitam
ffmpeg -i output.mp4 -vf blackdetect=d=0.1:pix_th=0.05 -an -f null - 2>&1 | grep black_
# frame beku
ffmpeg -i output.mp4 -vf freezedetect=n=-60dB:d=1.5 -an -f null - 2>&1 | grep freeze_
# keheningan tak disengaja dan level volume
ffmpeg -i output.mp4 -af silencedetect=noise=-50dB:d=0.5 -vn -f null - 2>&1 | grep silence_
ffmpeg -i output.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

Frame beku yang disengaja (jeda visual singkat) wajar; yang dicurigai adalah yang panjang atau di tempat yang tidak direncanakan. `max_volume` yang menyentuh 0 dB berarti ada risiko clipping.

Cek visual: ekstrak frame di titik-titik kunci (awal, tiap pergantian scene, akhir) dan lihat sendiri apakah teks terbaca, ejaan benar, aset tidak terpotong, dan tidak ada elemen bertabrakan.

```bash
ffmpeg -i output.mp4 -vf "fps=1/2,scale=640:-1" check/%02d.png
ffmpeg -ss $(awk -v d="$DUR" 'BEGIN{print d-0.1}') -i output.mp4 -frames:v 1 check/last.png
```

## 8. Musik latar buatan sendiri

Hanya kalau user tidak menyediakan musik. Buat pad ambient sederhana dengan numpy atau `aevalsrc`/`sine` dari ffmpeg: beberapa nada akor yang bertumpuk dengan volume pelan, ditambah denyut ringan di tempo yang pas dengan ritme visual (misalnya 100–120 BPM) bila ingin aksen beat. Ekspor sebagai WAV 48 kHz, lalu masukkan ke mix di atas.

Katakan terus terang ke user bahwa ini musik sintetis sederhana, bukan komposisi profesional, dan sarankan musik bebas royalti bila ingin hasil lebih kaya.

## 9. Jebakan umum

- **VFR (variable frame rate)**: paksa CFR dengan `-r 30`. Cek `r_frame_rate` dan `avg_frame_rate` sama-sama 30/1.
- **Durasi kurang atau lebih satu frame**: biasanya karena jumlah frame yang dirender tidak sama dengan `DUR × 30`. Hitung ulang sebelum encode.
- **Audio lebih panjang dari video** (atau sebaliknya): pakai `apad=whole_dur=$DUR` dan `atrim=0:$DUR` seperti di contoh, plus `-t $DUR`.
- **Font tidak ditemukan**: cek `fc-list`, atau unduh lewat `npm`, jangan diam-diam jatuh ke font bawaan yang jelek.
- **Teks Bahasa Indonesia terpotong di tepi**: ukur lebar teks dengan fungsi pengukur font, bukan menebak.
- **File sangat besar**: naikkan CRF (misalnya 20–22), jangan menurunkan resolusi.
