# Sistem desain Procurement

Versi 1.1 | 23 Oktober 2026

Status: diterapkan pada antarmuka lokal. Pemeriksaan lima peran dan batas cakupannya dicatat pada TESTING; instalasi bersih serta pemeriksaan akhir mengikuti Tugas 11.

## 1. Arah desain

Procurement memakai pendekatan Operations Desk. Halaman masuk mengutamakan pekerjaan berikutnya bagi setiap peran. Halaman detail menata informasi seperti berkas pengadaan: identitas, kebutuhan, item, keputusan, penawaran, dan PO. Ringkasan perjalanan proses membantu pengguna memahami posisi dokumen tanpa menambah navigasi terpisah.

Karakter tampilannya tenang, tegas, dan mudah dipindai. Identitas terlihat dari aksen teal, posisi nomor dokumen yang konsisten, kolom angka yang rapi, serta ringkasan tindakan di dekat informasi yang menjadi dasar keputusan.

| Dimensi   | Pilihan  | Penerapan                                                                  |
| --------- | -------- | -------------------------------------------------------------------------- |
| Energi    | 2 dari 3 | Heading tegas dan satu tindakan utama; rincian tetap tenang.               |
| Ritme     | 2 dari 3 | Daftar, form, dan detail mempunyai komposisi sesuai tugasnya.              |
| Gerak     | 1 dari 3 | Feedback interaksi singkat; konten tidak bergerak saat dibaca.             |
| Kepadatan | Sedang   | Informasi transaksi mudah dipindai tanpa mengecilkan kontrol.              |
| Tema      | Terang   | Tabel, berkas pengadaan, dan halaman cetak mempunyai kesinambungan visual. |

Setiap halaman menjawab dua pertanyaan: apa yang perlu diperiksa dan tindakan apa yang tersedia sekarang. Grafik, ringkasan angka, dan riwayat hanya ditampilkan bila membantu menjawabnya. Ringkasan wajib berasal dari data yang boleh dibaca pengguna.

Aturan produk mengikuti [PRD](PRD.md), transisi mengikuti [proses bisnis](BUSINESS_PROCESS.md), dan batas teknis mengikuti [arsitektur](ARCHITECTURE.md). Komponen visual tidak menetapkan izin atau perubahan status.

## 2. Struktur halaman dan navigasi

### Kerangka aplikasi

Desktop memakai sidebar berlabel dan area kerja utama. Lebar sidebar 16,5rem. Bagian atas area kerja memuat breadcrumb bila diperlukan, judul, keterangan singkat, dan tindakan halaman. Identitas akun serta peran aktif mudah ditemukan. Nama produk ditulis sebagai teks; logo dan foto profil tidak diperlukan.

Urutan isi: navigasi, pesan hasil tindakan, judul halaman, filter atau ringkasan yang relevan, lalu konten utama. Sediakan tautan lewati navigasi menuju konten. Halaman login menggunakan kolom form yang ringkas tanpa sidebar.

| Peran       | Prioritas beranda                           | Tujuan navigasi yang relevan                      |
| ----------- | ------------------------------------------- | ------------------------------------------------- |
| Pemohon     | Draf dan permintaan yang perlu revisi       | Beranda, Permintaan Saya                          |
| Approver    | Permintaan diajukan yang dapat diperiksa    | Beranda, Persetujuan, Permintaan, Purchase Order  |
| Procurement | Permintaan disetujui yang belum memiliki PO | Beranda, Permintaan, Vendor, Purchase Order       |
| Penerima    | PO terbuka yang dapat dicatat penerimaannya | Beranda, Purchase Order                           |
| Admin       | Pengelolaan akun dan data pendukung         | Beranda, Akun, Vendor, Permintaan, Purchase Order |

Tujuan di atas merupakan rancangan navigasi. Tampilkan hanya route yang sudah tersedia dan diizinkan. Jangan membuat halaman antrean terpisah jika daftar berfilter sudah memenuhi kebutuhan. Vendor tidak memiliki akun atau portal pada versi awal.

Satu akun mempunyai satu peran aktif. Navigasi tidak menyediakan tombol berganti peran. Penyembunyian menu dan tombol mengikuti policy server; URL langsung tetap diperiksa server.

### Antrean dan daftar

Beranda menampilkan antrean kerja utama, diikuti ringkasan yang membantu pengguna menentukan prioritas. Hindari deretan kartu statistik dengan bobot sama. Bila belum ada query ringkasan yang sesuai akses, tampilkan daftar yang tersedia.

Daftar permintaan mengutamakan nomor/judul, status, tanggal kebutuhan, dan nilai estimasi. Identitas pemohon ditambahkan bila relevan bagi peran pembaca. Daftar PO mengutamakan nomor, vendor, status PO, nilai, dan konteks permintaan asal. Kolom serta urutannya harus membantu keputusan pengguna pada daftar tersebut.

Nomor dokumen menjadi tautan detail yang jelas. Jangan menjadikan seluruh baris sebagai satu-satunya cara membuka detail. Pertahankan pencarian dan filter pada URL GET serta tautan paginasi. Filter tahap dan jenis pengadaan mengikuti data yang tersedia; sorting tambahan hanya ditampilkan setelah didukung server.

