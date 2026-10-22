# Pengujian Procurement

Diperbarui: 22 Oktober 2026

## Lingkup yang telah diverifikasi

Verifikasi mencakup akun, autentikasi, session, konfigurasi environment, 14 model Procurement, migrasi SQLite, parser angka, helper token/replay dan versi, serta service/form pengelolaan akun admin. Ini belum menjadi hasil pengujian seluruh aplikasi Procurement.

Lingkungan pemeriksaan: Python 3.12.14, Django 5.2.18, SQLite 3.53.1, dan JSON1 tersedia. Dependensi terpasang: asgiref 3.12.1, sqlparse 0.6.0, dan tzdata 2026.5. `pip check` tidak menemukan dependensi yang rusak.

## Pengujian otomatis

| Kelompok | Jumlah test | Perilaku yang diperiksa |
| --- | --- | --- |
| Autentikasi | 10 | Login/logout, akun nonaktif, kredensial salah, password tidak dipantulkan, CSRF, logout POST, redirect aman, pencabutan akses setelah nonaktif, serta route yang tidak disediakan |
| Peran dan guard | 6 | Lima peran dapat login, manipulasi role pada form tidak mengubah akun, peran invalid dan versi nol ditolak database, peran terkini dibaca kembali, dan halaman akun tidak menerima POST |
| Konfigurasi | 7 | Secret hilang/pendek, nilai DEBUG invalid, hostname produksi hilang/wildcard, Secure cookie dan HTTPS pada mode non-debug, serta database test terpisah |
| Angka berskala | 5 | Parsing ketat, batas int64, penolakan input ambigu, formatter kanonik, pembulatan half-up per baris, dan overflow hasil/jumlah |
| Constraint pengadaan | 10 | Header draft, nilai/status valid, keunikan revisi/keputusan/PO/item, kelengkapan metadata penutupan, periode bukti, parent yang tidak ada, dan FK historis |
| Token dan payload | 3 | Scope tepat, tanda tangan, TTL 24 jam, hash kanonik, urutan baris, serta penolakan field sensitif/float |
| Transaksi aksi | 7 | Replay sebelum pemeriksaan versi, konflik nonce/payload/scope, nonce sekali untuk password, resolver allowlist, kewajiban atomic, serta rollback dokumen/audit/hasil aksi |
| Service akun | 17 | Pembuatan/edit/reset, validasi username/role/password, admin terakhir, otorisasi terkini, nonce sekali, versi, batas int64 dan rollback |
| HTTP dan perlindungan form akun | 14 | Izin empat peran, CSRF, parameter privilege, token lintas aktor/target, 400/409/503, sesi dicabut, dan redaksi token/password pada exception report |
| Dua penulis akun | 1 | Dua admin menurunkan peran sendiri secara bersamaan; tepat satu perubahan berhasil dan satu admin aktif tetap tersedia |

Total: **80 test lulus**. Subtest beberapa input/peran tidak dihitung sebagai method test tambahan.

