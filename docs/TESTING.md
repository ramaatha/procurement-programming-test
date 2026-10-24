# Pengujian Procurement

Diperbarui: 23 Oktober 2026

## Ringkasan Status Terkini

Ringkasan per 23 Oktober 2026 memakai hasil pengujian ulang pada tindak lanjut Tahap 11. Angka dan keterbatasan pada rekam tahap lama tetap berlaku pada tahap masing-masing.

- **Regresi otomatis terbaru: 245 test lulus dalam 30,720 detik** pada salinan sumber terkini memakai interpreter proyek dan database tes terisolasi, termasuk concurrency SQLite berbasis file. Run ini tidak membuat virtualenv baru; bukti virtualenv bersih tetap berada pada rekam Tahap 11. Tujuh test seed dan lima test tindak lanjut melengkapi baseline 233 test sebelum Tahap 11. Subtest input/peran tidak dihitung sebagai method test tambahan.
- **Setup bersih dan data demo tersedia serta telah diuji secara terisolasi.** Salinan sumber tanpa virtualenv/database/rahasia kerja menjalani instalasi requirements dari wheel cache, migrasi, `seed_demo` dua kali dan pemeriksaan Django. Bootstrap memakai executable Python 3.12 langsung karena launcher Windows Store tidak tersedia. [README](../README.md) memuat setup dan [Panduan Pengguna](USER_GUIDE.md) memuat lima peran, contoh serta langkah transaksi. Ini bukan pemeriksaan instalasi pada seluruh mesin atau unduhan requirements dari jaringan.
- **Regresi browser terbaru: tiga suite lulus dengan 54 pemeriksaan terkelompok**: akun/vendor/sesi 15, filter/paginasi 5, dan transaksi/keadaan gagal 34. Satu pemeriksaan transaksi memuat 24 pemeriksaan lebar halaman; angka 54 bukan jumlah alur bisnis atau persentase coverage. Rincian assertion dan batas ada pada tindak lanjut di bawah. Angka historis 175 kombinasi halaman/peran dan 1.050 ukuran viewport juga bukan jumlah alur bisnis.
- **Lokasi pesan bukan cakupan penuh validasi bisnis.** Pemeriksaan 17 endpoint form/aksi mengirim POST kosong untuk memeriksa respons 400 dan penempatan error di dalam form. Pemeriksaan ini tidak membuktikan seluruh validasi field, token yang valid, cabang transaksi atau perubahan data pada 17 endpoint tersebut; bukti itu berasal dari pengujian service/HTTP dan interaksi browser yang disebutkan secara terpisah.
- **Hasil tetap lokal.** Pemeriksaan non-debug menghasilkan warning `security.W004` karena HSTS belum ditetapkan. Hosting, HTTPS nyata, perangkat fisik, pembaca layar, beban produksi serta penerimaan vendor nyata belum diverifikasi. Tidak ada klaim deployment atau kesiapan produksi.

## Tindak Lanjut Tahap 11: Regresi Browser Dan Status Historis

Pengujian ulang memakai Chrome headless melalui Playwright yang sudah terpasang. Runner menyalin sumber lokal terkini ke folder baru di luar repository, membuat password/secret sintetis acak, menjalankan migrasi serta seed pada database baru, lalu menyalakan server loopback dengan port sementara. Server milik runner dihentikan pada akhir run. Database kerja dan server pengguna tidak dipakai.

Run final: `procurement-browser-20261023-233221-dc8fda` di `C:/Users/Rama Atha/.codex/tmp/`. Bukti memuat `source-hashes.json`, log migrasi/seed/fixture/server, `summary.json`, JSON per suite, screenshot dan PDF PO. Path ini adalah artefak lokal mesin pemeriksaan, bukan berkas repository atau bukti hosting.

| Suite                       | Hasil                        | Bukti Yang Diperiksa                                                                                                                                                                                                                                                                                                 |
| --------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Akun, vendor, sesi          | 15 lulus                     | Login; Batal/Konfirmasi logout; login peran lain pada context sama; akun nonaktif dan penolakan login; aktivasi kembali; perubahan peran pada sesi berjalan; reset mencabut sesi lama, password lama gagal dan password baru berhasil; self-reset admin mengakhiri sesi; create/edit/nonaktif vendor dengan readback |
| Filter dan paginasi         | 5 lulus                      | Filter q/jenis/tahap request dan PO; 26 dokumen unik terbagi 25+1; berikut/sebelumnya menjaga query; Hapus Filter mereset URL/kontrol; pencarian nomor PO/PR; paginator aktif/historis saling menjaga page/history_page                                                                                              |
| Transaksi dan keadaan gagal | 34 lulus                     | Lima contoh awal; total/snapshot; revisi Procurement; dua jenis bukti jasa; pembatalan/penutupan; sembilan kelompok keadaan gagal panduan; konflik tab; alur lengkap tanpa JavaScript; cetak dan lebar halaman                                                                                                       |
| Django                      | 245 test lulus, 30,720 detik | Suite penuh termasuk concurrency SQLite; exit 0                                                                                                                                                                                                                                                                      |
| Pemeriksaan sumber          | Lulus                        | Django check, konsistensi migrasi, sintaks harness, Prettier check dan Git diff check                                                                                                                                                                                                                                |

Semua suite browser selesai tanpa `pageerror` yang tercatat. Pemeriksaan lebar berjumlah 24 pada empat keadaan halaman, masing-masing 320/390/640/768/1024/1440 piksel. Hasil ini berlaku untuk sampel tersebut; pemindaian viewport yang lebih luas pada tahap lama tetap merupakan bukti terpisah.

### Assertion Transaksi Yang Ditambahkan

- G-01/J-01/G-02/G-03/J-02 dibuka dari daftar melalui pencarian. Status diperiksa; G-03 mengikat label Dipesan/Diterima/Ditolak/Sisa ke nilai 10/6/2/4. Detail penerimaan J-02 memuat jenis bukti dan periode jasa.
- Permintaan barang baru menampilkan estimasi IDR 1.000.000,00. Setelah disetujui dan dipilih penawarannya, Procurement meminta revisi: pilihan vendor beserta kedua alasan dikosongkan, revisi/keputusan lama tetap ada. Pemohon mengedit lokasi, mengajukan revisi kedua dan memperoleh persetujuan kembali.
- PO baru menampilkan IDR 900.000,00 beserta vendor, item, tujuan, alasan pemilihan dan sumber tunggal. Pengamat read-only memeriksa nilai tersimpan. Penerimaan 6/ditolak 2 lalu diterima 4 menghasilkan lengkap, sementara riwayat penolakan 2 tetap ada.
- Dua permintaan jasa terpisah diselesaikan dengan `SERVICE_REPORT` dan `SERVICE_ACCEPTANCE`. Jenis bukti, referensi/catatan dan label periode dibaca dari detail; tanggal awal/akhir hari WIB, total IDR 180.000,00 dan status lengkap diperiksa pada data tersimpan.
- Pembatalan permintaan sebelum PO disimpan dengan alasan. Penutupan PO tanpa accepted menghasilkan CANCELLED; accepted sebagian menghasilkan CLOSED_SHORT dengan sisa historis 4. Pada kedua status terminal, POST form penerimaan lama dan penutupan kedua menghasilkan 409 tanpa mutasi; GET penerimaan baru juga 409.
- Context tanpa JavaScript menjalankan draft, pengajuan, persetujuan, penawaran/pilihan, penerbitan PO sampai penerimaan lengkap. Bukti cetak baru berupa PDF A4 untuk PO barang satu item; cetak 40 item/lima halaman merupakan bukti Tahap 11 sebelumnya, tidak dijalankan ulang pada tindak lanjut ini.

### Keadaan Gagal Pada Panduan Pengguna

| Percobaan Panduan                         | Bukti Browser Terbaru                                                                                                |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Password salah                            | HTTP 400; satu error di form; password dari server kosong; alert tidak menerima focus otomatis                       |
| Pengajuan tanpa header wajib              | HTTP 400 dengan alasan kebutuhan belum diisi; tidak menambah revisi atau perubahan bisnis                            |
| Jumlah negatif / harga invalid            | Dua POST edit terpisah menghasilkan 400 dan pesan angka; draft/item tetap sama                                       |
| Revisi / penolakan tanpa alasan           | Kedua keputusan menghasilkan 400 dan pesan alasan wajib; keputusan belum tersimpan                                   |
| Ditolak lebih dari nol tanpa alasan       | HTTP 400; belum ada penerimaan final atau perubahan PO                                                               |
| Periode jasa kosong / masa depan          | Keduanya ditolak untuk masing-masing jenis bukti jasa; tidak menambah penerimaan                                     |
| Admin membuka pembuatan permintaan        | HTTP 403                                                                                                             |
| Pemohon membuka detail milik pemohon lain | HTTP 404; tidak memuat dokumen atau mengubah data                                                                    |
| Form lama setelah dokumen berubah         | Dua tab mengedit draft: A berhasil, B mendapat 409; judul A tetap tersimpan. Form PO lama sesudah penutupan juga 409 |

