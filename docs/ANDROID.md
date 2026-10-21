# Membaca sensor Android asli

`--source simulator` menjalankan data buatan. **Agar memenuhi tugas 2 edge device, jalankan kode pada 2 HP Android terpisah.**

## 1. Persiapan di kedua HP

1. Pasang **Termux** dan **Termux:API** dari sumber yang kompatibel, misalnya F-Droid. Jangan mencampur versi aplikasi dari sumber berbeda.
2. Beri izin sensor yang diminta Android saat diperlukan.
3. Install paket di Termux:

```bash
pkg update
pkg install python termux-api git
pip install paho-mqtt python-dotenv
```

Periksa sensor:

```bash
termux-sensor -l
termux-sensor -a -n 1
```

Pastikan tersedia **Accelerometer** dan **Gyroscope**. Sebagian HP tidak punya gyroscope atau format/nama sensor berbeda.

## 2. Ambil source code

```bash
git clone https://github.com/myudak/contoh-project-iot1.git
cd contoh-project-iot1
cp .env.example .env
```

Edit `.env` pada kedua HP: cukup ganti `PROJECT_ID` dengan nama unik kelompok (harus sama di semua perangkat). Broker publik HiveMQ sudah menjadi default, tanpa username/password.

**Kedua HP harus berada pada Wi-Fi/hotspot yang sama dan terhubung ke internet.**

## 3. Jalankan setiap node

Di **HP A (dijaga)**:

```bash
python hp_dijaga.py
```

Di **HP B (pemilik)**:

```bash
python hp_pemilik.py
```

Di **laptop** jalankan detector:

```bash
python detector.py
```

Ketika HP A bergerak dan HP B diam, HP B menerima alert MQTT: **bergetar** (`termux-vibrate`) dan menampilkan **notifikasi Android** (`termux-notification`), selain mencetak pesan di terminal.

Mau melihat semuanya sekaligus? Buka dashboard web di laptop: [DASHBOARD.md](DASHBOARD.md).

## Catatan teknis

- Pembacaan `termux-sensor -n 1` berulang via subprocess sengaja dibuat sederhana. Bukan pembacaan frekuensi tinggi yang presisi; gerakan singkat dapat terlewat.
- Battery saver dan aturan background Android dapat menghentikan pembacaan sensor. Pertahankan Termux aktif selama demo.
- Periksa nama sensor dan JSON Termux:API di kedua HP sebelum presentasi. Jika perlu, ubah `shared/sensors.py`.
- Jika sensor tidak tersedia, cari HP lain; **simulasi tidak menggantikan kewajiban sensor fisik**.
- Pendekatan membandingkan gerak paling masuk akal bila kedua HP ditempatkan pada meja yang sama.
