# AI YouTube Agent

## Mode bawaan: LEGO Mekanis

Tahap naskah dan TTS tetap sama. Pada `[3/5]`, agen mengirim ringkasan adegan (prompt maksimal 2.000 byte) ke penulis JSON, dengan prioritas Groq. Satu respons valid cukup untuk seluruh video. Model hanya merakit `mech_rig` (node dan pipa) dan `scene_states` (fokus, zoom, cutaway, nilai aktif); tidak menulis TSX. Panjang respons, waktu dan kuota tetap bergantung pada jumlah adegan dan provider.

Remotion menggambar casing, tangki, piston, heater, katup, turbin, chamber, pegas, pipa dan objek konteks dengan komponen lokal. Kamera memakai pusat komponen yang sama dengan gambarnya; audio, subtitle dan citation badge tetap mengikuti timing TTS. **Mode ini tidak memanggil generator gambar atau Vision.** Sebelum render, koordinat pusat/titik pipa, ID unik, referensi fokus/aktif dan jumlah state diperiksa. Rig valid disimpan di `cache/last_session.json` bersama naskah/audio.

- **Lanjutkan video sebelumnya dengan rig baru:** `jalankan_agen.bat --resume --tanpa-upload`. Jika checkpoint hanya punya aset hybrid, rig dibuat sekali tanpa mengulang TTS. Jika sudah ada rig valid, tidak ada panggilan LLM tahap 3.
- **Mulai topik baru:** `python main_agent.py --topik "mesin kopi pod" --tanpa-upload`.
- **Pratinjau contoh tanpa API:** dari folder `video_engine`, jalankan `npm ci`, lalu `npx remotion studio src/index.ts --props=examples/pod-modular.json` dan pilih `ShortsComp`. Contoh mesin kopi berdurasi 8 detik, tanpa narasi.

### Siluet, suasana, dan analogi per adegan

Perakit memilih `mech_rig.archetype`: `appliance_box`, `aerodynamic_wing` (airfoil dengan dua laju aliran), `cylinder_tube`, `disc_rotary`, atau `open_frame` (tanpa selubung). Untuk bentuk khas topik, utamakan satu node `custom_shape`: tetap beri `id,x,y,w,h`, lalu `viewBox` lokal seperti `"0 0 400 200"` dan 1–5 `paths` (disarankan 2–5). Tiap path hanya berisi `d` dan `fill` heksadesimal, tanpa markup. Pakai segmen absolut `M L H V Q C Z`, satu set koordinat per perintah, nilai 0–400. Siluet ini menggantikan casing, di belakang pipa dan blok mekanis yang beranimasi.

`mech_rig.atmosphere` mengatur `bgTop`, `bgBottom`, `accent` (`#rrggbb`), `gridStyle` (`blueprint`, `radial_glow`, `clean`) dan `particle` (`wind_lines`, `bubbles`, `sparks`, `steam`, `dots`). Tidak ada preset kategori yang mengunci kombinasi warna. Batasi objek analogi dengan `visibleScenes`, misalnya `[3]` hanya untuk adegan keempat (indeks mulai 0). Tanpa daftar ini, node tersedia di semua adegan. Kamera tidak boleh menargetkan node tersembunyi.

Contoh tanpa API: dari `video_engine`, jalankan `npx remotion studio src/index.ts --props=examples/wing-modular.json`. Saat `--resume`, rig lama tanpa archetype/suasana dirakit ulang sekali memakai naskah dan audio checkpoint; rig baru yang valid langsung dipakai.

### Wujud asli di pembuka, komponen aksi, dan gerbang anti-aneh

Mode modular kini menampilkan **satu gambar benda asli** (`assets/01_exterior.png`, dibuat `asset_generator.generate_exterior` lewat provider gambar yang sudah ada; matikan dengan `EXTERIOR=off`) selama cutaway masih rendah — babak pertama dan penutup memperlihatkan benda yang dikenali penonton, lalu gambar memudar menampakkan jeroan modular. Gagal membuat gambar tidak menghentikan render; siluet archetype tetap tampil.

Komponen baru di `MechanicalKit.tsx`: `push_button` (tombol besar yang benar-benar turun saat aktif, lengkap panah tekan), `float_ball` (bola pelampung + lengan yang naik mengikuti permukaan air), dan `siphon_pipe` (pipa leher angsa S/U dengan aliran bergerak). Prompt perakit hanya boleh memakai komponen yang benar-benar ada di benda aslinya.

