# Panduan Pengguna Procurement

Panduan ini membantu penguji melihat contoh dan mencoba proses pengadaan dari awal. Gunakan data sintetis pada database demo, bukan akun atau dokumen kerja.

## Memulai Demo

Ikuti setup pada [README](../README.md), pilih `DJANGO_DATA_DIR` untuk database demo, lalu jalankan migrasi dan `seed_demo`. Password ditentukan oleh orang yang menyiapkan demo melalui `DEMO_PASSWORD`; repository tidak menyimpan password akun demo. Buka alamat server lokal yang sedang berjalan, lalu `/login/`.

| Username         | Peran       | Kegunaan                                                                         |
| ---------------- | ----------- | -------------------------------------------------------------------------------- |
| demo_admin       | Admin       | Mengelola akun/vendor dan membaca transaksi                                      |
| demo_pemohon     | Pemohon     | Membuat, mengubah, mengajukan dan membatalkan permintaan sendiri                 |
| demo_approver    | Approver    | Menyetujui, meminta revisi, menolak atau mengakhiri PO pengguna lain             |
| demo_procurement | Procurement | Mengelola penawaran, memilih vendor, menerbitkan PO dan meminta revisi kebutuhan |
| demo_penerima    | Penerima    | Mencatat penerimaan barang dan jasa                                              |

Admin tidak membuat permintaan atau menjalankan pekerjaan operasional peran lain. Status superuser juga tidak memberi pengecualian pada aturan bisnis aplikasi.

Satu profil browser menggunakan satu sesi aktif. Pilih Keluar, lalu konfirmasikan, sebelum masuk dengan akun berikutnya. Untuk membandingkan dua peran bersamaan, gunakan profil browser yang berbeda. Ikon mata hanya menampilkan/menyembunyikan isian password. Browser atau password manager dapat mengisi kredensial tersimpan; bila tidak diinginkan, ubah pengaturan pengisian otomatis di browser.

## Jalur A: Melihat Contoh

Command seed mencetak nomor permintaan dan PO untuk masing-masing kode. Nomor dokumen dihasilkan aplikasi, sehingga berbeda pada setiap database demo baru.

| Kode | Contoh Awal                  | Periksa Dengan                                                                       |
| ---- | ---------------------------- | ------------------------------------------------------------------------------------ |
| G-01 | Barang draft                 | Pemohon: Permintaan Pengadaan, cari `[DEMO G-01]`, buka detail dan Ubah Draft        |
| J-01 | Jasa disetujui, belum ada PO | Procurement: cari `[DEMO J-01]`, buka Penawaran Dan Pemilihan Vendor                 |
| G-02 | PO barang terbit             | Penerima: Purchase Order, cari judul `[DEMO G-02]`, buka detail dan Catat Penerimaan |
| G-03 | PO barang diterima sebagian  | Semua peran yang berhak: cari `[DEMO G-03]`, lihat Pemenuhan Pesanan                 |
| J-02 | PO jasa diterima lengkap     | Buka PO `[DEMO J-02]`, riwayat penerimaan dan bukti jasa                             |

Mulai sebagai admin untuk melihat daftar permintaan dan PO. Gunakan pencarian nomor/judul, Jenis Pengadaan dan Tahap Pengadaan, lalu Terapkan Pencarian Dan Filter. Hapus Filter mengembalikan daftar. Daftar kosong bisa berarti belum ada data, filter terlalu sempit, atau akun tidak mempunyai akses ke dokumen tersebut. Penerima hanya melihat permintaan yang sudah mempunyai PO; pemohon hanya melihat permintaannya sendiri.

Pada detail G-03, jumlah awal adalah dipesan 10, diterima 6, ditolak 2, sisa 4. Jumlah ditolak merupakan riwayat pemeriksaan, tidak mengurangi kewajiban pemenuhan; sisa dihitung dari dipesan dikurangi diterima. Buka Riwayat Pengadaan untuk melihat siapa menjalankan tindakan dan alasannya. Pada detail PO pilih Halaman Cetak, lalu gunakan Ctrl+P untuk preview/cetak. Snapshot vendor, item, harga dan alasan merupakan data pada saat PO diterbitkan.

