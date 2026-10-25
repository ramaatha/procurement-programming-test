# Bantuan AI untuk Draf Permintaan

Fitur opsional OPT-01 pada **Buat Permintaan** membantu Pemohon menyusun usulan dari teks atau gambar. Alur manual, service bisnis, snapshot, versi, dan penyimpanan uang tetap menjadi otoritas. Langkah pengguna ada di [USER_GUIDE](USER_GUIDE.md#bantu-isi-dengan-ai-opsional).

## Konfigurasi Privat

Gunakan akun Groq Free dan API key khusus aplikasi. Jangan menaruh key di chat, screenshot, kode, ZIP, atau dokumen publik. Di virtualenv aplikasi, jalankan:

```bash
python -m deploy.ai configure
```

Masukkan key dua kali pada prompt tersembunyi. File baru dibuat pada `~/.config/procurement-demo/ai.json`; file yang sudah ada tidak ditimpa. Konfigurasi hosting `environment.json` tidak diubah. Reload web app setelah konfigurasi.

Untuk lingkungan lokal, `GROQ_API_KEY` dapat dipakai sebagai environment variable proses. `PROCUREMENT_AI_CONFIG` dapat memilih file privat lain. Jangan memakai keduanya untuk mencampur akun pengujian dan demo. Key hilang atau file tidak valid membuat endpoint AI tidak tersedia, sementara form manual tetap berfungsi.

## Model dan Penghematan Token

- Model: `qwen/qwen3.8-27b`, masih preview pada saat implementasi 25 Oktober 2026; ketersediaan perlu diperiksa sebelum demo.
- `reasoning_effort=none`, maksimal 1.200 token keluaran, satu panggilan tanpa retry otomatis atau riwayat percakapan.
- Non-thinking tetap menerima gambar. Akurasi pembacaan dokumen belum dibandingkan dengan mode low; tidak ada klaim kesetaraan akurasi. Bagian tidak diketahui harus null dan diperiksa pengguna.
- Teks maksimal 1.500 karakter. Gambar tunggal maksimal 2 MiB dan 12 megapiksel, JPG/PNG statis; server memverifikasi isi, mengubah orientasi, mengecilkan ke sisi1600px dan membuat JPEG tanpa metadata sumber.
- Gambar memiliki biaya token input dari penyedia; mengecilkan file tidak dijanjikan mengurangi token gambar. Untuk uji awal, gunakan teks singkat.
- Batas lokal: sepuluh percobaan total dan lima per pengguna per hari WIB. Kegagalan setelah panggilan dicadangkan ikut dihitung. Satu lease aktif60detik; transport memiliki deadline total20detik dan tidak melakukan redirect.
- Uji otomatis memakai transport/penyedia simulasi sehingga tidak memakai token Groq. Aktivasi key tidak memicu panggilan: pengguna harus menekan Analisis.

## Aliran dan Batas Data

Browser mengirim POST ber-CSRF ke `/requests/assist/`; server memeriksa akun Pemohon aktif, ukuran dan format input, kemudian mereservasi kuota. Kuota memakai SQLite terpisah di `DATA_DIR/ai/usage.sqlite3`, berisi tanggal, ID akun, hitungan dan lease saja. Transaksi pengadaan tidak ditahan selama menunggu API. Tidak diperlukan migrasi model bisnis.

Respons JSON dibatasi64KiB, bentuknya diperiksa, kolom asing ditolak, jumlah/harga harus string numerik kanonik dan dalam rentang integer. Hasil tidak boleh berisi HTML aktif; browser memakai textContent. Gambar tidak disimpan sebagai lampiran aplikasi dan isi tidak dicatat ke log. Pengiriman ke penyedia tetap mengikuti kebijakan Groq; tidak menjanjikan retensi nol pada seluruh pihak.

UI meminta review eksplisit dan menerapkan hasil hanya ke kolom kosong. Pilihan jenis yang sudah disentuh atau berasal dari form POST dipertahankan. Item berisi tidak ditimpa; tambahan mengikuti management form dan batas1000item yang ada. Pembatalan/perubahan sumber membatalkan hasil lokal; proses server yang sudah dikirim mungkin tetap dihitung penyedia.

HTTPX digunakan dengan async cancellation untuk deadline keseluruhan; timeout socket saja tidak cukup menghadapi slow trickle. Proxy environment tetap dihormati untuk PythonAnywhere. Dependencies tambahan terpatok: Pillow13.0.0 dan HTTPX0.28.1. Tidak ada SDK provider, model lokal besar, akses browser ke API key, atau fallback ke penyedia lain.

## Verifikasi Sebelum Penggunaan Online

1. Pasang paket pembaruan dan requirements pada virtualenv hosting, lalu periksa Django dan static files.
2. Konfigurasikan key secara privat; jangan jalankan seed/configure hosting ulang.
3. Coba satu teks contoh melalui UI. Cocokkan hasil dengan input, kemudian simpan draf dan baca kembali nilainya.
4. Coba satu gambar buatan yang jelas. Periksa angka, bagian kosong, waktu respons dan sisa kuota pada dashboard Groq.
5. Jika perlu membandingkan none/low, lakukan sebagai percobaan terpisah dengan sampel yang sama dan batas token; jangan mengaktifkan retry berpikir otomatis.

Pemeriksaan penyedia simulasi membuktikan integrasi/validasi. Screenshot browser pengguna pada hosting menunjukkan teks dan gambar contoh jelas berhasil dianalisis, diterapkan ke form, lalu disimpan sebagai draf. Dokumen rumit, foto nyata yang buram, kuota penyedia, dan perbandingan mode none/low belum dinyatakan teruji.
