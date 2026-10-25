# Deployment Demo PythonAnywhere

## Status terbaru: 25 Oktober 2026

- Instalasi bersih versi akhir beserta dependensi AI dan 297 tes lulus lokal.
- Hosting: delapan aset publik cocok dengan sumber lokal; HTTPS, header, CSRF, route terlindungi, dan lima path privat lulus pemeriksaan anonim.
- Bukti browser pengguna sudah mencakup pengadaan barang/jasa, cetak PO, dan bantuan AI sampai draf tersimpan.
- Riwayat console menunjukkan paket v6 telah diterapkan dan VERIFY_OK. Ini bukti terpisah dari pemeriksaan HTTP terbaru.
- Screenshot console mengonfirmasi check --deploy hanya menghasilkan W005/W021, migrate --check tanpa error, serta izin folder privat 700 dan kedua file konfigurasi 600.
- Remote main commit 5209c62 sudah dipush dan diverifikasi. Revisi WBS/dokumentasi setelah commit tersebut masih lokal; pengiriman hasil belum dikonfirmasi.

Bagian bertanggal 24 Oktober di bawah merupakan riwayat tahap terdahulu. Pernyataan belum diuji pada bagian tersebut berlaku pada snapshot itu; gunakan status terbaru dan TESTING untuk keadaan akhir.

## Pilihan Dan Batas

Target demo tes kerja adalah akun ramaatha pada pythonanywhere.com, dengan Django 5.2, Python 3.12 dan SQLite. PythonAnywhere dipilih agar database serta transaksi IMMEDIATE yang sudah diuji tetap digunakan. Vercel + PostgreSQL memerlukan perubahan koneksi dan peninjauan ulang locking; pilihan itu tidak diterapkan.

Profil hosting terpisah dari konfigurasi lokal. Secret acak dan hostname disimpan pada `~/.config/procurement-demo/environment.json`, di luar checkout dan direktori static. Console dan WSGI memakai `config.settings_pythonanywhere`. Data demo berada pada `~/procurement-demo/var/pythonanywhere/db.sqlite3`; aplikasi tidak memakai database kerja di komputer pengguna.

Paket Beginner gratis menyediakan satu web app, satu worker dan penyimpanan 512 MiB. Aplikasi gratis mempunyai masa aktif satu bulan; periksa tanggal expiry dan opsi perpanjangan pada dashboard selama masa penggunaan demo. Ketersediaan Python bergantung system image; gunakan Python 3.12 pada console, virtualenv dan Web app yang sama.

## Status Persiapan Per 24 Oktober 2026

- [x] Regresi konfigurasi privat, host, HTTPS dan WSGI: tujuh test, terlebih dahulu gagal lalu lulus.
- [x] Suite penuh: 252 test lulus pada salinan aplikasi dengan database tes terpisah.
- [x] Migrasi, seed dua kali, konsistensi migrasi dan collectstatic lulus pada salinan sumber.
- [x] Review source independen selesai tanpa temuan P1/P2 pada konfigurasi hosting yang ditambahkan.
- [x] Screenshot console host: Python 3.12.8, SQLite 3.37.2 dan JSON1 OK.
- [x] Screenshot pengguna: sumber diunggah, requirements terpasang, migrasi selesai dan lima akun/lima skenario demo dibuat.
- [x] Web app Python 3.12 aktif; Force HTTPS ditunjukkan Enabled pada screenshot, dan aplikasi/static berhasil diakses dari jaringan.
- [x] GET anonim: HTTP menuju HTTPS/login, respons login dan CSS/JS/font 200; hash ketiga aset cocok dengan paket.
- [x] Screenshot pengguna: login demo_admin dan daftar PR/PO berisi data seed.
- [ ] Uji empat peran operasional, transaksi baru, cetak dan persistensi setelah Reload di host.

