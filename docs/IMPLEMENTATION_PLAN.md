# Rencana implementasi Procurement

Pengerjaan mengikuti urutan tugas setelah rancangan dan rencana ditinjau. Checklist berubah hanya setelah pekerjaan beserta verifikasinya selesai. Staging, commit, dan push dilakukan pemilik repository.

**Tujuan:** Membangun aplikasi pengadaan barang/jasa yang menjalankan FR-01 sampai FR-13 dengan data, status, akses, dan riwayat yang konsisten.

**Arsitektur:** Satu aplikasi Django dengan templates dan SQLite. Service menjalankan mutasi melalui transaksi IMMEDIATE, versi aggregate, dan token aksi. Model menyimpan snapshot historis dan angka berskala integer.

**Stack:** Python 3.12, Django 5.2 LTS, SQLite, HTML/CSS/JavaScript lokal, Django test runner.

**Dokumen rancangan:** [Arsitektur](ARCHITECTURE.md), [model data](DATA_MODEL.md), [PRD](PRD.md), dan [proses bisnis](BUSINESS_PROCESS.md).

Status: Tugas 1 sampai 7 selesai untuk fondasi, schema, akun, permintaan, approval, sourcing dan PO, dengan 180 pengujian lulus. Tugas 8 sampai 11 belum dikerjakan. Django telah dipilih; keputusan lanjutan tetap mengikuti rancangan terkait. Pengerjaan dilakukan berurutan, satu tugas sampai hasilnya terverifikasi. Arah visual ditinjau sebelum styling pada tugas 10. HTML semantik pada tugas awal adalah prototipe fungsional untuk menguji alur, belum UI final.

## Batas yang berlaku pada semua tugas

- Gunakan Python 3.12 dan Django 5.2 LTS; baseline dependensi 5.2.18. Periksa patch saat instalasi lalu patok versi tepat hasil instalasi terverifikasi.
- SQLite pada `var/db.sqlite3`, `transaction_mode="IMMEDIATE"`, `timeout=5`, dan `ATOMIC_REQUESTS=False`. Dukungan PostgreSQL belum diimplementasikan atau diklaim.
- Satu organisasi; role REQUESTER/APPROVER/PROCUREMENT/RECEIVER/ADMIN. Tidak ada persetujuan atau penutupan PO oleh pemohon sendiri, termasuk setelah berganti peran.
- Satu PO sepanjang riwayat request. Request tetap APPROVED setelah PO terbit. Pemenuhan mengikuti status PO.
- IDR; qty maksimal tiga desimal, uang maksimal dua desimal, total baris half-up dua desimal. Penyimpanan integer mengikuti DATA_MODEL.
- Snapshot revisi/PO dan penerimaan final tidak dapat diedit/dihapus melalui aplikasi. Audit serta ActionReceipt ditulis pada transaksi bisnis yang sama.
- GET membaca; POST memutasi dengan CSRF, policy server, token, dan versi. Kegagalan tidak boleh menyimpan sebagian perubahan.
- Semua input/output mengikuti allowlist. Tidak mencatat password, token, cookie, atau payload form bebas pada log/audit.
- Tidak ada stok, pembayaran, unggah berkas, portal vendor, pengiriman email otomatis, atau fitur AI pada implementasi wajib.
- Setiap tugas: test perilaku gagal dahulu, implementasi minimal, test lulus, lalu pemeriksaan alur HTTP terkait. Tidak menulis test yang hanya menyalin implementasi.
- Agent tidak menjalankan staging, commit, atau push. Pesan commit pada rencana adalah saran untuk pengguna setelah verifikasi.

## Fokus review lintas tugas

| Kasus                                                                      | Perilaku yang harus terbukti                                                | Pemilik             |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------- |
| Dua tab memakai versi lama atau satu token dengan payload berbeda          | 409, tidak menimpa perubahan atau menggandakan hasil                        | Tugas 2, 4, 5, 7, 8 |
| Role berubah setelah form dibuka atau pemohon menjadi approver             | Izin dibaca ulang; self-approval/penutupan sendiri tetap ditolak            | Tugas 3 dan 5       |
| Nilai dengan tiga desimal qty, half-cent, NaN, eksponen, atau overflow     | Hasil half-up konsisten; input invalid ditolak sebelum penyimpanan          | Tugas 2, 4, 6, 8    |
| Dua penulis menyentuh PO/sisa yang sama atau pembatalan melawan penerbitan | Satu hasil valid pada versi tersebut, rollback utuh untuk aksi lain         | Tugas 7 dan 8       |
| Submit gagal, JavaScript mati, atau layar kecil                            | Input aman tetap tersedia; alur dapat dilanjutkan; tidak ada tindakan palsu | Tugas 10 dan 11     |

## Struktur dan kontrak bersama

File produksi mengikuti ARCHITECTURE. Setiap package mempunyai `__init__.py`; model dan fungsi publik diekspor secara eksplisit. `procurement/inputs.py` mendefinisikan frozen dataclass berikut sebelum service memakainya:

| Tipe                                   | Field dan makna                                                                                                                                                   |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ActionContext` di `common/actions.py` | `actor_id: int`, `nonce: UUID`, `expected_version: int \| None`; view menetapkan actor dari session dan memverifikasi scope token                                 |
| `RequestLineInput`                     | `name: str`, `unit: str`, `quantity: str`, `unit_price: str`                                                                                                      |
| `DraftInput`                           | `kind: str`, `title: str`, `reason: str`, `destination: str`, `needed_on: date \| None`, `items: tuple[RequestLineInput, ...]`                                    |
| `QuoteLineInput`                       | `revision_item_id: UUID`, `unit_price: str`                                                                                                                       |
| `QuotationInput`                       | `vendor_id: UUID`, `reference: str`, `quoted_on: date`, `valid_until: date`, `fulfillment_days: int`, `items: tuple[QuoteLineInput, ...]`                         |
| `ReceiptLineInput`                     | `order_item_id: UUID`, `accepted: str`, `rejected: str`, `rejection_reason: str`                                                                                  |
| `ReceiptInput`                         | `reference: str`, `notes: str`, `evidence_type: str`, `service_started_on: date \| None`, `service_ended_on: date \| None`, `items: tuple[ReceiptLineInput, ...]` |

Seluruh service mengembalikan instance model hasil yang sudah commit. Conflict memakai `common.errors.ConflictError`; validasi memakai Django `ValidationError` berisi field/non-field errors; otorisasi memakai `PermissionDenied`. Mapping HTTP mengikuti ARCHITECTURE. Tidak ada fungsi service yang menerima status/total/pemilik langsung dari browser.

Factory test di `procurement/tests/factories.py` menyediakan `user(role: str) -> User`, `draft(owner: User, *, kind: str = "GOODS") -> PurchaseRequest`, `approved(owner: User, approver: User, *, kind: str = "GOODS") -> PurchaseRequest`, dan `issued(*, quantity: str = "10", kind: str = "GOODS") -> PurchaseOrder`. Factory menggunakan service setelah tersedia; fixture infrastruktur awal boleh membuat row minimum langsung untuk menguji constraint, tanpa menjadi jalur produksi. `context(actor: User, target: Model, *, nonce: UUID | None = None) -> ActionContext` membaca versi target saat dipanggil.

Perintah pada tugas berikut merupakan perintah rencana, belum bukti bahwa file atau test sudah ada. Test class/method bernama TC pada tiap tugas menjadi pemetaan skenario PRD. Satu ID dapat membutuhkan beberapa method.

## Tugas 1: Proyek berjalan dan autentikasi dasar

**Kebutuhan:** FR-01, FR-13; BP-00; WBS 1.4, 2.1, 6.1; TC-01, TC-02, TC-19.

**Berkas:** buat `manage.py`, `config/{settings,urls,wsgi,asgi}.py`, `accounts/{apps,models,forms,views,urls}.py`, `accounts/migrations/0001_initial.py`, `accounts/tests/test_auth.py`, `templates/registration/login.html`, dan `templates/base.html`. Perbarui `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `.env.example`, serta README. UI sementara cukup HTML semantik untuk menguji login, belum rancangan visual final.

**Kontrak:** custom `accounts.User`, AUTH_USER_MODEL ditetapkan sebelum migrasi pertama, lima role valid, session login/logout. Tidak ada Django admin atau registrasi publik. Pengguna anonim ke halaman internal diarahkan ke login; akun nonaktif ditolak.

- [x] Siapkan virtualenv, periksa Python/SQLite/JSON1, pasang Django patch terverifikasi, lalu catat versi tepat runtime/transitif. Dokumentasikan environment dan cara mengisi SECRET_KEY tanpa rahasia di Git. Buat var dan tetapkan database test `var/test.sqlite3` yang berbeda dari `var/db.sqlite3`; suite concurrency tidak memakai in-memory.
- [x] Tulis `AuthTests.test_TC01_login_logout`, `test_TC01_inactive_account`, `test_TC02_anonymous_redirect`, dan `test_TC01_logout_requires_post`. Assert session terbentuk/berakhir, inactive tidak login, logout GET 405, dan `next=https://example.invalid` tidak mengalihkan keluar aplikasi.
- [x] Jalankan `python manage.py test accounts.tests.test_auth -v 2`; periksa kegagalan sesuai perilaku yang belum dibuat. Implementasikan login/logout/session dan migrasi User.
- [x] Jalankan test yang sama, `python manage.py check`, dan `python manage.py migrate`. Semua lulus, tanpa warning migrasi/model. Buka login melalui runserver loopback; ini belum uji alur Procurement.
- [x] Siapkan daftar berkas tugas untuk commit pengguna: `chore: bootstrap Django project and session authentication`.

Bukti tahap: [TESTING](TESTING.md). Tersedia dua migrasi akun: struktur awal dan penambahan constraint role/version. Perintah setup/admin juga diperiksa pada database terisolasi. Checklist commit berarti saran berkas/pesan sudah disiapkan; staging, commit dan push tetap dilakukan pemilik repository.

## Tugas 2: Model, angka, audit, dan protokol aksi

**Kebutuhan:** AS-07, AS-08, AS-12; FR-02, FR-07, FR-08, FR-12; WBS 1.5, 2.2, 3.4, 4.1, 5.2; TC-04, TC-06, TC-11, TC-13, TC-18.

**Berkas:** buat seluruh `procurement/models/*.py`, migrasi yang diperlukan, `procurement/inputs.py`, `common/{actions,errors,numbers}.py`, `common/tests/test_numbers.py`, `procurement/tests/{factories,test_constraints,test_actions}.py`. Buat paket dan AppConfig serta daftarkan app pada settings.