Gerbang anti-aneh di `mech_rig.validate()` (dan skema Zod): komponen kerja wajib w/h minimal 85 (tidak ada lagi tombol sekecil titik), adegan inti (`cutaway>=0.5`) wajib zoom 1.35–1.9, dan komponen internal harus berada di dalam bodi atau menempel ujung pipa (anti melayang). Prompt naskah juga ditegakkan kode: hanya komponen fisik nyata, arah aliran harus benar, dan kalimat ajakan komentar otomatis dibuang dari penutup (`strip_comment_cta`).

### Prompt pembuka terkunci, auto-fit rig, dan zona aman Shorts

Gambar pembuka kini selalu memakai prompt terkunci (`asset_generator.exterior_prompt`: ilustrasi teknis cel-shaded benda aslinya, latar studio slate polos, tanpa teks/pemandangan/gua) dan dicek Gemini Vision dengan pertanyaan ya/tidak; penolakan memicu satu regenerasi. Saat `cutaway > 0.5`, gambar pembuka hilang total (bukan bayangan samar), latar blueprint bersih tampil dengan kerangka casing putus-putus yang membungkus semua komponen, dan auto-fit bounding box memperbesar rig hingga mengisi area tengah. Komponen non-fokus hanya turun ke opasitas 0.58.

Validator juga menolak label analogi (balon/spons/dsb.) tanpa `visibleScenes` terbatas, dan tuas/piston/pegas yang tidak bersentuhan tepi dengan komponen atau pipa lain. HUD status kini maksimal dua kata di tengah atas; subtitle berada di 69% tinggi layar; fokus kamera di zona aman 22–66% (`layout/SafeLayout.tsx`). `END_PAD` dipangkas ke 0.3 detik agar loop menyambung rapat; BGM otomatis ducking ke 0.085 saat narator bicara (0.16 di jeda), dan whoosh halus berbunyi saat transisi masuk X-ray atau lompatan zoom besar.

### Tanpa badai retry, tiga gambar cerita, dan simulasi yang bekerja

Badai retry di tahap rig diputus dari akarnya: prompt `mech_rig.py` kini menyebut jumlah adegan secara eksplisit ("WAJIB TEPAT N objek di scene_states (sceneIndex 0..N-1)"), validator menolak satu `focusNode` dipakai lebih dari 2 adegan berturut-turut, backoff LLM dipangkas ke 3s/6s dengan maksimal 2 percobaan per kunci dan timeout Gemini 30 detik. Error 503 berarti server model penuh (bukan kunci mati), jadi setelah 2 kunci berturut-turut kena 503 pada model yang sama, model itu diblokir untuk sesi tersebut dan pipeline pindah model. Run baru (bukan `--resume`) juga membersihkan sisa `public/clips/*` dan still gerbang topik lama secara otomatis—folder `public/` disalin Remotion di setiap bundling, jadi kebersihan folder ini langsung memangkas waktu bundel.

Setiap video kini punya 3 gambar cerita dari `asset_generator.generate_story_images()` (semuanya dicek Gemini Vision, maksimal 1 regenerasi, cache sha256): (1) hook aksi di detik 0-5—benda sedang mengerjakan sasaran aslinya, mis. dongkrak mulai mengangkat mobil; (2) visual analogi yang tampil penuh saat adegan narasi ber-mode analogi; (3) payoff/resolusi di adegan penutup. Layer X-ray dijamin opacity 0 saat gambar cerita tampil (tidak ada lagi kotak hantu di belakang gambar penutup).

Simulasi mekanik mengikuti sebab-akibat fisik: node rig dapat membawa `direction` (`up/down/left/right`) dan `load` (tire/car/weight/lid/box). Piston ber-`direction:"up"` benar-benar memanjang ke atas dengan beban yang ikut naik saat `active` 0->1, panah gaya berwarna hijau untuk angkat, merah untuk tekan, biru untuk samping; aliran pipa menyala mengikuti `active` sehingga rantai tuas dipompa -> oli mengalir -> level naik -> piston naik terbaca dalam satu tarikan napas. Empat elemen retensi melengkapi: inset picture-in-picture "AKSI LUAR" di kiri atas selama zoom X-ray, gauge angka kunci (mis. "2 TON") yang terisi mengikuti aktivasi fokus, BGM yang merunduk tepat sebelum kata klimaks lalu naik lagi sesudahnya, dan anti-tabrakan label otomatis—label/overlay yang berjarak vertikal <55px digeser sampai aman.

