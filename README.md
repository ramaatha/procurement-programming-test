# Procurement

Aplikasi web internal untuk mengelola pengadaan barang dan jasa dari pengajuan kebutuhan sampai penerimaan pesanan.

Fondasi Django sudah tersedia: akun dengan lima peran, login/logout, halaman akun yang memerlukan autentikasi, konfigurasi environment, dan migrasi SQLite. Schema untuk 14 entitas pengadaan, migrasi awal, parser angka, audit, dan helper token/replay sudah tersedia. Pemohon sudah dapat membuat dan mengubah draft, mengajukan permintaan dengan snapshot revisi, melihat riwayat, serta membatalkan permintaan sebelum ada PO. Approver sudah dapat menyetujui, meminta revisi, atau menolak revisi aktif. Procurement dapat mengembalikan permintaan disetujui untuk revisi sebelum ada PO. Procurement/admin sudah dapat mengelola vendor; procurement dapat mencatat, membandingkan dan memilih penawaran. PO serta penerimaan belum diimplementasikan. Admin sudah dapat membuat akun, mengubah peran/keaktifan, serta mereset password melalui halaman akun. Tampilan masih HTML fungsional; desain antarmuka final belum dikerjakan.

## Environment

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

Isi username dan password saat diminta. Akun ini memakai peran aplikasi ADMIN. Route `/admin/` tidak diaktifkan, dan status superuser tidak memberi pengecualian pada aturan bisnis. Pembuatan akun pertama memakai command line. Setelah login sebagai ADMIN, gunakan tautan Kelola akun pada beranda atau buka `/users/` untuk mengelola akun berikutnya. Admin aktif terakhir tidak dapat dinonaktifkan atau diubah perannya.

Jangan memakai password produksi untuk pengujian. Data contoh untuk seluruh alur pengadaan akan ditambahkan pada tahap berikutnya.

## Menjalankan aplikasi lokal

```powershell
& $python manage.py runserver 127.0.0.1:8000
```

Buka [halaman login lokal](http://127.0.0.1:8000/login/). Setelah login, halaman akun menampilkan username dan peran. Tombol Keluar mengakhiri sesi. Admin dapat membuka daftar akun, membuat akun, mengubah peran/status aktif, dan mereset password. Reset password mencabut sesi lama akun terkait; reset password sendiri mengakhiri sesi saat ini. Buka Daftar permintaan dari beranda untuk melihat data sesuai peran. Pemohon dapat membuat draft melalui `/requests/new/`. Draft boleh belum lengkap; setiap baris yang diisi harus lengkap, dengan jumlah dan harga positif. Simpan terlebih dahulu sebelum mengajukan. Pengajuan memerlukan header lengkap, tanggal kebutuhan hari ini atau setelahnya dalam WIB, serta minimal satu item. Setiap pengajuan menyimpan revisi yang tidak dapat diedit. Pembatalan memerlukan alasan dan hanya tersedia bagi pemilik sebelum ada PO. Approver membuka Antrean persetujuan pada `/approvals/`; permintaan sendiri tidak masuk antrean dan tidak boleh diputuskan sendiri setelah berganti peran. Review berlaku untuk revisi pengajuan aktif beserta plafonnya. Alasan wajib untuk meminta revisi atau menolak. Procurement dapat mengembalikan permintaan APPROVED sebelum ada PO dengan alasan; pemohon mengubah draft lalu mengajukan revisi berikutnya. Keputusan dan snapshot sebelumnya tetap dapat dibaca pada halaman revisi. Kelola vendor melalui `/vendors/`. Buka Penawaran dan pemilihan vendor pada detail permintaan untuk membandingkan harga serta waktu pemenuhan. Penawaran hanya ditulis untuk revisi aktif APPROVED sebelum PO; jumlah dan satuan mengikuti snapshot. Penawaran di luar tanggal berlaku atau plafon tetap dapat dicatat, tetapi tidak dapat dipilih. Pemilihan memerlukan alasan; jika hanya satu vendor yang layak, isi alasan sumber tunggal. Mengedit penawaran terpilih menghapus pilihan dan alasannya. Penerbitan PO belum tersedia. Hentikan server dengan Ctrl+C.

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

| Dokumen                                             | Isi                                       |
| --------------------------------------------------- | ----------------------------------------- |
| [PRD](docs/PRD.md)                                  | Kebutuhan dan kriteria penerimaan         |
| [Proses bisnis](docs/BUSINESS_PROCESS.md)           | Aktivitas, keputusan, dan transisi status |
| [Arsitektur](docs/ARCHITECTURE.md)                  | Modul, akses, transaksi, dan peta halaman |
| [Model data](docs/DATA_MODEL.md)                    | Entitas, snapshot, dan perhitungan        |
| [Rencana implementasi](docs/IMPLEMENTATION_PLAN.md) | Tugas, kontrak, dan pengujian             |
| [Alur kerja](docs/WORKFLOW.md)                      | Urutan pengerjaan dan kriteria selesai    |
| [Pedoman kualitas](docs/QUALITY_GUIDELINES.md)      | Kriteria kode, keamanan, dan antarmuka    |

## Hasil analisis

- [Diagram BPMN](outputs/Procurement_BPMN.pdf).
- [Diagram yang dapat diedit](outputs/Procurement_BPMN.drawio).
- [WBS](outputs/Procurement_WBS.xlsx), dengan tujuh modul dan 27 paket pekerjaan.

Dokumen analisis tidak menyatakan seluruh fitur sudah tersedia. Pengelolaan akun dan akses permintaan sesuai peran sudah tersedia; penerimaan FR-01 tetap menunggu seluruh modul dan pengujian alur lengkap. BPMN/WBS tidak diubah pada tahap permintaan ini.

## Struktur repository

- `accounts/`: model akun, form, view, route, migrasi, dan pengujian autentikasi.
- `config/`: konfigurasi Django dan pengujian environment.
- `common/`: parser/formatter angka, token aksi, pemeriksaan versi, replay, serta helper form dan respons error.
- `procurement/`: model data, migrasi, kontrak input, policy, selector, service/form/view permintaan, approval dan sourcing, pemeriksaan kelayakan penawaran, serta pengujian.
- `templates/`: HTML fungsional login, pengelolaan akun, daftar/form/detail permintaan, antrean persetujuan, snapshot revisi beserta keputusan, vendor dan penawaran.
- `docs/`: kebutuhan, proses, rancangan, dan hasil verifikasi.
- `outputs/`: hasil analisis.
- `var/`: database lokal yang diabaikan Git.
- `tmp/`: bukti pemeriksaan lokal yang diabaikan Git.

Buka folder repo langsung melalui Open Folder. [Panduan commit](docs/COMMIT_GUIDE.md) memuat pengelompokan berkas; staging, commit, dan push dilakukan pemilik repository.