**Kontrak:** `parse_quantity(value: str, *, allow_zero: bool = False) -> int`, `parse_money(value: str) -> int`, `line_total(qty_milli: int, unit_price_minor: int) -> int`, `format_quantity(value: int) -> str`, `format_money(value: int) -> str`. Harga harus positif; allow_zero hanya dipakai untuk accepted/rejected. Formatter mengeluarkan desimal baku dengan tiga digit qty atau dua digit uang; presentasi Indonesia dilakukan helper template terpisah. Form angka memakai field teks dan parser yang sama, lalu menghasilkan string kanonik pada input dataclass. `make_action_token(*, actor_id: int, target_type: str, target_key: str, action: str) -> str` dan `load_action_token(token: str, *, actor_id: int, target_type: str, target_key: str, action: str) -> UUID` menggunakan signing Django dan TTL 86.400 detik. `payload_hash(payload: dict) -> str` menerima payload whitelist yang sudah dikanonisasi; password dilarang masuk helper ini.

- [x] Tulis NumbersTests TC-04 dengan assertion `parse_quantity("0.333") == 333`, `parse_money("0.05") == 5`, `line_total(333, 5) == 2`, `line_total(1, 1) == 0`, dan `line_total(500, 1) + line_total(500, 1) == 2`. Uji penolakan presisi berlebih, float, `NaN`, `Infinity`, `1e3`, negatif, dan hasil di atas int64.
- [x] Tulis ConstraintTests untuk unique request/revision, keputusan tunggal, PO tunggal, item asing/berulang, check nilai negatif, dan FK historis PROTECT. Uji minimum baris pada service, bukan menganggap DB menjaganya.
- [x] Tulis ActionTokenTests untuk scope aktor/target/action salah, token kedaluwarsa, tampering, canonical hash, serta aturan replay. Test mekanisme transaksi memakai aksi fixture yang menulis AuditEvent dan ActionReceipt lalu sengaja gagal; assert keduanya rollback.
- [x] Jalankan `python manage.py test common.tests procurement.tests.test_constraints procurement.tests.test_actions -v 2` hingga melihat kegagalan yang relevan, implementasikan kontrak/model, lalu ulangi hingga lulus. Buat migrasi dan jalankan `python manage.py makemigrations --check --dry-run` sesudahnya.
- [x] Siapkan commit pengguna: `feat: add procurement data model and transaction primitives`. Tahap ini belum membuktikan seluruh aturan bisnis service.

Bukti tahap: [TESTING](TESTING.md). Migrasi awal memuat 14 model; siklus migrasi maju, rollback dan penerapan ulang diperiksa pada database terpisah. Penolakan item yang ada tetapi milik aggregate lain, minimum baris, dan jumlah kumulatif tetap diperiksa service pada tugas terkait.

## Tugas 3: Pengelolaan akun dan policy

**Kebutuhan:** FR-01, FR-12; BP-00; WBS 2.1, 5.2; TC-02, TC-18.

**Berkas:** tambah `accounts/{policies,services}.py`, `accounts/tests/{test_management,test_permissions}.py`, template `accounts/user_{list,form,password}.html`, dan route akun.

**Kontrak:** `save_user(ctx: ActionContext, *, user_id: int | None, username: str, role: str, is_active: bool, initial_password: str | None = None) -> User`; `reset_password(ctx: ActionContext, *, user_id: int, new_password: str) -> User`. Pembuatan user memerlukan password valid; edit biasa tidak mengubah password. Policy `require_role(actor: User, *roles: str) -> None` tidak menerima role browser atau bypass superuser.

- [x] Tulis TC-02: admin dapat mengelola akun; empat role lain mendapat 403; nonaktif kehilangan akses; perubahan role dari tab lain terbaca ulang; username duplikat/role invalid ditolak; password tersimpan hashed dan tidak muncul dalam audit/log.
- [x] Tulis create akun dengan password awal dan reset password dengan nonce sama dua kali: pertama sukses, kedua 409, tanpa menyimpan hash payload password. Uji stale version dan token yang milik admin lain.
- [x] Jalankan `python manage.py test accounts.tests -v 2` untuk red, implementasikan service/form/policy dan POST handler, lalu green. Form tidak memaparkan is_superuser/is_staff sebagai field editable.
- [x] Siapkan commit pengguna: `feat: add role based account management`.

Bukti tahap: [TESTING](TESTING.md). Halaman akun memakai HTML fungsional. Admin terakhir dijaga oleh transaksi IMMEDIATE; perubahan serentak diuji dengan dua koneksi SQLite berbasis file. Tidak ada migrasi baru pada tahap ini.

## Tugas 4: Draft, revisi pengajuan, dan pembatalan sebelum PO

**Kebutuhan:** FR-02, sebagian FR-10; BP-01, BP-02, BP-14; WBS 2.2, 4.3; TC-03, TC-04, TC-15.

**Berkas:** `procurement/services/requests.py`, `forms/requests.py`, `views/requests.py`, `policies.py`, `selectors.py`, `urls.py`, `tests/test_requests.py`, `templates/procurement/request_{list,form,detail,revision}.html`.

**Kontrak:** `save_draft(ctx: ActionContext, *, request_id: UUID | None, data: DraftInput) -> PurchaseRequest`; `submit_request(ctx: ActionContext, *, request_id: UUID) -> PurchaseRequest`; `cancel_request(ctx: ActionContext, *, request_id: UUID, reason: str) -> PurchaseRequest`. Selector `visible_requests(actor: User) -> QuerySet[PurchaseRequest]` menjadi dasar daftar maupun detail.