Setiap penolakan bisnis di atas memakai token dari form nyata. Harness membandingkan state sebelum/sesudah melalui SQLite `mode=ro` dan `PRAGMA query_only`: request, item, revisi, keputusan, penawaran beserta itemnya, PO, penerimaan beserta itemnya, dan audit dokumen terkait. Pemeriksaan ini menambah bukti perilaku; tidak mengubah arti pengujian 17 POST kosong yang hanya memeriksa lokasi error.

Dataset paginasi dibuat langsung lewat model pada database sintetis: 26 PR/PO, 26 penawaran aktif dan 26 historis, serta satu permintaan pemilik lain. Dataset ini hanya fixture untuk navigasi/izin baca, bukan bukti lifecycle UI atau integritas service pembuatan transaksi. Lifecycle barang/jasa pada suite transaksi dibuat melalui form browser.

Review independen menemukan query penawaran pada observer belum mengikuti revision_id dan dua assertion/instrumentasi yang perlu diperketat. Ketiganya diperbaiki, lalu seluruh runner dijalankan ulang pada database baru. Percobaan awal harness yang gagal karena ekspektasi status, label/terjemahan, runtime browser atau selector tidak dihitung sebagai hasil lulus. Tidak diperlukan perubahan kode bisnis untuk tindak lanjut ini.

### Mengulangi Regresi Browser

Sumber pengujian berada pada `scripts/browser/`: `run.py`, `accounts.cjs`, `pagination.cjs`, `pagination_fixture.py`, `business.cjs` dan `observe.py`. Runner membutuhkan Python environment proyek, Git, Node dan Playwright/Chrome yang sudah tersedia. Runner tidak memasang paket, melakukan Git writes, atau menjalankan migrasi pada database kerja.

Pada mesin pemeriksaan, runtime Playwright tersedia di bawah `LOCALAPPDATA/CodexTools/playwright-mcp/0.0.83/node_modules/playwright`. Contoh berikut memakai runtime tersebut; sesuaikan `PLAYWRIGHT_MODULE` bila lokasi/versi runtime terpasang berbeda.

```powershell
$python = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$env:PLAYWRIGHT_MODULE = Join-Path $env:LOCALAPPDATA 'CodexTools/playwright-mcp/0.0.83/node_modules/playwright'
& $python scripts/browser/run.py
if ($LASTEXITCODE -ne 0) { throw 'Regresi browser gagal; periksa log pada folder bukti.' }
```

`E2E_NODE` dapat menunjuk executable Node bila tidak ada di PATH. `E2E_SCRATCH_ROOT` dapat memilih induk folder bukti di luar repository; defaultnya `~/.codex/tmp`. Password/secret dibuat dalam memori dan tidak dicetak. JSON fixture dan bukti tersimpan di folder unik yang dicetak runner. Salinan database berisi akun sintetis dan hash password, sehingga tetap merupakan artefak uji lokal.

Bila menjalankan suite sendiri tanpa runner, sediakan origin loopback HTTP dengan port eksplisit, password sintetis, output di luar source, `E2E_ALLOW_MUTATIONS=isolated-synthetic` dan database dengan marker `.e2e-isolated`. Marker adalah guard pengujian, bukan bukti bahwa server yang dipilih memakai database tersebut; gunakan runner untuk menjaga pasangan server/database. `business.cjs` juga membutuhkan interpreter, observer serta path permintaan fixture milik user lain.

### Batas Yang Tetap Belum Terverifikasi

- Launcher `py`, dialog interaktif `createsuperuser`, serta rangkaian `Read-Host -AsSecureString`/pembersihan environment pada README belum dijalankan ulang secara literal. Runner memakai interpreter langsung dan environment sintetis; keberhasilan runner tidak menggantikan bukti langkah interaktif itu.
- Browser bersih tidak menguji Google Password Manager atau kredensial tersimpan pengguna. Perangkat fisik, pembaca layar, mesin/OS lain dan browser selain Chrome belum diuji.
- Tidak ada angka line/branch coverage dan tidak ada klaim seluruh kemungkinan input sudah diperiksa.
- Tindak lanjut ini bukan audit advisory dependency terbaru atau full security scan baru. Hasil audit sumber terdahulu tetap terbatas pada scope/bukti saat itu. Rate limiting login belum tersedia di aplikasi; risiko saat diekspos ke jaringan perlu ditangani pada persiapan deployment.
- Hosting publik, HTTPS/proxy nyata, HSTS, backup/restore, beban produksi dan interaksi vendor nyata tetap belum dibuktikan. Warning HSTS historis tidak ditandai selesai oleh pengujian browser lokal.

## Rekam Verifikasi Per Tahap

Bagian berikut mempertahankan hasil, jumlah test dan batas pada waktu masing-masing tahap. Pernyataan "belum" pada tahap lama bukan status produk terkini; gunakan ringkasan dan tindak lanjut terbaru di atas untuk status terakhir. Tanggal tiap run lama tidak dicatat terpisah, sehingga penanda tahap dipakai tanpa menebak tanggal.

### Lingkup Yang Telah Diverifikasi Sebelum Tahap 11

Pada ringkasan sebelum Tahap 11, verifikasi lokal mencakup akun, autentikasi, konfigurasi, model dan migrasi SQLite, angka berskala, protokol aksi, permintaan, approval, sourcing, PO, penerimaan barang/jasa, penutupan, tracking dan audit. Antarmuka diperiksa pada lima peran dalam browser. Instalasi dari checkout bersih dan data demo belum selesai; hasil ini tidak menyatakan deployment atau kesiapan produksi.

Lingkungan pemeriksaan: Python 3.12.14, Django 5.2.18, SQLite 3.53.1, dan JSON1 tersedia. Dependensi terpasang: asgiref 3.12.1, sqlparse 0.6.0, dan tzdata 2026.5. `pip check` tidak menemukan dependensi yang rusak.

### Pengujian Otomatis: Baseline 233 Test Sebelum Tahap 11

