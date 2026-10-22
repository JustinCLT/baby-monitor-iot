# Edge device lewat browser HP (tanpa Termux)

Ini **sensor sungguhan**, bukan simulator. Kode `web-edge/index.html` membaca data gerakan HP dengan `DeviceMotionEvent`, menghitung dua fitur (RMS percepatan dan total rotasi), lalu mengirim JSON telemetry MQTT ke cloud menggunakan **MQTT over WebSocket Secure (WSS)**.

## Persiapan

- **2 HP fisik** yang punya accelerometer dan gyroscope dan browser yang mendukung DeviceMotion.
- **1 laptop** menjalankan `python detector.py`.
- Semua perangkat pada **satu Wi-Fi/hotspot** dengan internet.
- Halaman browser edge harus tersedia melalui **HTTPS**. Alamat `http://192.168.x.x` dari laptop biasanya **tidak memenuhi** persyaratan secure context untuk akses sensor. `localhost` di HP adalah HP itu sendiri, bukan laptop.
- URL broker MQTT WebSocket harus tersedia (default: `wss://broker.hivemq.com:8884/mqtt`). Browser tidak bisa konek ke MQTT TCP port `8883` langsung.

## 1. Host halaman web-edge di HTTPS

Cara mudah: publish **folder `web-edge/` saja** ke hosting static dengan HTTPS seperti Netlify Drop. Bisa juga gunakan GitHub Pages yang sudah dikonfigurasi atau hosting HTTPS lain. **Tidak perlu backend tambahan untuk halaman edge.**

Contoh jika memakai layanan drag-and-drop: upload folder `web-edge`, tunggu URL `https://...`, lalu buka URL itu dari kedua HP.

**GitHub Pages:** pastikan Pages diaktifkan serta mem-publish `web-edge/index.html` (misalnya melalui workflow/deployment sendiri). Repo ini tidak otomatis mengaktifkan GitHub Pages.

## 2. Jalankan NODE 3 pada laptop

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python detector.py
```

Sesuaikan `PROJECT_ID` di `.env` (harus unik). Dashboard: **http://localhost:8000**.

## 3. Jalankan masing-masing edge via browser

Di **HP A**: buka link HTTPS tadi → pilih `Edge 1` → isi PROJECT_ID → tekan **Mulai membaca sensor**.

Di **HP B**: buka link HTTPS yang sama → pilih `Edge 2` → PROJECT_ID sama → tekan **Mulai membaca sensor**.

Chrome Android sering dapat mengakses DeviceMotion setelah izin/pengaturan terkait diaktifkan; iOS Safari biasanya meminta izin motion sensors melalui klik pengguna. Dukungan tergantung browser, versi OS, dan hardware. **Tidak semua HP menyediakan nilai `rotationRate` gyroscope.**

Jangan pindahkan browser ke background ketika demo; background tab dapat dibatasi/dihentikan oleh OS.

## 4. Validasi data benar-benar berasal dari sensor

Di setiap HP:
- Status harus `Sensor aktif · MQTT terhubung`.
- Angka **Pembacaan sensor valid** dan **Pesan MQTT terkirim** harus meningkat.
- Ketika HP digerakkan, **RMS** atau **Rotasi** harus berubah.
- Jika tertulis sensor tidak didukung/izin ditolak, jangan mengklaim ini sebagai dua sensor. Gunakan Termux atau perangkat lain.

Dashboard laptop menampilkan dua edge yang publish ke topic berikut:

```text
pocketguard/<PROJECT_ID>/edge/edge1/telemetry
pocketguard/<PROJECT_ID>/edge/edge2/telemetry
```

Payload browser memakai format yang sama persis dengan Python, jadi **boleh mencampur browser di HP A dengan Termux di HP B**.

## Cara kerja processing

1. `accelerationIncludingGravity` (m/s²) → `sqrt(ax²+ay²+az²)` → selisih dari 9,81 → **RMS**.
2. `rotationRate` (derajat/detik) → konversi ke radian/detik → integrasi ke waktu → **total rotasi** dalam satu window.
3. Setiap sekitar 1,8 detik data diolah, lalu publish JSON. Tidak mengirim data palsu ketika sensor tidak tersedia.

Kode inti dapat dilihat pada `features()` dan `onMotion()` di `web-edge/index.html`. Bandingkan dengan `shared/processing.py` yang memakai rumus ekuivalen dalam Python.

## Alert pada HP B

Ketika Edge 2 (browser) menerima MQTT `/alerts`, halaman menampilkan teks alert dan mencoba memakai `navigator.vibrate` bila didukung. **Bukan push notification sistem Android** dan dapat berhenti ketika tab berada di background.

## Keamanan

Broker publik hanya untuk pengujian. Siapa pun yang mengetahui topic bisa menyuntikkan data, membaca data, atau mengirim control. Gunakan `PROJECT_ID` unik dan jangan kirim data sensitif. Untuk broker privat, isi username/password lewat halaman pada saat koneksi, gunakan ACL minimal, dan pastikan endpoint WSS benar. Jangan menyimpan kredensial produksi di HTML statis.

## Debug sensor browser HP

Di halaman `web-edge/`, lihat empat counter: **Event motion diterima**, **Accelerometer tersedia**, **Gyroscope tersedia**, dan **Pembacaan 2 sensor valid**.

- **Event motion = 0:** halaman mungkin bukan HTTPS, dibuka di in-app browser, atau Chrome memblokir *Motion sensors*. Di Chrome Android: **⋮ → Settings/Setelan → Site settings/Setelan situs → Motion sensors/Sensor gerak → Allow/Izinkan**, kemudian refresh.
- **Event naik, accelerometer = 0:** browser tidak memberikan pembacaan accelerometer valid.
- **Accelerometer naik, gyroscope = 0:** `DeviceMotionEvent.rotationRate` tidak tersedia. Browser edge memerlukan **dua** sensor; gunakan mode Termux:API agar requirement tetap terpenuhi.
- **Dua sensor valid naik, MQTT sent = 0:** lihat status MQTT, URL `wss://`, koneksi internet dan PROJECT_ID. Nilai RMS/rotasi sekarang tetap tampil meskipun broker belum tersambung.
- **MQTT sent naik, tapi alarm tidak ada:** periksa apakah Edge 2 dan detector berjalan, aktif (ARM), dan berada pada PROJECT_ID yang sama; cek log detector.

Pertahankan tab di foreground. Beberapa browser membatasi sensor saat tab berpindah atau layar terkunci.
