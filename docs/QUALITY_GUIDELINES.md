# Pedoman kualitas Procurement

Diperbarui: 22 Oktober 2026

## Kode dan struktur

Gunakan Python dengan type hint pada input serta keluaran service. Pisahkan validasi form, keputusan akses, query, dan mutasi bisnis sesuai arsitektur. Beri nama fungsi dan field berdasarkan tugas pengadaan yang ditangani.

View mengatur respons HTTP; service memeriksa aturan dan menjalankan transaksi. ORM menangani akses penyimpanan. Tambahkan abstraksi atau dependensi hanya bila ada kebutuhan yang tidak dapat ditangani struktur yang sudah tersedia.

Tangani error yang dikenal dengan pesan yang sesuai. Biarkan error pemrograman tercatat untuk pemeriksaan, tanpa mengekspos detail internal kepada pengguna. Komentar menjelaskan alasan atau batasan yang tidak terlihat dari kode.

## Akses dan keamanan

- Periksa akun aktif, peran terkini, kepemilikan, dan izin objek pada server.
- Terapkan aturan yang sama pada halaman, form, dan service. Tombol tersembunyi tidak menggantikan otorisasi.
- Gunakan session, password hashing, validasi password, CSRF, dan escaping template.
- Ambil identitas aktor dari session. Jangan menerima pemilik, peran, total, atau status akhir sebagai keputusan dari browser.
- Simpan rahasia melalui environment. Jangan menuliskan password, cookie, token, atau payload bebas dalam log dan audit.
- Tolak perubahan pada revisi/PO historis dan penerimaan yang sudah final melalui seluruh jalur aplikasi.

## Ketepatan data

Ikuti skala integer dan pembulatan half-up pada DATA_MODEL. Jangan memakai float untuk menghitung uang. Hitung total dokumen dari total baris yang sudah dibulatkan.

Persetujuan terikat pada revisi tertentu. PO menyimpan snapshot vendor dan rincian pesanan. Accepted mengurangi remaining; rejected dicatat terpisah. Pembatalan dan penutupan sisa tidak boleh menghapus riwayat atau mengubah jumlah yang pernah diterima.

Perubahan bisnis, audit, dan hasil deduplikasi harus berhasil atau rollback bersama. Periksa versi, status, dan jumlah terbaru di dalam transaksi. Pengujian dua penulis harus menggunakan koneksi terpisah pada database berbasis file.

## Antarmuka

Utamakan pekerjaan pengguna: menemukan permintaan, menilai kebutuhan, membandingkan penawaran, menerbitkan PO, dan mengonfirmasi penerimaan. Tampilkan nilai, sisa, alasan keputusan, serta tindakan berikutnya pada bagian yang mudah ditemukan.

Gunakan istilah, kontrol, dan pola form yang konsisten. Setiap field memiliki label; kesalahan menjelaskan apa yang perlu diperbaiki dan mempertahankan input yang aman. Tindakan pembatalan atau konfirmasi final menjelaskan konsekuensinya sebelum dikirim.

Periksa keadaan kosong, submit berlangsung, kegagalan, konflik data, dan sukses. Tampilkan status dengan teks, bukan warna saja. Pastikan navigasi keyboard, focus, kontras, dan target sentuh dapat digunakan. Daftar dan form harus tetap terbaca pada lebar 390, 768, dan 1440 piksel.

Angka pada tabel rata kanan dengan presisi yang konsisten. Ringkasan harus berasal dari data yang sama dengan rincian. Gunakan data sintetis yang diberi label untuk demo; jangan membuat statistik bisnis, testimoni, atau klaim kapasitas yang belum diukur.

## Bahasa dan dokumentasi

Tulis dalam bahasa Indonesia yang langsung menjelaskan aktor, tindakan, dan hasil. Pertahankan istilah teknis yang membantu ketepatan. Hindari pembuka berulang, jargon pemasaran, dan klaim yang lebih kuat daripada buktinya.

Dokumentasi membahas produk, keputusan teknis, prosedur kerja, dan hasil verifikasi. Setiap aturan mempunyai satu dokumen pemilik; dokumen lain menautkannya tanpa menyalin seluruh isinya. Pertahankan ID kebutuhan, skenario pengujian, nama field, status, dan kontrak saat menyunting bahasa.

## Verifikasi dan penyelesaian

Pilih pengujian berdasarkan risiko perubahan. Prioritaskan izin per objek, transisi status, perhitungan, snapshot, pengiriman ulang, rollback, serta transaksi bersamaan. Lengkapi pengujian server dengan pemeriksaan alur di browser.

Catat perintah yang dijalankan, hasilnya, dan batas yang belum teruji. Jangan menyamakan pemeriksaan dokumen, struktur berkas, atau tampilan halaman dengan keberhasilan alur aplikasi.

Sebelum menyatakan satu tahap selesai, pastikan kriteria penerimaan terpenuhi, pengujian terkait lulus, dokumen sesuai perilaku aktual, dan perubahan siap ditinjau. Staging, commit, serta push dilakukan pemilik repository.
