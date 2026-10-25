# Panduan Pengguna Procurement

Buka [aplikasi Procurement](https://ramaatha.pythonanywhere.com/) dan ikuti bagian sesuai tugas Anda. Anda tidak perlu membaca seluruh panduan secara berurutan.

| Kebutuhan Anda                                  | Buka bagian                                               |
| ----------------------------------------------- | --------------------------------------------------------- |
| Masuk atau keluar dari aplikasi                 | [Mulai menggunakan aplikasi](#mulai-menggunakan-aplikasi) |
| Membuat dan mengajukan kebutuhan                | [Pemohon](#pemohon-membuat-dan-mengajukan-permintaan)     |
| Membantu mengisi draf dari teks atau gambar     | [Bantuan AI](#bantu-isi-dengan-ai-opsional)               |
| Memeriksa pengajuan                             | [Approver](#approver-memeriksa-permintaan)                |
| Mengelola penawaran dan menerbitkan pesanan     | [Procurement](#procurement-mengelola-penawaran-dan-po)    |
| Mencatat penerimaan barang atau jasa            | [Penerima](#penerima-mencatat-penerimaan)                 |
| Merevisi, membatalkan, atau mengakhiri pesanan  | [Tindakan lanjutan](#revisi-pembatalan-dan-penutupan-po)  |
| Mengelola akses pengguna atau data vendor       | [Akun dan vendor](#mengelola-akun-dan-vendor)             |
| Mencari dokumen, melihat riwayat, atau mencetak | [Menelusuri dokumen](#menelusuri-dokumen-dan-mencetak-po) |
| Mengatasi masalah penggunaan                    | [Bantuan](#mengatasi-kendala)                             |
| Melihat akun dan contoh latihan                 | [Demo](#akun-dan-contoh-demo)                             |

## Mulai Menggunakan Aplikasi

1. Buka aplikasi.
2. Isi **Username** dan **Password** yang diberikan admin. Jika belum memiliki akses, hubungi admin.
3. Klik **Masuk**.
4. Periksa nama akun dan peran yang tampil pada menu.

**Hasil:** halaman **Antrean Kerja** terbuka. Menu dan tindakan mengikuti peran akun Anda.

Tindakan utama ditampilkan sebagai tombol berwarna dekat judul halaman. Tombol **Lanjutkan Pengajuan** atau **Lanjutkan Penerbitan PO** mengarahkan Anda ke form untuk diperiksa sebelum dikirim.

- **Pemohon:** membuat dan mengajukan permintaan sendiri.
- **Approver:** memeriksa pengajuan dan mengakhiri PO sesuai kewenangannya.
- **Procurement:** mencatat penawaran, memilih vendor, dan menerbitkan PO.
- **Penerima:** mencatat penerimaan barang atau jasa.
- **Admin:** mengelola akun dan vendor serta membaca dokumen pengadaan.

Ikon mata menampilkan atau menyembunyikan isian password. Untuk keluar, klik **Keluar**, lalu **Ya, Keluar**. Pilih **Batal** jika ingin melanjutkan pekerjaan.

Jejak navigasi di atas judul menunjukkan posisi Anda. Klik halaman sebelumnya untuk kembali, misalnya **Daftar Permintaan** atau **Detail Permintaan**. Halaman aktif ditandai dengan teks tebal.

### Mengenali Alur dan Nomor Dokumen

Permintaan → persetujuan → penawaran → pemilihan vendor → penerbitan PO → penerimaan.

- **PR:** nomor permintaan pengadaan untuk menelusuri pengajuan.
- **PO (Purchase Order):** dokumen pesanan kepada vendor; gunakan nomornya saat mencatat penerimaan.
- **Status persetujuan:** keputusan atas permintaan. **Tahap pengadaan:** kemajuan proses sampai penerimaan.

## Pemohon: Membuat dan Mengajukan Permintaan

**Sebelum mulai:** masuk dengan peran **Pemohon**.

1. Buka **Permintaan Saya** atau **Antrean Kerja**.
2. Klik **Buat Permintaan**.
3. Isi informasi kebutuhan dan rincian item. Contoh latihan barang:

| Kolom                         | Contoh isian                    |
| ----------------------------- | ------------------------------- |
| Jenis pengadaan               | Barang                          |
| Judul                         | `UJI Barang Monitor`            |
| Alasan kebutuhan              | Penggantian monitor ruang kerja |
| Tujuan penerimaan / layanan   | Kantor Demo                     |
| Tanggal kebutuhan             | Hari ini atau setelahnya        |
| Nama item                     | Monitor Uji                     |
| Satuan                        | unit                            |
| Jumlah                        | `10`                            |
| Estimasi harga per unit (IDR) | `100000`                        |

4. Jika perlu, klik **Tambah Baris Item**. Centang **Hapus** pada baris yang tidak digunakan.
5. Klik **Simpan Draf**.
6. Periksa rincian dan total estimasi. Pada contoh di atas, totalnya **IDR 1.000.000,00**.
7. Klik **Lanjutkan Pengajuan** pada halaman detail.
8. Periksa isian, lalu klik **Ajukan Permintaan** pada form.
9. Catat nomor PR untuk penelusuran berikutnya.

**Hasil:** status berubah menjadi **Diajukan**. Salinan pengajuan tersimpan sebagai **Revisi 1** untuk diperiksa Approver.

**Perlu diperhatikan:**

- Harga menerima angka biasa (`100000`) atau format Indonesia (`100.000`). Untuk pecahan harga, gunakan `1.250,50`; format lama `1250.50` tetap diterima. Jangan sertakan `Rp`.
- Titik pada harga seperti `1.000` berarti pemisah ribuan: seribu rupiah. Pecahan harga maksimal dua angka desimal.
- Jumlah tetap memakai titik desimal, maksimal tiga angka desimal, misalnya `0.333`. Jangan memakai pemisah ribuan pada jumlah.
- Draf boleh belum lengkap. Lengkapi informasi wajib dan minimal satu item sebelum mengajukan. Setelah diajukan, perubahan memerlukan permintaan revisi.

### Bantu Isi dengan AI (Opsional)

**Pada Buat Permintaan, akun Pemohon:**

1. Isi manual seperti biasa, atau buka **Bantu Isi dengan AI**.
2. Pilih **Tulis Kebutuhan** (maksimal 1.500 karakter) atau **Gunakan Gambar** (satu JPG/PNG maksimal 2 MB dan 12 megapiksel).
3. Sertakan nama item, jumlah, satuan, dan harga jika diketahui. **Gunakan Contoh** menyiapkan contoh teks tanpa langsung mengirimkannya.
4. Klik **Analisis**. Masukan diproses AI; gunakan data contoh tanpa informasi sensitif.
5. Periksa usulan, terutama jumlah, satuan, harga, dan kolom yang belum tersedia. Maksimal sepuluh item per analisis.
6. Centang **Saya sudah memeriksa hasilnya**, lalu klik **Terapkan ke Form**.
7. Kolom kosong diisi dan item ditambahkan tanpa menimpa isian Anda. Lengkapi form, lalu klik **Simpan Draf**; pengajuan tetap dilakukan terpisah.

Jika bantuan belum aktif, gagal, atau batas harian tercapai, lanjutkan secara manual. **Tutup Bantuan** membatalkan hasil yang belum diterapkan. Penggunaan AI tidak menyimpan draf secara otomatis.

## Approver: Memeriksa Permintaan

**Sebelum mulai:** tersedia permintaan berstatus **Diajukan** dari pengguna lain.

1. Buka **Antrean Persetujuan**.
2. Buka permintaan yang akan diperiksa.
3. Klik **Tinjau Pengajuan** untuk menuju form keputusan.
4. Buka tautan revisi untuk membaca rincian dan total estimasinya, lalu kembali ke detail permintaan.
5. Pada kolom **Keputusan**, pilih **Setujui**.
6. Klik **Simpan Keputusan**.

**Hasil:** status menjadi **Disetujui**. Procurement dapat melanjutkan ke penawaran.

Permintaan sendiri tidak dapat diputuskan. Untuk revisi atau penolakan, lihat [tindakan lanjutan](#revisi-pembatalan-dan-penutupan-po).

## Procurement: Mengelola Penawaran dan PO

**Syarat:** permintaan **Disetujui**, belum mempunyai PO, dan vendor aktif tersedia. [Tambah vendor](#mengelola-vendor) jika diperlukan.

### Mencatat Penawaran

1. Buka **Permintaan Pengadaan**, lalu cari nomor PR.
2. Buka detail permintaan.
3. Klik **Penawaran dan Pemilihan Vendor**.
4. Klik **Tambah Penawaran**.
5. Isi data penawaran. Contoh untuk permintaan monitor di atas:

| Kolom                     | Contoh isian                                                 |
| ------------------------- | ------------------------------------------------------------ |
| Vendor                    | DEMO Vendor Peralatan, jika menggunakan data demo            |
| Referensi penawaran       | `UJI-Q-001`; gunakan referensi baru untuk latihan berikutnya |
| Tanggal penawaran         | Hari ini                                                     |
| Berlaku sampai            | Besok atau setelahnya                                        |
| Estimasi pemenuhan (hari) | `1`                                                          |
| Harga per unit (IDR)      | `90000`                                                      |

6. Klik **Simpan Penawaran**.

**Hasil contoh:** penawaran tampil dengan total **IDR 900.000,00**.

### Memilih Penawaran dan Menerbitkan PO

> **Sebelum menerbitkan:** rincian PO tidak dapat diedit. Satu permintaan hanya memiliki satu PO.

1. Pada bagian **Pilih Penawaran**, pilih kandidat pada kolom **Penawaran yang dipilih**.
2. Isi **Alasan pemilihan**.
3. Jika hanya satu vendor memiliki penawaran yang memenuhi syarat, isi **Alasan hanya satu vendor**.
4. Klik **Simpan Pilihan Vendor**.
5. Klik **Detail Permintaan** untuk kembali.
6. Klik **Lanjutkan Penerbitan PO**.
7. Periksa penawaran terpilih, lalu klik **Terbitkan PO** pada form.
8. Periksa vendor, rincian, total pesanan, dan nomor PO yang terbit.

**Hasil:** PO berstatus **Terbit** dan dapat dilanjutkan oleh Penerima.

**Perlu diperhatikan:**

- Penawaran yang belum berlaku, kedaluwarsa, atau melebihi total estimasi yang disetujui tidak dapat dipilih.
- Jika penawaran terpilih diubah, pilih kembali sebelum menerbitkan PO.

Sampaikan PO kepada vendor di luar aplikasi; aplikasi menyediakan [halaman cetak](#membaca-riwayat-dan-mencetak).

## Penerima: Mencatat Penerimaan

**Sebelum mulai:** PO sudah terbit dan masih memiliki sisa yang perlu dipenuhi.

### Penerimaan Barang

1. Buka **Purchase Order**, lalu cari nomor PO.
2. Buka detail PO dan periksa sisa setiap item.
3. Klik **Catat Penerimaan**.
4. Isi data pemeriksaan. Contoh penerimaan pertama untuk pesanan 10 monitor:

| Kolom               | Contoh isian                     |
| ------------------- | -------------------------------- |
| Referensi bukti     | `UJI-SJ-001`                     |
| Catatan pemeriksaan | Enam unit sesuai; dua unit rusak |
| Jenis bukti         | Surat jalan                      |
| Diterima sekarang   | `6`                              |
| Ditolak sekarang    | `2`                              |
| Alasan penolakan    | Dua unit rusak                   |

> **Sebelum menyimpan:** catatan final tidak dapat diedit atau dihapus. Isi jumlah untuk pemeriksaan saat ini.

5. Periksa seluruh isian, lalu klik **Simpan Penerimaan Final**.
6. Kembali ke detail PO dan periksa **Pemenuhan Pesanan**.

**Hasil contoh:** **Diterima sebagian**, sisa **4 unit**. Sisa dihitung dari jumlah dipesan dikurangi diterima; jumlah ditolak tetap tercatat.

Untuk menyelesaikan contoh, klik **Catat Penerimaan Berikutnya** pada detail penerimaan. Gunakan referensi berbeda: diterima `4`, ditolak `0`. Hasilnya **Diterima lengkap**, sisa **0**; riwayat sebelumnya tetap tersedia.

### Penerimaan Jasa

Kolom periode hanya tampil untuk PO **Jasa**. Ikuti langkah penerimaan yang sama, dengan tambahan berikut:

- Pilih **Laporan pekerjaan** atau **Berita acara jasa** pada **Jenis bukti**.
- Isi **Awal pelaksanaan jasa** dan **Akhir pelaksanaan jasa**.
- Tanggal mulai tidak boleh melewati tanggal selesai. Tanggal selesai tidak boleh melewati hari pencatatan dalam WIB.
- Catat jumlah sesuai satuan pada PO, misalnya kunjungan atau sesi.

## Revisi, Pembatalan, dan Penutupan PO

### Meminta Revisi atau Menolak Pengajuan

**Approver, pada permintaan yang masih Diajukan:**

1. Buka detail permintaan.
2. Pada **Keputusan**, pilih **Minta revisi** atau **Tolak**.
3. Isi **Alasan keputusan**, lalu klik **Simpan Keputusan**.

**Hasil:** **Perlu revisi** dikembalikan ke Pemohon; **Ditolak** mengakhiri permintaan.

**Pemohon, setelah diminta revisi:**

1. Buka permintaan melalui **Permintaan Saya**.
2. Klik **Ubah Draf**, lalu perbaiki isian sesuai alasan revisi.
3. Klik **Simpan Draf**, periksa hasilnya, lalu **Ajukan Permintaan** kembali.

**Hasil:** status kembali **Diajukan** dan nomor revisi bertambah. Salinan revisi sebelumnya tetap dapat dibaca.

### Mengembalikan Kebutuhan yang Sudah Disetujui

**Procurement, sebelum ada PO:**

1. Buka detail permintaan yang sudah **Disetujui**.
2. Pada **Kembalikan untuk Revisi**, isi **Alasan revisi**.
3. Klik **Minta Revisi Kebutuhan**.

**Hasil:** **Perlu revisi**. Pemohon memperbaiki dan mengajukan ulang. Pilihan vendor dikosongkan; penawaran lama menjadi riwayat.

### Membatalkan Permintaan

**Pemohon pemilik permintaan, sebelum ada PO:**

> Pembatalan bersifat akhir. Buat permintaan baru untuk kebutuhan berikutnya.

1. Buka detail permintaan.
2. Pada **Batalkan Permintaan**, isi **Alasan pembatalan**.
3. Klik **Batalkan Permintaan**.

**Hasil:** status menjadi **Dibatalkan**.

### Mengakhiri PO yang Belum Terpenuhi

**Approver yang bukan pemohon, pada PO yang masih terbuka:**

> PO yang sudah diakhiri tidak menerima pencatatan baru. Sisa historis tetap terlihat; kebutuhan lanjutan dibuat melalui permintaan baru.

1. Buka detail PO.
2. Pada **Batalkan PO atau Tutup Sisa**, isi **Alasan pembatalan atau penutupan sisa**.
3. Periksa konsekuensinya, lalu klik **Konfirmasi Akhiri PO**.

**Hasil:** jika belum ada jumlah diterima, PO menjadi **Dibatalkan**. Jika sudah diterima sebagian, PO menjadi **Selesai dengan kekurangan**.

## Mengelola Akun dan Vendor

### Mengelola Akun

**Peran: Admin.**

1. Buka **Kelola Akun**, lalu klik **Buat Akun**.
2. Isi **Username**, **Peran**, **Password awal**, dan **Ulangi password awal**. Centang **Akun aktif** agar akun dapat digunakan.
3. Klik **Buat Akun**.

**Hasil:** akun baru tampil dalam daftar.

Untuk mengubah akun, pilih **Ubah Akun** pada akun terkait, sesuaikan isian, lalu klik **Simpan Perubahan**. Akun nonaktif tidak dapat masuk atau melanjutkan sesi. Admin aktif terakhir tidak dapat dinonaktifkan atau diubah perannya.

### Mereset Password

**Peran: Admin.**

1. Buka **Kelola Akun** dan pilih **Reset Password** pada akun terkait.
2. Isi **Password baru** dan **Ulangi password baru** sesuai ketentuan pada form.
3. Klik **Reset Password**.

**Hasil:** sesi lama dicabut; pengguna masuk kembali dengan password baru. Reset password sendiri juga membuat Anda keluar.

Sampaikan password secara privat, tanpa menuliskannya dalam dokumen publik.

### Mengelola Vendor

**Peran: Admin atau Procurement.**

1. Buka **Kelola Vendor**, lalu klik **Tambah Vendor**.
2. Isi **Nama vendor** dan **Kontak**. Centang **Vendor aktif** agar dapat digunakan pada penawaran.
3. Klik **Simpan Vendor**.

**Hasil:** vendor tampil pada daftar. Untuk mengubahnya, klik **Ubah Vendor** pada vendor terkait, lalu **Simpan Vendor**.

Vendor nonaktif tetap tersimpan untuk riwayat dan tidak dapat digunakan pada penawaran baru.

## Menelusuri Dokumen dan Mencetak PO

### Mencari Permintaan atau PO

1. Buka **Permintaan Saya** untuk Pemohon, **Permintaan Pengadaan** untuk peran lain, atau **Purchase Order** untuk daftar PO.
2. Isi **Cari nomor atau judul**; pilih **Jenis pengadaan** dan **Tahap pengadaan** jika diperlukan.
3. Klik **Terapkan Pencarian dan Filter**.
4. Klik judul permintaan atau nomor PO untuk membuka detail.

Gunakan **Berikutnya** atau **Sebelumnya** untuk berpindah halaman. Klik **Hapus Filter** saat filter aktif untuk menampilkan kembali daftar tanpa penyaringan.

**Akses:** Pemohon melihat permintaannya sendiri; Penerima melihat permintaan yang sudah mempunyai PO.

### Membaca Riwayat dan Mencetak

- Pada detail permintaan atau PO, buka **Riwayat Pengadaan** untuk melihat tindakan, pelaku, waktu, dan alasan.
- Pada detail permintaan, klik nomor pada **Revisi Pengajuan** untuk membaca salinan pengajuan sebelumnya.
- Pada detail PO, buka catatan di **Riwayat Penerimaan** untuk memeriksa bukti dan hasil pemeriksaan.
- Untuk mencetak PO, buka **Halaman Cetak** dari detail PO, lalu klik **Cetak PO** atau tekan **Ctrl+P**.
- Pilih kertas **A4**, skala **100%**, dan matikan **Header dan footer** bawaan browser agar URL/tanggal browser tidak ikut tercetak. Periksa pratinjau sebelum mencetak atau menyimpan PDF.
- Dokumen cetak menyusun vendor, tujuan, rincian pesanan, total, dan dasar pemilihan. Pencetakan tidak mengirim PO kepada vendor secara otomatis.

## Troubleshooting

| Kendala                                    | Yang dapat Anda lakukan                                                                                           |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Tidak dapat masuk                          | Periksa username dan password terbaru. Jika tetap gagal atau akun nonaktif, hubungi admin.                        |
| Password terisi otomatis                   | Periksa pengaturan browser atau pengelola password. Pastikan akun yang diisikan sesuai.                           |
| Menu atau tombol tidak terlihat            | Periksa peran akun dan tahap dokumen. Tindakan hanya tersedia jika syaratnya terpenuhi.                           |
| Daftar kosong atau dokumen tidak ditemukan | Hapus filter. Periksa nomor dokumen dan apakah akun Anda memiliki akses.                                          |
| Permintaan tidak dapat diajukan            | Lengkapi informasi wajib, tanggal kebutuhan yang sesuai, dan minimal satu item dengan jumlah serta harga positif. |
| Penawaran tidak dapat dipilih              | Baca keterangannya pada daftar penawaran; periksa vendor aktif, masa berlaku, harga, dan rincian item.            |
| Penerimaan ditolak                         | Periksa sisa item, jumlah diterima/ditolak, alasan penolakan, dan periode jasa bila diperlukan.                   |
| Muncul pesan data sudah berubah            | Catat isian penting, muat ulang halaman, lalu periksa data terbaru sebelum mencoba kembali.                       |
| Akses ditolak                              | Gunakan akun dengan peran yang sesuai. Hubungi admin jika tugas Anda membutuhkan akses tersebut.                  |

Ikuti pesan pada form. Periksa detail dan riwayat sebelum mengulangi tindakan.

## Akun dan Contoh Demo

Bagian pilihan untuk latihan. Gunakan data buatan tanpa informasi pribadi atau dokumen kerja.

### Akun yang Tersedia

| Username           | Peran       | Kegunaan                                                |
| ------------------ | ----------- | ------------------------------------------------------- |
| `demo_admin`       | Admin       | Membaca dokumen dan mengelola akun/vendor               |
| `demo_pemohon`     | Pemohon     | Membuat dan mengajukan permintaan                       |
| `demo_approver`    | Approver    | Menyetujui, meminta revisi, menolak, atau mengakhiri PO |
| `demo_procurement` | Procurement | Mencatat penawaran, memilih vendor, dan menerbitkan PO  |
| `demo_penerima`    | Penerima    | Mencatat penerimaan barang/jasa                         |

Gunakan salah satu akun demo sesuai peran pada tabel. Password terbaru diberikan bersama informasi akses demo melalui kanal privat yang ditentukan; password tidak dicantumkan dalam panduan publik.

Untuk mencoba seluruh alur sendiri, gunakan urutan **demo_pemohon → demo_approver → demo_procurement → demo_penerima**. Keluar dan konfirmasikan sebelum berganti akun; gunakan nomor PR/PO yang sama untuk melanjutkan. Satu profil browser memakai satu sesi aktif.

### Contoh yang Dapat Dibuka

Kondisi pada tabel adalah **keadaan awal**. Data mungkin sudah dilanjutkan oleh pengguna lain atau penawarannya sudah kedaluwarsa.

| Kode pencarian | Kondisi awal                            | Mulai dengan                          |
| -------------- | --------------------------------------- | ------------------------------------- |
| `[DEMO G-01]`  | Permintaan barang masih draf            | Pemohon: **Permintaan Saya**          |
| `[DEMO J-01]`  | Permintaan jasa disetujui, belum ada PO | Procurement: **Permintaan Pengadaan** |
| `[DEMO G-02]`  | PO barang terbit                        | Penerima: **Purchase Order**          |
| `[DEMO G-03]`  | Barang diterima sebagian                | Penerima: **Purchase Order**          |
| `[DEMO J-02]`  | Jasa diterima lengkap                   | Penerima: **Purchase Order**          |

Cari kode di atas pada kolom pencarian, lalu buka detailnya. G-03 awalnya menunjukkan dipesan **10**, diterima **6**, ditolak **2**, dan sisa **4**.

Gunakan judul dan referensi berbeda untuk latihan baru. Contoh jasa: **2 kunjungan**, estimasi `100000`, penawaran `90000` per kunjungan; total PO **IDR 180.000,00**.

Jika memerlukan data demo dari awal, hubungi pengelola. Persiapan aplikasi lokal ada pada [README](../README.md); pengelolaan hosting ada pada [panduan deployment](DEPLOYMENT.md). Data lokal dan hosting terpisah.
