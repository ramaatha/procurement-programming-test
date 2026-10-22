# Alur kerja Procurement

Diperbarui: 22 Oktober 2026

## Tujuan

Membangun aplikasi pengadaan barang dan jasa dari pengajuan kebutuhan sampai penerimaan. Hasil pekerjaan mencakup aplikasi yang dapat dijalankan, dokumentasi proses, dan rincian paket pekerjaan.

Versi awal menggunakan Django dengan halaman HTML dan SQLite. Pengelolaan stok, invoice, dan pembayaran berada di luar cakupan. Bantuan input AI/Computer Vision ditunda sampai alur utama stabil.

## Status pekerjaan

| Bagian | Status |
| --- | --- |
| Kebutuhan produk dan aturan bisnis | Baseline tersedia pada PRD v1.1 |
| Proses pengadaan dan transisi status | Baseline tersedia pada BUSINESS_PROCESS v1.0 |
| Diagram BPMN dan WBS | Tersedia di outputs dan telah diperiksa |
| Framework | Django dipilih |
| Arsitektur, model data, dan rencana implementasi | Rancangan v1.0 tersedia untuk review |
| Arah visual dan antarmuka | Prototipe HTML autentikasi tersedia; desain final belum dikerjakan |
| Fondasi Django, migrasi akun, dan autentikasi | Tugas 1 selesai; 23 pengujian lulus |
| Schema, angka, audit, dan protokol aksi | Tugas 2 selesai; suite keseluruhan 48 pengujian lulus |
| Service, izin objek, dan halaman proses pengadaan | Belum dikerjakan |

Keberadaan rancangan tidak menyatakan fitur sudah dibangun. Status implementasi hanya berubah setelah kode, validasi, dan pengujian yang terkait selesai.

## Dokumen kerja

| Dokumen | Isi yang dikelola |
| --- | --- |
| [PRD](PRD.md) | Cakupan, peran, kebutuhan fungsional, aturan bisnis, dan kriteria penerimaan |
| [Proses bisnis](BUSINESS_PROCESS.md) | Aktivitas, gateway, transisi status, dan pengecualian |
| [Arsitektur](ARCHITECTURE.md) | Stack, modul, aliran request, akses, transaksi, dan peta halaman |
| [Model data](DATA_MODEL.md) | Entitas, relasi, snapshot, constraint, serta perhitungan |
| [Rencana implementasi](IMPLEMENTATION_PLAN.md) | Urutan tugas, kontrak service, dependensi, dan pengujian |
| [Pedoman kualitas](QUALITY_GUIDELINES.md) | Kriteria kode, keamanan, dokumentasi, dan antarmuka |
| [Panduan commit](COMMIT_GUIDE.md) | Pengelompokan berkas dan pesan commit |
| [README](../README.md) | Ringkasan aplikasi, struktur repo, hasil pekerjaan, dan petunjuk menjalankan saat tersedia |

Arah visual akan dicatat pada DESIGN_SYSTEM saat rancangan antarmuka ditinjau. Hasil pengujian akan dicatat pada TESTING setelah aplikasi dapat dijalankan. Jangan menulis petunjuk setup atau hasil pengujian yang belum dibuktikan.

## Urutan pengerjaan

1. **Tetapkan kebutuhan.** Periksa peran, alur, aturan angka, batas fitur, dan kriteria penerimaan. Catat perubahan kebutuhan pada PRD.
2. **Cocokkan proses.** Pastikan diagram dan WBS mengikuti pengajuan, approval, penawaran, PO, penerimaan, serta cabang kegagalannya.
3. **Tinjau rancangan teknis.** Periksa model data, izin per objek, transaksi, versi, deduplikasi, dan peta halaman sebelum mulai coding.
4. **Bangun fondasi.** Siapkan konfigurasi Django, database, migrasi, akun/peran, dan autentikasi. Buktikan bahwa server menolak akses yang tidak diizinkan.
5. **Kerjakan alur pengadaan.** Implementasikan permintaan dan revisi, keputusan approval, penawaran, penerbitan PO, lalu penerimaan barang/jasa sesuai urutan pada rencana implementasi.
6. **Uji pengecualian.** Periksa penolakan, pembatalan, penerimaan sebagian, kelebihan jumlah, penutupan sisa, transaksi bersamaan, dan kegagalan penyimpanan.
7. **Lengkapi antarmuka.** Tinjau arah visual sebelum styling. Periksa form, daftar, detail, pesan kesalahan, keyboard, dan layar kecil dengan alur yang benar-benar berjalan.
8. **Uji pemasangan bersih.** Jalankan aplikasi dari environment dan database kosong, muat data contoh, lalu ikuti perjalanan pengguna untuk tiap peran.
9. **Siapkan hasil akhir.** Cocokkan perilaku aplikasi dengan dokumentasi, perbarui status WBS berdasarkan bukti, dan periksa paket serah terima.

Rencana implementasi membagi pekerjaan menjadi 11 tugas. Setiap tugas memiliki keluaran dan pengujian yang dapat diperiksa. Selesaikan kegagalan pada tugas berjalan sebelum memperluas fitur berikutnya.

