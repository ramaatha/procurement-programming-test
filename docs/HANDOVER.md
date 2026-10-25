# Penyerahan Procurement

Diperbarui: 25 Oktober 2026.

Pemeriksaan deployment, migrasi, dan izin file privat sudah diperiksa pada server.
Penyerahan masih memerlukan pengujian login dengan password baru, peninjauan staged changes,
commit, push, serta pemeriksaan tautan dokumen pada repository remote.

## 1. Hasil pemeriksaan

| Bagian | Hasil dan sumber bukti |
| --- | --- |
| Instalasi bersih | 297 tes lulus pada environment dan database uji terpisah. |
| Profil deployment | Screenshot console: hanya warning `security.W005` dan `security.W021` yang telah didokumentasikan. |
| Migrasi server | Screenshot console: pemeriksaan migrasi kembali ke prompt tanpa error. |
| Izin konfigurasi | Screenshot console: folder privat `700`; kedua file konfigurasi `600`. |
| Akses publik | HTTPS, header keamanan, CSRF, proteksi route/path privat, dan delapan hash aset lulus pemeriksaan sebelumnya. |
| Password akun demo | Penggantian seluruh password dikonfirmasi pengelola; hasil login ulang belum dicatat. |
| Repository | Branch `main` dan origin sudah diperiksa; tidak ada hasil commit/push terbaru yang dinyatakan selesai. |

Hasil ini berlaku pada lingkup pemeriksaan tercatat. Perangkat fisik, pembaca layar,
beban produksi, foto rumit, dan perbandingan mode berpikir AI belum termasuk bukti tersebut.
Rincian teknis dan riwayat tersedia pada [catatan pengujian](TESTING.md)
dan [panduan deployment](DEPLOYMENT.md).

## 2. Siapkan akses demo

1. Coba login kelima akun dengan password baru, lalu logout setelah setiap pemeriksaan.
2. Cocokkan username dan peran dengan [panduan pengguna](USER_GUIDE.md#akun-yang-tersedia).
3. Gunakan [template informasi aplikasi](SUBMISSION_TEMPLATE.md) untuk tautan dan petunjuk uji.
4. Isi template kredensial yang disimpan di luar repository dengan password terbaru.
5. Kirim kredensial melalui kanal privat yang ditentukan. Simpan password hanya pada salinan privat.

Penggantian password tidak sama dengan bukti keberhasilan login ulang.
Password, API key, konfigurasi privat, dan database tidak dimasukkan ke dokumen publik atau arsip sumber.

## 3. Tinjau dan pisahkan perubahan

Buka terminal pada folder proyek, lalu jalankan:

```powershell
git status --short
git branch --show-current
git remote -v
git diff --check
```

Pisahkan commit berdasarkan tujuan perubahan:

| Commit | Isi |
| --- | --- |
| Implementasi | Kode aplikasi, konfigurasi contoh, requirements, tes, template halaman, serta aset CSS/JS/font. |
| Dokumentasi | Berkas Markdown, lampiran aktif, dan penghapusan tiga lampiran lama yang telah dikonfirmasi. |

Jika kode dan dokumentasi sudah berada bersama pada **Staged Changes**, keluarkan kelompok
dokumentasi dari staging melalui **Unstage Changes** terlebih dahulu. Tindakan ini hanya
mengubah staging; jangan memilih tindakan yang membuang perubahan berkas.

Lampiran aktif:

- [BPMN PDF v1.2](../outputs/Procurement_BPMN_v1.2.pdf).
- [BPMN yang dapat diedit v1.2](../outputs/Procurement_BPMN_v1.2.drawio).
- [WBS v1.3](../outputs/Procurement_WBS_v1.3.xlsx).

Penghapusan tiga lampiran berikut sudah dikonfirmasi dan termasuk commit dokumentasi:

- `outputs/Procurement_BPMN.drawio`
- `outputs/Procurement_BPMN.pdf`
- `outputs/Procurement_WBS.xlsx`

WBS v1.2 merupakan versi sebelumnya dan tidak termasuk lampiran aktif untuk commit ini.
Status dalam WBS v1.3 adalah snapshot saat berkas tersebut dibuat; hasil server yang lebih baru
dicatat pada tabel pemeriksaan di atas.

## 4. Commit dan push

1. Stage kelompok implementasi, lalu periksa:

   ```powershell
   git diff --cached --check
   git diff --cached --stat
   ```

2. Pastikan tidak ada dokumentasi atau file privat dalam kelompok tersebut. Buat commit:

   ```text
   feat: improve procurement workflows and add optional AI draft input
   ```

3. Stage kelompok dokumentasi dan lampiran, termasuk penghapusan yang sudah dikonfirmasi.
   Stage ulang dokumen yang baru diedit agar isi terbaru ikut tercatat.
4. Ulangi pemeriksaan staged changes, lalu buat commit:

   ```text
   docs: update guides diagrams and release verification
   ```

5. Setelah kedua commit ditinjau, push ke branch dan origin yang sudah diperiksa:

   ```powershell
   git push origin main
   git status --short
   ```

Staging, commit, dan push dilakukan pengelola repository. Jangan menyatakan versi remote
sudah diperbarui sebelum hasil push dan isinya diperiksa.

## 5. Periksa isi penyerahan

1. Buka URL repository dan aplikasi yang tercantum pada [README](../README.md).
2. Pastikan versi terbaru, panduan AI, serta tautan BPMN/WBS dapat dibuka.
3. Kirim dua bagian: informasi aplikasi/dokumen dan kredensial demo melalui kanal privat.
4. Gunakan URL dan akun demo sesuai [template informasi aplikasi](SUBMISSION_TEMPLATE.md).
5. Jika menyertakan ZIP, buat ulang setelah revisi dokumen terakhir. Arsip yang dibuat sebelumnya
   tidak otomatis ikut berubah. Jangan mengekstrak arsip sumber menimpa instalasi aktif.

Informasi penyerahan cukup memuat akses aplikasi dan dokumen yang diperlukan.
Akun hosting, akses pengelolaan repository, dan API key tetap privat.