### Sinkronisasi analogi, dua objek dalam satu frame, dan layar yang bersih

Gambar analogi kini dikunci ke adegan yang narasinya sendiri memuat kata perumpamaan: `svg_composer.view_mode()` mengembalikan mode `analogi` di posisi durasi berapa pun (dulu hanya di rentang 30-90%, sehingga analogi yang diucapkan di 00:14 jatuh ke X-ray dan gambarnya baru muncul 12 detik kemudian di adegan yang salah). Di Remotion, gambar analogi masuk dengan whip-pan 8 frame tepat di awal adegannya, tampil maksimal 4 detik, lalu potong balik ke X-ray - tidak pernah diam 8 detik.

Prompt gambar pembuka dan penutup wajib menampilkan dua objek berinteraksi dalam satu frame: benda bersama sasaran nyatanya, sedang memulai pekerjaannya (pembuka) atau dengan hasil akhir yang tuntas (penutup) - tidak ada lagi benda sendirian di lantai kosong atau mobil tanpa dongkraknya. Satu `STYLE_ANCHOR` ditempel ke semua prompt gambar dalam satu video: latar studio slate gelap yang sama, garis tinta cel-shaded yang sama, cahaya hangat dari kiri atas, dan warna khas benda yang tidak berubah antar-adegan (tidak ada lagi dinding batu di pembuka dan lingkaran oranye di penutup).

Elemen pengganggu dibuang: lingkaran kuning focus ring tidak lagi digambar di adegan ilustrasi (penyorot hanya di X-ray pada komponen spesifik), dan kotak PiP "AKSI LUAR" dihapus karena isinya gambar diam yang menabrak judul - seluruh layar kini untuk simulasi X-ray yang diperbesar. Label generik dilarang keras di `mech_rig.validate()` ("Benda Utama", "Komponen", "Alat", dst. ditolak; wajib nama fisik seperti Katup Pelepas), label berlabel silinder wajib berwujud node `piston`, dan piston angkat wajib `direction:"up"` plus `load` - batang memanjang ke atas mendorong beban, dan panah gaya mengikuti arah itu (terverifikasi: panah hijau kini benar-benar menunjuk ke atas). Transisi masuk X-ray memakai pukulan zoom 8 frame seolah kamera menembus cangkang. Terakhir, ritme naskah dikunci: satu adegan tepat satu kalimat pendek 8-14 kata (sekitar 3-4 detik), kalimat majemuk dipecah, dan tanda pisah (—) dipakai tepat sebelum fakta mengejutkan.

Validator rig kini memperbaiki, bukan membuang: sejak run dongkrak hidrolik menunjukkan Groq/Gemini sebenarnya berhasil membuat JSON rig tetapi digugurkan hal-hal kecil, tiga aturan di `mech_rig.validate()` menjadi auto-sanitize - komponen kerja di bawah 85px diperbesar otomatis ke minimum, label generik ("Benda Utama" dkk.) diganti otomatis (casing menjadi "Rangka Utama", node lain memakai nama id-nya yang dirapikan), dan piston angkat yang lupa diisi `direction`/`load` dilengkapi otomatis (`up` + `weight`). Aturan struktural yang memang tidak bisa diperbaiki dengan aman (komponen melayang, zoom adegan inti terlalu jauh, silinder berwujud corong/tangki, jumlah state tidak sama dengan adegan) tetap menolak, karena memperbaikinya otomatis justru akan mengarang-ngarang mekanisme.

Catatan batas yang disadari: bagian tengah video tetap diagram SVG modular dan punya langit-langit kualitas "diagram 2D bersih". Mengganti mayoritas adegan tengah dengan storyboard ilustrasi per adegan (seperti channel referensi) adalah langkah besar berikutnya - fondasinya sudah disiapkan lewat gambar cerita + `STYLE_ANCHOR` yang konsisten, tetapi belum diaktifkan karena biaya dan waktu generate per adegan perlu diukur di run nyata dulu.

