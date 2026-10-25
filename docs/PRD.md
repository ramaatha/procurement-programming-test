# PRD Procurement

Versi 1.1 | 22 Oktober 2026

Status implementasi ditinjau ulang pada 23 Oktober 2026; kebutuhan produk tetap sama.

## 1. Gambaran produk

Procurement adalah aplikasi web internal untuk mengelola pengadaan barang dan jasa. Pemohon mengajukan kebutuhan, approver menilai permintaan dan anggarannya, tim procurement memilih vendor serta menerbitkan purchase order (PO), lalu penerima mencatat hasil pemenuhan pesanan.

Setiap pihak dapat melihat tahap pengadaan, keputusan yang sudah diambil, dan jumlah pesanan yang masih harus dipenuhi. Riwayat permintaan, penawaran, PO, dan penerimaan tetap tersimpan meskipun proses berakhir melalui penolakan atau pembatalan.

## 2. Tujuan dan cakupan

Aplikasi mencatat satu alur pengadaan dari permintaan sampai penerimaan barang atau persetujuan hasil pekerjaan jasa. Cakupan versi awal meliputi:

- Pengajuan kebutuhan beserta rincian item dan estimasi biaya.
- Persetujuan satu tingkat, permintaan revisi, dan penolakan.
- Pencatatan penawaran, perbandingan harga dan waktu pemenuhan, serta pemilihan vendor.
- Penerbitan PO sesuai anggaran yang disetujui.
- Penerimaan lengkap atau bertahap, pencatatan ketidaksesuaian, dan penutupan sisa pesanan.
- Pembatasan akses per peran, pencarian, filter, dan riwayat tindakan.

Aplikasi digunakan oleh satu organisasi. Satu permintaan berisi barang atau jasa, menggunakan satu vendor, dan menghasilkan paling banyak satu PO. Pengelolaan stok gudang dan pembayaran berada di luar cakupan.

## 3. Pengguna dan hak akses

Pemohon menyiapkan kebutuhan. Approver memeriksa kelayakan permintaan dan plafon biayanya. Tim procurement menangani vendor, penawaran, dan PO. Penerima memeriksa barang atau hasil pekerjaan jasa.

Admin mengelola akun dan data pendukung. Vendor berkomunikasi di luar aplikasi dan tidak memiliki akun pada versi ini.

| Tindakan                                           | Pemohon                              | Approver                                  | Procurement                 | Penerima                                  | Admin             |
| -------------------------------------------------- | ------------------------------------ | ----------------------------------------- | --------------------------- | ----------------------------------------- | ----------------- |
| Melihat daftar dan detail permintaan               | Milik sendiri                        | Semua untuk review                        | Semua untuk pengadaan       | Permintaan dengan PO terbit atau terminal | Baca seluruh data |
| Membuat atau mengubah permintaan                   | Milik sendiri saat draft atau revisi | Tidak                                     | Tidak                       | Tidak                                     | Tidak             |
| Mengajukan atau membatalkan permintaan sebelum PO  | Milik sendiri, sesuai status         | Tidak                                     | Tidak                       | Tidak                                     | Tidak             |
| Menyetujui, meminta revisi, atau menolak           | Tidak                                | Permintaan diajukan, selain milik sendiri | Tidak                       | Tidak                                     | Tidak             |
| Mengelola vendor                                   | Tidak                                | Tidak                                     | Ya                          | Tidak                                     | Ya                |
| Mencatat penawaran, memilih vendor, menerbitkan PO | Tidak                                | Baca                                      | Permintaan disetujui        | Tidak                                     | Tidak             |
| Mengembalikan permintaan untuk revisi anggaran     | Tidak                                | Tidak                                     | Sebelum PO terbit           | Tidak                                     | Tidak             |
| Mencatat penerimaan                                | Tidak                                | Baca                                      | Baca                        | PO terbuka                                | Tidak             |
| Membatalkan PO atau menutup sisa pesanan           | Tidak                                | Sesuai aturan dan alasan                  | Mengusulkan melalui catatan | Baca                                      | Tidak             |
| Melihat riwayat                                    | Mengikuti akses permintaan           | Ya                                        | Ya                          | Mengikuti akses permintaan                | Ya                |
| Mengelola akun dan peran                           | Tidak                                | Tidak                                     | Tidak                       | Tidak                                     | Ya                |

Setiap akun memiliki satu peran aktif. Server memeriksa izin pada halaman, objek, dan tindakan yang diakses, termasuk melalui URL langsung atau form yang dimodifikasi. Perubahan peran tidak menghapus kepemilikan maupun riwayat. Pengguna tetap dilarang menyetujui permintaan miliknya sendiri.

