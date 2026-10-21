# Eksplorasi cybersecurity yang aman

**Lakukan eksperimen hanya pada akun, broker, dan namespace topic yang kalian miliki/diizinkan.** Jangan menguji jaringan/perangkat pihak lain tanpa izin.

## 1. Apa yang sudah dilindungi?

| Risiko | Implementasi | Keterbatasan |
|---|---|---|
| Penyadapan data di jalur komunikasi | MQTT over TLS + verifikasi sertifikat | Broker masih dapat membaca pesan |
| Publish topic tanpa izin | Broker ACL di broker pribadi | Broker publik tidak punya ACL: siapa pun bisa publish |
| Replay telemetry | `boot_id`, `sequence`, jendela timestamp | Bisa dilewati penyerang dengan kredensial penuh |
| Payload rusak | JSON parsing dan validasi tipe serta angka finite | Tidak mendeteksi semua nilai palsu |
| Sensor spoofing | Bandingkan dua edge | Tidak membuktikan keaslian sensor |

## 2. Lab A: replay message

Jalankan detector, hentikan Edge 1 agar log lebih jelas, lalu pada broker milik sendiri jalankan:

```bash
python -m scripts.replay_test
```

Dua pesan identik dikirim ke topik Edge 1. Detector akan mencetak `REJECTED_REPLAY` untuk pesan kedua. Ini pemeriksaan level aplikasi, **bukan serangan yang membobol TLS**.

## 3. Lab B: broker authorization

**Lab ini membutuhkan broker pribadi** (misalnya EMQX Cloud atau HiveMQ Cloud). Broker publik HiveMQ yang dipakai secara default tidak punya akun maupun ACL, jadi siapa pun bisa membaca dan mengirim ke topic kalian.

Buat identitas berbeda dan ACL per role:

```text
edge1    publish   pocketguard/<PROJECT_ID>/edge/edge1/telemetry
edge2    publish   pocketguard/<PROJECT_ID>/edge/edge2/telemetry
edge2    subscribe pocketguard/<PROJECT_ID>/alerts
detector subscribe pocketguard/<PROJECT_ID>/edge/+/telemetry
detector publish   pocketguard/<PROJECT_ID>/alerts
owner    publish   pocketguard/<PROJECT_ID>/control
dashboard subscribe pocketguard/<PROJECT_ID>/edge/+/telemetry
dashboard subscribe pocketguard/<PROJECT_ID>/status
dashboard subscribe pocketguard/<PROJECT_ID>/alerts
dashboard publish   pocketguard/<PROJECT_ID>/control
detector publish   pocketguard/<PROJECT_ID>/status
```

Dashboard menyimpan password di memori browser selama dibuka, jadi beri akun dashboard hak sekecil mungkin.

Dengan akun pengujian kalian sendiri, coba publish ke topic yang tidak diizinkan dan amati apakah broker menolaknya. Pastikan kebijakan default ACL tidak `allow all`.

Quickstart dapat memakai akun sama agar mudah, tetapi itu **bukan contoh least privilege**. Gunakan kredensial per perangkat untuk menguji peran.

## 4. Lab C: false data injection

Dalam namespace sendiri, kirim telemetry bergerak dari Edge 1 padahal HP fisik diam. Detector bisa mengeluarkan alert ketika Edge 2 diam. Ini menunjukkan mengapa **telemetry yang sudah melewati TLS belum tentu benar secara fisik**.

## 5. Metrik pengujian

- True positive: jumlah percobaan HP diangkat dan terdeteksi.
- False positive: jumlah percobaan HP diam namun alarm muncul.
- Detection latency: jeda dari gerakan awal hingga alarm diterima.
- Replay rejection rate: jumlah replay ditolak / total replay pengujian.

Catat threshold, hardware, interval sampel, dan hasil tiap percobaan. Uji sekitar 10 kali per skenario agar data evaluasi lebih informatif.