- [x] Tulis TC-03: draft boleh header belum lengkap dan belum ada item; submit wajib semua field/item serta tanggal kebutuhan >= hari WIB saat submit. Baris yang ditambahkan harus lengkap/positif; blank extra form tidak dianggap item. Pemilik dari session, total dari server.
- [x] Tulis TC-04: contoh pembulatan pada DATA_MODEL konsisten; submit membuat snapshot lengkap. TC-15: hanya pemilik, status yang diizinkan, alasan wajib; terminal tidak aktif ulang. Form invalid tidak menambah revisi/audit sukses.
- [x] Tulis replay create/save/submit/cancel dan stale-version; token create sama tidak membuat dua draft. Uji ID request pengguna lain melalui URL dan form (TC-02).
- [x] Jalankan `python manage.py test procurement.tests.test_requests -v 2` untuk red, implementasikan service/route/form, lalu green. Uji HTTP menggunakan CSRF checks dan verify database sesudah POST.
- [x] Siapkan commit pengguna: `feat: add purchase requests and submitted revisions`.

Bukti tahap: [TESTING](TESTING.md). Sebanyak 28 pengujian baru mencakup service, HTTP dan pengajuan serentak. Alur browser memakai database terpisah; styling final dan keputusan approval belum tersedia.

## Tugas 5: Review approval dan kembali ke revisi

**Kebutuhan:** FR-03, sebagian FR-06; BP-03, BP-07, GW-01; WBS 2.3, 3.3; TC-05, TC-06, TC-10.

**Berkas:** perluas service/form/view requests, `tests/test_approvals.py`, `templates/procurement/approval_list.html`, serta panel keputusan/detail.

**Kontrak:** `review_request(ctx: ActionContext, *, request_id: UUID, decision: str, reason: str) -> PurchaseRequest`; `request_revision(ctx: ActionContext, *, request_id: UUID, reason: str) -> PurchaseRequest`. Decision menerima hanya APPROVE/REQUEST_CHANGES/REJECT. Request_revision hanya procurement, APPROVED, belum ada PO.

- [x] Tulis TC-05 semua cabang gateway dan alasan wajib. TC-06: pemohon yang berganti role APPROVER tetap dilarang review; keputusan dua kali, versi lama, serta user yang baru dinonaktifkan ditolak.
- [x] Tulis TC-10: APPROVED dikembalikan procurement, kandidat terhapus, working copy boleh berubah, submit menaikkan revisi, snapshot/keputusan lama tetap sama. Revisi yang sudah memiliki PO ditolak pada tugas 7.
- [x] Jalankan `python manage.py test procurement.tests.test_approvals -v 2` untuk red, implementasikan, lalu green. Uji antrean tidak menyertakan request milik approver sendiri dan keputusan tidak tersedia pada status lain.
- [x] Siapkan commit pengguna: `feat: add approval decisions and revision workflow`.

Bukti tahap: [TESTING](TESTING.md). Sebanyak 23 test baru memeriksa service, HTTP dan keputusan serentak; alur revisi lintas peran diperiksa pada browser dengan database terpisah. Guard PO diuji memakai fixture, termasuk PO terminal. Tidak ada migrasi atau dependency baru.

## Tugas 6: Vendor, penawaran, dan pemilihan

**Kebutuhan:** FR-04, FR-05, FR-06; BP-04 sampai BP-07, GW-02/GW-03; WBS 3.1, 3.2, 3.3; TC-07, TC-08, TC-09, TC-10.

**Berkas:** `services/sourcing.py`, `forms/sourcing.py`, `views/sourcing.py`, `tests/{test_vendors,test_quotations}.py`, template `vendor_{list,form}.html`, `quotation_{list,form}.html`.

**Kontrak:** `save_vendor(ctx: ActionContext, *, vendor_id: UUID | None, name: str, contact: str, is_active: bool) -> Vendor`; `save_quotation(ctx: ActionContext, *, request_id: UUID, quotation_id: UUID | None, data: QuotationInput) -> Quotation`; `select_quotation(ctx: ActionContext, *, request_id: UUID, quotation_id: UUID, reason: str, single_source_reason: str) -> PurchaseRequest`. Quotation mutation memakai expected_version request, bukan version quote terpisah.

- [x] Tulis TC-07 izin vendor aktif/nonaktif dan riwayat. TC-08 menolak item hilang/duplikat/revisi asing, harga invalid, tanggal terbalik, request belum APPROVED, dan tampered qty/unit.
- [x] Tulis TC-09 satu sumber memerlukan alasan, harga terendah tidak otomatis dipilih, kandidat aktif hanya satu. Mengedit kandidat menghapus pemilihan/alasan; penawaran lama tidak dapat dipakai setelah revisi baru (TC-10).
- [x] Jalankan `python manage.py test procurement.tests.test_vendors procurement.tests.test_quotations -v 2` untuk red, implementasikan, lalu green. Pastikan perbandingan menampilkan total dan waktu pemenuhan dari baris/revisi yang sama, termasuk keadaan belum ada penawaran.
- [x] Siapkan commit pengguna: `feat: add vendors quotations and vendor selection`.

Bukti tahap: [TESTING](TESTING.md). Sebanyak 28 test baru mencakup vendor, penawaran, pemilihan, HTTP/replay dan dua penulis. Alur browser memakai database terpisah. Label pilihan diperjelas dengan total/waktu/masa berlaku setelah regresi; dua optimasi query daftar besar dicatat untuk tugas 10. Tidak ada migrasi atau dependency baru.

## Tugas 7: Penerbitan PO dan snapshot

**Kebutuhan:** FR-07, sebagian FR-10; BP-08/BP-09, GW-03; WBS 3.4, 4.3; TC-11, TC-15.