| Kelompok                        | Jumlah test | Perilaku yang diperiksa                                                                                                                                                                              |
| ------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Autentikasi                     | 11          | Login/logout, akun nonaktif, kredensial salah, password tidak dipantulkan, CSRF, logout POST, redirect aman, pencabutan akses setelah nonaktif, route yang tidak disediakan, dan pesan login tunggal |
| Peran dan guard                 | 6           | Lima peran dapat login, manipulasi role pada form tidak mengubah akun, peran invalid dan versi nol ditolak database, peran terkini dibaca kembali, dan halaman akun tidak menerima POST              |
| Konfigurasi                     | 7           | Secret hilang/pendek, nilai DEBUG invalid, hostname produksi hilang/wildcard, Secure cookie dan HTTPS pada mode non-debug, serta database test terpisah                                              |
| Angka berskala                  | 5           | Parsing ketat, batas int64, penolakan input ambigu, formatter kanonik, pembulatan half-up per baris, dan overflow hasil/jumlah                                                                       |
| Constraint pengadaan            | 10          | Header draft, nilai/status valid, keunikan revisi/keputusan/PO/item, kelengkapan metadata penutupan, periode bukti, parent yang tidak ada, dan FK historis                                           |
| Token dan payload               | 3           | Scope tepat, tanda tangan, TTL 24 jam, hash kanonik, urutan baris, serta penolakan field sensitif/float                                                                                              |
| Transaksi aksi                  | 7           | Replay sebelum pemeriksaan versi, konflik nonce/payload/scope, nonce sekali untuk password, resolver allowlist, kewajiban atomic, serta rollback dokumen/audit/hasil aksi                            |
| Service akun                    | 17          | Pembuatan/edit/reset, validasi username/role/password, admin terakhir, otorisasi terkini, nonce sekali, versi, batas int64 dan rollback                                                              |
| HTTP dan perlindungan form akun | 14          | Izin empat peran, CSRF, parameter privilege, token lintas aktor/target, 400/409/503, sesi dicabut, dan redaksi token/password pada exception report                                                  |
| Dua penulis akun                | 1           | Dua admin menurunkan peran sendiri secara bersamaan; tepat satu perubahan berhasil dan satu admin aktif tetap tersedia                                                                               |
| Service permintaan              | 15          | Draft tidak lengkap, validasi item/tanggal, pembulatan, snapshot/revisi, replay, versi, izin terkini, pembatalan, guard PO, overflow dan rollback                                                    |
| HTTP permintaan                 | 12          | Formset, tambah/hapus baris, data server-only, CSRF, akses objek, token lintas aktor, stale form, escaping dan redaksi exception report                                                              |
| Dua penulis permintaan          | 1           | Dua submit bersamaan dengan nonce sama atau berbeda menghasilkan tepat satu snapshot                                                                                                                 |
| Service approval                | 13          | Setuju/revisi/tolak, alasan, self-review, role terkini, replay, status/versi/snapshot, rollback, return procurement dan overflow                                                                     |
| HTTP approval                   | 9           | Antrean, paginasi, form keputusan, akses/CSRF/token, konflik, escaping, busy 503 dan redaksi POST pada exception report                                                                              |
| Dua reviewer                    | 1           | Dua keputusan bersamaan menghasilkan satu keputusan/audit; replay nonce sama tidak menggandakan hasil                                                                                                |
| Vendor                          | 6           | Create/edit/nonaktif, izin terkini, validasi, replay/versi, rollback, CSRF dan form                                                                                                                  |
| Penawaran dan pemilihan         | 21          | Item/harga/tanggal/total, status/izin/PO, sumber tunggal, revisi, pilihan, rollback, HTTP/token/CSRF, label dan replay setelah vendor nonaktif                                                       |
| Dua penulis penawaran           | 1           | Dua penawaran bersamaan memakai versi request; nonce sama replay, nonce berbeda konflik                                                                                                              |
| Service PO                      | 11          | Snapshot header/item, replay, izin terkini, status/revisi/kandidat, vendor/tanggal/plafon/sumber, rollback, terminal dan overflow                                                                    |
| HTTP PO                         | 6           | POST-only, parameter server, scope daftar/detail/cetak, snapshot setelah rename, CSRF/token/versi, 503 dan redaksi POST                                                                              |
| Race PO dan harness             | 4           | Dua issue, cancel vs issue, vendor nonaktif vs issue, dan penghentian proses yang macet                                                                                                              |
| Penerimaan dan penutupan        | 25          | Barang/jasa, multi-item, accepted/rejected/remaining, periode, terminal, replay, rollback, HTTP dan dua koneksi SQLite                                                                               |
| Tracking                        | 16          | Scope, pencarian/filter, tahap operasional, paginasi, label status, balance dan riwayat                                                                                                              |
| Antarmuka dan kegagalan         | 6           | Error field dalam form, input dipertahankan, 404/CSRF/500 aman, navigasi per peran, antrean approver dan management form negatif                                                                     |
| Navigasi dan logout             | 3           | Kapitalisasi, konfirmasi tanpa mengakhiri sesi, login wajib dan logout POST                                                                                                                          |
| Lokasi validasi form            | 2           | Lokasi error pada POST kosong ke 17 endpoint form/aksi dan dua filter invalid, pesan tunggal admin terakhir, serta akun tetap terlindungi                                                            |

Total historis sebelum Tahap 11: **233 test lulus** pada regresi revisi validasi/kapitalisasi antarmuka. Total terbaru yang dicatat adalah 245 test pada Tahap 11. Subtest beberapa input/peran tidak dihitung sebagai method test tambahan.

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

### Migrasi dan konsistensi schema

Database terisolasi `var/schema-migration-check` dipakai untuk migrasi dari kosong, rollback hanya app Procurement, lalu penerapan ulang. Empat belas tabel Procurement terbentuk kembali. Fixture barang dan jasa tersimpan dengan angka yang sesuai; pemeriksaan foreign key tidak menemukan pelanggaran dan `PRAGMA integrity_check` menghasilkan `ok`. Database kerja tidak dipakai untuk rollback ini.

Pengujian tahap schema terlebih dahulu gagal karena parser, model, dan protokol aksi belum tersedia. Setelah implementasi, seluruh suite lulus. Database hanya menjaga hubungan yang ada, keunikan dan kondisi dalam satu baris. Item yang ada tetapi milik request/PO lain tetap memerlukan pemeriksaan service.

### Pemeriksaan browser

Server dijalankan pada loopback dengan database sintetis terpisah di var/browser-smoke. Akun pemeriksaan tidak dibuat dalam database kerja.

- Login menghasilkan halaman akun dengan username dan peran Pemohon.
- Logout kembali ke login; membuka halaman akun setelahnya diarahkan ke login.
- Kredensial salah menampilkan pesan yang dapat dibaca; username dipertahankan dan password dikosongkan.
- Tab berpindah dari username ke password lalu tombol Masuk; focus terlihat.
- Pada viewport 1280 piksel, lebar konten tidak melampaui viewport pada halaman akun maupun login.
- Bootstrap admin melalui command line berhasil pada database terisolasi.

Bukti tampilan dan log berada pada tmp dan diabaikan Git. Server pemeriksaan dihentikan setelah alur selesai.

### Pengelolaan akun

Service membaca ulang admin aktif sebelum memeriksa replay, lalu memvalidasi input dan versi dalam transaksi IMMEDIATE. Akun, AuditEvent dan ActionReceipt rollback bersama jika salah satu penulisan gagal. Create/reset memakai nonce sekali dan payload hash kosong; metadata edit dapat direplay dengan payload sama. Admin aktif terakhir tidak dapat dinonaktifkan atau diturunkan perannya.

Pengujian batas versi menemukan overflow integer sebelum guard ditambahkan; regresinya kini lulus. Pengujian exception report juga terlebih dahulu membuktikan token belum tersamarkan, lalu lulus setelah redaksi parameter POST dan variabel lokal form diterapkan pada mode non-debug.

Browser memakai database terpisah `var/account-browser-check`. Alur yang diperiksa: login admin, buat akun dengan password invalid/valid, ubah peran, nonaktif/aktifkan, reset password, logout, login akun hasil reset, dan penolakan akses `/users/` untuk penerima. Input aman dipertahankan saat 400 dan password dikosongkan. Lima perubahan menghasilkan tepat lima audit dan lima receipt aksi.

Form edit tidak melampaui viewport 390/768/1440; Tab mencapai tautan daftar akun dengan focus terlihat. Ini pemeriksaan form fungsional, belum audit visual/aksesibilitas seluruh aplikasi. Console mencatat respons 400/403 yang sengaja diuji serta favicon 404; tidak ditemukan error JavaScript aplikasi. Server pemeriksaan dihentikan setelah selesai.

### Batas Verifikasi Pada Snapshot Tahap 7, Sebelum Tahap 8

Catatan historis ini merekam batas sebelum penerimaan/penutupan pada Tahap 8, antarmuka pada Tahap 10 serta setup/seed pada Tahap 11. Batas tersebut diperbarui pada rekam tahap berikutnya.

Pada snapshot ini, pengelolaan akun dan permintaan melalui UI/service sudah diuji, termasuk scope objek, replay, snapshot, rollback serta pengajuan serentak. Keputusan approval dan pengembalian ke CHANGES_REQUESTED sudah tersedia dan diuji melalui service serta browser. Sourcing sudah tersedia dan diuji. Penerbitan PO, snapshot dan persaingan cancel/issue sudah tersedia serta diuji. Factory PO memakai service penerbitan. Penerimaan dan penutupan PO belum diimplementasikan atau diuji.

Tampilan masih prototipe HTML fungsional. Form edit akun sudah diperiksa pada lebar 390/768/1440. Pemeriksaan aksesibilitas menyeluruh serta arah visual final menunggu tahap UI. Mode non-debug diperiksa melalui konfigurasi; hosting, reverse proxy, HTTPS nyata, dan kapasitas produksi belum diverifikasi.

Pembuatan virtual environment dan pemasangan requirements dilakukan dari lingkungan Python 3.12 yang tersedia. Launcher sistem pada mesin pemeriksaan belum mempunyai runtime Python 3.12 yang terdaftar; checkout lokal menggunakan interpreter pada .venv. Setup lintas mesin tetap mensyaratkan Python 3.12 tersedia.

Pada snapshot sebelum Tahap 11, data contoh lintas peran serta perjalanan pengadaan lengkap belum tersedia. FR-01 dan FR-13 baru diterapkan sebagian; status penerimaan keseluruhan kebutuhan tersebut belum dinaikkan menjadi selesai.

Regresi otomatis `account.create` dan `account.password` memakai opsi replay bawaan, memeriksa payload hash kosong dan penolakan digest nonkosong. Kedua service juga diuji saat nonce dikirim ulang dengan password atau metadata berbeda.