## Mode opsional: gambar hybrid (`--visual hybrid`)

Pipeline hybrid membuat Shorts dengan **3–4 ilustrasi AI per topik** dan motion graphics Remotion. Anatomi benda tidak lagi dibuat dengan meminta LLM menulis TSX. Bagian riwayat tahap di bawah juga mendokumentasikan mesin visual versi lama.

1. Penulis/editor menyusun naskah, deskripsi ilustrasi, komponen fokus, kamera, dan overlay per adegan sebagai JSON.
2. TTS menyimpan narasi dan timing kata/adegan ke checkpoint.
3. Agen membuat `01_exterior.png`, `02_analogy.png`, `03_cutaway.png` dan, bila diminta naskah, `04_closeup.png` di `video_engine/public/assets/`. Master style dan palet dipilih konsisten per judul. Hugging Face menerima seed bila didukung provider; semua generator memakai penguncian prompt/palet.
4. Gemini Vision membaca **PNG cutaway yang sudah dicrop**: satu respons JSON berisi titik komponen (0–1 dari kiri atas) dan pemeriksaan teks bocor. Jika ada teks, maksimal satu gambar pengganti dibuat dan dicek lagi. Bila komponen tidak ditemukan, adegannya memakai badge tanpa panah/spotlight spekulatif. Bila percobaan kedua juga ditolak, render berhenti untuk peninjauan.
5. Remotion menggerakkan kamera dan overlay menurut timing TTS. Transisi exterior → cutaway memakai sapuan sinar-X 18 frame + whoosh; pergantian gambar lain memakai crossfade. Subtitle dan citation badge tetap di koordinat layar.

**Provider gambar (urutan prioritas):**
1. Jika `CF_ACCOUNT_ID` dan `CF_API_TOKEN` terisi, coba FLUX.1-schnell di Cloudflare Workers AI. Bila gagal, lanjut ke provider berikutnya.
2. Jika `SKIP_GEMINI_IMAGE=1`, lewati semua key dan model Gemini Image. Jika tidak, untuk setiap key di `GEMINI_API_KEY` (dipisah koma), coba `IMAGE_MODEL` atau `gemini-3.1-flash-image`, lalu `gemini-3.1-flash-lite-image`, `gemini-2.5-flash-image`, dan `gemini-3-pro-image`.
3. Hugging Face memakai `InferenceClient(provider="auto")` dengan `HF_TOKEN` berizin Inference Providers. `HF_IMAGE_MODEL` bisa diganti (bawaan `black-forest-labs/FLUX.1-schnell`). Jika parameter gambar ditolak, coba sekali dengan ukuran bawaan provider. Gambar persegi dari Cloudflare/HF dipotong ke 1080×1920 sebelum Vision dan render.

Flag tersebut tidak menonaktifkan Gemini Vision: jika ada `GEMINI_API_KEY`, pemeriksaan cutaway mencoba `VISION_MODEL` (opsional), lalu `gemini-3.8-flash` dan `gemini-3.6-flash` tanpa duplikat. Bila Vision tidak tersedia atau gagal, checkpoint menandai pemeriksaan dilewati: gambar tetap dipakai tanpa verifikasi teks, kamera fokus ke tengah, dan overlay cutaway hanya berupa badge. Simpan token hanya di `.env`. Akses model, biaya dan kuota mengikuti akun/provider.

**Jalankan:** `python main_agent.py --visual hybrid --topik "pemanas air instan" --tanpa-upload`. Setelah kegagalan aset/Vision/render, jalankan `python main_agent.py --visual hybrid --resume --tanpa-upload`. Checkpoint `cache/last_session.json` menyimpan path aset, checksum, hasil Vision dan status percobaan per gambar. Gambar utuh yang sudah lolos tidak dibuat lagi; pemeriksaan yang terputus memakai PNG yang sama. Jika gambar pengganti ditolak, periksa PNG sebelum memulai topik baru. Run tanpa `--resume` membersihkan empat nama PNG milik generator setelah naskah baru disimpan; aset pribadi dengan nama lain tidak dihapus.

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

## Tahap 21: setrika dan keping bimetal