## 4. Alur pengadaan

1. Pemohon membuat draft, memilih jenis pengadaan, lalu mengisi alasan, tanggal kebutuhan, lokasi penerimaan atau layanan, serta rincian item.
2. Saat permintaan diajukan, sistem memvalidasi isian, menghitung total estimasi, dan menyimpan revisi yang akan diperiksa.
3. Approver menyetujui permintaan, meminta perbaikan, atau menolak dengan alasan.
4. Untuk permintaan yang disetujui, procurement mencatat penawaran vendor dan membandingkan kesesuaian item, harga, masa berlaku, serta waktu pemenuhan.
5. Procurement memilih vendor dengan alasan yang tercatat. Bila kebutuhan atau anggaran perlu berubah, permintaan dikembalikan untuk direvisi dan disetujui ulang.
6. Procurement menerbitkan PO dari penawaran terpilih. PO menyimpan salinan rincian vendor, item, harga, dan tujuan penerimaan pada saat penerbitan.
7. Procurement menyampaikan PO kepada vendor secara manual. Vendor mengirim barang atau melaksanakan jasa di luar aplikasi.
8. Penerima memeriksa pemenuhan dan mencatat jumlah yang diterima atau ditolak. Penerimaan jasa dilengkapi periode pelaksanaan, referensi, dan catatan hasil pekerjaan.
9. Sistem menghitung sisa setiap item. Pesanan selesai saat seluruh jumlah diterima. Pembatalan atau penutupan sisa menghasilkan status akhir yang berbeda.

Rincian aktivitas dan transisi status tersedia pada [alur proses pengadaan](BUSINESS_PROCESS.md).

## 5. Aturan bisnis

| ID    | Aturan                                                                                                                                                                                                                                         |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AS-01 | Persetujuan menggunakan satu tingkat dan dilakukan oleh approver yang berbeda dari pemohon.                                                                                                                                                    |
| AS-02 | Satu permintaan berisi barang atau jasa. Beberapa item diperbolehkan selama jenis pengadaannya sama.                                                                                                                                           |
| AS-03 | Satu permintaan menggunakan satu vendor untuk seluruh item dan menghasilkan paling banyak satu PO sepanjang riwayatnya. Setelah PO berakhir, kebutuhan lanjutan dibuat sebagai permintaan baru.                                                |
| AS-04 | Procurement mencatat penawaran dari komunikasi di luar aplikasi. Setiap penawaran harus mencakup seluruh item, jumlah, dan unit pada revisi permintaan yang sedang berlaku.                                                                    |
| AS-05 | Satu penawaran valid sudah dapat diproses. Pemilihan vendor memerlukan alasan; penawaran tunggal juga memerlukan alasan penggunaan sumber tunggal.                                                                                             |
| AS-06 | Persetujuan berlaku untuk satu revisi dan plafon estimasinya. Nilai PO tidak boleh melebihi plafon. Perubahan kebutuhan atau plafon harus melalui revisi dan persetujuan ulang sebelum ada PO.                                                 |
| AS-07 | Mata uang yang digunakan adalah IDR. Kuantitas memiliki maksimal tiga desimal dan nominal maksimal dua desimal. Harga final per unit sudah mencakup biaya yang disepakati; pajak, ongkir, dan kurs tidak dihitung terpisah.                    |
| AS-08 | Rincian PO yang sudah terbit dan penerimaan yang sudah dicatat tidak dapat diedit atau dihapus melalui aplikasi. Status PO hanya berubah melalui tindakan yang diizinkan. Koreksi penerimaan setelah pencatatan belum tersedia pada versi ini. |
| AS-09 | Penerimaan dapat dilakukan bertahap. Hanya jumlah yang diterima sesuai pesanan yang mengurangi sisa. Penolakan dicatat beserta alasannya tanpa membuat transaksi stok atau retur gudang.                                                       |
| AS-10 | Approver dapat membatalkan PO yang belum memiliki jumlah diterima, atau menutup sisa PO yang sudah diterima sebagian. Alasan wajib dicatat. Penutupan dengan kekurangan tidak dianggap sebagai penerimaan lengkap.                             |
| AS-11 | Bukti penawaran dan penerimaan berupa nomor referensi serta catatan teks. Penerimaan jasa juga memuat periode pelaksanaan dan hasil pekerjaan. Unggah dokumen dan tanda tangan elektronik belum tersedia.                                      |
| AS-12 | Server menerbitkan nomor dokumen yang unik. Pengiriman ulang tindakan yang sama tidak boleh menghasilkan keputusan, PO, atau penerimaan ganda.                                                                                                 |