### Draft, pengajuan dan pembatalan permintaan

Pengujian awal gagal karena service dan route belum tersedia. Regresi tambah baris kemudian menangkap alert validasi yang tampil meskipun setiap form valid; template kini memeriksa jumlah error sebenarnya. Suite keseluruhan lulus 108 test, termasuk 28 test permintaan. Tidak ada perubahan migrasi atau dependensi.

Pengujian mencakup draft kosong, item lengkap/positif, tanggal hari WIB, angka kanonik dan pembulatan half-up per baris, snapshot lama setelah pengajuan ulang, replay create/edit/submit/cancel, payload berbeda, versi lama, role/akun terkini, pemilik, akses per objek dan PO terminal. Kegagalan audit membatalkan snapshot/status. Versi, nomor revisi, total dan nilai baris diperiksa terhadap batas int64. Pengujian HTTP memeriksa CSRF, escaping, pengabaian parameter pemilik/status/total, form invalid, dan redaksi token pada exception report. Pengajuan serentak memakai TransactionTestCase dan dua koneksi SQLite berbasis file.

Browser memakai `var/request-browser-check`. Alur: simpan draft kosong, submit ditolak 400, lengkapi dua item, tambah baris tanpa menyimpan dan tanpa kehilangan input, simpan, ajukan, baca snapshot revisi 1, lalu batalkan dengan alasan. Dua baris masing-masing 0.5 Ã— IDR 0.01 menghasilkan IDR 0,01 per baris dan total IDR 0,02. Database akhirnya memuat satu permintaan CANCELLED, satu revisi dengan dua item, serta empat audit dan empat receipt aksi. Akun pemohon lain tidak melihat permintaan pada daftar dan mendapat 404 saat membuka URL detailnya.

Form dua item tidak melampaui viewport 390/768/1440; keyboard Tab mencapai kontrol Hapus dengan outline terlihat. Screenshot mobile diperiksa. Pemeriksaan ini memakai HTML fungsional, belum audit aksesibilitas atau UI final. Respons 400 dan 404 merupakan skenario yang sengaja diuji; tidak ada JavaScript aplikasi pada form ini. Server dihentikan setelah pemeriksaan dan data sintetis tidak masuk database kerja.

Review kode tidak menemukan masalah Critical/Important. Saran minor: memperketat management counts formset agar nilai negatif atau urutan initial/total yang rusak ditolak eksplisit. Perilaku bawaan saat ini dapat memperlakukan total negatif sebagai nol baris; pemilik memang diizinkan menyimpan draft kosong, sehingga ini bukan perubahan hak akses. Penguatan beserta regresi penolakan tanpa mutasi dijadwalkan pada pemeriksaan form tugas 10.

### Approval dan pengembalian untuk revisi

Sebelum implementasi, 23 test baru gagal karena service dan endpoint belum tersedia. Setelah implementasi, seluruh 131 test lulus. Pengujian service mencakup tiga keputusan, alasan, snapshot aktif, larangan self-review setelah pergantian role/superuser, akun nonaktif, role terkini sebelum replay, payload berbeda, versi lama, keputusan berulang, batas versi serta rollback keputusan/status/audit/receipt. Return procurement memerlukan persetujuan revisi aktif, alasan dan belum adanya PO, termasuk PO terminal. Kandidat dibersihkan dan snapshot/keputusan/penawaran lama tetap ada setelah submit ulang.

Pengujian HTTP mencakup antrean yang tidak menampilkan permintaan sendiri, paginasi 25 baris, POST-only, input aman dipertahankan saat invalid, parameter aktor/status diabaikan, CSRF, token aktor lain, konflik versi, escaping alasan, SQLite busy 503 dan error database yang tidak dikenal tetap diteruskan. Redaksi parameter POST token/CSRF diperiksa pada exception report non-debug; variabel lokal helper ditandai sensitif dan diperiksa melalui kode, belum melalui exception runtime khusus jalur approval.

TransactionTestCase memakai dua koneksi SQLite berbasis file. Dua approver dengan nonce berbeda menghasilkan satu sukses dan satu konflik; pengiriman ulang nonce/payload sama oleh aktor sama menghasilkan dua respons sukses dengan satu keputusan dan satu audit.

Browser memakai `var/approval-browser-check`: antrean menampilkan dua permintaan pengguna lain dan menyembunyikan permintaan milik approver. Minta revisi tanpa alasan ditolak 400; pilihan tetap tersimpan. Sesudah alasan diisi, pemohon mengedit lalu submit revisi 2. Approver menyetujui revisi 2 dan menolak permintaan lain. Procurement kemudian mengembalikan permintaan APPROVED untuk revisi dengan alasan. Snapshot revisi 1 tetap memuat judul awal dan keputusan REQUEST_CHANGES; revisi 2 memuat judul baru dan keputusan APPROVE, keduanya tanpa kontrol edit.

Form keputusan tidak melampaui viewport 390/768/1440. Tab mencapai tombol Simpan keputusan dengan outline terlihat; screenshot mobile diperiksa. Data akhir: tiga request, empat revisi, tiga keputusan, dua belas audit dan dua belas receipt aksi, termasuk enam aksi persiapan data. Satu request CHANGES_REQUESTED, satu REJECTED dan satu milik approver tetap SUBMITTED. Ini belum UI final atau audit aksesibilitas menyeluruh. Respons 400 dan favicon 404 tercatat; form tidak memuat JavaScript aplikasi. Server dihentikan setelah pemeriksaan; akun sintetis tidak masuk database kerja.

Review kode independen tidak menemukan defect pada perubahan tahap ini. Reviewer menilai kode dan log suite, tanpa menjalankan suite atau mengakses database. Validasi browser dilakukan terpisah. Tidak ada migrasi, dependensi, diagram atau workbook yang berubah.

### Vendor, penawaran dan pemilihan

Pengujian awal memuat 26 test yang gagal karena modul sourcing belum tersedia. Regresi tambahan menangkap replay HTTP yang tertolak setelah vendor dinonaktifkan: validasi status aktif kini berada di service sesudah pencarian receipt. Aksi baru tetap menolak vendor nonaktif. Regresi lain menangkap label dua penawaran yang sama nama vendor/referensinya; label pilihan kini memuat total, waktu pemenuhan dan masa berlaku. Suite akhir lulus 159 test, termasuk 28 test baru.

Vendor diuji untuk procurement/admin, penolakan peran lain/superuser, field wajib, status boolean, versi, replay dan rollback. Penawaran diuji terhadap exact item set, duplikat/ID tak sesuai, harga/presisi/overflow, tanggal, hari pemenuhan, vendor aktif, revisi/status/PO, peran sebelum replay dan total server. Pemilihan menguji tanggal berlaku, plafon, total yang tidak konsisten, alasan, beberapa penawaran vendor sama, alternatif tidak layak, dan pemilihan selain harga terendah. Edit kandidat membersihkan pilihan; penawaran revisi lama tetap tersimpan namun terkunci.

HTTP memeriksa form invalid, management counts negatif/nol, CSRF, parameter jumlah/total yang diabaikan, token aktor lain, versi lama, peran, escaping kontak, replay dan redaksi parameter POST token/CSRF. Helper form bertanda variabel sensitif diperiksa melalui kode; jalur exception runtime belum diperiksa menyeluruh. Dua koneksi SQLite berbasis file membuktikan hanya satu penawaran dibuat pada versi yang sama; nonce sama menghasilkan replay tanpa duplikasi.

Browser memakai `var/sourcing-browser-check`. Procurement membuat vendor dan penawaran IDR 80,00; pemilihan tanpa alasan sumber tunggal ditolak 400 lalu berhasil sesudah diisi. Edit harga menjadi IDR 70,00 menghapus pilihan sebelumnya. Vendor kedua mempunyai penawaran IDR 60,00 dengan waktu lima hari; procurement tetap dapat memilih IDR 70,00 dengan alasan pemenuhan dua hari. Sesudah vendor alternatif dinonaktifkan, pemilihan ulang kembali mewajibkan alasan sumber tunggal. Pemohon pemilik dapat membaca perbandingan tanpa form/tombol mutasi.

Form penawaran dan perbandingan tidak melampaui viewport 390/768/1440. Tab mencapai tautan dengan outline terlihat; screenshot mobile diperiksa. Label final menampilkan harga, estimasi hari dan tanggal berlaku. Database akhir memuat dua vendor (satu nonaktif), dua penawaran, satu pilihan aktif, dua belas audit dan dua belas receipt termasuk tiga aksi persiapan request/approval. Tidak ada PO. Akun sintetis tidak masuk database kerja; server dihentikan setelah pemeriksaan. Respons 400 dan favicon 404 merupakan skenario yang diketahui. Ini belum UI final atau audit aksesibilitas seluruh aplikasi.