- Dua animasi 3D baru: `setrika` (bodi tembus pandang, tapak, elemen pemanas menyala merah, keping bimetal, kain) dan `bimetal` (dua lapis kuningan dan besi benar-benar melengkung saat panas lalu lurus lagi saat dingin, berubah warna dari abu-abu ke jingga merah, termometer naik, saklar terdorong, lampu pemanas mati).
- Gerakan berputar dan perubahan warna kini bisa bolak-balik (`loop`), dan warna berubah bertahap seperti suhu. Batas bagian per animasi dinaikkan (60 benda, 140 gerakan).
- Adegan yang sudah punya animasi bawaan tidak lagi diganti model 3D dari Poly Pizza (dulu muncul pemanas ruangan untuk "setrika"). Model yang judulnya pemanas, radiator, atau benda berbeda juga ditolak.
- Subtitle dikecilkan, dibuat dalam bantalan gelap tipis, dan diturunkan agar tidak menutupi tengah layar.

## Tahap 22: arsitektur penuh (10 modul)

Repo ini memakai Python sebagai pengatur (`main_agent.py`, dijalankan lewat `jalankan_agen.bat`; boleh juga `--topic` selain `--topik`) dan Remotion untuk gambar. Sepuluh modul dipasang sesuai pembagian itu. Satu hal sengaja berbeda: LLM tidak menulis kode Remotion. Ia hanya memilih jenis adegan, animasi terverifikasi, dan isi teks, sehingga tidak ada kode karangan yang bisa rusak.

| # | Modul | Berkas |
|---|-------|--------|
| 1 | Skema Zod dan gerbang validasi | `video_engine/src/schemas/sceneSchema.ts`, `video_engine/src/cli/validateProps.ts`, `schema_gate.py` |
| 2 | Registry komponen terverifikasi | `video_engine/src/components/library/` (IronBody, HeatingCoil, BimetalStrip, ThermostatSwitch) |
| 3 | Mesin perumpamaan visual | `metaphors.py` (kamus), dipakai `sim_library.KEYWORDS`, prompt naskah, dan Director |
| 4 | Animasi pegas dan stagger | `video_engine/src/utils/animation.ts` |
| 5 | Kamera sinematik | `video_engine/src/components/CameraRig.tsx` |
| 6 | Zona aman dan tata letak | `video_engine/src/layout/SafeLayout.tsx` |
| 7 | Irama dan bobot adegan | `pacing.py` (+ lama transisi per adegan di `ShortsComp.tsx`) |
| 8 | Audio dan SFX | sudah ada: `Sfx.tsx`, `tools/buat_sfx.py`. Sengaja hanya di momen penting, bukan per kata |
| 9 | AI Director | `director.py` |
| 10 | Pekerja render dan pemulihan | `render_worker.py` |

Alur: naskah (penulis + editor) -> Director memeriksa dan memperbaiki -> irama diberi tag -> suara dan visual -> data divalidasi Zod (dengan perbaikan otomatis oleh LLM bila ditolak) -> render dengan pemulihan otomatis -> keras suara disamakan.

- Zod dipasang pada versi persis 4.6.7 karena itu yang diminta Remotion 4.0.541.
- Komponen registry dipakai lewat `sim.components` (`{id, pos, scale, rot, props, labels}`). Id di luar registry ditolak oleh `clean_sim` dan skema.
- Animasi `setrika` dan `bimetal` kini dibangun dari komponen registry. Preset baru `aliran_listrik` dan `panas_berlebih` ditambahkan oleh mesin perumpamaan.
- Zona visual: isi adegan 3D/diagram dikecilkan ke 72% tinggi layar, subtitle di zona bawah dengan bantalan gelap. Latar, footage, dan gambar penuh tetap memenuhi layar.
- Kamera: 3 detik pertama zoom-in cepat, setelahnya pan pelan yang arahnya berganti tiap adegan.
- Irama: hook memakai potongan footage sekitar 1,5 detik dan perpindahan cepat, penjelasan 3 sampai 4 detik, penutup lembut.
- Render worker: periksa tipe kode, validasi data, lalu bila gagal baca galat dan pulihkan (mode GL, memori, model macet, 3D diganti 2D, semua tambahan dibuang).

## Tahap 23: paket Node otomatis setelah pembaruan

