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

## Schema dan helper transaksi

Pesan: `feat: add procurement data model and transaction primitives`

Pilih berkas baru pada `common/` dan `procurement/`, termasuk pengujian, fixture, serta migrasi awal. Sertakan perubahan `config/settings.py`, `README.md`, `AGENTS.md`, dan dokumen yang diperbarui: ARCHITECTURE, DATA_MODEL, IMPLEMENTATION_PLAN, WORKFLOW, TESTING, serta panduan ini.

Jangan memasukkan database kerja/test, cadangan database, cache, log, atau isi `tmp/`. Diagram dan workbook tidak berubah pada tahap schema.

## Pengelolaan akun dan policy peran

Pisahkan implementasi dan dokumentasi menjadi dua commit.

Pesan kode: `feat: add admin account management and role policies`

Pilih `accounts/forms.py`, `accounts/policies.py`, `accounts/services.py`, `accounts/urls.py`, `accounts/views.py`, `accounts/tests/test_management.py`, `accounts/tests/test_permissions.py`, `procurement/tests/test_actions.py`, `templates/base.html`, serta `templates/accounts/home.html`, `user_list.html`, `user_form.html`, dan `user_password.html`.

Pesan dokumentasi: `docs: document account management and verification results`

Pilih `AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/TESTING.md`, `docs/WORKFLOW.md`, dan panduan ini. Database sintetis, screenshot, log dan isi tmp tidak disertakan. Tidak ada perubahan migrasi, dependency, diagram, atau workbook pada tahap ini.

## Draft, pengajuan dan pembatalan permintaan

Pisahkan menjadi dua commit, lalu push satu kali setelah keduanya selesai.

Pesan kode: `feat: add purchase requests and submitted revisions`

Pilih 25 berkas:

- `accounts/forms.py`
- `accounts/views.py`
- `common/forms.py`
- `common/http.py`
- `config/urls.py`
- `procurement/forms/__init__.py`
- `procurement/forms/requests.py`
- `procurement/policies.py`
- `procurement/selectors.py`
- `procurement/services/__init__.py`
- `procurement/services/requests.py`
- `procurement/templatetags/__init__.py`
- `procurement/templatetags/procurement_numbers.py`
- `procurement/tests/factories.py`
- `procurement/tests/test_actions.py`
- `procurement/tests/test_requests.py`
- `procurement/urls.py`
- `procurement/views/__init__.py`
- `procurement/views/requests.py`
- `templates/accounts/home.html`
- `templates/base.html`
- `templates/procurement/request_detail.html`
- `templates/procurement/request_form.html`
- `templates/procurement/request_list.html`
- `templates/procurement/request_revision.html`

Pesan dokumentasi: `docs: document request workflow and verification results`

Pilih 8 berkas:

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMIT_GUIDE.md`
- `docs/DATA_MODEL.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TESTING.md`
- `docs/WORKFLOW.md`

Setelah kedua commit dibuat, jalankan `git status -sb` dan pastikan tidak ada perubahan yang tertinggal. Kemudian `git push origin main`, dilanjutkan `git status -sb`; hasil yang diharapkan `## main...origin/main` tanpa ahead/behind. Jangan sertakan `.env`, `.venv`, `var`, database, cache, screenshot, log atau isi `tmp`. Tidak ada perubahan migration, dependency, diagram atau workbook pada tahap ini.

## Approval dan pengembalian untuk revisi

Buat dua commit berikut, kemudian push satu kali.

Pesan kode: `feat: add approval decisions and revision workflow`

Pilih 12 berkas:

- `procurement/forms/requests.py`
- `procurement/policies.py`
- `procurement/selectors.py`
- `procurement/services/requests.py`
- `procurement/tests/factories.py`
- `procurement/tests/test_approvals.py`
- `procurement/urls.py`
- `procurement/views/requests.py`
- `templates/accounts/home.html`
- `templates/procurement/approval_list.html`
- `templates/procurement/request_detail.html`
- `templates/procurement/request_revision.html`

