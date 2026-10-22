# Sensor Playground (iPhone / Android, tanpa Termux)

Mode ini adalah **fitur tambahan** pada halaman lama PocketGuard, bukan aplikasi atau proyek baru.

1. Buka halaman edge di HTTPS (misalnya `iot.myudak.com`) menggunakan **Safari di iPhone** atau **Chrome di Android**.
2. Tekan tombol **Buka Sensor Playground**.
3. Isi **Device ID**, **MQTT WSS broker**, dan **MQTT topic** yang unik.
4. Centang sensor yang tersedia pada HP, kemudian tekan **Start sensor sender**.
5. Izinkan akses sensor ketika browser meminta. Pertahankan tab tetap terbuka.
6. Untuk melihat data, buka MQTTX Web / MQTTX Desktop dan **subscribe ke topic persis sama** yang ditampilkan.
7. Tekan **Stop** untuk menghentikan pembacaan sensor, GPS watcher, microphone dan MQTT.

## Sensor & data yang dikirim

| Checkbox | Browser API | Data JSON |
|---|---|---|
| Accelerometer | `DeviceMotionEvent.accelerationIncludingGravity` | `sensors.accelerometer.{x,y,z,magnitude}` (m/s²) |
| Gyroscope | `DeviceMotionEvent.rotationRate` | `sensors.gyroscope.{x,y,z,magnitude}` (rad/s) |
| Orientation | `DeviceOrientationEvent` | `sensors.orientation.{alpha,beta,gamma}` (deg) |
| GPS | `navigator.geolocation.watchPosition` | `sensors.gps.{latitude,longitude,accuracy_m}` |
| Microphone | `getUserMedia` + Web Audio | `sensors.microphone.rms` (normalized amplitude, **not dB SPL**) |

**Extra processing pada HP:** `features.motion_rms` diperoleh dari RMS perbedaan magnitudo akselerasi dan 9,81 m/s² dalam satu jendela pengiriman.

Contoh struktur pesan (**angka ilustrasi**, bukan pembacaan sensor asli):

```json
{
  "device_id": "iphone-1",
  "sent_at_ms": 1790000000000,
  "sequence": 3,
  "sensors": {
    "accelerometer": {"x": 0.1, "y": 0.2, "z": 9.8, "magnitude": 9.8026},
    "gyroscope": {"x": 0.01, "y": 0.02, "z": 0.01, "magnitude": 0.0245, "unit": "rad/s"}
  },
  "features": {"motion_rms": 0.015}
}
```

## MQTT contoh

- WebSocket Secure broker default: `wss://broker.hivemq.com:8884/mqtt`
- Topic contoh: `iot/kelas-demo/iphone-1/telemetry`
- MQTTX Web subscribe ke topic ini, lalu gerakkan HP untuk melihat payload.
- Karena broker publik, **jangan gunakan data pribadi** dan pilih topic unik supaya tidak tabrakan dengan pengguna lain.

> **Privasi GPS:** jika memilih GPS pada broker publik, akan muncul konfirmasi karena koordinat bisa dibaca oleh subscriber publik yang mengetahui topik. Untuk demo kelas, sebaiknya nonaktifkan GPS atau gunakan broker privat + autentikasi/ACL.

## Kalau tidak terbaca

- Web harus dibuka lewat **HTTPS**, bukan HTTP ke IP laptop.
- Safari iOS meminta izin motion/orientation saat tombol Start ditekan. Jika ditolak, periksa izin situs dan refresh.
- Browser tidak selalu menyediakan semua sensor. Sensor yang tidak tersedia **tidak dibuatkan data palsu**.
- Gyroscope tidak dijamin tersedia di tiap perangkat/browser; monitor isi JSON dan pesan log.
- Microphone hanya mengirim nilai RMS, bukan audio. Jika izin ditolak, sensor lain masih bisa dipakai.
- Browser yang pindah ke background/layar terkunci dapat menghentikan sensor.
- Jika JSON muncul tetapi MQTT sent tetap 0, periksa broker WSS, kredensial, dan jaringan.
- Untuk kebutuhan dosen, **2 edge device harus benar-benar 2 HP terpisah**. Gunakan topic berbeda per perangkat.

Mode PocketGuard lama tetap bisa dibuka dengan tombol **Kembali ke PocketGuard**.
