# Penggunaan GitHub untuk pembelajaran

Repository: https://github.com/myudak/contoh-project-iot1

## Clone

```bash
git clone https://github.com/myudak/contoh-project-iot1.git
cd contoh-project-iot1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Alur pengerjaan kelompok

1. **Anggota Edge** mengerjakan `nodes/edge1_protected/`, `nodes/edge2_guardian/`, dan `shared/sensors.py`.
2. **Anggota Algoritma** mengerjakan `shared/processing.py`, `nodes/detector_service/rules.py`, serta pengujian.
3. **Anggota Cloud** mengerjakan broker, MQTT, ACL, `shared/mqtt_connection.py`, dashboard (`dashboard/index.html`), serta dokumentasi.

Buat branch kecil per fitur, lalu ajukan pull request dengan penjelasan percobaan.

## Keamanan

File `.env` bisa berisi kredensial (jika memakai broker pribadi) dan **tidak boleh di-commit**. Hanya unggah `.env.example` yang berisi placeholder. Tidak perlu membuka broker kelas sebagai broker publik.

GitHub Actions di `.github/workflows/test.yml` mencoba menjalankan unit test pada setiap push atau pull request (bila Actions diaktifkan).