J-02 sudah diterima lengkap. Buka catatan penerimaannya untuk memeriksa jenis bukti, referensi, catatan dan periode jasa. Dokumen penerimaan final tidak dapat diedit atau dihapus.

## Jalur B: Mencoba Dari Awal

Gunakan judul baru seperti `UJI Barang Monitor` agar contoh awal tetap mudah dikenali. Tanggal kebutuhan dan tanggal berlaku penawaran mengikuti hari WIB saat pengujian.

### 1. Pemohon Membuat Permintaan

Masuk sebagai demo_pemohon. Dari Antrean Kerja atau Permintaan Pengadaan, pilih Buat Permintaan. Isi:

- Jenis Pengadaan: Barang.
- Judul: `UJI Barang Monitor`.
- Alasan Kebutuhan: `Penggantian monitor ruang kerja uji`.
- Tujuan Penerimaan / Layanan: `Kantor Demo`.
- Tanggal Kebutuhan: hari ini atau setelahnya.
- Item: `Monitor Uji`, satuan `unit`, jumlah `10`, estimasi harga per unit `100000`.

Gunakan titik untuk angka desimal, tanpa pemisah ribuan. Kuantitas maksimal tiga desimal; harga dua desimal. Tambah Baris Item menambah baris; centang Hapus untuk membuang baris yang tidak dipakai. Pilih Simpan Draft. Periksa rincian dan total estimasi IDR 1.000.000,00, lalu Ajukan Permintaan. Catat nomor PR. Status menjadi Diajukan dan revisi pertama tersimpan.

### 2. Approver Memutuskan

Keluar dan masuk sebagai demo_approver. Buka Antrean Persetujuan atau cari nomor PR. Periksa salinan revisi, pilih keputusan Setujui dan Simpan Keputusan. Status menjadi Disetujui. Pemohon tidak dapat menyetujui permintaannya sendiri meskipun perannya kemudian diganti.

Untuk mencoba cabang lain, buat permintaan uji terpisah. Pilih Minta Revisi dan isi alasan; pemohon kemudian mengubah draft serta mengajukan ulang. Revisi sebelumnya tetap dapat dibaca. Pilih Tolak dengan alasan untuk keputusan penolakan final. Procurement juga dapat meminta revisi atas permintaan yang sudah disetujui sebelum PO diterbitkan; pilihan vendor lama dibersihkan.

### 3. Procurement Menyiapkan PO

Masuk sebagai demo_procurement. Cari PR, buka detail lalu Penawaran Dan Pemilihan Vendor. Pilih Tambah Penawaran. Gunakan vendor `DEMO Vendor Peralatan`, referensi unik, tanggal penawaran hari ini, berlaku sampai setidaknya besok, estimasi pemenuhan 1 hari dan harga per unit `90000`. Simpan Penawaran.

Pada Pilih Penawaran, pilih kandidat tersebut, isi alasan pemilihan dan Alasan Sumber Tunggal karena hanya satu vendor layak. Simpan Pilihan Vendor, kembali ke detail permintaan dan pilih Terbitkan PO. Periksa total IDR 900.000,00, snapshot vendor/item, dan status Terbit. Harga melebihi plafon atau tanggal yang tidak berlaku membuat penawaran tidak layak dipilih. Mengedit penawaran terpilih menghapus pilihan sebelumnya sehingga perlu dipilih ulang.

### 4. Penerima Mencatat Barang

Masuk sebagai demo_penerima. Buka PO, pilih Catat Penerimaan. Isi referensi `UJI-SJ-001`, Catatan Pemeriksaan, bukti Surat Jalan, diterima `6`, ditolak `2`, serta alasan penolakan. Pilih Simpan Penerimaan Final. Hasilnya Diterima Sebagian dengan sisa 4. Untuk menyelesaikan, catat penerimaan kedua diterima `4`, ditolak `0` dengan referensi baru. Status menjadi Diterima Lengkap, sisa 0. Catatan pertama tetap menunjukkan penolakan 2.