Review independen menilai kode dan log 158 test sebelum perbaikan label, tanpa eksekusi suite/DB. Label diperbaiki melalui RED ke GREEN dan diverifikasi suite akhir 159 test. Dua catatan minor ditunda ke tugas 10: bangun comparison rows setelah paginasi queryset; muat snapshot item sekali saat mengevaluasi seluruh kandidat agar query berulang dalam transaksi berkurang. Kapasitas produksi belum diukur. Tidak ada perubahan migration, dependency, diagram atau workbook.

### Penerbitan PO dan snapshot pesanan

Sebanyak 20 test awal gagal karena service/route penerbitan belum tersedia, kemudian lulus setelah implementasi. Review menemukan batas `ThreadPoolExecutor.map(timeout=15)` tidak membatasi shutdown/join jika worker macet. Regresi tambahan terlebih dahulu gagal; race workers kini berjalan di subprocess terpisah yang dapat diterminasi/dihentikan dengan join terbatas. Suite akhir lulus 180 test, termasuk 21 test PO baru. Tidak ada migrasi atau dependensi baru.

Service diuji untuk snapshot header/item/issuer, status request tetap APPROVED, PO ISSUED/version 1, kenaikan versi request, audit dan receipt. Replay mengembalikan PO yang sama setelah vendor nonaktif; perubahan payload/versi atau role/akun nonaktif ditolak. Validasi mengulang persetujuan revisi, kandidat/parent, alasan pemilihan/sumber tunggal, vendor aktif, tanggal berlaku, item/total/plafon dan batas versi. Kegagalan audit membatalkan PO/item, versi request dan receipt. Vendor yang diedit sesudah terbit tidak mengganti snapshot. PO terminal tetap menolak penerbitan kedua, revisi dan pembatalan request sebelum PO.

HTTP memeriksa input total/status/vendor/quotation yang diabaikan, POST-only, redirect 303, replay, scope pemohon/approver/procurement/admin/penerima, objek di luar scope 404, CSRF, token aktor lain, versi lama, busy 503 dan error database tidak dikenal. Nama vendor/kontak serta nama penerbit pada cetak tetap historis sesudah rename. Parameter POST token/CSRF diperiksa redaksinya pada exception report; helper bertanda variabel sensitif diperiksa melalui kode, belum melalui pengujian exception runtime menyeluruh.

Tiga skenario race memakai TransactionTestCase dan dua koneksi SQLite dalam subprocess: issue bersamaan dengan nonce berbeda menghasilkan satu sukses/satu konflik; nonce sama menghasilkan replay dengan satu PO; cancel melawan issue tidak dapat sama-sama berhasil; penonaktifan vendor selalu tersimpan dan issue hanya berhasil jika lebih dahulu tervalidasi. Barrier ditempatkan sebelum transaksi. Parent memakai deadline proses 15 detik dan terminate/kill dengan join terbatas. Regresi worker tidur lima detik dengan deadline 0,2 detik membuktikan penghentian sebelum batas empat detik, termasuk cleanup. Harness menolak database yang bukan file test terpisah. Ini pemeriksaan transaksi SQLite, bukan pengukuran kapasitas produksi.

Browser memakai `var/order-browser-check`: procurement menerbitkan PO IDR 80,00 dari revisi dengan plafon IDR 100,00. Detail menunjukkan satu item dan alasan pemilihan/sumber tunggal. Halaman cetak tidak memuat form dan tidak melampaui viewport 390/768/1440; keyboard focus terlihat pada tautan kembali, screenshot mobile diperiksa. Nama/kontak vendor lalu diubah dan vendor dinonaktifkan; cetak tetap menampilkan salinan awal. Permintaan masih Disetujui, menampilkan tautan PO dan tidak lagi menawarkan penerbitan/revisi. Penerima dapat melihat PO pada daftar.

Database akhir berisi satu PO ISSUED, satu item, request APPROVED dengan versi 6, delapan audit dan delapan receipt termasuk enam aksi persiapan serta satu edit vendor setelah penerbitan. Vendor saat ini nonaktif, tetapi snapshot PO tetap memuat nama/kontak awal. Akun sintetis tidak ada dalam database kerja; server dihentikan setelah pemeriksaan. Console hanya mencatat favicon 404. Halaman cetak dibuka di browser; dialog printer, hasil cetak fisik, pagination kertas dan ekspor PDF belum diverifikasi.

Review independen tidak menemukan defect penting pada jalur aplikasi berdasarkan kode dan log suite 179 test. Catatan batas join harness diselesaikan melalui RED ke GREEN dan suite akhir 180 test; tidak ada review putaran kedua. UI final, deployment, PostgreSQL dan performa produksi belum dinilai.

### Penerimaan barang/jasa dan penutupan PO

Tahap 8 menambahkan 25 test sehingga suite berisi 205 test. Tiga belas test service awal terlebih dahulu gagal karena fitur belum tersedia. Empat test HTTP gagal karena route dan konteks form belum tersedia. Dua test race terlebih dahulu gagal karena worker belum mengenali aksi penerimaan/penutupan, lalu lulus setelah integrasi. Pemeriksaan tambahan mencakup multi-item, CSRF, akses per objek, versi lama, respons sibuk, dan batas agregat penolakan.

Skenario barang ordered 10, accepted 6/rejected 2 menghasilkan sisa 4; accepted 4 berikutnya menghasilkan RECEIVED. Penolakan saja mempertahankan ISSUED. Nol seluruhnya, negatif, presisi berlebih, item asing/duplikat, accepted berlebih, alasan penolakan kosong, serta referensi/catatan kosong ditolak. PO dua item tetap PARTIALLY_RECEIVED setelah satu item selesai; baris kedua yang invalid membatalkan seluruh posting. Hanya setelah kedua item diterima penuh status menjadi RECEIVED.

Jasa memerlukan jenis bukti dan periode awal <= akhir <= hari konfirmasi WIB. Waktu konfirmasi berasal dari server. Unit mengikuti snapshot PO tanpa mutasi stok. Receipt tidak mempunyai route edit/hapus. Kegagalan audit membatalkan receipt, baris, versi/status PO, dan penanda replay. Penutupan juga rollback bila audit gagal.

Replay memakai payload yang dikanonisasi: angka 6 dan 6.000 menghasilkan receipt yang sama untuk nonce yang sama; perubahan payload konflik. Peran dan akun aktif diperiksa ulang sebelum replay. Approver yang menjadi pemohon melalui perubahan peran tetap tidak dapat menutup PO miliknya. Penutupan accepted nol menghasilkan CANCELLED; setelah partial menghasilkan CLOSED_SHORT dan tetap menyimpan sisa. PO terminal menolak posting baru.

Tes HTTP memeriksa redirect 303, input invalid tetap tersimpan, management form negatif, token invalid, GET pada aksi penutupan 405, objek pemohon lain 404, detail receipt bagi pemilik, CSRF dengan enforce_csrf_checks, konflik 409, serta database terkunci 503 dengan Retry-After. Detail PO menampilkan sisa dan riwayat penerimaan.

Dua koneksi SQLite dalam subprocess berdeadline membuktikan dua receipt accepted 6 pada ordered 10 dengan versi sama menghasilkan satu sukses/satu konflik. Nonce sama menghasilkan dua hasil sukses dengan hanya satu receipt. Close melawan receive pada versi sama tidak dapat keduanya berhasil. Tes membaca jumlah, versi, dan status yang tersimpan setelah worker berakhir.

Review independen menemukan total rejected historis dapat melampaui int64 walaupun setiap baris valid. Regresi memperlihatkan masalah tersebut; formatter agregat kini menerima total integer Python tanpa menambah batas bisnis pada riwayat. Dua rejection-only maksimum per baris tetap dapat ditampilkan pada detail PO dan form penerimaan. Tes ini lulus setelah perbaikan.

Pemeriksaan ini mencakup service dan respons HTML melalui test client. Interaksi browser, tampilan 390/768/1440, keyboard, dan keseluruhan UI Tahap 8 belum diuji di browser. Tidak ada migrasi, dependency, data produksi, atau pengiriman PO ke pihak luar. Penerapan visual mengikuti sistem desain pada tahap UI.

### Tracking, pencarian, filter dan audit