**Berkas:** `services/orders.py`, `forms/orders.py`, `views/orders.py`, `tests/{test_orders,test_order_concurrency}.py`, template `order_{list,detail,print}.html`.

**Kontrak:** `issue_order(ctx: ActionContext, *, request_id: UUID) -> PurchaseOrder`. expected_version adalah versi request. Cetak PO hanya GET snapshot, tanpa mutasi atau pengiriman eksternal.

- [x] Tulis TC-11 approval/revisi salah, vendor nonaktif, quote masa depan/kedaluwarsa, plafon terlewati, kandidat kosong, alasan tunggal yang belum ada, serta payload manipulasi. Assert satu PO, seluruh item/header snapshot, satu audit, dan replay mengembalikan PO sama.
- [x] Tulis TC-11/TC-15 concurrency dengan dua koneksi terpisah pada SQLite file: dua issue dengan token berbeda; cancel request vs issue; vendor deactivate vs issue. Assert hasil mengikuti transaksi yang menang, tidak ada PO ganda atau request CANCELLED dengan PO aktif.
- [x] Jalankan `python manage.py test procurement.tests.test_orders procurement.tests.test_order_concurrency -v 2` untuk red, implementasikan, lalu green. Pakai `TransactionTestCase`, koneksi per thread, timeout/join terbatas; jangan menaruh barrier sesudah memperoleh write lock. Test harus menegaskan aksi apa yang sukses dan error apa yang terjadi, bukan hanya jumlah row akhir.
- [x] Uji snapshot tidak berubah sesudah vendor diedit. Pastikan request tetap APPROVED, revisi/cancel request pasca-PO ditolak, dan PO terminal tidak membuka kesempatan PO kedua.
- [x] Siapkan commit pengguna: `feat: issue immutable purchase orders with concurrency guards`.

Bukti tahap: [TESTING](TESTING.md). Sebanyak 21 test baru mencakup service/HTTP, tiga skenario race dan batas waktu harness. Race dua koneksi berjalan dalam subprocess dengan penghentian proses dan join terbatas; regresi worker macet lulus. Alur browser serta snapshot detail/cetak diperiksa. Dialog printer/ekspor PDF belum diuji. Tidak ada migrasi atau dependency baru.

## Tugas 8: Penerimaan dan penutupan PO

**Kebutuhan:** FR-08, FR-09, FR-10; BP-10 sampai BP-15, GW-04/GW-05/GW-06; WBS 4.1, 4.2, 4.3; TC-12, TC-13, TC-14, TC-16.

**Berkas:** `services/receipts.py`, `forms/receipts.py`, `views/receipts.py`, perluas orders, `tests/{test_receipts,test_services_receipts,test_closure,test_receipt_concurrency}.py`, template `receipt_{form,detail}.html`, dan form penutupan pada detail PO.

**Kontrak:** `post_receipt(ctx: ActionContext, *, order_id: UUID, data: ReceiptInput) -> Receipt`; `close_order(ctx: ActionContext, *, order_id: UUID, reason: str) -> PurchaseOrder`. Keduanya memakai versi PO. Close menentukan CANCELLED/CLOSED_SHORT dari accepted, tidak menerima target status dari browser.

- [x] TC-12/TC-13: ordered 10; accepted 6/rejected 2 menyisakan 4; accepted 4 berikutnya menyelesaikan PO. Uji rejected saja tetap ISSUED, alasan penolakan wajib, receipt seluruh nol ditolak, baris negatif/asing/duplikat/accepted berlebih menggagalkan seluruh posting.
- [x] TC-14: jasa memakai unit pesanan, bukti dan periode wajib, awal <= akhir <= hari konfirmasi WIB. Tidak ada mutasi stok atau persentase tambahan. Konfirmasi waktu berasal dari server.
- [x] TC-16: approver selain pemohon membatalkan accepted nol, atau menutup sisa setelah partial; remaining historis tidak menjadi nol. Status terminal menolak receipt/edit/penutupan kedua.
- [x] Tulis concurrency TC-13/TC-16: dua receipt accepted 6 untuk ordered 10 dengan versi sama, replay token sama, serta close vs receive. Gunakan SQLite file dan koneksi terpisah. Fault injection audit harus mengembalikan jumlah receipt/item/status/version ke nilai sebelum transaksi.
- [x] Jalankan `python manage.py test procurement.tests.test_receipts procurement.tests.test_services_receipts procurement.tests.test_closure procurement.tests.test_receipt_concurrency -v 2` untuk red, implementasikan, lalu green. Test receipt bukan sekadar mock selector; baca jumlah/status database yang sudah commit.
- [x] Siapkan commit pengguna: `feat: add goods services receipts and order closure`.

Bukti tahap: [TESTING](TESTING.md). Service dan HTTP mencakup barang/jasa, pemenuhan bertahap, penutupan, replay, rollback, multi-item dan dua koneksi SQLite terpisah. Pemformatan agregat penolakan historis diperiksa dengan nilai melampaui batas satu baris. Pemeriksaan browser dan UI final belum dilakukan pada tahap ini. Tidak ada migrasi atau dependency baru.

## Tugas 9: Tracking, query, dan audit yang dapat ditelusuri

**Kebutuhan:** FR-11; BP-16; WBS 5.1; TC-17, sebagian TC-02.

**Berkas:** `selectors.py`, `views/tracking.py`, `tests/test_tracking.py`, template daftar/detail/riwayat dan helper presentasi `procurement/templatetags/procurement_display.py`.

