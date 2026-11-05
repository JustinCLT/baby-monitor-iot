# Smart Multimodal Baby Guardian & Closed-Loop Safety Telemetry System

Sistem IoT pemantauan keselamatan bayi berbasis **2 Edge Device** (Baby Node & Parent Node), **6 Fitur Multimodal**, dan **Machine Learning (Scikit-Learn Random Forest + Temporal State Smoothing)** di sisi Server/Laptop melalui **MQTT Cloud** (`broker.hivemq.com`).

---

## Arsitektur Sistem

1. **Edge 1 — Baby Node ([hp_dijaga.py](hp_dijaga.py) / [web-edge/index.html](web-edge/index.html))**:
   Membaca *accelerometer*, *gyroscope*, dan *audio*, lalu mengekstrak **6 fitur multimodal ringan**:
   - **Processing A (IMU)**: `motion_rms`, `jerk_metric`, `tilt_angle`
   - **Processing B (Audio)**: `audio_rms`, `spectral_centroid_approx`, `zcr`
2. **Edge 2 — Parent Node ([hp_pemilik.py](hp_pemilik.py) / [web-edge/index.html](web-edge/index.html))**:
   Menerima pesan darurat dari topik `{PROJECT_ID}/alerts`, memicu getaran (`termux-vibrate` / browser vibration) serta notifikasi/sirine saat status `ALERT`.
3. **Central Server & ML Detector ([detector.py](detector.py) & [nodes/detector_service/rules.py](nodes/detector_service/rules.py))**:
   Menjalankan inferensi **Random Forest (`baby_guardian_model.joblib`)** terhadap 4 kelas target (`0: SLEEPING`, `1: RESTLESS`, `2: CRYING`, `3: PRONE_RISK`) yang dilengkapi **Temporal State Smoothing Filter (Hysteresis 3-state buffer)** untuk memetakan status ke `NORMAL`, `RESTLESS`, dan `ALERT`.

---

## Cara Menjalankan

### 1. Install Dependensi & Latih Model Machine Learning
```bash
python -m pip install -r requirements.txt
python train_model.py
```
Perintah `python train_model.py` akan menghasilkan file `baby_guardian_model.joblib` beserta laporan akurasi (*Classification Report*).

### 2. Jalankan Server ML Detector & Dashboard
```bash
python detector.py
```
- **Dashboard Utama**: `http://localhost:8000`
- **Halaman Sensor Browser (Tanpa Termux)**: `http://localhost:8000/edge`

### 3. Jalankan Edge 1 & Edge 2 (Pilih Browser Online atau CLI)

#### Opsi A: Via Browser Online (`http://localhost:8000/edge` atau HTTPS Netlify/GitHub Pages)
- Buka halaman `/edge` untuk **Edge 1 (Baby Node)** dan **Edge 2 (Parent Node)**.
- Bisa menggunakan sensor fisik HP (*Microphone + Accelerometer/Gyroscope*) atau memilih **Simulasi ML Kelas 0–3 (`SLEEPING`, `RESTLESS`, `CRYING`, `PRONE_RISK`)**.

#### Opsi B: Via Python CLI (Simulator / Termux)
```bash
# Terminal 2 — Parent Node (Edge 2)
python hp_pemilik.py --source simulator --scenario sleeping

# Terminal 3 — Baby Node (Edge 1) - pilih: sleeping | restless | crying | prone_risk
python hp_dijaga.py --source simulator --scenario crying
```

### 4. Menjalankan Unit Tests
```bash
python -m unittest discover -s tests -v
```
