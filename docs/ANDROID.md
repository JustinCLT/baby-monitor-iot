# Opsi edge asli: Android + Termux

Jalankan NODE 1 dan NODE 2 pada **dua HP Android terpisah**, bukan dua terminal di laptop.

## Instalasi di kedua HP

1. Install **Termux** dan **Termux:API** dari sumber distribusi yang kompatibel (contoh F-Droid), lalu berikan izin sensor yang diperlukan.
2. Buka Termux:

```bash
pkg update
pkg install python git termux-api
git clone https://github.com/myudak/contoh-project-iot1.git
cd contoh-project-iot1
python -m pip install -r requirements.txt
cp .env.example .env
termux-sensor -l
```

Jika `termux-sensor -l` tidak menampilkan accelerometer dan gyroscope, gunakan HP yang mendukung keduanya.

3. Edit `PROJECT_ID` dalam `.env` agar **sama persis** dengan laptop. Broker publik default dapat dipakai tanpa username/password.

## Jalankan node yang sesuai

**HP A — yang dijaga:**

```bash
python hp_dijaga.py
```

**HP B — HP pemilik:**

```bash
python hp_pemilik.py
```

**Laptop — detector dan dashboard:**

```bash
python detector.py
```

Lihat **http://localhost:8000** di browser laptop.

Sensor masing-masing HP → RMS percepatan dan total rotasi → publish telemetry MQTT. Saat HP A bergerak dan HP B diam, HP B menerima alert, menjalankan getar `termux-vibrate` dan notifikasi `termux-notification` jika izin tersedia.

**Termux bukan satu-satunya pilihan.** Jika mahasiswa ingin menggunakan browser HP tanpa Termux, baca [BROWSER_EDGE.md](BROWSER_EDGE.md).

## Catatan

- Pembacaan sensor via Termux:API dilakukan berulang dan tidak berfrekuensi tinggi; gerakan cepat bisa terlewat.
- Battery saver/background Android dapat menghentikan pembacaan.
- Mode default Python pada HP menggunakan **sensor Android asli**. Simulasi hanya aktif jika pengguna secara eksplisit menambahkan `--source simulator`.
- Semua perangkat tetap dalam satu Wi-Fi/hotspot dengan akses internet.