**Kontrak:** `operational_stage(request: PurchaseRequest) -> str`, `order_balances(order: PurchaseOrder) -> dict[UUID, dict[str, int]]` dengan key `ordered_milli/accepted_milli/rejected_milli/remaining_milli`; `visible_orders(actor: User) -> QuerySet[PurchaseOrder]`. Labels Indonesia berasal dari mapping status tunggal.

- [x] Tulis TC-17 pencarian nomor/judul, gabungan filter jenis/tahap, pagination 25, input filter invalid, audit kronologis, dan tidak bocor data lintas pemohon. Penerima bisa membaca PO terminal, tetapi tidak request pra-PO.
- [x] Assert request APPROVED dengan PO CLOSED_SHORT ditampilkan sebagai selesai dengan kekurangan, remaining tetap ada, dan tidak dilabeli penerimaan lengkap. Header/detail memakai sumber jumlah sama.
- [x] Jalankan `python manage.py test procurement.tests.test_tracking -v 2` untuk red, implementasikan, lalu green. Periksa query relasi dengan data multi-item; gunakan prefetch tanpa menetapkan klaim performa yang belum diukur.
- [x] Siapkan commit pengguna: `feat: add procurement tracking and audit history`.

Bukti tahap: [TESTING](TESTING.md). Pencarian/filter berjalan setelah scope akses, daftar/audit memakai paginasi 25, dan label serta perhitungan dipusatkan. Validasi server/HTTP tersedia; browser dan UI final tetap pada tugas 10. Tidak ada migrasi atau dependency baru.

## Tugas 10: UI per peran, aksesibilitas, dan penanganan kegagalan

**Kebutuhan:** FR-12 serta permukaan UI FR-01 sampai FR-11; WBS 1.6, 5.2; TC-18.

**Berkas:** `static/css/app.css`, `static/js/forms.js`, template seluruh alur, error handler di config/views terkait, `tests/test_http_errors.py`, `docs/DESIGN_SYSTEM.md`, dan bukti browser dalam tmp. Dokumen desain dibuat setelah arah visual ditinjau, tidak berdasarkan asumsi bahwa warna/font sudah disepakati.

**Kontrak:** style yang konsisten untuk form/list/detail; fallback submit tanpa JavaScript; error 400/403/404/409/503/500 seperti ARCHITECTURE. Token/versi tidak hilang saat field invalid. Loading berlaku pada submit atau blok async yang benar-benar ada.

- [x] Terapkan arah Operations Desk pada antrean, detail dan form, lalu perluas kerangka bersama ke halaman lainnya. Sistem desain mencatat identitas, tema, tipografi dan alasan komposisi.
- [x] Tambahkan TC-18 untuk input/error summary, management form negatif, scope antrean dan error aman. Regresi 409/503, Retry-After, CSRF dan GET action tetap berjalan dalam suite modul terkait. Suite akhir lulus 227 test.
- [x] Periksa lima peran pada browser dengan enam lebar, termasuk 390/768/1440. Catat interaksi, tanpa JavaScript, klik berulang, pemulihan Back, focus dan reduced motion. Matriks terakhir mencakup 85 halaman/peran; cabang yang belum diulang melalui klik tetap disebutkan pada TESTING.
- [x] Periksa screenshot, kontras dan overflow, serta perbaiki temuan menu tanpa JavaScript melalui regresi gagal lalu lulus. Simpan bukti di tmp dan catat batas perangkat/pembaca layar/cetak.
- [x] Siapkan tiga kelompok perubahan untuk commit pengguna: implementasi antarmuka, pemformatan yang memahami Django, dan dokumentasi. Staging, commit dan push tetap dilakukan pengguna.

Bukti tahap: [TESTING](TESTING.md). Tidak ada migrasi atau paket runtime baru. Comparison rows dibangun setelah paginasi, pembacaan item PO diprefetch, dan label snapshot mengikuti mapping operasional. Dua temuan P3 dari review tetap terbuka: parameter paginasi dua daftar penawaran saling mereset, dan panel tindakan mobile berada setelah rincian panjang. Optimasi query snapshot saat menilai banyak kandidat juga belum selesai. Penyempurnaan tersebut masuk pemeriksaan akhir Tugas 11; hasil lokal ini belum membuktikan deployment atau kapasitas produksi.

## Tugas 11: Instalasi bersih, demo, panduan pengguna, dan dokumentasi akhir

**Status: rancangan, belum dieksekusi.** Penambahan cakupan di bawah hanya menjadi rencana kerja. Akun demo, data contoh, command seed, dan panduan pengguna belum dibuat pada pembaruan ini.

**Kebutuhan:** FR-13 dan regresi seluruh kebutuhan; WBS 6.1 beserta paket pengujian/dokumentasi modul 6; TC-19 dan TC-01 sampai TC-18.

**Berkas yang direncanakan:** `procurement/management/commands/seed_demo.py` beserta initializer package yang diperlukan, `procurement/tests/test_demo_setup.py`, `docs/USER_GUIDE.md`, README, `.env.example`, requirements bila diperlukan, dan `docs/TESTING.md`. PRD/proses/BPMN/WBS disesuaikan hanya bila perilaku aktual berubah. File output tetap langsung pada outputs tanpa folder ID sesi. Panduan pengguna direncanakan sebagai Markdown yang ditautkan dari README; ekspor PDF bukan syarat penyelesaian tahap ini.