- Dulu paket Node hanya dipasang kalau `node_modules` belum ada. Setelah `git pull` yang menambah paket baru (misalnya `zod` di Tahap 22), render gagal karena paketnya tidak ditemukan. Sekarang setiap render memeriksa `package.json` dan memasang paket yang kurang secara otomatis.
- Bila galat render berbunyi "cannot find module" atau "can't resolve", pekerja render memasang ulang paket lalu mengulang render.
- Keluaran konsol dan galat dibaca dengan UTF-8 supaya tidak crash di Windows.
- Catatan: validator Zod di sisi Python butuh Node 22.6 atau lebih baru. Kalau Node lebih lama, langkah itu dilewati dengan pesan di layar, dan validasi tetap berjalan di dalam Remotion.


## Tahap 27: bersih, tegas, dan hanya benda yang disebut

- Prompt visual diganti tiga aturan tegas: dilarang menghalusinasi benda, kunci ke aset topik (kalau tidak ada, gelombang suara), dan kiasan tidak boleh diterjemahkan harfiah.
- Gambar kartun 3D, foto Wikimedia, stok video, dan model unduhan MATI secara bawaan. Nyalakan lagi dengan `ASET_LUAR=on` di `.env` (tidak disarankan).
- Komponen baru `SoundWave`: gelombang suara dihitung tiap frame (bising, gelombang lawan, hasil lurus). Topik headphone terkunci ke aset ini.
- Gerak mekanis mulai tepat saat kata pemicu diucapkan (`trigger` di naskah, waktu kata dari suara).
- Latar gradasi radial gelap tanpa garis kotak; subtitle 52 sampai 56 px, 120 px dari bawah; musik latar 0,10; pendaran di benda menyala; cangkang tembus pandang (X-ray) pada pemantik dan headphone.
- Tahap Editor wajib berhasil (kalau tidak, naskah diulang dengan sumber lain). Bypass hanya dengan `ALLOW_UNEDITED=on`. Prompt Editor diperkecil agar tidak kena 413 di Groq. Batas waktu Gemini 120 detik; `gemini-2.5-flash` dihapus dari daftar.

## Tahap 28: primitif fisika, kanvas bersih, pembuka mekanis

- Lima komponen primitif universal: `ParticleFlow`, `WaveInterference`, `PressureChamber`, `HeatTransfer`, `MechanicalTrigger`. Kalau tidak ada animasi khusus untuk topik, adegan memakai salah satunya (dipilih dari kata di narasi), bukan benda acak.
- Animasi bawaan (jembatan, pipa listrik, gelombang headphone, dan lainnya) hanya dipakai kalau kata kuncinya ada di judul/topik video. Simulasi 3D bebas buatan AI mati (`SIM_LLM=on` untuk menyalakan).
- Teks label di dalam animasi hanya dari `items` naskah; tidak ada lagi label tertulis mati. Siluet headphone hanya muncul di topik headphone.
- Dihapus dari kanvas 3D: lantai jaring-jaring dan semua kilatan layar putih. Momen klimaks hanya memberi pantulan skala kecil dan bayangan cahaya.
- Pembuka (detik 0 sampai 5) wajib simulasi mekanis berupa potongan melintang, tidak boleh tanda tanya.
- Jarak antarbaris teks dalam animasi 1,25.

## Tahap 29: mekanika benda padat, tanpa tanda tanya, grafik dibatasi

- Komponen dipilih sesuai BIDANG topik. Mekanika (mobil, poros, sendi, bantalan): `RotatingShaftAndJoint`, `BallBearingCage`, `RigidVsFlexibleRod`, ditambah pemicu pegas dan panas. Fluida, gas, listrik, gelombang: partikel, gelombang, ruang bertekanan. Komponen satu bidang tidak dipakai di bidang lain kecuali kalimat adegannya sendiri jelas membahasnya.
- Kata pemicu hanya untuk simulasi mekanis. Benda tampil utuh dan bergerak pelan sejak frame 0; aksi klimaks (menekuk, patah, miring) baru jalan saat kata pemicu. Adegan grafik/angka tidak pernah menunggu.
- Adegan tanda tanya dihapus total (skema, prompt, kode, komponen). Grafik paling banyak satu per video; sisanya diganti simulasi bergerak. Derajat di narasi (mis. "45 derajat") jadi sudut miring benda.
- Semua kilatan putih tersisa dihapus. Cangkang bulat dibuat sangat tipis. Batang grafik dan satuan dibatasi agar tidak menabrak judul.