### 5. Mencoba Jasa

Ulangi langkah 1–3 dengan judul `UJI Jasa Jaringan`, jenis Jasa, item `Pemeriksaan Jaringan`, satuan `kunjungan`, jumlah `2`, estimasi harga `100000` dan penawaran `90000` per kunjungan. Saat penerimaan, pilih Laporan Pekerjaan atau Berita Acara Jasa. Isi referensi, catatan, awal/akhir pelaksanaan hari ini dan jumlah diterima `2`, ditolak `0`. Periode wajib memenuhi awal <= akhir <= hari konfirmasi WIB. Periksa status Diterima Lengkap dan bukti/periode pada detail penerimaan. Tidak ada persentase kemajuan atau mutasi stok.

### 6. Pembatalan Dan Penutupan Sisa

Untuk mencoba penutupan, gunakan PO uji lain yang baru diterima sebagian. Masuk sebagai demo_approver selain pemohon. Pada detail PO isi Alasan Pembatalan Atau Penutupan Sisa, lalu Konfirmasi Akhiri PO. Status operasional menjadi Selesai Dengan Kekurangan; sisa historis tetap ditampilkan. Jika accepted masih nol, PO menjadi Dibatalkan. PO terminal tidak menerima pencatatan penerimaan atau penutupan kedua.

Pemohon hanya dapat membatalkan permintaan sendiri sebelum ada PO, dengan alasan. Sesudah ada PO, gunakan aturan penutupan PO oleh approver; jangan mengubah status melalui database.

## Memeriksa Keadaan Gagal

| Percobaan                                      | Hasil Yang Diharapkan                                                            |
| ---------------------------------------------- | -------------------------------------------------------------------------------- |
| Login dengan password salah                    | Satu pesan kredensial di form login; password tidak dirender kembali dari server |
| Mengajukan draft dengan header wajib kosong    | Validasi dalam form; tidak ada revisi pengajuan baru                             |
| Jumlah negatif atau harga tidak valid          | Form ditolak, dokumen belum berubah                                              |
| Menolak atau meminta revisi tanpa alasan       | Pesan alasan wajib pada form; keputusan belum disimpan                           |
| Penerimaan ditolak lebih dari nol tanpa alasan | Form ditolak; belum ada penerimaan final baru                                    |
| Periode jasa kosong/masa depan                 | Form ditolak, belum ada penerimaan baru                                          |
| Admin membuka `/requests/new/`                 | Akses ditolak (403); admin tetap dapat membaca daftar/detail                     |
| Pemohon membuka URL detail milik pemohon lain  | Tidak ditemukan/tidak tersedia (404), tanpa membocorkan dokumen                  |
| Mengirim form lama sesudah dokumen berubah     | Konflik (409); muat ulang dan periksa hasil sebelum mengulangi                   |

Pesan kesalahan yang berbeda dapat muncul pada masing-masing field. Satu kesalahan tidak diulang sebagai alert global di luar form. Form gagal mempertahankan isian yang aman; password tidak diisi ulang oleh server. Ketika simpan berhasil, periksa detail dan riwayat sebelum menekan tindakan lagi.

## Mengulangi Demo

Menjalankan `seed_demo` kembali tidak mereset akun, password, peran atau transaksi yang sudah dipakai. Nomor contoh tetap sama. Penawaran lama bisa kedaluwarsa dan draft yang sudah diajukan tetap berada pada tahap barunya. Untuk mengulang seluruh keadaan awal, hentikan server dan arahkan `DJANGO_DATA_DIR` ke folder baru di dalam repository, misalnya `var/demo-baru`; jalankan migrate dan seed kembali. Database lama tetap tersedia. Terminal dan server harus memakai folder data yang sama.

Demo lokal tidak otomatis mempunyai URL publik. Untuk pengujian recruiter jarak jauh, pemilik proyek perlu menyiapkan deployment dan membagikan alamat beserta kredensial demo melalui kanal pengumpulan. Panduan ini tidak menyatakan deployment sudah tersedia.