### Detail dokumen

Pada layar lebar, susun konten utama dan panel ringkasan dengan rasio awal sekitar 2:1. Panel berisi status, nilai, dan tindakan yang diizinkan. Pada layar sempit, tempatkan ringkasan penting sebelum rincian. Urutan DOM harus tetap masuk akal untuk keyboard dan pembaca layar.

Kelompok informasi:

1. Nomor, judul, jenis pengadaan, dan identitas pemohon.
2. Status permintaan serta status PO bila sudah ada.
3. Alasan kebutuhan, tujuan, tanggal kebutuhan, dan rincian item.
4. Keputusan dan alasan yang relevan dengan revisi aktif.
5. Penawaran, vendor terpilih, PO, dan penerimaan sesuai akses serta tahap.
6. Riwayat tindakan dengan pengguna, waktu WIB, dan alasan.

Ringkasan proses memakai label tahap yang sesuai data. Status permintaan dan PO selalu dibedakan. Tahap berikutnya tidak ditampilkan sebagai sudah selesai. Revisi, penolakan, pembatalan, serta penutupan sisa memiliki penjelasan tersendiri; proses tidak dipaksa menjadi garis kemajuan yang selalu naik.

### Jejak Navigasi

Gunakan komponen bersama di atas judul halaman aplikasi: Beranda, daftar, detail, lalu halaman turunan. Contoh: Beranda -> Daftar Permintaan -> Detail Permintaan -> Penawaran -> Tambah Penawaran. Urutan menunjukkan hierarki dokumen, bukan riwayat kunjungan browser.

Pemisah ditampilkan sebagai panah kanan dan disembunyikan dari pembaca layar. Halaman induk berupa tautan; halaman aktif berupa teks tebal tanpa tautan dengan aria-current=page. Gunakan landmark Jejak navigasi dan daftar berurutan. Tautan mengacu pada route aplikasi yang tersedia tanpa query tambahan ke database.

Ukuran teks 1rem (16px pada pengaturan awal), line-height 1.5, dan tinggi target tautan minimal 44px. Gunakan warna teks/tautan existing serta underline dan focus ring. Pada layar sempit, rangkaian membungkus ke baris berikutnya; jangan mengecilkan font, memotong label, atau memaksa scroll horizontal.

Halaman yang dirender saat edit terkunci tetap menentukan penanda aktifnya. Tautan lintas dokumen seperti Permintaan Sumber dan tindakan Halaman Cetak berada di luar hierarki breadcrumb. Dokumen cetak mempertahankan tata letak cetaknya.

Label form **Alasan hanya satu vendor** menggantikan istilah sumber tunggal pada antarmuka. Bantuan menjelaskan bahwa isian wajib jika hanya satu vendor memiliki penawaran yang memenuhi syarat. Kriteria vendor dan aturan bisnis tetap sama.

## 3. Warna dan token semantik

Nilai berikut menjadi baseline CSS variables. Komponen menggunakan nama token agar perubahan palet tidak memerlukan penyuntingan setiap halaman.

| Token                                    | Nilai                 | Penggunaan                                       |
| ---------------------------------------- | --------------------- | ------------------------------------------------ |
| `--color-canvas`                         | `#F4F7F6`             | Latar area kerja.                                |
| `--color-surface`                        | `#FFFFFF`             | Form, dokumen, menu, dan tabel.                  |
| `--color-text`                           | `#172B2B`             | Judul, isi, dan nilai utama.                     |
| `--color-text-muted`                     | `#475569`             | Keterangan, metadata, dan bantuan field.         |
| `--color-primary`                        | `#0F5E5E`             | Tindakan utama dan tautan.                       |
| `--color-primary-hover`                  | `#0B4B4B`             | Hover tombol utama.                              |
| `--color-on-primary`                     | `#FFFFFF`             | Teks tombol utama.                               |
| `--color-selected`                       | `#E4F0ED`             | Latar navigasi atau pilihan aktif.               |
| `--color-divider`                        | `#D6DEDA`             | Pemisah bagian; bukan satu-satunya batas input.  |
| `--color-control-border`                 | `#64748B`             | Batas kontrol pada permukaan putih.              |
| `--color-focus`                          | `#0F5E5E`             | Focus ring pada permukaan terang.                |
| `--color-info` / `--color-info-bg`       | `#1E40AF` / `#EFF6FF` | Informasi dan proses aktif.                      |
| `--color-success` / `--color-success-bg` | `#166534` / `#F0FDF4` | Persetujuan dan penerimaan lengkap.              |
| `--color-warning` / `--color-warning-bg` | `#854D0E` / `#FEFCE8` | Revisi, penerimaan sebagian, dan penutupan sisa. |
| `--color-danger` / `--color-danger-bg`   | `#B91C1C` / `#FEF2F2` | Penolakan, error, dan tindakan merusak.          |
| `--color-neutral` / `--color-neutral-bg` | `#475569` / `#F1F5F9` | Draf, pembatalan, dan informasi netral.          |

