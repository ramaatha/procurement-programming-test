# Pengujian Procurement

Diperbarui: 22 Oktober 2026

## Lingkup yang telah diverifikasi

Verifikasi mencakup akun, autentikasi, session, konfigurasi environment, 14 model Procurement, migrasi SQLite, parser angka, helper token/replay dan versi, service/form pengelolaan akun admin, draft, pengajuan, snapshot revisi dan pembatalan permintaan sebelum PO, keputusan approval dan pengembalian untuk revisi, serta vendor, penawaran dan pemilihan. Ini belum menjadi hasil pengujian seluruh aplikasi Procurement.

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
| Service permintaan | 15 | Draft tidak lengkap, validasi item/tanggal, pembulatan, snapshot/revisi, replay, versi, izin terkini, pembatalan, guard PO, overflow dan rollback |
| HTTP permintaan | 12 | Formset, tambah/hapus baris, data server-only, CSRF, akses objek, token lintas aktor, stale form, escaping dan redaksi exception report |
| Dua penulis permintaan | 1 | Dua submit bersamaan dengan nonce sama atau berbeda menghasilkan tepat satu snapshot |
| Service approval | 13 | Setuju/revisi/tolak, alasan, self-review, role terkini, replay, status/versi/snapshot, rollback, return procurement dan overflow |
| HTTP approval | 9 | Antrean, paginasi, form keputusan, akses/CSRF/token, konflik, escaping, busy 503 dan redaksi POST pada exception report |
| Dua reviewer | 1 | Dua keputusan bersamaan menghasilkan satu keputusan/audit; replay nonce sama tidak menggandakan hasil |
| Vendor | 6 | Create/edit/nonaktif, izin terkini, validasi, replay/versi, rollback, CSRF dan form |
| Penawaran dan pemilihan | 21 | Item/harga/tanggal/total, status/izin/PO, sumber tunggal, revisi, pilihan, rollback, HTTP/token/CSRF, label dan replay setelah vendor nonaktif |
| Dua penulis penawaran | 1 | Dua penawaran bersamaan memakai versi request; nonce sama replay, nonce berbeda konflik |

Total: **159 test lulus**. Subtest beberapa input/peran tidak dihitung sebagai method test tambahan.

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

Pengelolaan akun dan permintaan melalui UI/service sudah diuji, termasuk scope objek, replay, snapshot, rollback serta pengajuan serentak. Keputusan approval dan pengembalian ke CHANGES_REQUESTED sudah tersedia dan diuji melalui service serta browser. Sourcing sudah tersedia dan diuji. Penerbitan PO dan penerimaan belum diimplementasikan atau diuji. Keberadaan PO memakai fixture untuk menguji guard; perjalanan penerbitan dan persaingan cancel/issue sebenarnya menunggu tugas terkait.

Tampilan masih prototipe HTML fungsional. Form edit akun sudah diperiksa pada lebar 390/768/1440. Pemeriksaan aksesibilitas menyeluruh serta arah visual final menunggu tahap UI. Mode non-debug diperiksa melalui konfigurasi; hosting, reverse proxy, HTTPS nyata, dan kapasitas produksi belum diverifikasi.

Pembuatan virtual environment dan pemasangan requirements dilakukan dari lingkungan Python 3.12 yang tersedia. Launcher sistem pada mesin pemeriksaan belum mempunyai runtime Python 3.12 yang terdaftar; checkout lokal menggunakan interpreter pada .venv. Setup lintas mesin tetap mensyaratkan Python 3.12 tersedia.

Data contoh lintas peran serta perjalanan pengadaan lengkap belum tersedia. FR-01 dan FR-13 baru diterapkan sebagian; status penerimaan keseluruhan kebutuhan tersebut belum dinaikkan menjadi selesai.

Regresi otomatis `account.create` dan `account.password` memakai opsi replay bawaan, memeriksa payload hash kosong dan penolakan digest nonkosong. Kedua service juga diuji saat nonce dikirim ulang dengan password atau metadata berbeda.

## Draft, pengajuan dan pembatalan permintaan

Pengujian awal gagal karena service dan route belum tersedia. Regresi tambah baris kemudian menangkap alert validasi yang tampil meskipun setiap form valid; template kini memeriksa jumlah error sebenarnya. Suite keseluruhan lulus 108 test, termasuk 28 test permintaan. Tidak ada perubahan migrasi atau dependensi.