Screenshot pengguna menunjukkan dashboard sudah login sebagai ramaatha. Akses otomatis ke Chrome terhenti karena alat tidak dapat memverifikasi URL. Kondisi ini bukan alasan meminta pengguna login ulang pada Chrome yang sama. URL publik sekarang berhasil diakses sampai halaman login; alur terautentikasi masih perlu diverifikasi.

Jika aplikasi sudah aktif, gunakan [pembaruan paket v1](#pembaruan-instalasi-aktif-dengan-paket-v1). Langkah instalasi awal di bawah tidak perlu diulang.

## 1. Unggah Sumber

Gunakan arsip `procurement-demo-pythonanywhere.zip` yang disiapkan dari sumber lokal yang telah diuji. Arsip tidak memuat virtualenv, node_modules, direktori Git, database, konfigurasi privat, log, atau password kerja. Versi dan hash sumber dicatat pada SOURCE_MANIFEST.json di dalam arsip.

Pada tab **Files**, unggah arsip ke `/home/ramaatha/`. Lalu buka console **Bash** dari dashboard. Ekstrak hanya pada folder baru agar checkout atau data existing tidak tertimpa:

```bash
cd ~
python3.12 - <<'PY'
from pathlib import Path
from zipfile import ZipFile

target = Path.home() / "procurement-demo"
if target.exists():
    raise SystemExit("Folder procurement-demo sudah ada. Gunakan prosedur pembaruan, jangan timpa instalasi.")
with ZipFile(Path.home() / "procurement-demo-pythonanywhere.zip") as archive:
    for item in archive.infolist():
        if not (target / item.filename).resolve().is_relative_to(target.resolve()):
            raise SystemExit("Path arsip tidak valid.")
    archive.extractall(target)
print(target)
PY
```

Alternatifnya, setelah perubahan di-commit dan di-push pengguna, checkout repository GitHub dapat dipakai. Jangan mengasumsikan isi GitHub sudah sama dengan perubahan lokal yang belum dipush.

## 2. Buat Environment Dan Konfigurasi Privat

```bash
python3.12 -m venv ~/.virtualenvs/procurement-demo
source ~/.virtualenvs/procurement-demo/bin/activate
cd ~/procurement-demo
python -m pip install -r requirements.txt
python -m deploy.pythonanywhere configure --hostname ramaatha.pythonanywhere.com
export DJANGO_SETTINGS_MODULE=config.settings_pythonanywhere
python manage.py check
```

Periksa exit code setiap perintah. Jika Python 3.12 tidak tersedia, periksa **Account → System Image** sebelum melanjutkan. Jangan mengganti versi atau menambah paket Node untuk deployment ini.

Command configure membuat secret baru tanpa mencetaknya dan menolak file existing. File dibuat dengan mode 0600 pada Linux. Jangan mengunggah konfigurasi privat ke Git, menyalinnya ke folder static, atau memasukkan isinya ke chat. Jangan menjalankan configure ulang untuk merotasi secret secara tidak sengaja; perubahan secret mengakhiri sesi yang sudah ada.

Profil hosting memaksa DEBUG=false, host eksplisit, cookie Secure, HTTPS redirect, serta direktori database demo. Environment lokal yang menyatakan DEBUG=true tidak mengalahkan profil hosting.

## 3. Periksa Runtime Dan Siapkan Demo

```bash
python - <<'PY'
import sqlite3
print("SQLite:", sqlite3.sqlite_version)
with sqlite3.connect(":memory:") as connection:
    print("JSON1:", connection.execute("SELECT json_valid('{}')").fetchone()[0])
PY
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
python manage.py check --deploy
```

JSON1 harus menghasilkan 1. Versi SQLite perlu memenuhi dukungan Django 5.2; jika migrasi atau check gagal, hentikan langkah berikutnya dan periksa log, jangan melewati constraint.

Tetapkan password sintetis demo secara langsung pada console. Password tidak tampil saat diketik; jangan gunakan password akun PythonAnywhere atau password pribadi.

```bash
read -r -s -p 'Password sintetis lima akun demo: ' DEMO_PASSWORD
printf '\n'
export DEMO_PASSWORD
python manage.py seed_demo
unset DEMO_PASSWORD
```

Gunakan password acak yang cukup panjang dan simpan melalui sarana privat milik pengguna. Command mengikuti validator aplikasi dan tidak mencetak password. Lima username dan skenario tetap mengikuti USER_GUIDE. Menjalankan seed kembali tidak mereset password, role atau kemajuan transaksi.

Pada console baru, aktifkan virtualenv dan export DJANGO_SETTINGS_MODULE lagi sebelum menjalankan manage.py. Jangan menjalankan migrate atau seed di dalam WSGI saat aplikasi menerima request.

## 4. Konfigurasikan Web App

Pada tab **Web**, pilih **Add a new web app**, domain ramaatha.pythonanywhere.com, **Manual configuration**, lalu **Python 3.12**. Pastikan pilihan masih dalam paket Beginner gratis.

Isikan:

| Pengaturan        | Nilai                                                     |
| ----------------- | --------------------------------------------------------- |
| Source code       | /home/ramaatha/procurement-demo                           |
| Working directory | /home/ramaatha/procurement-demo                           |
| Virtualenv        | /home/ramaatha/.virtualenvs/procurement-demo              |
| Static URL        | /static/                                                  |
| Static directory  | /home/ramaatha/procurement-demo/var/pythonanywhere/static |

Edit file WSGI yang ditautkan dari dashboard **Web**, bukan mengganti config/wsgi.py lokal. Gunakan adaptor dalam checkout:

```python
import runpy
from pathlib import Path

application = runpy.run_path(
    str(Path.home() / "procurement-demo" / "deploy" / "pythonanywhere_wsgi.py")
)["application"]
```

Jangan menyalin isi deploy/pythonanywhere_wsgi.py langsung ke /var/www: adaptor menghitung root dari lokasi file sendiri. Jangan memetakan /var/ atau direktori database sebagai static files.

Simpan, aktifkan **Force HTTPS**, lalu **Reload**. Tidak perlu menjalankan manage.py runserver pada PythonAnywhere. Profil tidak mempercayai X-Forwarded-Proto secara otomatis; verifikasi perilaku proxy host lewat smoke test sebelum mengubah kebijakan header.

## 5. Verifikasi URL Publik

Alamat target adalah **<https://ramaatha.pythonanywhere.com/>**. Domain ini baru boleh disebut ter-deploy setelah respons publik diuji.

- HTTP dialihkan ke HTTPS; HTTPS tidak berulang kali redirect.
- /login/ berhasil dibuka, CSS/font/JavaScript termuat, dan DEBUG tetap false.
- /static/css/app.css berhasil; database atau konfigurasi privat tidak dapat diakses melalui static mapping.
- Login masing-masing lima akun demo, cek username/role dan lakukan logout.
- Admin dapat membaca contoh PR/PO; pemohon hanya melihat dokumen miliknya.
- Coba barang hingga penerimaan lengkap, jasa dengan bukti/periode, dan satu kasus invalid sesuai USER_GUIDE.
- Periksa filter/paginasi, detail, riwayat, serta cetak PO.
- Reload aplikasi dari dashboard, lalu pastikan transaksi uji tetap tersedia.

Bagikan kredensial demo kepada pengguna melalui kanal pengumpulan yang ditentukan, bukan repository publik. Data demo dibagi antar penguji; gunakan judul transaksi uji yang berbeda agar contoh awal tetap mudah dikenali.

## Pembaruan, Backup Dan Pemulihan

Sebelum pembaruan, catat versi sumber dan buat backup SQLite yang konsisten melalui API backup:

```bash
python - <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

source = Path.home() / "procurement-demo" / "var" / "pythonanywhere" / "db.sqlite3"
target = Path.home() / ("procurement-demo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".sqlite3")
with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as reader:
    with sqlite3.connect(target) as writer:
        reader.backup(writer)
print(target)
PY
```

Backup tetap privat dan memakai kuota penyimpanan akun. Periksa kuota lalu unduh backup melalui tab Files bila diperlukan.

Pembaruan sumber harus mempertahankan direktori var/pythonanywhere dan konfigurasi privat di luar checkout. Install requirements bila berubah, periksa migrasi, jalankan migrate/collectstatic, lalu Reload dan smoke test. Jangan mengekstrak ulang arsip awal menimpa instalasi aktif atau menghapus database untuk memperbaiki error.

Jika login, data, atau alur transaksi gagal setelah pembaruan, hentikan pengujian demo dan periksa error log. Kembalikan sumber ke versi yang diketahui baik. Pemulihan database hanya dilakukan dari backup terverifikasi saat request dihentikan; simpan database sebelumnya dan periksa kecocokan schema sebelum menggantinya.

## Bukti Lokal Sebelum Verifikasi Host

Bukti lokal berada pada C:/Users/Rama Atha/.codex/tmp/pythonanywhere-20261024. Tujuh test konfigurasi/WSGI lulus dan suite penuh berisi 252 test, selesai dalam 32,826 detik. Migrasi, seed ulang, collectstatic empat file dan pemeriksaan konsistensi migrasi menghasilkan exit 0 pada database sintetis.

Check deployment menghasilkan security.W005 dan security.W021: HSTS diterapkan hanya pada hostname selama satu jam, tanpa includeSubDomains atau preload. Batas ini disengaja untuk demo pada subdomain provider; tidak ada warning yang disembunyikan. HTTPS nyata pada host belum diuji pada run lokal tersebut; bukti publik berikutnya dicatat terpisah di bawah. Tidak ada perubahan default lokal atau migrasi/model bisnis baru.

Review independen bersifat statis dan tidak menjalankan database atau jaringan. Batas Linux permission, proxy host dan paket runtime PythonAnywhere belum dibuktikan oleh hasil Windows lokal. Rate limiting login belum tersedia; demo memakai data sintetis dan kredensial terpisah. Ini bukan klaim kesiapan operasional perusahaan.

## Sumber Resmi

- [Deploy proyek Django existing](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/).
- [Static files Django](https://help.pythonanywhere.com/pages/DjangoStaticFiles/).
- [Force HTTPS](https://help.pythonanywhere.com/pages/ForcingHTTPS/).
- [Versi Python](https://help.pythonanywhere.com/pages/PythonVersions/).
- [Batas akun gratis](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/).

## Verifikasi Publik Awal - 24 Oktober 2026

GET anonim oleh agen ke <http://ramaatha.pythonanywhere.com/> berakhir di <https://ramaatha.pythonanywhere.com/login/?next=/> dengan HTTP 200, tanpa loop atau pengabaian validasi sertifikat. GET login langsung juga 200. Halaman memuat form username/password, cookie CSRF Secure, HSTS max-age=3600, X-Frame-Options DENY dan nosniff.

CSS app.css, JavaScript forms.js dan font IBMPlexSans.ttf masing-masing menghasilkan HTTP 200 dengan MIME yang sesuai; hash isi cocok dengan arsip yang diunggah pengguna. Header keamanan aplikasi tersebut diperiksa pada HTML, bukan diasumsikan tersedia pada respons static provider.

Bukti HTTP tersimpan di C:/Users/Rama Atha/.codex/tmp/pythonanywhere-20261024/public-smoke.json. Bukti instalasi host berasal dari screenshot pengguna, terpisah dari GET oleh agen: Python 3.12.8, SQLite 3.37.2/JSON1, migrasi, empat static files dan seed lima akun/lima skenario. Dashboard menunjukkan expiry 24 November 2026; periksa/perpanjang melalui dashboard sebelum masa aktif berakhir.

Tidak ada kredensial yang dipakai agen pada pemeriksaan publik ini. Login lima peran, POST transaksi, cetak terautentikasi dan persistensi setelah Reload belum dinyatakan teruji pada hosting.

## Verifikasi Admin Pada Hosting - 24 Oktober 2026

Dua screenshot pengguna menunjukkan sesi demo_admin dengan peran Admin, daftar Permintaan Pengadaan berisi J-02/G-03, serta daftar PO dengan status Diterima Lengkap, Diterima Sebagian dan Terbit. PO yang terlihat memuat vendor demo dan total IDR 900.000,00. Ini bukti login dan pembacaan data admin melalui browser pengguna; agen tidak memakai atau menerima password.

Bukti ini belum mencakup login empat peran operasional, POST transaksi baru, detail penerimaan, cetak atau persistensi sesudah Reload pada host. Pengujian lokal sebelumnya tetap terpisah.

## Verifikasi Pemohon Pada Hosting - 24 Oktober 2026

Screenshot pengguna menunjukkan login demo_pemohon, pembuatan draft UJI Hosting Barang (Monitor Uji, 10 unit, estimasi IDR 100.000,00 per unit, total IDR 1.000.000,00), serta pengajuan berhasil dengan status Diajukan. Revisi 1 dan dua riwayat (Draft Dibuat, Permintaan Diajukan) terlihat, dan permintaan tampil kembali pada daftar. Ini bukti interaksi browser pengguna pada host, bukan pengujian agen dengan kredensial.

Login dan aksi Approver/Procurement/Penerima, penerbitan PO, penerimaan, cetak dan persistensi setelah Reload pada host masih menunggu pengujian.

## Verifikasi Approver Pada Hosting - 24 Oktober 2026

Dua screenshot pengguna menunjukkan demo_approver aktif sebagai Approver, notifikasi keputusan berhasil disimpan dan UJI Hosting Barang berubah menjadi Disetujui. Estimasi IDR 1.000.000,00 serta Revisi 1 tetap terlihat. Riwayat memuat persetujuan oleh demo_approver pada 15:13 WIB dengan alasan Kebutuhan demo sesuai, setelah draft dan pengajuan oleh demo_pemohon.

Ini bukti browser pengguna untuk login dan persetujuan pada host. Penawaran/penerbitan PO oleh Procurement, penerimaan oleh Penerima, cetak dan persistensi setelah Reload pada host belum diverifikasi.

## Verifikasi Penerbitan PO pada Hosting - 24 Oktober 2026

Screenshot pengguna menunjukkan PO-dc46e4c2-f766-4fe7-9d5b-84bd2dce3fb1 berhasil diterbitkan dari PR-cbd2a748-c3e2-4cc4-8bbb-fb6479cb4269 (UJI Hosting Barang), Revisi 1. PO berstatus Terbit, vendor DEMO Vendor Peralatan, 10 unit Monitor Uji, total IDR 900.000,00 dan penerbit demo_procurement pada 22:42 WIB. Riwayat memperlihatkan pemilihan vendor dan penerbitan PO. Ini bukti browser pengguna pada alur hosting, bukan aksi agen dengan kredensial.

Jumlah diterima dan ditolak masih nol, sisa 10 unit, serta belum ada riwayat penerimaan. Langkah hosting yang tersisa: login Penerima, pencatatan penerimaan, cetak dan persistensi sesudah Reload. Koreksi bahasa, breadcrumb dan tampilan notifikasi lokal belum diklaim terpasang pada host.

## Pembaruan Instalasi Aktif dengan Paket v1

Prosedur ini khusus paket procurement-update-20261024-v1, dibandingkan dengan ZIP instalasi awal. Isinya pembaruan source dan dokumentasi; tidak memuat database, private environment, virtualenv, atau rahasia. Requirements dan migrasi tidak berubah. Paket dapat membawa perubahan lokal yang belum di-commit; manifest mencatat commit dasar dan hash berkas, tanpa menyatakan GitHub sudah sama.

1. Unduh procurement-update-20261024-v1.zip dan procurement-update-20261024-v1.py dari hasil persiapan lokal.
2. Unggah keduanya melalui Files ke /home/ramaatha/. Jangan mengekstrak ZIP ke aplikasi secara manual.
3. Di console Bash PythonAnywhere, cocokkan SHA256 helper dengan nilai pada hasil persiapan, lalu jalankan pemeriksaan read-only:

```bash
cd /home/ramaatha
python3.12 procurement-update-20261024-v1.py check
```

CHECK_OK berarti paket, baseline source dan database dapat diperiksa. Jika muncul STOP atau source berbeda, hentikan langkah berikutnya dan simpan pesan error; helper tidak mengizinkan overwrite diam-diam atas perubahan host.

4. Hentikan penggunaan form dan perintah console lain yang mengubah data. Nonaktifkan sementara aplikasi dari bagian Disable di tab Web. Jangan membuat web app baru.
5. Di Bash, jalankan blok berikut. Jika satu perintah gagal, blok berhenti; jangan mengaktifkan aplikasi sebelum diperiksa atau di-rollback.

```bash
(
set -e
cd /home/ramaatha
python3.12 procurement-update-20261024-v1.py apply
source /home/ramaatha/.virtualenvs/procurement-demo/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings_pythonanywhere
cd /home/ramaatha/procurement-demo
python -m pip check
python manage.py check
python manage.py migrate --check
python manage.py collectstatic --noinput
python3.12 /home/ramaatha/procurement-update-20261024-v1.py verify
)
```

Apply memvalidasi source sebelum menulis, membuat backup source yang diganti dan snapshot SQLite melalui API backup, lalu memperbarui berkas secara atomik per berkas. Backup berada di /home/ramaatha/.procurement-backups/ dengan direktori privat; path lengkap dicetak sebagai BACKUP. Script tidak merotasi secret, mereset password, menjalankan seed, atau memigrasikan database. ALREADY_CURRENT berarti source sudah cocok dan tidak ditulis ulang. Pemulihan otomatis dicoba jika penulisan source gagal; jika console melaporkan kegagalan, periksa hasilnya sebelum melanjutkan. Pemeriksaan jumlah baris membantu membandingkan snapshot, tetapi tidak membuktikan tidak ada UPDATE bersamaan; penghentian seluruh penulis database tetap diperlukan.

VERIFY_OK berarti source serta static hasil collectstatic cocok dengan paket dan database masih dapat dibaca. Ini pemeriksaan filesystem/SQLite, bukan bukti login atau respons publik.

6. Aktifkan kembali aplikasi yang sama pada tab Web, lalu Reload.
7. Buka aplikasi dan lakukan hard refresh (Ctrl+F5).
8. Periksa breadcrumb, tombol proses, notifikasi tanpa bullet, dan form penerimaan: periode tidak tampil untuk Barang, tetap wajib untuk Jasa. Buka PO yang telah dibuat dan pastikan kemajuan transaksinya tetap sesuai sebelum pembaruan. Lanjutkan uji penerimaan/cetak dan Reload tanpa mengulang pembuatan data yang sudah ada.

### Pemulihan Source Paket v1

Jika source baru gagal bekerja, nonaktifkan sementara aplikasi yang sama, lalu jalankan:

```bash
(
set -e
cd /home/ramaatha
python3.12 procurement-update-20261024-v1.py rollback
source /home/ramaatha/.virtualenvs/procurement-demo/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings_pythonanywhere
cd /home/ramaatha/procurement-demo
python manage.py check
python manage.py collectstatic --noinput
)
```

ROLLBACK_OK mengembalikan source lama dari backup terakhir paket v1, termasuk menghapus hanya berkas baru yang dibuat paket. Database aktif tidak ditimpa dengan snapshot lama, sehingga transaksi setelah pembaruan tetap dipertahankan. Rollback berhenti jika source diedit lagi atau backup tidak sesuai. Setelah pemeriksaan berhasil, aktifkan kembali aplikasi dan Reload. Snapshot database tetap privat sebagai cadangan; jangan mengunggahnya ke repository atau folder static.
