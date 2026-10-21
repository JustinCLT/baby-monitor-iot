# Setup MQTT Broker

Contoh ini memakai **broker publik HiveMQ** (`broker.hivemq.com`): gratis, **tanpa daftar akun**, dan berada di internet (cloud). Cukup isi `PROJECT_ID` yang unik.

## Yang dibutuhkan

- Laptop dengan Python 3.10+ dan akses internet.
- Untuk memenuhi tugas fisik: 2 HP Android dengan sensor accelerometer dan gyro, berada pada Wi-Fi/hotspot yang sama.

## 1. Broker yang dipakai

| Pengaturan | Nilai |
|---|---|
| Host | `broker.hivemq.com` |
| MQTT over TLS (Python) | port `8883` |
| MQTT over WebSocket TLS (dashboard) | `wss://broker.hivemq.com:8884/mqtt` |
| Username / password | tidak perlu |

**Penting:** broker publik dipakai bersama semua orang. Siapa pun yang tahu topic kalian bisa membaca dan mengirim pesan. Karena itu:

- pakai `PROJECT_ID` yang unik (misalnya nama kelas + nomor kelompok),
- jangan kirim data pribadi atau rahasia.

Ingin broker pribadi dengan username/password dan ACL? Pakai layanan seperti EMQX Cloud atau HiveMQ Cloud, lalu isi `MQTT_HOST`, `MQTT_USERNAME`, dan `MQTT_PASSWORD` di `.env`. Kode tidak perlu diubah.

## 2. Konfigurasi dan install

Dari folder root proyek:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Di `.env`, cukup ganti `PROJECT_ID` dengan nama unik kelompokmu:

```env
PROJECT_ID=kelas_iot_kelompok_07
MQTT_HOST=broker.hivemq.com
MQTT_PORT=8883
MQTT_TLS=true
MQTT_USERNAME=
MQTT_PASSWORD=
```

`PROJECT_ID` harus **sama** di HP A, HP B, laptop, dan dashboard. `MQTT_TLS=true` mengenkripsi koneksi; jangan dimatikan.

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

Opsional: buka `dashboard/index.html` untuk melihat semuanya secara visual ([DASHBOARD.md](DASHBOARD.md)).

Untuk tes menggunakan perangkat fisik Android, baca [ANDROID.md](ANDROID.md).

## 4. Topic MQTT dan arah data

```text
pocketguard/<PROJECT_ID>/edge/edge1/telemetry     # Edge 1 --> broker --> detector
pocketguard/<PROJECT_ID>/edge/edge2/telemetry     # Edge 2 --> broker --> detector
pocketguard/<PROJECT_ID>/control                  # Owner --> broker --> detector
pocketguard/<PROJECT_ID>/alerts                   # Detector --> broker --> Edge 2 + dashboard
pocketguard/<PROJECT_ID>/status                   # Detector --> broker --> dashboard (retained)
```

Dashboard web memakai topic yang sama lewat **MQTT over WebSocket**. Lihat [DASHBOARD.md](DASHBOARD.md).

Topik subscribe milik detector: `pocketguard/<PROJECT_ID>/edge/+/telemetry`. Simbol `+` adalah MQTT wildcard untuk **satu** level topik.

## 5. ARM / DISARM

```bash
python -m scripts.send_control DISARM
python -m scripts.send_control ARM
```

Bisa juga lewat tombol ARM/DISARM di dashboard. Perintah ini berupa payload teks `ARM` atau `DISARM` pada topik `/control`. Di broker publik siapa pun bisa mengirim ke topic ini; di broker pribadi, **ACL harus membatasi siapa yang boleh mengirim control**. Ini contoh sederhana untuk pembelajaran, belum protokol control otentikasi end-to-end yang siap produksi.

## 6. Troubleshooting

| Gejala | Kemungkinan penyebab |
|---|---|
| Warning `PROJECT_ID masih 'kelas_iot_demo'` | Belum mengganti `PROJECT_ID` di `.env` |
| Gagal connect / timeout | Tidak ada internet, atau jaringan memblokir port 8883 (coba hotspot HP) |
| `not authorized` | Username/password salah (hanya untuk broker pribadi) |
| `certificate verify failed` | Host TLS atau sertifikat salah |
| Telemetry terlihat, alert tidak keluar | Dua edge belum berjalan, scenario belum aktif, atau sensor kurang bergerak |
| Edge tidak menerima alarm | `PROJECT_ID` berbeda antarperangkat, atau Edge 2 belum berjalan |
| `REJECTED_STALE` | Jam kedua perangkat tidak sinkron, atau pesan tertunda >30 detik |

Untuk demo awal tanpa broker gunakan `python -m scripts.offline_demo`.