Pesan dokumentasi: `docs: document approval workflow and verification results`

Pilih 8 berkas:

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMIT_GUIDE.md`
- `docs/DATA_MODEL.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TESTING.md`
- `docs/WORKFLOW.md`

Setelah kedua commit, periksa `git status -sb`: tidak ada perubahan tersisa dan branch menunjukkan dua commit di depan origin/main jika tidak ada commit lain. Jalankan `git push origin main`, lalu periksa kembali `git status -sb`; hasil yang diharapkan `## main...origin/main` tanpa ahead/behind. Jangan stage database, environment, cache, screenshot, log atau tmp. Migrasi, dependency, diagram dan workbook tidak berubah.

## Vendor, penawaran dan pemilihan

Buat dua commit, lalu push sekali setelah keduanya selesai.

Pesan kode: `feat: add vendors quotations and vendor selection`

Pilih 16 berkas:

- `procurement/forms/sourcing.py`
- `procurement/policies.py`
- `procurement/quotations.py`
- `procurement/selectors.py`
- `procurement/services/sourcing.py`
- `procurement/tests/factories.py`
- `procurement/tests/test_quotations.py`
- `procurement/tests/test_vendors.py`
- `procurement/urls.py`
- `procurement/views/sourcing.py`
- `templates/accounts/home.html`
- `templates/procurement/quotation_form.html`
- `templates/procurement/quotation_list.html`
- `templates/procurement/request_detail.html`
- `templates/procurement/vendor_form.html`
- `templates/procurement/vendor_list.html`

Pesan dokumentasi: `docs: document sourcing workflow and verification results`

Pilih 8 berkas:

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMIT_GUIDE.md`
- `docs/DATA_MODEL.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TESTING.md`
- `docs/WORKFLOW.md`

Sesudah kedua commit, jalankan `git status -sb` dan pastikan tidak ada perubahan tersisa. Jika tidak ada commit lain, branch menunjukkan ahead 2. Jalankan `git push origin main`, lalu `git status -sb`; hasil yang diharapkan `## main...origin/main` tanpa ahead/behind. Jangan stage environment, database, cache, log, screenshot atau tmp. Migrasi, dependency, diagram dan workbook tidak berubah.

## Penerbitan PO dan snapshot pesanan

Buat dua commit, kemudian push sekali setelah keduanya selesai.

Pesan kode: `feat: issue immutable purchase orders with concurrency guards`

Pilih 16 berkas:

- `procurement/forms/orders.py`
- `procurement/selectors.py`
- `procurement/services/orders.py`
- `procurement/tests/factories.py`
- `procurement/tests/order_workers.py`
- `procurement/tests/test_orders.py`
- `procurement/tests/test_order_concurrency.py`
- `procurement/urls.py`
- `procurement/views/orders.py`
- `procurement/views/requests.py`
- `templates/accounts/home.html`
- `templates/procurement/_order_snapshot.html`
- `templates/procurement/order_list.html`
- `templates/procurement/order_detail.html`
- `templates/procurement/order_print.html`
- `templates/procurement/request_detail.html`

Pesan dokumentasi: `docs: document purchase orders and verification results`

Pilih 8 berkas:

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMIT_GUIDE.md`
- `docs/DATA_MODEL.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TESTING.md`
- `docs/WORKFLOW.md`

Setelah kedua commit, jalankan `git status -sb` dan pastikan tidak ada perubahan tersisa. Jika tidak ada commit lain, branch menunjukkan ahead 2. Jalankan `git push origin main`, lalu periksa `git status -sb`; hasil yang diharapkan `## main...origin/main` tanpa ahead/behind. Jangan stage database, environment, cache, log, screenshot atau tmp. Migrasi, dependency, diagram dan workbook tidak berubah.
