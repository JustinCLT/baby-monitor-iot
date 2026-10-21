# Dashboard laptop — http://localhost:8000

Dashboard disajikan otomatis saat **`python detector.py`** dijalankan di laptop.

- Melihat telemetry Edge 1 dan Edge 2, grafik RMS, serta status `NORMAL`, `ALERT`, atau `COMMON_MOTION`.
- Tombol **ARM / DISARM** mengirim kontrol melalui MQTT Cloud.
- Melihat riwayat alert saat halaman aktif.

## Jalankan

```bash
python -m pip install -r requirements.txt
python detector.py
```

Buka URL yang ditampilkan di terminal, default **http://localhost:8000**. Server HTTP hanya terikat ke `127.0.0.1` untuk akses laptop sendiri. `DASHBOARD_PORT` bisa diubah di `.env` jika port 8000 dipakai aplikasi lain.

Server menyajikan `dashboard/index.html` dan `/config.json` yang hanya berisi PROJECT_ID serta URL WSS broker (tanpa password/kredensial). Pada broker publik default dashboard **auto-connect** dengan konfigurasi ini.

Untuk broker pribadi, dashboard menampilkan form agar pengguna mengisi kredensial **khusus dashboard**. Password broker dari `.env` laptop **tidak dikirim ke browser**. Set `MQTT_WS_URL` di `.env` untuk URL WSS broker privat.

## Mengapa ada dua koneksi?

```text
HP A / HP B ---- MQTT TLS atau MQTT WSS ----> Broker Cloud
Laptop Detector ---------- MQTT TLS --------> Broker Cloud
Laptop Browser ----------- MQTT WSS --------> Broker Cloud
                       ^
          localhost:8000 hanya untuk file HTML
```

Browser tidak bisa memakai koneksi MQTT TCP port 8883, jadi memakai WebSocket over TLS (WSS). Semua memakai namespace topic `pocketguard/<PROJECT_ID>/...`.

## Troubleshooting

| Gejala | Pemeriksaan |
|---|---|
| Port 8000 dipakai | Set `DASHBOARD_PORT=8001` pada `.env` dan restart |
| Dashboard terbuka tapi MQTT belum terhubung | Internet, alamat WSS, CDN MQTT.js, atau kredensial browser |
| Dashboard kosong | PROJECT_ID harus sama pada laptop dan kedua HP |
| Status OFFLINE | Pastikan proses `python detector.py` masih berjalan |
| HP browser tidak punya sensor | Gunakan [BROWSER_EDGE.md](BROWSER_EDGE.md) untuk pengecekan dukungan sensor |

Perlu browser pada HP sebagai edge? Itu halaman **berbeda**, `web-edge/index.html`, dan harus di-host lewat HTTPS. Dashboard lokal sendiri **tidak membaca sensor HP**.