**Kontrak:** `python manage.py seed_demo` memakai `DEMO_PASSWORD` dari environment untuk akun demo baru dan mengikuti validator password aplikasi. Command tidak menghapus data atau mereset password, peran maupun transaksi yang sudah ada. Akun dan dokumen demo mempunyai identitas yang dapat dikenali pada pemanggilan berikutnya. Benturan dengan data yang bukan milik seed dilaporkan tanpa mengambil alih atau menimpanya. Semua transaksi contoh dibuat melalui service dan izin peran yang tersedia, termasuk snapshot, audit, versi dan hasil aksi.

### Akun dan data demo

Sediakan lima akun dengan identitas demo yang jelas:

| Akun rencana | Peran | Tujuan pengujian |
| --- | --- | --- |
| `demo_admin` | ADMIN | Pengelolaan akun/vendor dan pembacaan transaksi |
| `demo_pemohon` | REQUESTER | Draft, pengajuan, revisi dan pembatalan sebelum PO |
| `demo_approver` | APPROVER | Keputusan atas pengajuan pengguna lain dan penutupan PO |
| `demo_procurement` | PROCUREMENT | Penawaran, perbandingan, pemilihan vendor dan penerbitan PO |
| `demo_penerima` | RECEIVER | Penerimaan barang/jasa serta pembacaan hasil pemenuhan |

Password akun baru berasal dari environment, bukan password pribadi atau nilai rahasia dalam repo. Panduan menjelaskan cara menetapkannya saat setup lokal. Bila tersedia demo online, alamat dan kredensial demo yang boleh dibagikan disampaikan oleh pemilik proyek melalui kanal pengumpulan; rencana ini tidak mengizinkan pengiriman pesan atau deployment.

Gunakan database demo terpisah, misalnya melalui `DJANGO_DATA_DIR` yang menunjuk `var/demo`, dan jelaskan pemilihan database itu pada setup. Akun/transaksi kerja yang sudah ada tetap dipertahankan. Siapkan vendor serta penawaran yang diperlukan untuk lima skenario berikut:

| Label skenario | Contoh | Keadaan awal yang bisa dilihat |
| --- | --- | --- |
| G-01 | Permintaan barang draft | Bisa diedit dan diajukan oleh pemohon |
| J-01 | Permintaan jasa disetujui, belum ada PO | Siap dicatat penawarannya oleh procurement |
| G-02 | PO barang terbit | Tampil di daftar PO dan siap diterima |
| G-03 | PO barang diterima sebagian | Dipesan 10, diterima 6, ditolak 2, sisa 4; bisa dilanjutkan atau ditutup sesuai peran |
| J-02 | PO jasa diterima lengkap | Bukti/periode jasa dan riwayat pemenuhan bisa dibaca |

Label skenario membantu panduan mengenali contoh; nomor dokumen tetap dihasilkan aplikasi. Command melaporkan akun dan nomor dokumen yang tersedia tanpa mencetak password/token. Tanggal contoh mengikuti hari WIB saat pembuatan agar skenario aktif dapat diuji. Pemanggilan ulang tidak mengubah snapshot atau mengembalikan transaksi yang telah dilanjutkan pengguna ke keadaan awal. Jelaskan bila contoh lama sudah berpindah tahap atau penawarannya kedaluwarsa; pengulangan dari awal dilakukan pada database demo baru, bukan dengan penghapusan otomatis.

### Panduan pengguna dan pengujian recruiter

`docs/USER_GUIDE.md` ditujukan kepada pembaca yang belum mengetahui struktur aplikasi. Bedakan dua jalur berikut:

1. **Melihat contoh:** login sesuai peran, buka Permintaan Pengadaan/PO, cari nomor contoh, periksa detail, snapshot, pemenuhan dan riwayat, lalu buka cetak PO. Jelaskan bahwa admin dapat membaca transaksi tetapi tidak membuat permintaan atau menjalankan aksi operasional peran lain.
2. **Mencoba dari awal:** pemohon membuat dan mengajukan permintaan; approver memberi keputusan; procurement mencatat serta memilih penawaran dan menerbitkan PO; penerima mencatat barang/jasa; pengguna memeriksa perubahan tahap dan jumlah. Sediakan cabang revisi/penolakan dan penutupan sisa beserta batas perannya.

Setiap skenario menyebut akun/peran, prasyarat, menu/tombol, contoh input sintetis, hasil yang diharapkan dan cara memeriksa hasilnya. Sertakan alur barang dan jasa, kasus field wajib kosong, akses yang ditolak, serta pembedaan jumlah ditolak dari sisa pesanan. Contoh uji negatif harus menyebut pesan/status yang diharapkan tanpa menyarankan bypass izin atau validator.

Panduan juga menjelaskan login/logout, pemilihan database, pencarian/filter, daftar kosong, perpindahan akun, arti status, dan password manager browser. Satu jendela browser memakai satu sesi aktif; gunakan logout/login atau profil browser terpisah saat menguji beberapa peran. Jelaskan cara mengulangi demo tanpa merusak data yang sudah ada. Tambahkan screenshot seperlunya setelah tampilan serta data demo final diverifikasi. README menjadi pintu masuk untuk setup dan tautan panduan, sedangkan bukti teknis tetap berada pada TESTING.

### Urutan pekerjaan dan kriteria penerimaan