Pengujian mencakup draft kosong, item lengkap/positif, tanggal hari WIB, angka kanonik dan pembulatan half-up per baris, snapshot lama setelah pengajuan ulang, replay create/edit/submit/cancel, payload berbeda, versi lama, role/akun terkini, pemilik, akses per objek dan PO terminal. Kegagalan audit membatalkan snapshot/status. Versi, nomor revisi, total dan nilai baris diperiksa terhadap batas int64. Pengujian HTTP memeriksa CSRF, escaping, pengabaian parameter pemilik/status/total, form invalid, dan redaksi token pada exception report. Pengajuan serentak memakai TransactionTestCase dan dua koneksi SQLite berbasis file.

Browser memakai `var/request-browser-check`. Alur: simpan draft kosong, submit ditolak 400, lengkapi dua item, tambah baris tanpa menyimpan dan tanpa kehilangan input, simpan, ajukan, baca snapshot revisi 1, lalu batalkan dengan alasan. Dua baris masing-masing 0.5 × IDR 0.01 menghasilkan IDR 0,01 per baris dan total IDR 0,02. Database akhirnya memuat satu permintaan CANCELLED, satu revisi dengan dua item, serta empat audit dan empat receipt aksi. Akun pemohon lain tidak melihat permintaan pada daftar dan mendapat 404 saat membuka URL detailnya.

Form dua item tidak melampaui viewport 390/768/1440; keyboard Tab mencapai kontrol Hapus dengan outline terlihat. Screenshot mobile diperiksa. Pemeriksaan ini memakai HTML fungsional, belum audit aksesibilitas atau UI final. Respons 400 dan 404 merupakan skenario yang sengaja diuji; tidak ada JavaScript aplikasi pada form ini. Server dihentikan setelah pemeriksaan dan data sintetis tidak masuk database kerja.

Review kode tidak menemukan masalah Critical/Important. Saran minor: memperketat management counts formset agar nilai negatif atau urutan initial/total yang rusak ditolak eksplisit. Perilaku bawaan saat ini dapat memperlakukan total negatif sebagai nol baris; pemilik memang diizinkan menyimpan draft kosong, sehingga ini bukan perubahan hak akses. Penguatan beserta regresi penolakan tanpa mutasi dijadwalkan pada pemeriksaan form tugas 10.

## Approval dan pengembalian untuk revisi

Sebelum implementasi, 23 test baru gagal karena service dan endpoint belum tersedia. Setelah implementasi, seluruh 131 test lulus. Pengujian service mencakup tiga keputusan, alasan, snapshot aktif, larangan self-review setelah pergantian role/superuser, akun nonaktif, role terkini sebelum replay, payload berbeda, versi lama, keputusan berulang, batas versi serta rollback keputusan/status/audit/receipt. Return procurement memerlukan persetujuan revisi aktif, alasan dan belum adanya PO, termasuk PO terminal. Kandidat dibersihkan dan snapshot/keputusan/penawaran lama tetap ada setelah submit ulang.

Pengujian HTTP mencakup antrean yang tidak menampilkan permintaan sendiri, paginasi 25 baris, POST-only, input aman dipertahankan saat invalid, parameter aktor/status diabaikan, CSRF, token aktor lain, konflik versi, escaping alasan, SQLite busy 503 dan error database yang tidak dikenal tetap diteruskan. Redaksi parameter POST token/CSRF diperiksa pada exception report non-debug; variabel lokal helper ditandai sensitif dan diperiksa melalui kode, belum melalui exception runtime khusus jalur approval.

TransactionTestCase memakai dua koneksi SQLite berbasis file. Dua approver dengan nonce berbeda menghasilkan satu sukses dan satu konflik; pengiriman ulang nonce/payload sama oleh aktor sama menghasilkan dua respons sukses dengan satu keputusan dan satu audit.

Browser memakai `var/approval-browser-check`: antrean menampilkan dua permintaan pengguna lain dan menyembunyikan permintaan milik approver. Minta revisi tanpa alasan ditolak 400; pilihan tetap tersimpan. Sesudah alasan diisi, pemohon mengedit lalu submit revisi 2. Approver menyetujui revisi 2 dan menolak permintaan lain. Procurement kemudian mengembalikan permintaan APPROVED untuk revisi dengan alasan. Snapshot revisi 1 tetap memuat judul awal dan keputusan REQUEST_CHANGES; revisi 2 memuat judul baru dan keputusan APPROVE, keduanya tanpa kontrol edit.

