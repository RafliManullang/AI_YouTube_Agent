# Panduan Visual dan Kreatif

Baca file ini sebelum membangun scene. Isinya adalah arah kreatif default. Sesuaikan dengan aset user dan topik; jangan memaksakan warna atau layout yang sama di setiap scene.

## Daftar isi
1. Membaca video referensi
2. Gaya default
3. Tipografi kinetik
4. Menganimasikan aset
5. Transisi
6. Sinkronisasi dengan voiceover
7. Musik dan mixing audio

## 1. Membaca video referensi

Referensi adalah tolok ukur kualitas, bukan cetakan. Yang diambil adalah prinsipnya: kenapa video itu enak dilihat, bukan urutan efeknya.

Perhatikan: palet warna, hierarki tipografi, cara teks dan gambar saling bertumpuk, ritme potongan, jenis transisi, penggunaan bayangan dan kedalaman, serta hubungan gerak dengan suara.

Yang dilarang: menyalin adegan satu per satu, memakai komposisi yang sama persis, menempatkan teks di posisi yang sama, atau meniru urutan animasi dan transisi frame demi frame. Tujuannya video yang orisinal dan terasa lebih rapi dari referensinya.

## 2. Gaya default (kalau tidak ada referensi)

Editorial modern, minimalis, premium, dengan eksekusi yang berani:

- Latar putih, abu muda, atau warna lain yang kontras dengan aset.
- Tipografi hitam tebal dengan hierarki yang tegas.
- Satu warna aksen terang (misalnya kuning) yang cocok dengan aset. Boleh berganti antar scene selama tetap satu keluarga warna.
- Teks besar dan ekspresif, komposisi asimetris, ruang kosong yang disengaja, lapisan yang saling menimpa.
- Gambar cut-out, ilustrasi, dan ikon menyatu dengan tata letak.
- Bayangan, kedalaman, masking, motion blur, dan skala dipakai secara terkontrol.

Hindari tampilan "slideshow": gambar statis di samping teks dengan fade-in atau slide-in yang diulang-ulang. Setiap scene punya satu ide visual sendiri, tetapi seluruh video tetap terasa satu kesatuan.

Kalau tidak ada gambar dari user, bangun visual dari bentuk geometris, ikon vektor, diagram, angka besar, garis, dan tipografi. Ini grafis buatan kode, jadi desainnya harus kuat di komposisi dan gerak.

## 3. Tipografi kinetik

Tipografi adalah elemen bercerita, bukan sekadar subtitle.

Teknik yang bisa dipakai sesuai konteks: teks muncul bersamaan dengan kata yang diucapkan, reveal dengan mask, animasi kata atau huruf bertahap, skala dengan overshoot terkontrol, animasi spasi antar huruf, teks masuk dari balik objek, clipping dan layering kreatif, penekanan lewat ketebalan, warna, atau ukuran.

Aturan:
- Pilih font modern, tebal, dan sangat terbaca. Pakai font asli lewat kode (bukan teks hasil generate gambar), sehingga huruf tidak pernah rusak atau jadi kata palsu.
- Pertahankan ejaan dan makna teks persis seperti naskah.
- Pecah teks jadi frasa pendek. Jangan menampilkan satu paragraf utuh sekaligus. Sorot hanya kata kunci.
- Pisahkan jelas tingkatan: judul, kata kunci, teks pendukung, label kecil.
- Hindari huruf besar acak, font yang sulit dibaca, dan dekorasi berlebihan.

## 4. Menganimasikan aset

Aset penting jangan dibiarkan diam kecuali memang ada momen jeda yang disengaja.

Teknik: scale in/out, gerak terarah dan rotasi halus, parallax dan lapisan kedalaman, reveal dengan mask, zoom kamera terkontrol, cropping kreatif, gerak melayang dan gerak sekunder, motion blur dan bayangan lembut, serta hubungan visual antara aset dan teks.

Variasikan teknik sesuai isi. Gunakan easing profesional (percepatan, perlambatan, overshoot, antisipasi, settling), bukan kecepatan konstan.

Boleh memotong, mengubah ukuran, memposisikan, memasking, dan menumpuk aset user selama makna dan detail pentingnya tidak hilang. Jangan memotong objek penting, jangan meregangkan gambar, jangan biarkan elemen bertabrakan canggung.

Pemotongan latar (cut-out): kalau tool pemotong latar tidak tersedia, pakai masking manual atau framing yang membuat gambar tetap menarik tanpa cut-out, dan jangan menjanjikan hasil cut-out yang tidak bisa dibuat.

## 5. Transisi

Pilihan: match cut, whip, wipe terarah, reveal dengan mask, transisi bentuk, transisi skala, transisi yang digerakkan tipografi, transisi parallax berlapis, transisi motion blur, dan elemen grafis yang berpindah antar scene.

Ini pilihan, bukan daftar centang. Pilih yang cocok dengan isi dan jaga kesatuan gaya. Sebisa mungkin hubungkan elemen visual antar scene supaya tidak terasa terputus.

Hindari glitch berlebihan, putaran acak, kilatan tanpa alasan, dan transisi yang menutupi penjelasan. Semua transisi harus muat di dalam durasi total yang sudah dihitung. Durasi video tidak boleh melar karena transisi.

## 6. Sinkronisasi dengan voiceover

Voiceover adalah acuan timing utama, sedangkan durasi total video ditetapkan di Tahap 4 SKILL.md (durasi suara + pembuka dan penutup, maksimal 60 detik).

Untuk setiap frasa penting: tampilkan teks saat kata itu diucapkan, munculkan aset saat relevan, tekankan kata kunci lewat skala/warna/bobot/posisi/gerak, berikan jeda visual singkat ketika penonton butuh waktu mencerna, dan sesuaikan kecepatan animasi dengan ritme pembicara.

Gerak harus terasa merespons suara, bukan berputar acak. Efek visual tidak boleh mengalihkan perhatian dari informasi yang dijelaskan.

## 7. Musik dan mixing audio

- Voiceover harus tetap jelas dan dominan. Turunkan musik di bawah suara (ducking) terutama saat informasi penting.
- Selaraskan beberapa transisi atau aksen animasi dengan beat bila memang pas dengan narasi.
- Efek suara dipakai hemat dan tidak bersaing dengan suara narator.
- Jangan mempercepat suara atau memotong kata demi mengejar durasi. Pertahankan ritme dan jeda asli.
- Musik fade-out halus di akhir, dan audio berakhir tepat di detik terakhir video tanpa ekor suara atau terpotong mendadak.
- Cegah clipping, distorsi, perubahan volume mendadak, dan keheningan yang tidak disengaja.

Kalau user tidak punya musik: buat musik latar sederhana yang cocok dengan gaya visual (lihat `render-dan-verifikasi.md`), dan katakan terus terang bahwa itu musik sintetis sederhana. Alternatifnya render tanpa musik dan sarankan user menambahkan musik bebas royalti.