Teal mengarahkan perhatian pada tindakan. Warna semantik menjelaskan keadaan dokumen melalui pasangan latar dan teks. Setiap status tetap mempunyai label tertulis. Label status bersudut ringan tanpa glow atau animasi.

Focus ring memakai outline 3px dengan offset 3px. Berikan ruang latar putih di antara kontrol berwarna dan ring bila diperlukan agar batas focus dapat dibedakan. Uji kembali pasangan warna pada seluruh keadaan hover, focus, invalid, dan disabled.

Tema gelap belum termasuk baseline. Tambahkan hanya sebagai pekerjaan tersendiri yang mencakup seluruh token, komponen, dan pemeriksaan kedua tema.

## 4. Tipografi, angka, dan jarak

Gunakan IBM Plex Sans sebagai typeface utama karena bentuk hurufnya tegas untuk label dan cukup terbuka untuk teks transaksi. Host berkas font berlisensi secara lokal, sertakan lisensinya, dan gunakan `font-display: swap`. Sebelum aset font tersedia, gunakan fallback `system-ui, sans-serif` tanpa ketergantungan jaringan.

| Peran teks           | Ukuran awal                         | Bobot dan line-height |
| -------------------- | ----------------------------------- | --------------------- |
| Judul halaman        | `clamp(1.5rem, 1.1rem + 1vw, 2rem)` | 600; 1.25             |
| Judul bagian         | `1.125rem`                          | 600; 1.4              |
| Isi, label, input    | `1rem`                              | 400 atau 600; 1.5     |
| Metadata dan bantuan | `0.875rem`                          | 400; 1.5              |

### Penulisan teks antarmuka

Gunakan EYD V untuk ejaan dan kapitalisasi serta KBBI untuk bentuk kata baku. Kapitalisasi mengikuti fungsi teks:

| Fungsi                                                                    | Aturan proyek                                                              | Contoh                                                                |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Judul halaman/bagian, navigasi, dan tombol                                | Kapital pada kata utama; kata tugas di tengah tetap kecil                  | Detail Permintaan; Penawaran dan Pemilihan Vendor; Kembali ke Beranda |
| Label form, keterangan data, pilihan status/keputusan/bukti               | Kapital pada awal frasa, lalu huruf kecil kecuali nama diri atau singkatan | Berlaku sampai; Alasan pemilihan; Diterima sebagian; Surat jalan      |
| Riwayat tindakan                                                          | Frasa biasa, bukan judul                                                   | Draf dibuat; Permintaan diajukan; Vendor dipilih; PO diterbitkan      |
| Paragraf, bantuan, tooltip deskriptif, pesan validasi, dan keadaan kosong | Kapital pada awal kalimat                                                  | Belum ada riwayat.                                                    |

Kata tugas seperti dan, atau, di, ke, dari, untuk, dengan, dalam, pada, yang, sampai, atas, sebagai, dan tanpa tidak diawali kapital di tengah judul. Pada awal judul atau kalimat, gunakan kapital. Pertahankan singkatan PO, IDR, dan WIB serta nama diri. Gunakan bentuk baku **draf** untuk teks bahasa Indonesia.

Nama akun, vendor, judul dokumen, item, catatan, dan data pengguna ditampilkan sesuai isinya. Tetapkan ejaan pada sumber teks antarmuka dan label Django. Jangan memakai filter title, str.title(), atau CSS text-transform untuk mengubah seluruh nilai dinamis.