## Tahap 30: satu kanvas yang digambar AI untuk setiap topik (tanpa preset)

Cara lama (memilih salah satu dari sekitar 10 gambar preset lalu mengganti tulisannya) dihapus total. Sekarang:

- Seluruh video adalah SATU benda utuh dalam tampak potongan melintang, dari detik 0 sampai akhir. Benda tidak berganti tiap adegan; yang berganti hanya posisi kamera (zoom ke bagian yang dibahas) dan bagian yang bergerak.
- AI menulis sendiri kode gambarnya untuk topik itu (`svg_composer.py`, hasilnya di `video_engine/src/generated/GeneratedMechanism.tsx`, file ini dibuat ulang di setiap video dan tidak ikut git). Pertama AI membuat rancangan bagian benda, lalu kodenya.
- Kode dari AI melewati pemeriksaan sebelum dipakai: (1) hanya boleh memakai `react` dan `remotion`, tanpa acak atau internet; (2) pemeriksaan tipe TypeScript; (3) render beberapa bingkai sungguhan untuk menangkap galat saat dijalankan; (4) bingkai pertama tidak boleh kosong. Kalau gagal, pesan galat dikirim kembali ke AI untuk diperbaiki (paling banyak 2 kali). Kalau tetap gagal, video dibatalkan, bukan memakai gambar cadangan.
- Gerak klimaks tiap adegan mulai tepat di kata pemicu (waktu kata dari suara).
- Dihapus: komponen bola 1-2, tabung VS, lift, bearing, grafik, tanda tanya, judul bab di atas layar, hook besar yang menutupi benda, dan semua kode pemilih preset (`director`, `topic_lock`, `primitives`, `sim_*`, `metaphors`, rekaman stok, gambar kartun, model 3D).
- Prompt naskah diganti: satu benda utama, tiap adegan menyorot satu bagian, `trigger` wajib.
- Catatan: pembuatan kanvas butuh model yang kuat menulis kode (Gemini lebih baik daripada model cadangan kecil), dan memakan sekitar 1 sampai 3 menit tambahan.

## Tahap 32: naskah rantai sebab-akibat, kedalaman 2.5D, jangkar kamera, pemeriksa visual

- Naskah mengikuti 5 babak mekanis (hook paradoks, bedah komponen, kondisi normal, rantai reaksi, resolusi) tanpa sejarah atau fakta umum di tengah.
- Prompt gambar mewajibkan gradasi logam 3 titik warna, bayangan, dan warna fluida yang berubah halus (`interpolateColors`). Pemeriksa kode menolak gambar yang hanya memakai warna datar.
- Kode gambar wajib punya `COMPONENT_ANCHORS`; kamera mengunci jangkar komponen yang dibahas tepat di pusat layar.
- Sebelum render penuh, 3 bingkai kunci dirender dan dilihat Gemini (butuh `GEMINI_API_KEY`). Kalau ada cacat jelas, kode direvisi sekali dan revisi hanya dipakai kalau lolos semua pemeriksaan. Tanpa kunci Gemini, langkah ini dilewati.

## Tahap 36: tampilan studio universal

- Tiga tampilan dalam satu kanvas, diatur otomatis menurut urutan adegan: benda utuh di tempat aslinya (pembuka dan penutup), analogi sehari-hari, lalu cetak biru / sinar-X dengan lingkaran pembesar.
- Naskah memilih `environment` dari enam latar bergerak (`video_engine/src/components/env`). Latar cetak biru berganti halus saat masuk adegan bedah.
- Lapisan tetap milik sistem (bukan gambar AI): kalimat tanya pembuka 12 detik, kotak klaim beserta sumber, dan subtitle di 68% layar dengan kata aktif dalam kotak oranye.
- Komponen HUD siap pakai di `components/hud`: `CitationBadge`, `SegmentedForceArrow`, `LoadWeightBadge`, `MisconceptionCross`. Angka HUD dan klaim hanya dipakai kalau angkanya memang diucapkan di naskah.
- Prompt gambar: gaya cel-shaded (garis tepi `#0f172a`, warna fungsional), fisika mikro (lengkung elastis, partikel benturan), dan svg wajib transparan.

## Tahap 37: alur sinematik 4 babak

