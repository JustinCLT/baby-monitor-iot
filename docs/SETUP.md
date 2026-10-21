# Setup MQTT Cloud (EMQX)

## Yang dibutuhkan

- Laptop dengan Python 3.10+ dan akses internet.
- Akun EMQX Cloud / broker MQTT cloud lain dengan koneksi MQTT TLS.
- Untuk memenuhi tugas fisik: 2 HP Android dengan sensor accelerometer dan gyro, berada pada Wi-Fi/hotspot yang sama.

## 1. Siapkan broker

1. Buka https://www.emqx.com/en/cloud dan buat deployment sesuai opsi yang tersedia pada akun.
2. Di konsol broker, buat username dan password MQTT untuk praktikum.
3. Catat **hostname** MQTT dan port TLS (biasanya `8883`, periksa halaman koneksi deployment).
4. Untuk demo awal gunakan satu akun kelas. Untuk pengujian **security**, buat akun terpisah per edge dan atur **topic authorization / ACL** sehingga tiap edge hanya bisa publish pada topiknya sendiri.

**Jangan commit kredensial ke GitHub!** File `.env` sudah ada dalam `.gitignore`.

## 2. Konfigurasi dan install

Dari folder root proyek:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Isi `.env` dengan hostname dan username/password asli. `PROJECT_ID` harus unik agar tidak tercampur dengan kelompok lain:

```env
PROJECT_ID=kelas_iot_kelompok_07
MQTT_HOST=xxxxxxxx.emqxsl.com
MQTT_PORT=8883
MQTT_TLS=true
MQTT_USERNAME=your_broker_username
MQTT_PASSWORD=your_broker_password
```

**MQTT_TLS=true** mengaktifkan verifikasi sertifikat broker. Jangan matikan TLS untuk koneksi cloud. Penggunaan broker publik `1883` tanpa autentikasi tidak cocok untuk proyek keamanan.

## 3. Jalankan 3 node pada 3 terminal

Pertama jalankan detector:

```bash
python -m nodes.detector_service.main
```

Lalu Edge 2 (HP pemilik / simulator):

```bash
python -m nodes.edge2_guardian.main --source simulator --scenario still
```

Lalu Edge 1 (HP dijaga / simulator):

```bash
python -m nodes.edge1_protected.main --source simulator --scenario pickup
```

Tunggu beberapa detik. Detector menerima dua telemetry, menghitung alert, lalu mengirim pesan ke Edge 2 via cloud broker.

Untuk tes menggunakan perangkat fisik Android, baca [ANDROID.md](ANDROID.md).

## 4. Topic MQTT dan arah data

```text
pocketguard/<PROJECT_ID>/edge/edge1/telemetry     # Edge 1 --> broker --> detector
pocketguard/<PROJECT_ID>/edge/edge2/telemetry     # Edge 2 --> broker --> detector
pocketguard/<PROJECT_ID>/control                  # Owner --> broker --> detector
pocketguard/<PROJECT_ID>/alerts                   # Detector --> broker --> Edge 2
```

Topik subscribe milik detector: `pocketguard/<PROJECT_ID>/edge/+/telemetry`. Simbol `+` adalah MQTT wildcard untuk **satu** level topik.

## 5. ARM / DISARM

```bash
python -m scripts.send_control DISARM
python -m scripts.send_control ARM
```

Perintah ini berupa payload teks `ARM` atau `DISARM` pada topik `/control`. **Broker ACL harus membatasi siapa yang boleh mengirim control.** Ini contoh sederhana untuk pembelajaran, belum protokol control otentikasi end-to-end yang siap produksi.

## 6. Troubleshooting

| Gejala | Kemungkinan penyebab |
|---|---|
| `Configure MQTT_HOST` | Belum isi `.env` |
| `not authorized` / gagal connect | Username/password salah atau ACL menolak |
| `certificate verify failed` | Host TLS atau sertifikat salah |
| Telemetry terlihat, alert tidak keluar | Dua edge belum berjalan, scenario belum aktif, atau sensor kurang bergerak |
| Edge tidak menerima alarm | Periksa subscription ke topik `alerts` dan authorization subscribe |
| `REJECTED_STALE` | Jam kedua perangkat tidak sinkron, atau pesan tertunda >30 detik |

Untuk demo awal tanpa broker gunakan `python -m scripts.offline_demo`.
