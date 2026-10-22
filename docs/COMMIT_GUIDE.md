# Panduan commit

Staging, commit, dan push dilakukan pemilik repository. Periksa isi perubahan sebelum memilih berkas; saran berikut tidak menjalankan tindakan Git.

## Inisialisasi repository

Message: `chore: initialize procurement workspace`

Pilih:

- `.gitignore`
- `AGENTS.md`
- `docs/QUALITY_GUIDELINES.md`

## Dokumentasi dan hasil analisis

Message: `docs: add procurement requirements diagrams and technical design`

Pilih:

- `README.md`
- `docs/PRD.md`
- `docs/BUSINESS_PROCESS.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/WORKFLOW.md`
- `docs/COMMIT_GUIDE.md`
- `outputs/Procurement_BPMN.pdf`
- `outputs/Procurement_BPMN.drawio`
- `outputs/Procurement_WBS.xlsx`

Jika berkas tersebut sudah mempunyai commit dan perubahan hanya menyunting dokumentasi, gunakan pesan `docs: streamline procurement project documentation` dan pilih hanya Markdown yang berubah. Jangan memasukkan ulang artefak yang isinya tidak berubah.

## Pemeriksaan sebelum commit

1. Buka Source Control pada folder repository.
2. Stage berkas untuk satu kelompok perubahan dan periksa Staged Changes.
3. Pastikan perubahan sesuai pesan commit dan tidak memuat rahasia, database lokal, cache, log, atau isi tmp.
4. Buat commit, lalu ulangi untuk kelompok berikutnya.
5. Push setelah memeriksa commit lokal dan tujuan remote.

Fondasi akun/autentikasi sudah tersedia; modul pengadaan belum selesai. Commit dokumentasi tidak menyatakan seluruh aplikasi sudah selesai.

## Fondasi Django dan autentikasi

Pesan: `feat: bootstrap Django accounts and session authentication`

Pilih berkas baru dan perubahan terkait tahap ini:

- `.gitignore`
- `.env.example`
- `manage.py`
- `requirements.txt`
- `requirements-dev.txt`
- `config/` termasuk pengujian konfigurasi
- `accounts/` termasuk dua migrasi dan pengujian autentikasi/peran
- `templates/`
- `README.md`
- `AGENTS.md` jika pembaruan statusnya belum termasuk commit sebelumnya
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/WORKFLOW.md`
- `docs/TESTING.md`
- `docs/COMMIT_GUIDE.md`

Jangan pilih `.venv/`, `var/`, `tmp/`, `.env`, database SQLite, journal database, atau cache Python. Hasil BPMN/WBS tidak berubah pada tahap ini. Jika repository belum mempunyai commit, kelompok inisialisasi dan dokumentasi dapat dibuat lebih dahulu, lalu commit fondasi ini berisi berkas yang masih baru atau berubah.
