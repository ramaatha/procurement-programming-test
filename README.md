# Procurement

Aplikasi web internal untuk mengelola pengadaan barang dan jasa dari pengajuan kebutuhan sampai penerimaan pesanan.

Fondasi Django sudah tersedia: akun dengan lima peran, login/logout, halaman akun yang memerlukan autentikasi, konfigurasi environment, dan migrasi SQLite. Modul permintaan, approval, vendor, penawaran, PO, serta penerimaan belum diimplementasikan. Tampilan awal masih berupa HTML fungsional untuk memeriksa autentikasi.

## Kebutuhan lingkungan

- Python 3.12 dengan pip dan dukungan SQLite.
- Windows PowerShell untuk perintah di bawah.
- Database lokal dan virtual environment tidak disertakan ke Git.

Tidak ada build frontend pada tahap ini. Semua dependensi Python dipatok pada requirements. Tailwind belum menjadi dependensi.

## Menyiapkan aplikasi

Buka terminal pada folder repository. Jika `.venv` sudah tersedia pada checkout ini, langkah pembuatan environment akan dilewati. Untuk checkout baru, pastikan launcher `py -3.12` dapat menemukan Python 3.12.

```powershell
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 belum tersedia pada launcher py.' }
}
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Instalasi dependensi gagal.' }

if (-not $env:DJANGO_SECRET_KEY) {
    $env:DJANGO_SECRET_KEY = (& $python -c "import secrets; print(secrets.token_urlsafe(64))")
}
$env:DJANGO_DEBUG = 'true'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,[::1]'

& $python manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Migrasi gagal.' }
& $python manage.py check
```

Konfigurasi membaca environment. `.env.example` mendokumentasikan nama variabel; aplikasi tidak memuat file `.env` secara otomatis. Gunakan terminal yang sama untuk perintah selanjutnya. Secret yang dibuat di atas tersimpan pada environment terminal dan tidak ditampilkan. Mengganti secret akan mengakhiri sesi yang menggunakan secret sebelumnya.

Pada environment kerja yang telah disiapkan, Python tersedia melalui `.venv`. Ketersediaan Python pada launcher sistem berbeda dari ketersediaan interpreter di dalam virtual environment.

## Membuat akun pertama

```powershell
& $python manage.py createsuperuser --role ADMIN
```

Isi username dan password saat diminta. Akun ini memakai peran aplikasi ADMIN. Route `/admin/` tidak diaktifkan, dan status superuser tidak memberi pengecualian pada aturan bisnis. Halaman pengelolaan akun belum tersedia pada tahap ini; pembuatan akun pertama memakai command line.

Jangan memakai password produksi untuk pengujian. Data contoh untuk seluruh alur pengadaan akan ditambahkan pada tahap berikutnya.

## Menjalankan aplikasi lokal

```powershell
& $python manage.py runserver 127.0.0.1:8000
```

Buka [halaman login lokal](http://127.0.0.1:8000/login/). Setelah login, halaman akun menampilkan username dan peran. Tombol Keluar mengakhiri sesi. Hentikan server dengan Ctrl+C.

Server pengembangan hanya untuk penggunaan lokal. Mode `DEBUG=false` mewajibkan hostname eksplisit dan mengaktifkan HTTPS redirect serta Secure cookie. Deployment dan HTTPS pada lingkungan hosting belum diuji.

## Menjalankan pemeriksaan

Gunakan environment terminal dari langkah setup. Pastikan tidak ada proses lain yang menjalankan suite pada database test yang sama.

```powershell
& $python -m pip check
& $python manage.py check
& $python manage.py makemigrations --check --dry-run
& $python manage.py test -v 2
```

Database kerja berada pada `var/db.sqlite3`; test runner memakai `var/test.sqlite3`. `DJANGO_DATA_DIR` dapat menunjuk folder lain di dalam repository untuk pemeriksaan terisolasi. File SQLite dan journal-nya diabaikan Git. Hasil serta batas verifikasi tercatat pada [pengujian](docs/TESTING.md).

## Cakupan produk

Versi awal dirancang untuk satu tingkat approval, satu vendor dan maksimal satu PO per permintaan, penerimaan barang/jasa bertahap, serta riwayat keputusan dan perubahan. Stok gudang, invoice, dan pembayaran tidak termasuk. Bantuan input AI/Computer Vision tetap ditunda.

| Dokumen | Isi |
| --- | --- |
| [PRD](docs/PRD.md) | Kebutuhan dan kriteria penerimaan |
| [Proses bisnis](docs/BUSINESS_PROCESS.md) | Aktivitas, keputusan, dan transisi status |
| [Arsitektur](docs/ARCHITECTURE.md) | Modul, akses, transaksi, dan peta halaman |
| [Model data](docs/DATA_MODEL.md) | Entitas, snapshot, dan perhitungan |
| [Rencana implementasi](docs/IMPLEMENTATION_PLAN.md) | Tugas, kontrak, dan pengujian |
| [Alur kerja](docs/WORKFLOW.md) | Urutan pengerjaan dan kriteria selesai |
| [Pedoman kualitas](docs/QUALITY_GUIDELINES.md) | Kriteria kode, keamanan, dan antarmuka |

## Hasil analisis

- [Diagram BPMN](outputs/Procurement_BPMN.pdf).
- [Diagram yang dapat diedit](outputs/Procurement_BPMN.drawio).
- [WBS](outputs/Procurement_WBS.xlsx), dengan tujuh modul dan 27 paket pekerjaan.

Dokumen analisis tidak menyatakan seluruh fitur sudah tersedia. Status paket autentikasi penuh tetap menunggu pengelolaan akun dan izin objek pada tahap terkait. BPMN/WBS tidak diubah pada tahap fondasi ini.

## Struktur repository

- `accounts/`: model akun, form, view, route, migrasi, dan pengujian autentikasi.
- `config/`: konfigurasi Django dan pengujian environment.
- `templates/`: HTML fungsional login dan halaman akun.
- `docs/`: kebutuhan, proses, rancangan, dan hasil verifikasi.
- `outputs/`: hasil analisis.
- `var/`: database lokal yang diabaikan Git.
- `tmp/`: bukti pemeriksaan lokal yang diabaikan Git.

Buka folder repo langsung melalui Open Folder. [Panduan commit](docs/COMMIT_GUIDE.md) memuat pengelompokan berkas; staging, commit, dan push dilakukan pemilik repository.