Tahap 9 menambahkan 16 test tracking. Pengujian awal menemukan delapan kegagalan dan satu error karena kontrak tahap/balance, filter dan konteks riwayat belum tersedia; dua pengujian perilaku lama tetap lulus. Fixture status terminal kemudian disesuaikan agar menyertakan metadata penutupan yang diwajibkan constraint. Hasil tes fitur lulus setelah implementasi.

Pencarian nomor/judul diuji bersama jenis dan tahap untuk barang/jasa. Daftar PO juga mencari nomor permintaan asal. Kind/stage yang tidak dikenal dan pencarian terlalu panjang menghasilkan 400 tanpa mengembalikan daftar luas. Input HTML dan pola mirip SQL diperlakukan sebagai teks; HTML form/riwayat tetap di-escape. Daftar permintaan dan PO berisi 26 objek diuji pada dua halaman yang tidak beririsan, dengan filter dipertahankan pada tautan. Halaman invalid mempunyai pemulihan yang dapat diprediksi.

Scope tetap membatasi pemohon ke objek miliknya. Penerima tidak dapat membaca permintaan pra-PO dan tetap dapat membaca PO terminal. GET tracking tidak menambah audit atau baris penerimaan. Login diperlukan dan daftar menolak POST. Semua tahap request pra-PO serta tahap PO diperiksa terhadap selector operasional.

PO ordered 10 dengan accepted 6/rejected 2 yang ditutup tetap mempunyai remaining 4. Detail permintaan dan PO sama-sama menampilkan Selesai dengan kekurangan tanpa label Diterima lengkap. Service penerimaan dan penutupan memakai selector balance yang sama dengan presentasi; suite sebelumnya tetap menguji multi-item, rollback, replay dan race.

Audit diuji kronologis dan berhalaman, memakai nama historis meskipun username kini berubah. Alasan berisi HTML tidak dieksekusi. Pemindaian tahap tiga request ber-PO memerlukan maksimal dua query; perhitungan balance juga maksimal dua query pada riwayat tiga receipt. Pemeriksaan ini membatasi pola query pada fixture, tanpa klaim kapasitas produksi.

Pemeriksaan browser, tampilan mobile, keyboard, dan layout final belum dilakukan pada tahap ini. Tidak ada migrasi atau dependency baru. Bukti server/HTTP tidak menggantikan pemeriksaan UI menyeluruh pada Tugas 10.

Suite akhir Tahap 9 lulus 221 test. Setelah ekstraksi formatter, regresi penuh menangkap import format_quantity yang masih diperlukan detail penerimaan; import dipulihkan dan seluruh suite diulang hingga lulus. Pemeriksaan migrasi tidak mendeteksi perubahan. Review independen tidak menemukan cacat P0-P2 berdasarkan source/diff. Dua penyempurnaan P3 dicatat untuk Tugas 10: prefetch item agar pembacaan snapshot/balance tidak berulang, dan penyelarasan label status PO pada snapshot/cetak dengan tahap operasional. Pembacaan item saat ini merupakan overhead tetap, bukan query tambahan per item. Reviewer tidak menjalankan suite database atau browser.

### Antarmuka per peran dan pemulihan

Tahap 10 menambahkan enam test, sehingga regresi penuh lulus 227 test. Regresi terakhir setelah pemformatan template selesai dalam 33,704 detik. System check tidak menemukan isu; makemigrations --check --dry-run tidak mendeteksi perubahan. Pemeriksaan sintaks JavaScript melalui node --check juga lulus. Tidak ada migrasi atau paket runtime baru; dua paket Node hanya menjadi dependensi development untuk formatter.

Pengujian awal menangkap tidak adanya kerangka antarmuka/error summary serta penolakan management form negatif. Regresi management form gagal dengan respons 303 sebelum guard ditambahkan; sesudah perbaikan, respons menjadi 400 dan item draft tetap tersimpan. Test tambahan memastikan antrean approver tidak menawarkan permintaan miliknya serta exception tak terduga menghasilkan 500 yang aman dalam mode non-debug. Token, pesan internal dan traceback tidak muncul dalam body respons. Test 400/403/404 baru melengkapi pengujian 409/503, Retry-After, CSRF, POST-only, replay dan rollback pada modul sebelumnya.

Browser memakai database sintetis terpisah di var/stage10-browser. Pemohon, approver, procurement, penerima dan admin diperiksa pada lebar 320, 390, 640, 768, 1024 dan 1440px. Pemindaian terakhir memuat 85 kombinasi halaman/peran: 13 pemohon, 13 approver, 16 procurement, 7 penerima dan 36 admin. Semua respons GET yang diperiksa berhasil; tidak ditemukan overflow halaman atau exception JavaScript pada pemindaian itu. Ini adalah jumlah halaman yang dapat ditemukan dari navigasi/data uji saat pemeriksaan, bukan seluruh kemungkinan data atau cabang transaksi.

| Kontrol/alur browser                | Hasil aktual                                                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Login dan navigasi lima peran       | Login berhasil; tujuan menu dan tautan dokumen yang ditemukan memberi respons 200.                                        |
| Menu mobile                         | Dapat dibuka; Escape menutup dan mengembalikan focus ke summary.                                                          |
| Menu tanpa JavaScript lalu resize   | Regresi terlebih dahulu gagal ketika tombol pembuka hilang pada desktop; sesudah perbaikan summary native tetap tersedia. |
| Draft dengan jumlah negatif         | Respons 400 mempertahankan input; focus menuju ringkasan error yang menautkan field.                                      |
| Simpan draft                        | Input valid menghasilkan redirect ke detail dan pesan sukses.                                                             |
| Tambah/hapus baris tanpa JavaScript | Dua fieldset dirender; baris ekstra kosong yang dicentang Hapus tidak ikut disimpan.                                      |
| Approval                            | Pengajuan pengguna lain dapat disetujui dari form keputusan.                                                              |
| Penawaran, pemilihan dan PO         | Penawaran dibuat, dipilih dengan alasan sumber tunggal, lalu PO diterbitkan melalui kontrol halaman.                      |
| Penerimaan barang dan penutupan     | Accepted 6/rejected 2 pada ordered 10 menyisakan 4; approver menutup sisa dan dokumen menjadi Selesai dengan kekurangan.  |
| Akun dan vendor                     | Admin membuat akun, menonaktifkan, mereset password, serta membuat vendor sintetis.                                       |
| Keyboard                            | Tab mencapai skip link; Enter memindahkan focus ke main. Focus tombol simpan memiliki outline 3px.                        |
| Submit berulang                     | Respons POST sengaja ditahan; pesan proses terlihat dan dua aktivasi simpan hanya menghasilkan satu POST.                 |
| Browser Back                        | Setelah simpan, kembali ke form membersihkan aria-busy dan pesan proses.                                                  |
| Reduced motion                      | Transisi tombol menjadi 0 detik ketika preferensi reduce aktif.                                                           |
| Pembesaran teks                     | Ukuran teks root 200% pada daftar di lebar 390px tidak menimbulkan overflow halaman.                                      |
| Cetak                               | Satu PO dirender ke PDF A4 melalui browser headless. Dialog printer dan hasil fisik belum diuji.                          |

Screenshot antrean, detail dan form diperiksa secara visual. Enam belas pasangan warna dari stylesheet dihitung: seluruh teks yang diukur melampaui 4,5:1, minimum 5,91:1; batas kontrol 4,76:1 melampaui 3:1. Status selalu disertai teks. Pemeriksaan ini tidak mencakup pembaca layar, keyboard layar perangkat fisik, seluruh kombinasi data panjang, ataupun dokumen cetak beberapa halaman. Penerimaan jasa dan cabang penolakan/revisi/cancel tetap mempunyai tes service/HTTP dan bukti tahap sebelumnya; seluruh cabang tersebut tidak diulang lewat klik pada tahap ini.

Review independen memeriksa source, tanpa menjalankan database atau browser. Satu temuan P2 tentang menu tanpa JavaScript diselesaikan melalui reproduksi gagal lalu lulus. Dua temuan P3 tetap terbuka: paginasi daftar aktif dan historis penawaran mereset parameter satu sama lain, serta panel tindakan mobile masih berada setelah rincian panjang. Tautan menuju tindakan tersedia di awal detail. Optimasi snapshot item saat evaluasi seluruh kandidat, yang dicatat pada tahap sourcing, juga masih terbuka. Comparison rows kini dibangun setelah paginasi; detail PO/cetak dan form penerimaan sudah memakai prefetch item. Label snapshot PO mengikuti mapping tahap yang sama.