Setiap pengajuan menyimpan salinan rincian revisinya. Pemohon mengedit draft kerja saat diminta memperbaiki permintaan; isi revisi yang pernah disetujui dan penawaran yang merujuknya tetap tersimpan.

## 6. Kebutuhan fungsional

| ID / fitur                           | Kriteria penerimaan                                                                                                                                                                                                                                                                                                                                                       | Skenario uji                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| FR-01 Autentikasi dan hak akses      | Pengguna dapat login dan logout. Akun nonaktif ditolak. Pengguna tanpa izin tidak dapat membaca atau mengubah objek melalui URL maupun form. Akun demo tersedia untuk setiap peran dan tidak memakai rahasia produksi.                                                                                                                                                    | TC-01 login/logout; TC-02 izin peran dan objek.                                                   |
| FR-02 Permintaan dan rincian item    | Pemohon dapat menyimpan draft miliknya. Pengajuan memerlukan jenis, judul, alasan, tujuan, tanggal kebutuhan yang tidak lampau saat diajukan, dan minimal satu item dengan nama, unit, jumlah > 0, serta estimasi harga > 0. Server menghitung totalnya.                                                                                                                  | TC-03 draft dan pengajuan valid/invalid; TC-04 total dan presisi.                                 |
| FR-03 Review permintaan              | Hanya permintaan SUBMITTED yang dapat diputuskan approver selain pemohon. Persetujuan mengikat revisi dan plafonnya. Permintaan revisi serta penolakan memerlukan alasan. Keputusan dicatat sekali; permintaan berstatus akhir tidak dapat diaktifkan ulang.                                                                                                              | TC-05 setuju/revisi/tolak; TC-06 persetujuan sendiri dan keputusan berulang.                      |
| FR-04 Vendor                         | Procurement dan admin dapat membuat, memperbarui, atau menonaktifkan vendor. Nama dan kontak wajib diisi. Vendor nonaktif tidak dapat dipakai untuk penawaran baru atau penerbitan PO. Vendor yang sudah dirujuk dokumen tidak dihapus.                                                                                                                                   | TC-07 vendor aktif/nonaktif dan riwayat.                                                          |
| FR-05 Penawaran                      | Procurement dapat mencatat penawaran untuk permintaan APPROVED yang belum memiliki PO. Vendor harus aktif. Referensi, tanggal, masa berlaku, estimasi pemenuhan, dan harga positif wajib diisi. Tanggal penawaran tidak melewati batas masa berlakunya. Item, jumlah, dan unit harus cocok dengan revisi aktif; perbandingan memakai penawaran pada revisi tersebut.      | TC-08 kelengkapan item, masa berlaku, dan perbandingan.                                           |
| FR-06 Pemilihan vendor dan revisi    | Pemilihan vendor memerlukan alasan dan boleh mempertimbangkan faktor selain harga terendah. Penawaran tunggal memerlukan alasan sumber tunggal. Procurement dapat meminta revisi sebelum ada PO. Pengajuan ulang menaikkan nomor revisi dan membuat penawaran lama tidak berlaku untuk penerbitan PO.                                                                     | TC-09 pemilihan vendor; TC-10 revisi anggaran.                                                    |
| FR-07 Penerbitan PO                  | PO hanya diterbitkan dari penawaran terpilih dengan tanggal penawaran <= hari penerbitan <= akhir masa berlaku. Revisi harus disetujui dan nilai PO <= plafon. Maksimal satu PO tersedia per permintaan. Nomor, pengguna penerbit, waktu, vendor, item, harga, dan tujuan disimpan sebagai snapshot. Isi PO tidak dapat diedit; status mengikuti transisi yang diizinkan. | TC-11 validasi, plafon, snapshot, dan pengiriman ulang.                                           |
| FR-08 Penerimaan barang              | Penerima hanya dapat mencatat penerimaan untuk PO barang berstatus ISSUED atau PARTIALLY_RECEIVED. Minimal satu item memiliki accepted atau rejected > 0; keduanya tidak boleh negatif. Accepted tambahan <= sisa item. Rejected memerlukan alasan. Referensi dan catatan wajib diisi. Seluruh rincian disimpan dalam satu transaksi.                                     | TC-12 penerimaan lengkap/bertahap; TC-13 penolakan, kelebihan, duplikasi, dan tindakan bersamaan. |
| FR-09 Penerimaan jasa                | Penerimaan jasa hanya dilakukan pada PO jasa yang masih terbuka, dengan aturan jumlah seperti FR-08. Jenis bukti, referensi, ringkasan hasil, dan periode pelaksanaan wajib diisi. Tanggal awal <= tanggal akhir <= tanggal konfirmasi. Accepted hanya mencatat jasa yang dinyatakan sesuai dan tidak membuat mutasi stok.                                                | TC-14 jasa bertahap, periode tidak valid, dan penolakan hasil.                                    |
| FR-10 Pembatalan dan penutupan sisa  | Pemohon dapat membatalkan permintaan miliknya pada status DRAFT, CHANGES_REQUESTED, SUBMITTED, atau APPROVED selama belum ada PO dan alasan diisi. Setelah PO terbit, hanya approver yang dapat mengakhirinya sesuai AS-10. Jumlah yang pernah diterima tetap tersimpan. PO berstatus akhir menolak penerimaan baru.                                                      | TC-15 pembatalan sebelum PO; TC-16 pembatalan PO, penutupan sisa, dan status akhir.               |
| FR-11 Tracking dan riwayat           | Pengguna dapat mencari nomor atau judul dan memfilter tahap serta jenis pengadaan. Detail menampilkan status permintaan dan PO, accepted, rejected, remaining per item, serta riwayat pengguna, waktu, dan alasan. Akses daftar dan detail mengikuti FR-01.                                                                                                               | TC-17 pencarian, filter, akses, dan audit.                                                        |
| FR-12 Antarmuka dan pesan kesalahan  | Saat isian tidak valid, form menampilkan pesan yang spesifik dan mempertahankan input yang aman. Tersedia tampilan kosong, proses pengiriman, dan kegagalan. Aplikasi membatasi tindakan berulang pada UI dan server. Kontrol dapat digunakan dengan keyboard dan layout dapat digunakan pada layar kecil.                                                                | TC-18 alur browser per peran, state, keyboard, dan responsive.                                    |
| FR-13 Lingkungan uji dan data contoh | Tim dapat menyiapkan aplikasi dari database kosong dengan mengikuti README, menjalankan migrasi, memuat data sintetis, login pada setiap peran, dan menjalankan pengujian. Alur inti tidak bergantung pada API pihak ketiga.                                                                                                                                              | TC-19 instalasi bersih dan alur contoh barang/jasa.                                               |

