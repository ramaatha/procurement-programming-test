# Pedoman penyusunan commit untuk agen

## Batas kewenangan

Staging, commit, dan push dilakukan pengguna. Agen memeriksa perubahan dan menyiapkan rekomendasi tanpa menjalankan tindakan Git tersebut. Jangan memasang hook atau otomatisasi yang melakukan tindakan itu sebagai efek samping.

## Menentukan kelompok perubahan

Dasarkan kelompok commit pada diff aktual dan tujuan perubahan. Kode fitur beserta pengujiannya berada dalam kelompok yang sama. Pisahkan dokumentasi jika dapat ditinjau sendiri tanpa mengaburkan perubahan implementasi.

Setiap kelompok harus mempunyai cakupan yang jelas dan pesan yang sesuai dengan isinya. Sertakan migrasi ketika diperlukan oleh perubahan model. Hindari pemisahan yang meninggalkan import, route, template, atau pengujian dalam keadaan tidak lengkap.

Periksa status terbaru sebelum menyusun daftar berkas. Nama, jumlah, dan status file dapat berubah setelah pengguna melakukan rename, staging, atau commit. Jangan memakai daftar dari tahap sebelumnya sebagai bukti keadaan sekarang. Pertahankan perubahan pengguna yang berada di luar tugas.

## Memilih pesan commit

Gunakan format `type: ringkasan perubahan` dengan kata kerja yang menjelaskan hasilnya. Pilih `feat` untuk kemampuan baru, `fix` untuk perbaikan perilaku, `docs` untuk dokumentasi, `refactor` untuk perubahan struktur tanpa perubahan perilaku, dan `test` untuk tambahan pengujian yang berdiri sendiri. Gunakan `chore` untuk pemeliharaan yang tidak termasuk kelompok tersebut.

Pesan menyebut kemampuan yang benar-benar tersedia. Hasil pemeriksaan lokal tidak boleh digambarkan sebagai deployment atau bukti kesiapan produksi.

## Pemeriksaan sebelum merekomendasikan commit

- Tinjau diff dan pastikan setiap berkas mendukung tujuan kelompoknya.
- Jalankan pemeriksaan yang sesuai dengan risiko perubahan dan catat hasil aktual. Jelaskan bagian yang belum diuji.
- Pastikan rahasia, environment lokal, database, journal, cache, screenshot, log, dan berkas sementara tidak masuk daftar rekomendasi. Artefak hasil akhir hanya disertakan bila memang bagian deliverable dan telah berubah.
- Jangan memasukkan file yang tidak berubah atau menganggap file untracked sudah tercakup oleh pemeriksaan diff biasa.
- Periksa kembali penamaan dan tautan setelah rename, termasuk kapitalisasi untuk checkout pada filesystem yang membedakan huruf besar dan kecil.

## Pelaporan oleh agen

Agen menyampaikan rekomendasi staging dan commit melalui chat. Setiap rekomendasi memuat daftar lengkap berkas per commit, pesan commit yang dapat disalin, dan arahan push yang jelas di akhir respons.

Agen membedakan perubahan lokal, staged, committed, dan pushed berdasarkan pemeriksaan terbaru. Sebelum menyatakan branch sudah sinkron atau working tree bersih, agen memeriksa keadaan repository.

Agen menyesuaikan arahan operasional dengan keadaan repository saat itu. Daftar berkas dan perintah untuk pengguna disampaikan melalui chat, tanpa disimpan sebagai prosedur tetap per tahap dalam dokumen ini.