## Cara mengerjakan perubahan

- Baca dokumen dan kode yang memiliki aturan terkait sebelum mengubah fitur.
- Tentukan perilaku yang diharapkan, lalu tulis pengujian untuk perubahan status, akses, atau data yang berisiko.
- Jalankan pengujian dan periksa kegagalannya sebelum implementasi; ulangi setelah perubahan hingga hasilnya sesuai.
- Simpan mutasi bisnis beserta audit dalam satu transaksi. Periksa kembali keadaan terbaru di server, termasuk saat dua tindakan datang bersamaan.
- Gunakan pemeriksaan browser untuk memastikan form, navigasi, dan tindakan pengguna bekerja dari awal sampai akhir.
- Perbarui dokumen pemilik aturan bila implementasi mengubah keputusan yang sudah dicatat.
- Laporkan perubahan, hasil verifikasi, batas yang belum teruji, serta berkas untuk commit.

Peninjauan rancangan dilakukan pada batas tahap. Perubahan implementasi rutin dalam cakupan yang telah ditinjau tidak memerlukan pengulangan persetujuan untuk setiap edit.

## Keterlacakan dan kriteria selesai

PRD menghubungkan kebutuhan FR/AS/OPT dengan aktivitas BP, gateway GW, paket WBS, dan skenario TC. ID tetap dipertahankan saat urutan implementasi berubah.

Satu fitur selesai setelah kriteria penerimaannya terpenuhi, izin dan validasi server diterapkan, efek database benar, kegagalan penting tertangani, dan pengujian terkait lulus. Antarmuka yang terlibat harus diperiksa di browser. Rancangan atau screenshot saja tidak membuktikan perilaku aplikasi.

Gunakan status **Direncanakan**, **Diimplementasikan**, **Terverifikasi**, dan **Ditunda** sesuai bukti. Pekerjaan opsional yang ditunda tidak dihitung sebagai fitur selesai. Bedakan hasil lokal, ter-commit, ter-push, ter-deploy, dan teruji produksi.

## Keluaran dan batas pekerjaan

Register ini menghubungkan keluaran proyek dengan ID yang digunakan pada WBS.

| ID | Ketentuan |
| --- | --- |
| EX-01 | Produk yang dibangun adalah aplikasi Procurement. |
| EX-02 | Diagram BPMN tersedia dalam satu dokumen PDF dan berkas draw.io yang dapat diedit. |
| EX-03 | WBS modul dan fitur tersedia dalam satu workbook Excel. |
| EX-04 | Kode aplikasi dikelola dalam satu repository GitHub. |
| EX-05 | Aplikasi menggunakan Python; pilihan database yang diperbolehkan adalah SQLite atau PostgreSQL. Rancangan awal memakai SQLite. |
| EX-06 | Cakupan dimulai dari permintaan sampai penerimaan barang/jasa; stok gudang dan pembayaran tidak termasuk. |
| EX-07 | Bantuan input AI/Computer Vision merupakan pengembangan opsional. |
| US-01 | Target penyelesaian: 25 Oktober 2026 pukul 23:59:59 WIB. |
| US-02 | Paket serah terima berisi diagram BPMN, workbook WBS, dan URL repository kode aplikasi. |

Hasil akhir berada langsung pada [outputs](../outputs/). Dokumentasi berada pada docs. Folder tmp menyimpan bukti pemeriksaan lokal dan diabaikan Git. Buka folder repo langsung melalui Open Folder di editor.

## Commit dan serah terima

Pemilik repository melakukan staging, commit, dan push. Setiap perubahan disertai saran pengelompokan berkas dan pesan commit pada COMMIT_GUIDE. Jangan memasukkan database lokal, konfigurasi rahasia, cache, atau log ke commit.

Sebelum serah terima, pastikan petunjuk instalasi sudah dijalankan, pengujian relevan lulus, tautan hasil pekerjaan dapat dibuka, dan repository memuat kode yang sesuai dengan dokumentasi. Deployment belum menjadi bukti sampai lingkungan tersebut benar-benar dijalankan dan diuji.

## Hasil tahap fondasi

Konfigurasi Django, custom User lima peran, login/logout, pembatasan akses halaman akun, CSRF, redirect aman, dan migrasi SQLite tersedia. Suite fondasi berisi 23 test. Setelah penambahan schema, parser angka, audit, dan helper token/replay, suite keseluruhan berisi 48 test lulus; system check bersih dan tidak ada migrasi model yang tertinggal. Pemeriksaan browser memakai database sintetis terpisah, mencakup login/logout, pesan gagal, keyboard, dan overflow pada viewport 1280.

Rincian bukti dan batas verifikasi berada pada [TESTING](TESTING.md). Pengelolaan akun, izin objek, transaksi bisnis, modul pengadaan, data contoh lengkap, dan UI final belum selesai. FR-01/FR-13 baru diterapkan sebagian; WBS tidak dinaikkan menjadi selesai hanya karena fondasi sudah tersedia.