## 7. Data dan konsistensi

Data utama meliputi akun dan peran, permintaan beserta rincian revisi, keputusan persetujuan, vendor, penawaran, PO, penerimaan, dan riwayat tindakan.

- Perhitungan uang menggunakan desimal. Total item dihitung dari jumlah x harga, dibulatkan dua desimal dengan metode half-up. Total dokumen merupakan penjumlahan total item.
- Server memvalidasi jumlah dan nilai. Perubahan angka pada browser tidak dapat melewati pemeriksaan tersebut.
- Sisa item dihitung dari jumlah dipesan dikurangi accepted kumulatif. Rejected disimpan terpisah dan tidak mengurangi sisa.
- Penerimaan beberapa item disimpan seluruhnya atau dibatalkan seluruhnya bila satu item tidak valid.
- Accepted kumulatif tidak boleh melebihi jumlah pesanan, termasuk ketika dua penerimaan diproses bersamaan.
- Form dengan versi data yang sudah berubah ditolak dengan pesan untuk memuat ulang. Aplikasi tidak menimpa perubahan terbaru secara diam-diam.
- Snapshot PO dan revisi permintaan tetap sama meskipun data master vendor atau draft berikutnya berubah.
- Riwayat mencatat pengguna, waktu, tindakan, objek, dan alasan yang diperlukan. Waktu ditampilkan dalam WIB.

## 8. Kualitas dan batas teknis

Aplikasi web menggunakan Python dengan SQLite atau PostgreSQL. Pemilihan framework dan rincian arsitektur dibahas terpisah.

Autentikasi, izin per objek, validasi server, dan proteksi form diterapkan sejak awal. Pesan kesalahan tidak boleh menampilkan stack trace, password, token, atau konfigurasi rahasia. Log dan riwayat tidak menyimpan password maupun token.

Daftar menggunakan paginasi. Tampilan menjelaskan status melalui teks dan angka, sehingga pengguna tidak harus mengandalkan warna. Navigasi, form, focus, dan pesan kesalahan harus dapat digunakan dengan keyboard serta pada layar kecil.

## 9. Batas versi awal dan pengembangan berikutnya

Versi awal belum mencakup pengelolaan stok dan lokasi penyimpanan, stock opname, retur setelah barang diterima, koreksi penerimaan setelah pencatatan, invoice, pembayaran, akuntansi, atau perhitungan pajak otomatis. Persetujuan bertingkat, multi-organisasi, pemecahan satu permintaan ke beberapa vendor/PO, portal vendor, tender, kontrak, penilaian vendor, notifikasi email/push, dan unggah berkas juga berada di luar cakupan.