Perintah yang dijalankan:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test -v 2
.\.venv\Scripts\python.exe manage.py migrate --noinput
```

Perintah Django menggunakan environment sebagaimana langkah setup pada README. Hasil: system check tanpa isu; tidak ada perubahan model yang memerlukan migrasi baru; seluruh migrasi akun, autentikasi, content types, session, dan Procurement berhasil.

Sebelum implementasi, pengujian route autentikasi gagal karena route belum tersedia. Pengujian konfigurasi menangkap setelan yang belum ditolak. Pengujian berikutnya menangkap tidak adanya constraint role/version dan pembatasan POST pada halaman akun. Setelah implementasi guard, seluruh suite lulus.

Database test berbasis file berada pada var/test.sqlite3 dan terpisah dari database kerja. Pengujian CSRF memakai client dengan pemeriksaan CSRF aktif. Tidak ada mock autentikasi atau database untuk hasil di atas.

## Migrasi dan konsistensi schema

Database terisolasi `var/schema-migration-check` dipakai untuk migrasi dari kosong, rollback hanya app Procurement, lalu penerapan ulang. Empat belas tabel Procurement terbentuk kembali. Fixture barang dan jasa tersimpan dengan angka yang sesuai; pemeriksaan foreign key tidak menemukan pelanggaran dan `PRAGMA integrity_check` menghasilkan `ok`. Database kerja tidak dipakai untuk rollback ini.

Pengujian tahap schema terlebih dahulu gagal karena parser, model, dan protokol aksi belum tersedia. Setelah implementasi, seluruh suite lulus. Database hanya menjaga hubungan yang ada, keunikan dan kondisi dalam satu baris. Item yang ada tetapi milik request/PO lain tetap memerlukan pemeriksaan service.

## Pemeriksaan browser

Server dijalankan pada loopback dengan database sintetis terpisah di var/browser-smoke. Akun pemeriksaan tidak dibuat dalam database kerja.

- Login menghasilkan halaman akun dengan username dan peran Pemohon.
- Logout kembali ke login; membuka halaman akun setelahnya diarahkan ke login.
- Kredensial salah menampilkan pesan yang dapat dibaca; username dipertahankan dan password dikosongkan.
- Tab berpindah dari username ke password lalu tombol Masuk; focus terlihat.
- Pada viewport 1280 piksel, lebar konten tidak melampaui viewport pada halaman akun maupun login.
- Bootstrap admin melalui command line berhasil pada database terisolasi.

Bukti tampilan dan log berada pada tmp dan diabaikan Git. Server pemeriksaan dihentikan setelah alur selesai.

## Pengelolaan akun

Service membaca ulang admin aktif sebelum memeriksa replay, lalu memvalidasi input dan versi dalam transaksi IMMEDIATE. Akun, AuditEvent dan ActionReceipt rollback bersama jika salah satu penulisan gagal. Create/reset memakai nonce sekali dan payload hash kosong; metadata edit dapat direplay dengan payload sama. Admin aktif terakhir tidak dapat dinonaktifkan atau diturunkan perannya.

Pengujian batas versi menemukan overflow integer sebelum guard ditambahkan; regresinya kini lulus. Pengujian exception report juga terlebih dahulu membuktikan token belum tersamarkan, lalu lulus setelah redaksi parameter POST dan variabel lokal form diterapkan pada mode non-debug.

Browser memakai database terpisah `var/account-browser-check`. Alur yang diperiksa: login admin, buat akun dengan password invalid/valid, ubah peran, nonaktif/aktifkan, reset password, logout, login akun hasil reset, dan penolakan akses `/users/` untuk penerima. Input aman dipertahankan saat 400 dan password dikosongkan. Lima perubahan menghasilkan tepat lima audit dan lima receipt aksi.

Form edit tidak melampaui viewport 390/768/1440; Tab mencapai tautan daftar akun dengan focus terlihat. Ini pemeriksaan form fungsional, belum audit visual/aksesibilitas seluruh aplikasi. Console mencatat respons 400/403 yang sengaja diuji serta favicon 404; tidak ditemukan error JavaScript aplikasi. Server pemeriksaan dihentikan setelah selesai.

## Batas verifikasi

Pengelolaan akun melalui UI dan service sudah diuji. Izin per objek Procurement, keputusan approval, penerbitan PO, dan penerimaan belum diimplementasikan atau diuji. Parser angka, token, replay, versi dan rollback sudah diuji sebagai helper dan pada mutasi akun; alur transaksi pengadaan belum tersedia. Service harus membaca ulang akun/izin sebelum replay dan memeriksa seluruh relasi serta jumlah dalam transaksi. Concurrency dua penulis pada aksi pengadaan belum dibuktikan oleh tahap ini.

Tampilan masih prototipe HTML fungsional. Form edit akun sudah diperiksa pada lebar 390/768/1440. Pemeriksaan aksesibilitas menyeluruh serta arah visual final menunggu tahap UI. Mode non-debug diperiksa melalui konfigurasi; hosting, reverse proxy, HTTPS nyata, dan kapasitas produksi belum diverifikasi.

Pembuatan virtual environment dan pemasangan requirements dilakukan dari lingkungan Python 3.12 yang tersedia. Launcher sistem pada mesin pemeriksaan belum mempunyai runtime Python 3.12 yang terdaftar; checkout lokal menggunakan interpreter pada .venv. Setup lintas mesin tetap mensyaratkan Python 3.12 tersedia.

Data contoh lintas peran serta perjalanan pengadaan lengkap belum tersedia. FR-01 dan FR-13 baru diterapkan sebagian; status penerimaan keseluruhan kebutuhan tersebut belum dinaikkan menjadi selesai.

Regresi otomatis `account.create` dan `account.password` memakai opsi replay bawaan, memeriksa payload hash kosong dan penolakan digest nonkosong. Kedua service juga diuji saat nonce dikirim ulang dengan password atau metadata berbeda.