Acuan: [EYD V — Huruf Kapital](https://ejaan.kemendikdasmen.go.id/eyd/penggunaan-huruf/huruf-kapital/) dan [KBBI — draf](https://kbbi.kemendikdasmen.go.id/entri/draf). Pemilihan gaya label dan tombol di atas merupakan konvensi antarmuka proyek yang mengikuti konteks, bukan kewajiban mengapitalkan semua kata.

Hindari heading monospace dan huruf kapital dengan tracking lebar. Nomor dokumen boleh memakai angka tabular; angka uang dan kuantitas menggunakan `font-variant-numeric: tabular-nums` serta rata kanan.

Nilai IDR ditampilkan konsisten dengan dua desimal. Kuantitas bulat ditampilkan tanpa desimal tambahan (4 unit, 0 unit). Pecahan memakai koma dan maksimal tiga angka desimal tanpa nol tambahan (0,333 unit; 1,5 unit); ribuan memakai titik (1.000 unit). Unit selalu terlihat. Format tampilan Indonesia tidak mengubah parser input atau nilai kanonik server. Petunjuk input menjelaskan format yang benar-benar diterima. Preview perhitungan pada browser harus diberi label estimasi sampai server mengonfirmasi hasilnya.

Skala jarak: `--space-1` 0.25rem, `--space-2` 0.5rem, `--space-3` 0.75rem, `--space-4` 1rem, `--space-6` 1.5rem, `--space-8` 2rem, dan `--space-12` 3rem. Gunakan jarak kecil untuk label dengan isian, 1rem antarkontrol, dan 1.5rem sampai 2rem antarbagian.

Konten daftar/detail memiliki lebar maksimum awal 80rem. Form berfokus pada satu dokumen menggunakan area sekitar 52rem; login sekitar 26rem. Semua lebar dibatasi oleh ruang yang tersedia. Padding halaman 1rem pada layar sempit dan 1.5rem sampai 2rem pada layar lebar.

Radius: 4px untuk label status, 6px untuk input/tombol, dan 8px untuk permukaan kelompok. Permukaan utama tetap datar. Bayangan ringan hanya menandai menu atau dialog yang berada di atas konten, bukan diterapkan ke setiap baris dan kartu.

## 5. Komponen dan perilaku

### Tombol dan tindakan

Tindakan proses ditempatkan dekat judul dengan kelompok page-actions: tindakan utama memakai tombol berwarna, pendukung memakai tombol sekunder. Contoh: Catat Penerimaan pada detail PO, Tambah Penawaran pada daftar penawaran, serta Buat Akun/Tambah Vendor pada daftar pengelolaan. Tautan judul dokumen, riwayat, breadcrumb dan paginasi tetap mengikuti fungsi navigasinya.

Tombol Lanjutkan Pengajuan, Tinjau Pengajuan dan Lanjutkan Penerbitan PO hanya mengarahkan ke form terkait; penyimpanan tetap membutuhkan pengiriman form. Heading tujuan dapat menerima fokus keyboard. Tindakan hanya tampil sesuai peran dan keadaan dokumen. Setelah penerimaan sebagian, Catat Penerimaan Berikutnya tampil untuk Penerima; setelah lengkap, tersedia Buka Detail PO.

Pertahankan font awal 1rem, target minimal 44px dan flex-wrap untuk kelompok tindakan. Hindari baris tombol yang melebar keluar layar atau menutupi data. Tindakan per baris memakai gaya sekunder; tambah baris item juga sekunder terhadap Simpan Draf. Kelompok tindakan disembunyikan saat mencetak.

Form penerimaan Barang tidak merender kolom awal/akhir pelaksanaan jasa. Form Jasa tetap mewajibkan keduanya. Pengiriman tanggal jasa yang dipaksakan untuk Barang ditolak di server; jangan sekadar menyembunyikan input melalui CSS.

Satu kelompok keputusan mempunyai satu tindakan utama yang ditonjolkan. Gunakan label yang menyebut hasil: "Simpan Draf", "Ajukan Permintaan", "Setujui Permintaan", "Minta Revisi", "Pilih Vendor", "Terbitkan PO", atau "Catat Penerimaan".

Tombol utama memakai teal. Tombol sekunder memakai permukaan putih dan batas kontrol. Tindakan pembatalan/penutupan dipisahkan dari alur utama serta menjelaskan konsekuensinya pada halaman konfirmasi. Tindakan yang memerlukan alasan menyediakan field alasan sebelum submit.

Tautan dipakai untuk navigasi; tombol submit untuk perubahan data. Target sentuh minimal 44 x 44px dan memiliki jarak yang cukup. Ikon mendampingi label bila mempercepat pengenalan tindakan. Gunakan SVG lokal dengan gaya dan ketebalan konsisten; ikon dekoratif disembunyikan dari pembaca layar. Tombol ikon saja memerlukan nama aksesibel yang menjelaskan objek tindakannya.

### Form dan validasi

Kelompokkan permintaan menjadi informasi kebutuhan, rincian item, dan ringkasan biaya. Gunakan label terlihat, fieldset/legend untuk kelompok terkait, penanda wajib yang dijelaskan, serta petunjuk di dekat field yang membutuhkan format khusus. Placeholder tidak menggantikan label.

Form invalid mempertahankan input aman. Tampilkan setiap kesalahan sekali di dalam form yang terkait: pesan field berada dekat isian dengan hubungan `aria-describedby`, sedangkan kesalahan umum berada di awal form. Jangan mengulang pesan melalui ringkasan global atau pemberitahuan tambahan di luar form. Tidak ada pemindahan focus otomatis ke error. Field error memakai `aria-invalid`; focus pada kontrol tetap terlihat saat digunakan melalui keyboard.

Tambahkan/hapus baris item menyediakan kontrol berlabel yang menjelaskan baris terkait. Penghapusan baris yang sudah diisi harus dapat ditinjau sebelum disimpan. Tanpa JavaScript, pengguna tetap mempunyai jalur server untuk menambah dan menghapus baris serta menyelesaikan alur inti.

Saat submit, tampilkan feedback seperti "Menyimpan permintaan...". JavaScript boleh mencegah klik berulang setelah validasi browser lolos, tetapi jangan menonaktifkan field atau menghilangkan nilai tombol yang dibutuhkan POST. Server tetap memeriksa token aksi, versi, dan duplikasi. Pemulihan halaman lewat tombol kembali harus mengembalikan kontrol yang dapat dipakai.

### Tabel dan perbandingan penawaran

Gunakan elemen tabel semantik, caption atau nama aksesibel, dan header dengan `scope` yang sesuai. Nilai dalam satu kolom memiliki format yang sama. Rincian satu objek memakai pasangan label/nilai; jangan memaksakan semua metadata menjadi tabel.

Baris awal sekitar 3rem dan boleh bertambah tinggi saat teks membungkus. Nama item dan alasan dapat membungkus; jangan memotong informasi yang menentukan keputusan. Pertahankan angka bersama unitnya. Aksi sekunder dapat ditempatkan pada detail agar baris tidak penuh tombol.

Perbandingan penawaran menampilkan vendor, referensi, masa berlaku, waktu pemenuhan, rincian harga, dan total pada revisi yang sama. Vendor terpilih memiliki penanda teks. Jangan menetapkan harga terendah sebagai pemenang otomatis. Sediakan ruang untuk alasan pemilihan dan alasan sumber tunggal bila diperlukan.

### Konfirmasi dan pesan

Notifikasi status memakai lebar sesuai isi, dibatasi lebar area konten. Hilangkan penanda bullet dan pertahankan role status. Pesan panjang membungkus pada layar sempit; beberapa pesan tetap tersusun vertikal dengan jarak yang jelas. Aturan ini khusus notifikasi status, tanpa mengubah penempatan error pada form.

Gunakan halaman konfirmasi server untuk keputusan penting. Tampilkan nomor dokumen, tindakan, nilai atau sisa yang terdampak, alasan yang diperlukan, serta tombol kembali. Jika dialog ditambahkan sebagai peningkatan, sediakan focus trap, Escape, pengembalian focus, dan jalur tanpa JavaScript.

Pesan sukses menjelaskan hasil, misalnya "PO berhasil diterbitkan. Rincian pesanan tersimpan dan tidak dapat diedit." Pesan error menyebut masalah dan langkah pemulihan. Jangan tampilkan traceback atau token. Pesan yang muncul dinamis memakai pengumuman aksesibel tanpa pengulangan berlebihan.

## 6. Status dan integritas informasi

Label status mengikuti pilihan model. Gunakan namespace dokumen agar status dengan nama sama tetap jelas.

| Dokumen    | Status               | Label                     | Semantik   |
| ---------- | -------------------- | ------------------------- | ---------- |
| Permintaan | `DRAFT`              | Draf                      | Netral     |
| Permintaan | `SUBMITTED`          | Diajukan                  | Informasi  |
| Permintaan | `CHANGES_REQUESTED`  | Perlu revisi              | Peringatan |
| Permintaan | `APPROVED`           | Disetujui                 | Sukses     |
| Permintaan | `REJECTED`           | Ditolak                   | Bahaya     |
| Permintaan | `CANCELLED`          | Dibatalkan                | Netral     |
| PO         | `ISSUED`             | Terbit                    | Informasi  |
| PO         | `PARTIALLY_RECEIVED` | Diterima sebagian         | Peringatan |
| PO         | `RECEIVED`           | Diterima lengkap          | Sukses     |
| PO         | `CANCELLED`          | Dibatalkan                | Netral     |
| PO         | `CLOSED_SHORT`       | Selesai dengan kekurangan | Peringatan |

Persetujuan menyebut revisi dan plafon yang berlaku. Rincian PO menampilkan snapshot penerbitan. Perubahan data master vendor tidak boleh mengubah tampilan snapshot historis.

Penerimaan menampilkan jumlah dipesan, diterima kumulatif, ditolak, dan tersisa dengan judul kolom yang jelas. Jumlah ditolak tidak mengurangi sisa. Pada form penerimaan, bedakan jumlah yang dicatat sekarang dari akumulasi sebelumnya. Jasa mempunyai field periode dan hasil pekerjaan sesuai PRD. Penerimaan final tidak menyediakan kontrol edit/hapus.

"Selesai dengan kekurangan" menyertakan alasan penutupan dan kekurangan yang masih ada. Jangan menampilkannya sebagai "Diterima lengkap" atau kemajuan 100%. Riwayat tetap dapat dibaca setelah penolakan, pembatalan, atau penutupan sesuai izin objek.

## 7. Keadaan halaman

| Keadaan              | Isi dan tindakan                                                                                                                                   |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Belum ada permintaan | Jelaskan bahwa belum ada permintaan; tampilkan "Buat Permintaan" hanya kepada pemohon.                                                             |
| Antrean kosong       | Jelaskan bahwa tidak ada pekerjaan pada antrean tersebut; jangan menampilkan tombol yang tidak sesuai peran.                                       |
| Filter tanpa hasil   | Tampilkan kriteria aktif dan tautan "Hapus Filter".                                                                                                |
| Submit berlangsung   | Sebut tindakan yang sedang diproses; pertahankan konteks dokumen.                                                                                  |
| Validasi gagal       | Pesan di dalam form/field terkait, tanpa pengulangan di atas halaman; input aman dipertahankan.                                                    |
| Data berubah         | Jelaskan bahwa versi terbaru berbeda dan sediakan muat ulang; jangan kirim ulang perubahan secara diam-diam.                                       |
| Kegagalan jaringan   | Jika dapat dideteksi, jelaskan bahwa hasil belum dapat dipastikan. Periksa detail sebelum mengulangi tindakan; jangan membuat token baru otomatis. |
| Akses ditolak        | Gunakan respons 403/404 sesuai aturan aplikasi tanpa membocorkan objek yang tidak boleh dibaca.                                                    |
| Sesi berakhir        | Arahkan ke login melalui tujuan kembali yang aman; jangan menjanjikan pemulihan isian yang tidak disimpan.                                         |

Halaman server-rendered tidak membutuhkan skeleton saat HTML sudah berisi data. Indikator loading ditambahkan pada proses yang dapat diamati, seperti submit atau pengambilan data tambahan. Data demo diberi label sintetis. Ringkasan, riwayat, serta grafik tidak diisi aktivitas atau angka fiktif yang tampak nyata.

## 8. Responsive dan aksesibilitas

Mulai dari satu kolom. Sidebar berubah menjadi menu berlabel ketika ruang konten tidak cukup; kandidat awal 64rem. Dua kolom detail hanya digunakan saat keduanya tetap terbaca. Breakpoint akhir ditetapkan dari hasil resize konten, bukan nama perangkat.

Daftar sederhana dapat menjadi ringkasan per dokumen pada mobile dengan label field yang tetap terlihat. Tabel rincian/perbandingan yang membutuhkan hubungan antarkolom memakai scroll horizontal lokal. Area scroll mempunyai nama aksesibel, dapat difokuskan, dan menyediakan petunjuk bila isinya lebih lebar. Seluruh halaman tidak boleh ikut bergeser ke samping.

Gunakan `min-width: 0` pada anak flex/grid, pembungkusan untuk judul dan referensi panjang, serta ukuran media yang tidak melebihi kontainer. Jangan menutup overflow pada body untuk menyembunyikan kontrol atau teks yang terpotong. Jika tampilan tabel dan daftar mobile memakai markup berbeda, hanya representasi aktif yang masuk accessibility tree; ID elemen harus tetap unik.

Teks normal memenuhi kontras minimal 4.5:1; teks besar yang memenuhi kategori WCAG minimal 3:1. Batas kontrol, indikator focus, dan informasi nonteks yang diperlukan memenuhi 3:1 terhadap warna yang bersebelahan. Warna status selalu disertai teks.

Navigasi keyboard mengikuti urutan baca. Kontrol native mempertahankan perilaku Enter/Space yang sesuai. Menu mobile mendukung penutupan dan pengembalian focus; konten tersembunyi tidak menerima focus. Header atau panel sticky tidak boleh menutup field, focus, atau tombol terakhir. Pada mobile, input tetap dapat dicapai ketika keyboard layar terbuka.

Gerak dibatasi pada perubahan keadaan singkat sekitar 120ms sampai 180ms. Hormati `prefers-reduced-motion`; feedback teks dan focus tetap tersedia tanpa animasi. Jangan memakai scroll reveal, parallax, atau gerak berulang pada ruang kerja transaksi.

## 9. Implementasi frontend dan cetak

Gunakan Django templates, CSS lokal, dan JavaScript seperlunya. Form server, navigasi, validasi, serta konfirmasi inti tetap berfungsi ketika JavaScript dinonaktifkan. Integrasi memakai form/policy/service yang ada; perhitungan dan otorisasi akhir selalu di server.

Pisahkan token dan komponen dalam `static/css/app.css`, enhancement form dalam `static/js/forms.js`, serta partial template untuk elemen yang benar-benar digunakan ulang. Kerangka bersama berada pada `templates/base.html`. Nama file tambahan mengikuti kebutuhan implementasi; tidak perlu framework frontend atau build tool baru untuk menerapkan arah ini.

Muat font lokal dan SVG secukupnya. Hindari ketergantungan CDN untuk alur inti, pemuatan seluruh dataset di browser, dan library grafik tanpa kebutuhan. Gunakan paginasi server serta pertahankan responsivitas kontrol saat request berjalan.

Halaman cetak PO memakai template dokumen tersendiri, CSS static/css/print.css, dan tombol Cetak PO. Urutan baca: identitas PO, nomor permintaan dan waktu penerbitan, vendor dan tujuan, tabel rincian, total, serta dasar pemilihan vendor. Gunakan kertas A4, margin 14 mm di sisi dan 18 mm di bawah, teks gelap pada latar putih, dan angka rata kanan. Nomor dokumen panjang harus membungkus tanpa melebar keluar halaman. Tabel memuat nomor baris, uraian, jumlah, satuan, harga satuan (IDR), dan total (IDR). Header tabel diulang pada halaman lanjutan; total keseluruhan tampil sekali di akhir tabel. Nomor halaman berada di bawah bila browser mendukung margin halaman CSS. Jangan membuat seluruh tabel atau paragraf panjang tidak boleh terpisah karena dapat menyisakan halaman kosong.

Navigasi dan tombol hanya tampil di layar. Ctrl+P tetap bekerja tanpa JavaScript; JavaScript tombol hanya memanggil dialog cetak. Petunjuk layar meminta A4, skala 100%, serta menonaktifkan header/footer bawaan browser untuk menghindari URL dan tanggal tambahan. Rincian serta vendor mengikuti snapshot PO; status diberi label sebagai status saat dicetak. Halaman cetak tidak menambahkan tanda tangan, identitas organisasi, atau klaim persetujuan yang tidak tercatat.

Saat ini hanya PO mempunyai rute cetak khusus. Aturan print pada app.css juga merapikan Ctrl+P pada halaman detail permintaan, PO, dan penerimaan: navigasi/form/tindakan disembunyikan, layout sisi menjadi satu kolom, tinggi viewport dibatalkan agar tidak menambah halaman kosong, dan jarak paragraf disesuaikan untuk kertas. Isi dan riwayat tidak dihapus demi memaksa satu halaman.

## 10. Urutan penerapan dan pemeriksaan

Mulai dengan tiga halaman representatif: antrean kerja, detail permintaan, dan form permintaan. Gunakan pola nyata yang tersedia; kebutuhan antrean baru dicatat sebagai pekerjaan implementasi tersendiri. Periksa ketiga halaman sebelum memperluas styling ke vendor, perbandingan, PO, dan penerimaan.

| Pemeriksaan          | Bukti yang perlu dicatat                                                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Hierarki             | Tindakan berikutnya, status, dan nilai dapat ditemukan pada setiap halaman representatif.                                                      |
| Cakupan akses        | Menu, daftar, detail, dan aksi diperiksa dengan akun setiap peran serta URL langsung.                                                          |
| Responsive           | Lebar 390, 768, dan 1440px diperiksa; tambahkan 320px sebagai uji batas. Resize di antara lebar tersebut tidak memotong konten.                |
| Teks dan zoom        | Zoom 200% dan uji reflow setara lebar 320 CSS px mempertahankan informasi dan kontrol; tabel dua dimensi tetap berada dalam area scroll lokal. |
| Kontras              | Pasangan teks/latar, status, kontrol, dan focus dihitung pada keadaan yang benar-benar dirender.                                               |
| Keyboard             | Login, menu, filter, paginasi, form, dan konfirmasi dapat diselesaikan; focus terlihat dan tidak tertutup.                                     |
| State                | Kosong, filter tanpa hasil, invalid, proses, sukses, konflik, serta 403/404 diperiksa sesuai halaman.                                          |
| Ketepatan transaksi  | Revisi, snapshot, total, batas plafon, accepted/rejected/remaining, dan status akhir sesuai hasil server.                                      |
| Submit dan pemulihan | Klik berulang, kembali dari browser, token kedaluwarsa, dan kegagalan tidak menghasilkan aksi ganda.                                           |
| Tanpa JavaScript     | Pengisian item, pengajuan, keputusan, serta navigasi inti masih memiliki jalur yang dapat digunakan.                                           |
| Cetak                | PO satu dan beberapa halaman terbaca, total terlihat, dan navigasi tidak ikut tercetak.                                                        |

Catat halaman, peran, viewport, tindakan, hasil aktual, dan masalah yang masih terbuka. Dokumen desain, pemeriksaan token, atau screenshot saja tidak membuktikan seluruh alur sudah bekerja. Pembaruan aturan visual dipusatkan di berkas ini setelah hasil penerapannya ditinjau.

## 11. Hasil penerapan

Antrean, form permintaan, dan detail dokumen menjadi dasar penerapan ke halaman lainnya. Font IBM Plex Sans dimuat dari static/fonts bersama lisensi OFL. Sidebar berubah menjadi menu pada lebar di bawah 64rem; keadaan antara 40rem dan 64rem memakai metadata dua kolom serta navigasi dua kolom saat terbuka. Focus memiliki outline 3px. Form dan tombol memakai tinggi minimum 44px. Tema terang dipertahankan untuk membaca dokumen dan kesinambungan hasil cetak.

Detail permintaan menempatkan nomor, status dan tautan menuju tindakan sebelum rincian. Pada desktop, panel tindakan berada di sebelah kanan. Pada mobile, panel lengkap masih berada setelah rincian/riwayat; pemindahan ringkasan tindakan yang lebih lengkap ke awal dokumen menjadi penyempurnaan terbuka. Urutan visual tidak dibalik melalui CSS agar urutan keyboard tetap mengikuti DOM.

Pemeriksaan browser terakhir, setelah pemformatan template, mencakup 85 halaman pada lima peran, masing-masing pada lebar 320, 390, 640, 768, 1024 dan 1440px. Tidak ditemukan overflow halaman pada sampel tersebut. Pembesaran teks 200%, jalur tanpa JavaScript, focus error, submit berulang, pemulihan Back, dan reduced motion diperiksa secara terpisah. Enam belas pasangan kontras lulus: teks terendah 5,91:1 dan batas kontrol 4,76:1 pada pasangan yang diukur. Ini bukan audit aksesibilitas dengan pembaca layar atau pengujian perangkat fisik.

## 12. Penyempurnaan proporsi dan navigasi

Identitas aplikasi, akun dan navigasi diperkuat agar mudah ditemukan saat bekerja. Brand sidebar memakai 28px, subjudul 16px, header Pengadaan Internal 17px, nama akun 18px, dan tombol Beranda 16px pada ukuran root standar. Brand pada login memakai 32px. Ukuran tetap berbasis rem agar mengikuti pembesaran teks pengguna. Label navigasi dan judul utama mengikuti aturan penulisan teks antarmuka pada bagian tipografi; nama akun serta isi dokumen dipertahankan apa adanya.

Sidebar memakai navigation #123B3B dengan teks putih, navigation-muted #D1E1DE dan hover #225252. Permukaan kerja tetap terang. Perbedaan terang/gelap memisahkan navigasi dari pekerjaan dokumen tanpa menambahkan dekorasi atau statistik. Teks putih pada sidebar mempunyai rasio 12,25:1; subjudul 9,06:1. Indikator focus #B8E0D6 mempunyai rasio 8,56:1 terhadap sidebar.

Filter daftar disusun satu kolom pada layar kecil, dua kolom pada ukuran menengah, dan tiga kolom pada desktop. Tombol filter berada dalam satu kelompok di bawah field. Pada lebar 1440px, tinggi filter sekitar 195px sehingga daftar lebih cepat terlihat. Area konten lebih dekat ke navigasi dengan padding desktop 2rem. Login memakai konteks aplikasi dan form dalam dua kolom pada layar lebar, lalu kembali satu kolom di mobile.

Keluar membuka dialog konfirmasi dengan Batal sebagai focus awal. Escape dan Batal menutup dialog serta memulihkan focus. Ya, Keluar mengirim POST dengan CSRF. Tanpa JavaScript, tautan menuju halaman konfirmasi; GET tidak mengakhiri sesi. Peringatan menjelaskan bahwa isian yang belum disimpan dapat hilang.

Pemeriksaan terakhir mencakup 93 halaman/peran pada enam lebar 320 sampai 1440px. Lima halaman admin juga diperiksa pada 1920px; tidak ditemukan overflow pada sampel tersebut. Dialog, pembatalan, focus, konfirmasi dan fallback tanpa JavaScript diuji melalui browser. Tiga regresi baru melengkapi suite menjadi 230 test. Pemeriksaan perangkat fisik dan pembaca layar tetap belum dilakukan.

## 13. Visibilitas password dan error login

Kolom password memakai tombol ikon mata berukuran minimum 44px, dengan label aksesibel yang menyebut kolomnya. Mata dicoret menandakan tindakan menyembunyikan password yang sedang terlihat. Setiap kolom dapat diubah terpisah; tombol tidak melakukan submit. Default, submit, dan pageshow mengembalikan kolom ke keadaan tersembunyi. Tanpa JavaScript, input tetap merupakan password native dan tidak menampilkan tombol yang tidak berfungsi.

Halaman login menampilkan kesalahan autentikasi satu kali dalam form. Seluruh halaman form mengikuti pola yang sama: tidak ada ringkasan error global. Pesan login memakai role alert tanpa pemindahan focus atau outline otomatis. Nilai username dipertahankan dan server tidak merender ulang password.

Seleksi teks memakai latar teal #0F5E5E dan teks putih, termasuk pada input dan textarea, dengan rasio 7,55:1. Form serta kolom login meminta autocomplete off. Browser/password manager dapat mengabaikan permintaan tersebut untuk kredensial tersimpan; aplikasi tidak mengisi nilai password melalui JavaScript atau mengembalikan password dalam HTML setelah kegagalan. Pemeriksaan perilaku autofill perlu membedakan browser uji bersih dari profil pengguna yang mempunyai kredensial tersimpan.

## Bantuan AI Opsional

Pada Buat Permintaan, bantuan AI berada dalam details tertutup di atas form manual. Kontrol sumber memakai radio berlabel Tulis Kebutuhan/Gunakan Gambar dengan target label44px; radio tidak mewarisi lebar input teks. Desktop menata sumber dan hasil berdampingan, layar sampai64rem menumpuknya. Grid memakai minmax(0,1fr), teks membungkus dan preview gambar dibatasi kontainernya. Tidak ada modal atau navigasi chatbot baru.

Hasil belum diterapkan sampai pengguna mencentang pemeriksaan dan menekan Terapkan ke Form. Kolom kosong diisi, item ditambahkan, dan jenis dari form bound/pilihan manual dijaga. Status proses dan error berada di panel bantuan; alert baru diberi role saat benar-benar ada error. Input manual dan Simpan Draf tetap tersedia, termasuk tanpa JavaScript. Nama item/warning model selalu dirender sebagai teks. Tampilan mengikuti warna, font, fokus dan kontrol yang sudah ada; alasan layout adalah perbandingan sumber dan usulan sebelum penyimpanan.

## 14. Lokasi pesan validasi

Pesan validasi hanya berada di dalam form yang menerima input. Kesalahan umum tampil di awal form; kesalahan field tampil dekat isian terkait dengan penanda aria-invalid dan aria-describedby dari Django. Satu kesalahan tidak diulang pada ringkasan global atau pemberitahuan belum disimpan di atas form. Bila beberapa field bermasalah, masing-masing tetap mempunyai pesannya sendiri. Tidak ada pemindahan focus otomatis ke error.

Tautan Muat ulang data dipertahankan di dalam form untuk memulihkan konflik versi atau mengambil token baru. Filter invalid menampilkan pesan di dalam form filter tanpa kartu pesan kedua pada daftar. Pemberitahuan keadaan dokumen yang tidak menyediakan form serta halaman 403/404/500 tetap memakai satu penjelasan kontekstual; jangan membuat form semu hanya untuk menampung pesan tersebut. Aturan ini menggantikan pola ringkasan error pada penerapan awal.