OPT-01: bantuan AI opsional pada Buat Permintaan menerima teks atau satu gambar JPG/PNG. Qwen melalui Groq menghasilkan usulan maksimal sepuluh item yang divalidasi server. Pengguna memeriksa hasil dan menerapkannya ke kolom kosong sebelum menyimpan. Fitur tidak menyimpan/mengajukan draf, menyetujui permintaan, atau menerbitkan PO. Input manual tetap tersedia tanpa JavaScript/API key maupun saat layanan gagal. Implementasi diuji lokal memakai penyedia simulasi; akurasi model dan koneksi hosting belum diverifikasi. Konfigurasi dan batas ada pada [AI_INPUT](AI_INPUT.md).

## 10. Pemetaan kebutuhan

ID proses dan gateway mengacu pada [alur proses pengadaan](BUSINESS_PROCESS.md). ID WBS menghubungkan kebutuhan dengan paket pekerjaan. Status di bawah menunjukkan rencana implementasi fitur.

| Kebutuhan | Peran                     | Proses / gateway                  | ID WBS | Skenario uji                             | Status                                      |
| --------- | ------------------------- | --------------------------------- | ------ | ---------------------------------------- | ------------------------------------------- |
| FR-01     | Seluruh pengguna internal | BP-00                             | 2.1    | TC-01; TC-02                             | Teruji lokal                                |
| FR-02     | Pemohon                   | BP-01; BP-02                      | 2.2    | TC-03; TC-04                             | Teruji lokal                                |
| FR-03     | Approver                  | BP-03; GW-01                      | 2.3    | TC-05; TC-06                             | Teruji lokal                                |
| FR-04     | Procurement; Admin        | BP-04                             | 3.1    | TC-07                                    | Teruji lokal                                |
| FR-05     | Procurement               | BP-05; GW-02                      | 3.2    | TC-08                                    | Teruji lokal                                |
| FR-06     | Procurement; Pemohon      | BP-06; BP-07; GW-03               | 3.3    | TC-09; TC-10                             | Teruji lokal                                |
| FR-07     | Procurement               | BP-08; BP-09                      | 3.4    | TC-11                                    | Teruji lokal                                |
| FR-08     | Penerima                  | BP-10; BP-11; BP-13; GW-04; GW-05 | 4.1    | TC-12; TC-13                             | Teruji lokal                                |
| FR-09     | Penerima                  | BP-10; BP-12; BP-13; GW-04; GW-05 | 4.2    | TC-14                                    | Teruji lokal                                |
| FR-10     | Pemohon; Approver         | BP-14; BP-15; GW-06               | 4.3    | TC-15; TC-16                             | Teruji lokal                                |
| FR-11     | Seluruh pengguna internal | BP-16                             | 5.1    | TC-17                                    | Teruji lokal                                |
| FR-12     | Seluruh pengguna internal | Seluruh proses internal           | 5.2    | TC-18                                    | Teruji lokal                                |
| FR-13     | Tim pengembang            | BP-00 sampai BP-16                | 6.1    | TC-19                                    | Teruji lokal                                |
| OPT-01    | Pemohon                   | Sebelum BP-01                     | 7.1    | Integrasi lokal dengan provider simulasi | Terimplementasi lokal; AI live belum teruji |

Bukti suite terbaru dan batas pengujian ada pada [TESTING](TESTING.md). Aktivitas vendor dan penyampaian PO di luar aplikasi tetap manual. Pengujian OPT-01 menggunakan provider simulasi; tidak membuktikan kualitas ekstraksi model atau koneksi AI hosting.

## 11. Kriteria penerimaan versi awal

Versi awal dapat diterima setelah:

1. Seluruh kebutuhan FR-01 sampai FR-13 tersedia dan skenario pengujiannya lulus.
2. Alur barang dan jasa berjalan dari pembuatan permintaan sampai penerimaan lengkap.
3. Revisi, penolakan, pembatalan, penerimaan sebagian, ketidaksesuaian, dan penutupan sisa menghasilkan jumlah serta status yang benar.
4. Pengujian membuktikan pembatasan akses, perhitungan total, snapshot, transisi status, dan penanganan tindakan berulang atau bersamaan.
5. Aplikasi dapat disiapkan dari database kosong melalui README, dengan data contoh yang jelas sintetis.
6. Form, navigasi, dan tampilan status dapat digunakan pada browser, keyboard, dan layar kecil.
7. Dokumentasi proses dan model data sesuai dengan perilaku yang diimplementasikan.