Form keputusan tidak melampaui viewport 390/768/1440. Tab mencapai tombol Simpan keputusan dengan outline terlihat; screenshot mobile diperiksa. Data akhir: tiga request, empat revisi, tiga keputusan, dua belas audit dan dua belas receipt aksi, termasuk enam aksi persiapan data. Satu request CHANGES_REQUESTED, satu REJECTED dan satu milik approver tetap SUBMITTED. Ini belum UI final atau audit aksesibilitas menyeluruh. Respons 400 dan favicon 404 tercatat; form tidak memuat JavaScript aplikasi. Server dihentikan setelah pemeriksaan; akun sintetis tidak masuk database kerja.

Review kode independen tidak menemukan defect pada perubahan tahap ini. Reviewer menilai kode dan log suite, tanpa menjalankan suite atau mengakses database. Validasi browser dilakukan terpisah. Tidak ada migrasi, dependensi, diagram atau workbook yang berubah.

## Vendor, penawaran dan pemilihan

Pengujian awal memuat 26 test yang gagal karena modul sourcing belum tersedia. Regresi tambahan menangkap replay HTTP yang tertolak setelah vendor dinonaktifkan: validasi status aktif kini berada di service sesudah pencarian receipt. Aksi baru tetap menolak vendor nonaktif. Regresi lain menangkap label dua penawaran yang sama nama vendor/referensinya; label pilihan kini memuat total, waktu pemenuhan dan masa berlaku. Suite akhir lulus 159 test, termasuk 28 test baru.

Vendor diuji untuk procurement/admin, penolakan peran lain/superuser, field wajib, status boolean, versi, replay dan rollback. Penawaran diuji terhadap exact item set, duplikat/ID tak sesuai, harga/presisi/overflow, tanggal, hari pemenuhan, vendor aktif, revisi/status/PO, peran sebelum replay dan total server. Pemilihan menguji tanggal berlaku, plafon, total yang tidak konsisten, alasan, beberapa penawaran vendor sama, alternatif tidak layak, dan pemilihan selain harga terendah. Edit kandidat membersihkan pilihan; penawaran revisi lama tetap tersimpan namun terkunci.

HTTP memeriksa form invalid, management counts negatif/nol, CSRF, parameter jumlah/total yang diabaikan, token aktor lain, versi lama, peran, escaping kontak, replay dan redaksi parameter POST token/CSRF. Helper form bertanda variabel sensitif diperiksa melalui kode; jalur exception runtime belum diperiksa menyeluruh. Dua koneksi SQLite berbasis file membuktikan hanya satu penawaran dibuat pada versi yang sama; nonce sama menghasilkan replay tanpa duplikasi.

Browser memakai `var/sourcing-browser-check`. Procurement membuat vendor dan penawaran IDR 80,00; pemilihan tanpa alasan sumber tunggal ditolak 400 lalu berhasil sesudah diisi. Edit harga menjadi IDR 70,00 menghapus pilihan sebelumnya. Vendor kedua mempunyai penawaran IDR 60,00 dengan waktu lima hari; procurement tetap dapat memilih IDR 70,00 dengan alasan pemenuhan dua hari. Sesudah vendor alternatif dinonaktifkan, pemilihan ulang kembali mewajibkan alasan sumber tunggal. Pemohon pemilik dapat membaca perbandingan tanpa form/tombol mutasi.

Form penawaran dan perbandingan tidak melampaui viewport 390/768/1440. Tab mencapai tautan dengan outline terlihat; screenshot mobile diperiksa. Label final menampilkan harga, estimasi hari dan tanggal berlaku. Database akhir memuat dua vendor (satu nonaktif), dua penawaran, satu pilihan aktif, dua belas audit dan dua belas receipt termasuk tiga aksi persiapan request/approval. Tidak ada PO. Akun sintetis tidak masuk database kerja; server dihentikan setelah pemeriksaan. Respons 400 dan favicon 404 merupakan skenario yang diketahui. Ini belum UI final atau audit aksesibilitas seluruh aplikasi.

Review independen menilai kode dan log 158 test sebelum perbaikan label, tanpa eksekusi suite/DB. Label diperbaiki melalui RED ke GREEN dan diverifikasi suite akhir 159 test. Dua catatan minor ditunda ke tugas 10: bangun comparison rows setelah paginasi queryset; muat snapshot item sekali saat mengevaluasi seluruh kandidat agar query berulang dalam transaksi berkurang. Kapasitas produksi belum diukur. Tidak ada perubahan migration, dependency, diagram atau workbook.