- Babak 1 (adegan pertama): benda utuh di tempat aslinya. Babak 2: kamera menembus cangkang (mode `xray`, cangkang 0.25). Babak 3: mekanisme inti (mode `blueprint`, panah gaya HUD dan lingkaran pembesar). Babak 4 (adegan terakhir): zoom-out, cangkang menutup, benda utuh menyelesaikan tugasnya.
- Mode `analogi` dari Tahap 36 dihapus; perumpamaan cukup satu kalimat di naskah babak 3.

## Tahap 38: kanvas modular dan anti kehabisan kuota

- AI tidak lagi menggambar satu SVG raksasa. Ia hanya menggambar tiga tampilan (`Exterior` bodi luar, `Analogy` perumpamaan, `Cutaway` potongan dalam) dan mengisi tabel `ANCHORS`/`CAMERA`. Kamera, label, panah gaya, beban, tanda silang, dan kaca pembesar dikerjakan panggung sistem (`components/MechanismStage.tsx`).
- `components/MechanicalPrimitives.tsx` berisi pegas, pipa berisi aliran, piston, roda gigi, dan membran karet yang sudah jadi, jadi model kecil pun menghasilkan bentuk yang rapi.
- Mode `analogi` kembali: satu adegan di babak 3 yang diawali "Ibarat ..." memakai tampilan perumpamaan.
- Hal kecil (latar layar penuh, teks karangan, `<svg>` bersarang, ekspor yang kurang) diperbaiki otomatis oleh kode, bukan dengan memanggil ulang AI. Hanya galat nyata yang diulang.
- Naskah dan editor dikerjakan Groq lebih dulu supaya kuota Gemini dipakai untuk menulis kanvas. Ubah dengan `TEXT_FIRST=gemini` di `.env`.
- Banyak key: tulis dipisah koma, misalnya `GEMINI_API_KEY=kunci1,kunci2,kunci3`. Key dirotasi otomatis saat kena batas.
- Jeda pintar: 429/503/504 menunggu sesuai petunjuk server ("try again in Xs"), kalau tidak ada 10 detik x percobaan. Model yang tidak ada (404) atau terlalu besar (413) langsung dilewati. `gemini-2.5-flash` dihapus dari daftar.

## Melanjutkan render tanpa mengulang naskah dan suara

Jika pembuatan aset di `[3/5]` atau render di `[4/5]` gagal, jalankan:

```sh
python main_agent.py --resume --tanpa-upload
```

Di Windows bisa juga memakai `jalankan_agen.bat --resume --tanpa-upload`. Checkpoint `cache/last_session.json` ditulis setelah naskah siap, lalu diperbarui setelah TTS dengan waktu kata, jadwal adegan, durasi, dan nama audio di `video_engine/public/`. Jika baru naskah yang tersimpan, `--resume` mulai dari TTS. Jangan hapus atau timpa audio sesi tersebut. Menjalankan agen tanpa `--resume` membuat sesi baru; `--unggah-saja` tetap khusus untuk video yang sudah selesai. Sesi lama dari sebelum fitur ini tidak dapat dilanjutkan.

**Catatan mesin SVG lama (bukan jalur hybrid):** Prompt kanvas standar maksimal 6.500 karakter; Groq memakai versi compact maksimal 4.900 karakter dan `max_tokens=3500`. Batas ini juga berlaku untuk revisi: jika kode lama tidak muat utuh, model menerima brief dan diagnostik untuk menulis ulang. Di `cache/debug_last_prompt.txt` ada nama sumber, jumlah karakter, dan prompt terakhir; `cache/debug_last_response.txt` berisi jawaban mentah atau status gagal. File lokal ini tidak masuk Git.

Penulis kanvas Gemini memakai timeout 240 detik dan thinking rendah pada model Flash yang mendukungnya. Saat 503, agen langsung mencoba key lain; dua key berturut-turut terkena 503 menonaktifkan model itu untuk sesi kanvas. Error kuota 429 tidak membuka breaker. Untuk fallback opsional setelah Groq/Cerebras, isi `OPENROUTER_API_KEY` di `.env`. Bawaan `openrouter/free` merutekan ke model gratis; isi `OPENROUTER_MODEL` dengan ID model coding `:free` yang tersedia jika ingin memilih sendiri. Ketersediaan dan kuota tetap bergantung pada provider.