- [ ] Selesaikan tindak lanjut antarmuka: paginasi dua daftar penawaran, akses tindakan pada detail mobile panjang, serta pembacaan snapshot kandidat. Lengkapi pemeriksaan cetak beberapa halaman dan cabang interaksi yang belum diulang di browser.
- [ ] Tulis TC-19: seed dua kali tidak menggandakan akun/dokumen/audit, tidak menimpa data existing, tidak mereset password/peran, dan melaporkan benturan identitas demo dengan aman. Password hilang/tidak valid ditolak sebelum mutasi. Transaksi yang sudah dilanjutkan pengguna tidak dikembalikan ke keadaan awal.
- [ ] Implementasikan lima akun serta lima skenario melalui service. Verifikasi scope daftar/detail, keputusan, snapshot, accepted/rejected/remaining, status dan audit. Pastikan minimal satu permintaan dan satu PO terlihat setelah login sebagai admin pada database demo.
- [ ] Uji dari virtualenv dan database kosong yang terpisah dari data kerja: install requirements, isi environment, migrate, seed, check, test, runserver. Semua perintah README harus sudah dijalankan pada lingkungan ini sebelum dinyatakan valid.
- [ ] Susun USER_GUIDE dan tautkan dari README. Jalankan kedua jalur pengujian dari panduan pada browser menggunakan akun demo, tanpa command internal untuk menggantikan tindakan pengguna. Catat nomor contoh, langkah, hasil aktual dan batas yang belum diuji; perbaiki panduan bila berbeda dari UI.
- [ ] Uji satu alur barang dan satu jasa dari awal sampai hasil pemenuhan sesuai panduan. Pastikan pergantian peran/sesi, kasus invalid, cabang revisi/penolakan dan penutupan sisa menghasilkan perilaku yang dijelaskan. Sampel siap lihat harus tetap dapat dikenali meskipun contoh lain telah dipakai untuk uji mutasi.
- [ ] Jalankan `python manage.py check`, `python manage.py makemigrations --check --dry-run`, dan `python manage.py test -v 2`. Periksa migrasi/model, seluruh suite termasuk file-backed concurrency, serta output error/warning. Jangan memakai `--parallel` untuk suite concurrency SQLite yang dirancang dua koneksi sendiri.
- [ ] Catat versi, perintah, hasil, dan batas yang belum teruji pada TESTING. Periksa setelan non-debug secara terpisah; deployment atau production tidak dinyatakan teruji tanpa pelaksanaannya.
- [ ] Cocokkan fitur aktual dengan FR/BP/GW/WBS/TC. Perbarui status fitur hanya dengan bukti. OPT-01 tetap Ditunda. Periksa PDF/XLSX, tautan repo, serta file yang akan di-stage; email dan Git tetap dilakukan pengguna.
- [ ] Siapkan pengelompokan commit pengguna: kode seed/pengujian sebagai `feat: add repeatable procurement demo data`; panduan dan bukti sebagai `docs: add verified setup demo and user guide`. Laporkan daftar berkas aktual setelah implementasi; jangan memperlakukan daftar berkas rencana sebagai perubahan yang sudah tersedia.

Tahap ini selesai setelah setup bersih dapat dijalankan, data demo aman untuk dibuat ulang, kedua jalur pengujian dapat diikuti, dan hasilnya tercatat. URL publik hanya dicantumkan bila deployment benar-benar tersedia dan teruji; menjalankan demo lokal tidak membuktikan deployment. Seluruh checklist di atas tetap belum selesai sampai implementasi serta verifikasinya diinstruksikan dan dijalankan.

## Urutan dan bukti kemajuan

| Paket WBS          | Tugas / keadaan                                                          |
| ------------------ | ------------------------------------------------------------------------ |
| 1.1, 1.2           | BPMN/WBS sudah tersedia; pemeriksaan ulang pada tugas 11                 |
| 1.3                | PRD/proses baseline; perbarui hanya jika kebutuhan berubah               |
| 1.4, 1.5           | Rancangan pada tiga dokumen ini; realisasi dan pembuktian pada tugas 1-2 |
| 1.6                | Tugas 10                                                                 |
| 2.1                | Tugas 1 dan 3                                                            |
| 2.2, 2.4           | Tugas 4                                                                  |
| 2.3                | Tugas 5                                                                  |
| 3.1, 3.2, 3.3      | Tugas 6, dengan revisi persetujuan pada tugas 5                          |
| 3.4, 3.5           | Tugas 7                                                                  |
| 4.1, 4.2, 4.3, 4.4 | Tugas 8; pembatalan sebelum PO pada tugas 4                              |
| 5.1                | Tugas 9                                                                  |
| 5.2, 5.3           | Tugas 10; HTTP/form dasar diuji pada tugas masing-masing                 |
| 6.1, 6.2, 6.3, 6.4 | Tugas 11; keamanan dan pengujian juga melekat pada tugas 1-10            |
| 7.1                | Ditunda, tidak menjadi bagian implementasi wajib                         |

Tugas 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11. Pengujian server mengikuti setiap tugas; pemeriksaan browser alur lengkap dan visual dilakukan pada tahap UI, lalu regresi pada setup bersih. Tidak perlu membuat seluruh schema/UI sekaligus tanpa hasil uji antara.

Setelah satu tugas, laporkan perubahan, perintah/hasil pengujian, batas yang belum diuji, dan file untuk commit pengguna. Kegagalan test atau kontrak harus diselesaikan sebelum memperluas fitur. Kekurangan waktu dilaporkan; kebutuhan wajib tidak dihapus diam-diam.

Tugas 1 sampai 10 sudah mempunyai bukti implementasi dan pemeriksaan lokal pada TESTING, termasuk revisi antarmuka setelah tahap UI. Langkah berikutnya adalah Tugas 11, yang masih berupa rancangan. Akun/data demo dan panduan penggunanya belum tersedia. Rancangan fitur berikutnya belum menjadi bukti implementasi; checklist berubah setelah pekerjaan dan verifikasinya dijalankan.