Bukti lokal tersimpan dalam tmp: log regresi, matriks halaman/viewport, catatan interaksi, hasil kontras, screenshot dan render A4. Akun/data sintetis tidak masuk database kerja atau Git. Belum ada klaim kapasitas produksi, deployment, maupun hasil instalasi bersih.

### Kompatibilitas pemformatan template

Pemformat HTML generik memecah tag Django hingga 14 template gagal dikompilasi; beberapa ekspresi variabel juga menjadi teks literal. Tag tersebut diperbaiki sambil mempertahankan perapihan HTML. Proyek kini memakai Prettier 3.7.4 dan prettier-plugin-django-alpine 1.3.0 sebagai dependensi development dengan lockfile. Konfigurasi lokal memuat plugin untuk file template; CSS dan JavaScript tetap memakai pemformatan Prettier.

Uji pada 28 template memeriksa urutan/nilai token Django sebelum dan sesudah format serta kestabilan dua kali format. Seluruhnya lulus. Sesudah npm run format, pemeriksaan kompilasi menemukan nol kegagalan dan nol tag multiline, sedangkan npm run format:check lulus. Satu assertion tracking yang semula bergantung pada whitespace HTML mentah disesuaikan menjadi perbandingan HTML semantik; pesan lengkap dan perilaku pemulihannya tetap diperiksa. Seluruh 227 test kemudian lulus, diikuti pemeriksaan browser 85 halaman/peran serta menu, keyboard, submit berulang dan Back. Pengaturan format-on-save VS Code yang sudah aktif tetap dipertahankan.

### Revisi proporsi, kepadatan dan konfirmasi logout

Tiga test baru terlebih dahulu gagal karena kapitalisasi dan route konfirmasi belum tersedia. Setelah implementasi, suite penuh lulus 230 test dalam 23,006 detik. GET konfirmasi tetap mempertahankan sesi, akun anonim diarahkan ke login, dan POST logout mengakhiri sesi. Endpoint logout tetap POST-only serta dilindungi CSRF oleh pengujian autentikasi yang ada.

Browser memeriksa lima halaman admin pada tujuh lebar 320/390/640/768/1024/1440/1920, dilanjutkan pemindaian 93 halaman/peran pada enam lebar sampai 1440. Tidak ditemukan overflow halaman atau pageerror JavaScript pada sampel. Ukuran terukur: brand 28px, subjudul 16px, topbar 17px, nama akun 18px dan Beranda 16px. Filter pada 1440 mempunyai tinggi sekitar 195px.

Konfirmasi logout diuji dengan klik, Batal, Escape, focus awal pada Batal, pengembalian focus ke pemicu, serta Ya, Keluar. Pada konteks tanpa JavaScript, tautan membuka halaman konfirmasi, Batal kembali ke beranda, dan Ya, Keluar mengakhiri sesi. Screenshot login, daftar dan dialog diperiksa. Pemeriksaan visual menangkap dua delimiter HTML yang terlihat pada sidebar; regresi browser terlebih dahulu gagal lalu lulus setelah markup dibetulkan.

Enam pasangan warna tambahan lulus: teks putih/sidebar 12,25:1, teks sekunder/sidebar 9,06:1, teks putih/hover 8,76:1, focus/sidebar 8,56:1, pemisah akun/sidebar 3,84:1 dan teal/putih 7,55:1. Pemindai desain tidak melaporkan temuan pada target eksplisit, tetapi tidak dapat mengikuti tautan stylesheet berupa tag static Django, sehingga hasil templatenya terbatas. Hasil render dan pengukuran warna diperiksa terpisah. Prettier dengan plugin Django dan pemeriksaan kompilasi tetap menjadi bagian verifikasi. Bukti tersimpan pada tmp/ui-refinement di workspace pemeriksaan; database kerja tidak dipakai untuk data sintetis. Perangkat fisik, pembaca layar dan deployment belum diuji.

### Visibilitas password dan pesan login tunggal

Regresi browser terlebih dahulu gagal karena tombol mata belum tersedia. Sesudah implementasi, lima kolom pada login, pembuatan akun, dan reset password lulus pemeriksaan ikon tanpa tulisan, label aksesibel, kontrol per kolom, nilai tetap sama, klik, Space, focus outline 3px dan target minimum 44px. Keempat lebar 320/390/768/1440 tidak menghasilkan overflow pada halaman yang diperiksa. Konteks tanpa JavaScript tetap memuat input password native tanpa tombol tambahan.

Regresi HTTP terlebih dahulu menemukan dua pesan salah kredensial. Setelah perubahan, pesan hanya muncul satu kali dalam form login dan error-summary tidak dirender pada halaman itu. Browser juga memeriksa jumlah pesan serta focus pada login-errors. Server preview dengan --noreload sempat memakai template yang tersimpan sebelum revisi; setelah restart, pemeriksaan memakai source terbaru dan lulus. Screenshot error serta ikon diperiksa secara visual. Suite penuh terakhir lulus 231 test dalam 33,433 detik. Data uji memakai database terpisah; tidak ada perubahan password atau akun kerja.

### Focus login, autocomplete dan seleksi teks

Dua regresi terlebih dahulu gagal pada atribut autocomplete dan pemicu focus alert yang masih tersedia. Sesudah perubahan, 58 test akun/error HTTP lulus dalam 16,633 detik. Pengujian tetap memastikan username dipertahankan, pesan tunggal berada di form, dan widget password tidak merender atribut value. Ringkasan error transaksi tetap diperiksa oleh suite HTTP.

Browser uji memverifikasi autocomplete off pada form/dua kolom, alert tidak menerima focus otomatis, password kosong setelah respons gagal maupun setelah focus dan dua klik ikon mata, serta pesan hanya satu kali. Seleksi input terukur rgb(15,94,94) dengan teks rgb(255,255,255), rasio 7,55:1. Screenshot diperiksa; lebar 320/390/768/1440 tidak menghasilkan overflow pada halaman yang diuji. Tidak ada penugasan nilai password dalam source JavaScript. Pemeriksaan ini memakai profil browser bersih dan tidak mengakses kredensial tersimpan pengguna, sehingga tidak membuktikan bahwa password manager pengguna menaati autocomplete off. Bukti tersimpan pada tmp/login-refinement.

### Validasi tunggal di dalam form

Dua test baru terlebih dahulu gagal karena ringkasan global dan pemberitahuan tambahan masih dirender di luar form. Pemeriksaan parameter dengan POST kosong mencakup 17 endpoint form/aksi: akun baru/edit/reset, vendor baru/edit, draft baru/edit/submit/cancel, approval/revisi, penawaran baru/edit/pilih, penerbitan PO, penerimaan dan penutupan; ditambah dua daftar dengan filter invalid. Parser HTML memeriksa bahwa error list dan alert validasi berada di dalam form, serta error-summary global tidak ada. Ini bukti lokasi pesan pada respons 400 untuk POST kosong, bukan pengujian seluruh aturan bisnis, token valid atau seluruh field pada setiap endpoint. Pengujian service/HTTP dengan payload terisi serta interaksi browser di tahap terkait menjadi bukti perilaku bisnis yang terpisah. Kasus admin aktif terakhir juga memastikan pesan hanya sekali dan akun tetap ADMIN aktif.

Penelusuran menemukan POST penerbitan PO yang invalid, tanpa penawaran terpilih, gagal saat template memformat nilai yang belum ada. Regresi gagal sebelum guard ditambahkan; setelah perbaikan, form tetap dirender untuk menyampaikan validasi tanpa nilai penawaran fiktif. Pesan tambahan pada daftar saat filter invalid juga diuji gagal terlebih dahulu lalu dihapus. Empty state untuk pencarian/filter valid tetap tersedia.

Suite penuh lulus 233 test setelah seluruh perubahan sumber. Browser memeriksa kasus admin terakhir, konfirmasi password berbeda, field vendor kosong, filter invalid dan jumlah item negatif, pada lebar 320/390/768/1440. Pesan admin terakhir muncul satu kali dalam form; GET berikutnya memastikan role tetap ADMIN. Kasus vendor dengan dua field kosong mempunyai dua pesan untuk kesalahan yang berbeda, bukan pengulangan satu kesalahan di luar form. Tautan muat ulang tetap tersedia di dalam form akun/draft. Screenshot desktop/mobile diperiksa. Renderer, partial, CSS dan pemindahan focus ringkasan global yang tidak dipakai telah dihapus.

Pengujian memakai database sintetis terpisah dan tidak mengubah akun kerja. Pada penutupan revisi validasi form sebelum implementasi Tahap 11, dokumen rancangan Tahap 11 dipertahankan; command seed dan panduan pengguna belum dibuat. Keduanya kemudian tersedia dan diverifikasi pada Tahap 11 di bawah. Hasil terdahulu mengenai focus atau ringkasan global merupakan rekam penerapan sebelumnya dan digantikan pola validasi pada bagian ini. Bukti lokal berada di tmp/form-errors.

