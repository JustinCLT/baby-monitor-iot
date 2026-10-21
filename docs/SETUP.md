# MQTT Cloud: konfigurasi

Proyek ini memakai MQTT ke **broker di cloud**, bukan komunikasi langsung antar-HP.

## Default (tanpa daftar akun)

Gunakan broker publik HiveMQ untuk belajar:
- MQTT Python (TLS): `broker.hivemq.com:8883`
- MQTT browser (WSS): `wss://broker.hivemq.com:8884/mqtt`

Broker publik **tidak aman untuk data rahasia**: orang lain dapat membaca atau mengirim pada topic yang diketahui.

## Konfigurasi perangkat

Di laptop, buat `.env` berdasarkan `.env.example`:

```env
PROJECT_ID=iot_kelompok_07
MQTT_HOST=broker.hivemq.com
MQTT_PORT=8883
MQTT_TLS=true
MQTT_WS_URL=wss://broker.hivemq.com:8884/mqtt
MQTT_USERNAME=
MQTT_PASSWORD=
```

**Semua edge dan detector harus memakai PROJECT_ID yang sama.** Nama kelompok berbeda = namespace topic berbeda.

- **Termux edge:** salin `.env` di tiap HP (tidak perlu menyalin kredensial berlebih).
- **Browser edge:** masukkan `PROJECT_ID` yang sama pada halaman HTTPS.
- **Dashboard laptop:** otomatis mengambil `PROJECT_ID` dan `MQTT_WS_URL` dari server lokal.

## Topic

```text
pocketguard/<PROJECT_ID>/edge/edge1/telemetry
pocketguard/<PROJECT_ID>/edge/edge2/telemetry
pocketguard/<PROJECT_ID>/status
pocketguard/<PROJECT_ID>/alerts
pocketguard/<PROJECT_ID>/control
```

Edge publish telemetry; detector subscribe telemetry dan publish status/alerts; dashboard subscribe semua status dan bisa publish ARM/DISARM. Edge 2 subscribe alerts.

## Broker privat (untuk security)

Ganti `MQTT_HOST`, `MQTT_USERNAME`, dan `MQTT_PASSWORD` untuk Python. Set `MQTT_WS_URL` ke alamat WSS broker yang benar untuk browser. **Jangan memasukkan password dalam URL halaman ataupun menyimpannya di repository.**

Dashboard lokal tidak mengirim kredensial laptop melalui `/config.json`; pengguna dashboard harus memasukkan kredensial **khusus dashboard** secara manual. Browser-edge juga membutuhkan kredensial sendiri untuk broker privat.

Untuk eksperimen access control, atur ACL topic di broker privat seperti pada [SECURITY.md](SECURITY.md).
