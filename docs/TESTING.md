# Pengujian Procurement

Diperbarui: 22 Oktober 2026

## Lingkup yang telah diverifikasi

Verifikasi mencakup akun, autentikasi, session, konfigurasi environment, 14 model Procurement, migrasi SQLite, parser angka, serta helper token/replay dan versi. Ini belum menjadi hasil pengujian seluruh aplikasi Procurement.

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

Total: **48 test lulus**. Subtest beberapa input/peran tidak dihitung sebagai method test tambahan.

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

## Batas verifikasi

Pengelolaan akun melalui UI, izin per objek Procurement, keputusan approval melalui service, penerbitan PO, dan penerimaan belum diimplementasikan atau diuji. Parser angka, token, replay, versi dan rollback sudah diuji sebagai helper, belum sebagai alur mutasi bisnis lengkap. Service harus membaca ulang akun/izin sebelum replay dan memeriksa seluruh relasi serta jumlah dalam transaksi. Concurrency dua penulis pada aksi pengadaan belum dibuktikan oleh tahap ini.

Tampilan masih prototipe HTML fungsional. Lebar 390/768/1440, pemeriksaan aksesibilitas menyeluruh, dan arah visual final menunggu tahap UI. Mode non-debug diperiksa melalui konfigurasi; hosting, reverse proxy, HTTPS nyata, dan kapasitas produksi belum diverifikasi.

Pembuatan virtual environment dan pemasangan requirements dilakukan dari lingkungan Python 3.12 yang tersedia. Launcher sistem pada mesin pemeriksaan belum mempunyai runtime Python 3.12 yang terdaftar; checkout lokal menggunakan interpreter pada .venv. Setup lintas mesin tetap mensyaratkan Python 3.12 tersedia.

Data contoh lintas peran serta perjalanan pengadaan lengkap belum tersedia. FR-01 dan FR-13 baru diterapkan sebagian; status penerimaan keseluruhan kebutuhan tersebut belum dinaikkan menjadi selesai.

Catatan cakupan regresi: penolakan replay password sudah diuji dengan `replayable=False`. Guard bawaan `account.create` dan `account.password`, hash kosong, serta penolakan digest nonkosong lulus probe terpisah. Pengujian otomatis kedua aksi dengan opsi replay bawaan akan dilengkapi bersama service pengelolaan akun pada Tugas 3.