### Konsistensi Kapitalisasi Antarmuka

Seluruh 29 template diperiksa, termasuk partial riwayat, snapshot PO, pemenuhan pesanan, navigasi, form, dan cetak. Judul, caption, label form, tombol, pilihan status serta nama tindakan riwayat mengikuti kapital pada awal setiap kata. Sumber label form Django ikut diperbarui. Paragraf bantuan, pesan validasi dan keadaan kosong tetap memakai sentence case; nama akun, vendor, item, judul dan isi dokumen ditampilkan sesuai data pengguna. Nilai status dan kontrak transaksi tidak berubah.

Audit sumber untuk heading, tautan, tombol, label, legend dan nama navigasi tidak menemukan pelanggaran kapitalisasi. Semua template berhasil dikompilasi, tag Django tetap utuh, dan Prettier lulus. Enam kegagalan awal suite disebabkan ekspektasi teks lama; sesudah penyesuaian teks yang diperiksa, 233 test lulus dalam 23,310 detik tanpa mengurangi assertion perilaku atau keamanan.

Browser lima peran memeriksa 97 kombinasi halaman/peran pada enam lebar 320/390/640/768/1024/1440, sebanyak 582 pemeriksaan ukuran tanpa overflow halaman. Tidak ditemukan pageerror JavaScript. Label form dan pilihan status diperiksa pada hasil render, termasuk caption detail dan cetak PO. Screenshot detail PO ditinjau; nama akun tetap sesuai sumber. Alur tambah baris, hapus baris kosong dan simpan draft tanpa JavaScript serta render PDF A4 tetap lulus. Bukti lokal tersimpan di tmp/ui-capitalization pada workspace pemeriksaan. Pengujian memakai database sintetis terpisah. Hash rancangan Tahap 11 tetap sama; perangkat fisik, pembaca layar dan deployment belum diuji.

### Tahap 11: Setup Bersih Dan Pengujian Demo

Salinan sumber dibuat tanpa virtualenv, database, node_modules atau rahasia kerja. Python 3.12 membuat virtualenv baru; requirements dipasang dari wheel cache: Django 5.2.18, asgiref 3.12.1, sqlparse 0.6.0 dan tzdata 2026.5. `pip check`, migrasi 0001 dan 0002, `seed_demo` dua kali, `check` dan `makemigrations --check --dry-run` selesai dengan exit 0. Launcher Windows Store `py` tidak dapat dijalankan; bootstrap memakai executable Python 3.12 langsung sebagaimana alternatif README. Server preview memakai port 8017 dan database `clean-source/var/demo`; database kerja tidak dimigrasikan atau diisi data.

TC-19 menambah tujuh test untuk lima skenario, pengulangan tanpa duplikasi audit/dokumen, password/peran yang sudah berubah, password hilang/tidak valid, benturan identitas, progres draft yang sudah diajukan, serta rollback kegagalan service di tengah seed. Registry DemoSetup dan seluruh data dibuat dalam satu transaksi. Password tidak dicetak ke stdout atau disimpan pada registry. Benturan tidak mengambil alih akun/vendor existing. Bootstrap admin menggunakan validasi akun normal; empat akun berikutnya melalui service admin. Dokumen, keputusan, penawaran, snapshot, penerimaan dan audit memakai service bisnis.

Regresi tindak lanjut terlebih dahulu gagal untuk paginator yang saling mereset, snapshot comparison berulang dan target focus detail. Setelah perbaikan, kedua paginator menjaga parameter page/history_page; browser mengonfirmasi tautan tindakan memindahkan focus ke followup pada layar mobile. Evaluasi pemilihan delapan kandidat awalnya melakukan sembilan pembacaan snapshot, kemudian satu setelah prefetch; jalur issue_order yang sebelumnya sudah bounded tetap diuji. Lima test tindak lanjut melindungi perilaku ini. Review independen tidak menemukan P1/P2 dan menemukan jalur pemilihan tersebut; perbaikannya mengikuti red-green tanpa mengubah izin atau perhitungan.

Suite akhir pada virtualenv bersih menjalankan `python manage.py test --noinput -v 2`: **245 test lulus dalam 39,002 detik**, termasuk concurrency SQLite file-backed tanpa parallel. Pemeriksaan normal dan konsistensi migrasi lulus. Pemeriksaan `DEBUG=false` dengan allowed host eksplisit menghasilkan satu warning `security.W004` karena SECURE_HSTS_SECONDS belum ditetapkan. HTTPS/hosting belum diuji; HSTS perlu ditentukan saat deployment, bukan diasumsikan aktif dari pemeriksaan lokal.

#### Bukti Browser Dari Panduan

Lima akun demo berhasil login dan membaca daftar permintaan/PO yang tidak kosong. Browser mengikuti jalur melihat contoh, lalu membuat transaksi uji baru melalui form, tanpa command internal untuk menggantikan tindakan pengguna:

| Alur              | Hasil                                                                                                                                                 |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Barang            | Draft, submit, Minta Revisi, edit/resubmit, setuju, penawaran, pilih vendor, terbit PO; accepted 6/rejected 2/sisa 4, lalu accepted 4 menjadi lengkap |
| Jasa              | Draft hingga PO dan penerimaan lengkap dengan bukti SERVICE_REPORT serta periode hari WIB                                                             |
| Penolakan         | Permintaan uji terpisah ditolak dengan alasan                                                                                                         |
| Penutupan         | PO uji baru diterima sebagian, approver mengakhiri sisa; status CLOSED_SHORT dan sisa 4 tetap ada                                                     |
| Invalid dan akses | Penerimaan rejected tanpa alasan ditolak dalam form; admin membuka pembuatan permintaan mendapat 403                                                  |
| Cetak             | PO 40 item menghasilkan lima halaman A4; teks item terakhir dan total utuh, seluruh halaman dirender PNG dan diperiksa visual                         |

Nomor/URL transaksi uji dicatat pada browser-results.json; pemetaan kode G-01/J-01/G-02/G-03/J-02 serta nomor awal ada pada clean-setup.log. Skenario awal tidak direset sesudah uji; seed tetap aman dipanggil ulang dan panduan menjelaskan cara memakai folder demo baru. Pemindaian setelah penambahan transaksi mencakup **175 kombinasi halaman/peran dan 1.050 pemeriksaan viewport** pada 320/390/640/768/1024/1440, tanpa overflow halaman atau pageerror JavaScript. Menu, Escape/pengembalian focus, tambah/hapus baris kosong dan simpan draft tanpa JavaScript juga lulus.

#### Ketertelusuran Dan Batas

FR-01/BP-00/WBS 2.1 mengacu pada tes akun/policy dan login lima peran. FR-02â€“FR-03/BP-01â€“03/GW-01/WBS 2.2â€“2.3 memakai regresi request/approval dan alur revisi/penolakan browser. FR-04â€“FR-07/BP-04â€“09/GW-02â€“03/WBS 3.1â€“3.4 memakai suite vendor/sourcing/orders dan browser penawaran hingga PO. FR-08â€“FR-10/BP-10â€“15/GW-04â€“06/WBS 4.1â€“4.3 memakai suite receipt/jasa/closure/concurrency dan alur pemenuhan browser. FR-11/BP-16/WBS 5.1 memakai suite tracking; FR-12/WBS 5.2 memakai regresi HTTP/form, browser responsive/keyboard dan cetak. FR-13/WBS 6.1/TC-19 memakai instalasi bersih, seed dan panduan. TC-01 sampai TC-18 tetap berjalan dalam suite penuh; OPT-01 tetap Ditunda.

PDF BPMN dapat dibaca sebagai lima halaman; workbook WBS dapat dibuka dan memuat sheet WBS/Tracking. Struktur analisis tidak diubah karena transisi bisnis tetap sama. Tautan dokumen lokal diperiksa; remote Git tetap acuan repository, bukan bukti deployment publik. Perangkat fisik, pembaca layar, beban produksi, penerimaan vendor nyata serta deployment belum diuji. Bukti mentah berada di tmp/stage11 pada workspace pemeriksaan. Beberapa percobaan harness gagal karena listener sandbox, locator form logout yang terlalu luas dan contoh penutupan yang sudah terminal; harness diperbaiki tanpa mengubah aturan aplikasi. Hasil final di atas berasal dari run yang lulus, bukan dari percobaan tersebut.
