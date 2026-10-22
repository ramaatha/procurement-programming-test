# Pedoman pengembangan Procurement

## Stack dan cakupan

- Gunakan Python dan Django. Rancangan awal memakai Django templates, CSS/JavaScript lokal, dan SQLite.
- Ikuti cakupan pada [PRD](docs/PRD.md) dan transisi pada [proses bisnis](docs/BUSINESS_PROCESS.md).
- Baca [arsitektur](docs/ARCHITECTURE.md), [model data](docs/DATA_MODEL.md), dan [rencana implementasi](docs/IMPLEMENTATION_PLAN.md) sebelum mengubah fitur terkait.
- Django sudah dipilih. Fondasi akun/autentikasi serta schema pengadaan dan helper transaksi tersedia dan teruji. Pengelolaan akun admin dan policy peran sudah tersedia; izin objek dan service alur pengadaan belum diimplementasikan. Jangan menyamakan rancangan dengan fitur yang sudah dibangun atau teruji.

## Implementasi

- Tulis kode modular dan lengkap, dengan type hint pada batas service serta inputnya.
- Pisahkan form, policy, selector, service, dan model sesuai tanggung jawabnya. Gunakan ORM tanpa menambah lapisan abstraksi yang tidak diperlukan.
- Rancang aliran data, izin, perubahan status, dan kegagalan sebelum menulis fitur yang kompleks.
- Terapkan validasi server dan izin per objek. Jangan mempercayai peran, pemilik, status, atau total dari browser.
- Simpan perubahan bisnis, audit, dan hasil aksi dalam satu transaksi. Jaga snapshot, versi, deduplikasi, presisi, serta batas jumlah.
- Tangani error yang dikenal dengan pesan aman; jangan menyembunyikan error pemrograman atau menuliskan rahasia pada log.
- Periksa sintaks, import, tipe, migrasi, serta perilaku yang terdampak sebelum melaporkan hasil.
- Saat memberikan kode, sebutkan lokasi file. Komentar menjelaskan alasan teknis yang diperlukan.

## Dokumentasi dan kualitas

- Ikuti [pedoman kualitas](docs/QUALITY_GUIDELINES.md) untuk kode, keamanan, data, antarmuka, dan bahasa.
- Dokumentasi hanya menjelaskan produk, keputusan teknis, prosedur kerja, dan hasil verifikasi.
- Pertahankan aturan bisnis, ID kebutuhan/pengujian, nama field, status, dan kontrak saat menyunting gaya.
- Catat arah visual sebelum styling. Periksa form, navigasi, aksesibilitas, responsive, dan keadaan gagal/sukses pada alur yang bekerja.
- Perbarui dokumen pemilik ketika keputusan berubah. Hindari duplikasi dan berkas yang tidak mempunyai fungsi proyek.

## Cara bekerja dan pelaporan

- Jawab ringkas dalam bahasa Indonesia: hasil, bukti verifikasi, batas yang belum teruji, dan langkah berikutnya.
- Gunakan pencarian terarah; baca bagian yang relevan beserta konteks dan perluas bila belum cukup.
- Simpan log panjang sebagai bukti lokal, lalu tampilkan ringkasan, hasil proses, dan error yang relevan.
- Selesaikan perubahan rutin dalam cakupan yang sudah ditinjau tanpa meminta persetujuan untuk setiap edit. Tinjau kembali bila cakupan atau keputusan penting berubah.
- Jangan mengirim pesan, membuat percakapan baru, atau mengubah layanan eksternal tanpa instruksi pengguna.
- Bedakan hasil lokal, ter-commit, ter-push, ter-deploy, dan teruji produksi.
- Staging, commit, dan push hanya dilakukan pengguna. Di akhir saran commit, sertakan daftar lengkap berkas dan pesan commit. Pisahkan kode dan dokumentasi bila masing-masing dapat ditinjau sendiri; jangan menjalankan tindakan Git tersebut.
