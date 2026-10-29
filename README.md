# Smart Dual-Zone Baby Monitor & Restlessness/Cry Guard

Sistem IoT pemantauan bayi berbasis **2 Edge Device** (Baby Node & Parent Node) dan **1 Central Detector + Web Dashboard** melalui **MQTT Cloud** (`broker.hivemq.com`).

## Arsitektur & Kebutuhan Sistem

1. **Edge Devices (2 Nodes)**:
   - **Edge 1 (`Baby Node`)**: Diletakkan di dekat kasur/bayi. Memantau getaran kasur (kegelisahan fisik) dan amplitudo audio lingkungan (suara tangisan bayi).
   - **Edge 2 (`Parent Node`)**: Dipegang orang tua di ruangan lain. Menerima notifikasi darurat (getar/suara via Browser atau Termux) dan memantau status kamar bayi.
2. **Sensor yang Digunakan**:
   - **Motion Sensor**: Accelerometer & Gyroscope (mengukur getaran fisik/aktivitas di kasur).
   - **Audio Sensor**: Microphone / Audio Amplitude (`audio_rms` — mengukur level suara/amplitudo tangisan bayi).
3. **Data Processing di Sisi Edge (`shared/processing.py` & `web-edge/index.html`)**:
   - **Processing A (Motion)**: Root Mean Square (`motion_rms`) dari deviasi percepatan linier terhadap gravitasi bumi ($9.81\text{ m/s}^2$) serta integrasi rotasi sudut giroskop (`rotation_rad`).
   - **Processing B (Audio)**: Audio RMS / Short-Time Energy (`audio_rms`) untuk mengukur volume kebisingan dan tangisan dalam satu window waktu.
4. **Central Detector / Decision Engine (`nodes/detector_service/rules.py`)**:
   - **`SLEEPING_SOUNDLY`**: Audio hening (`audio_rms` rendah), kasur tenang (`motion_rms` rendah).
   - **`RESTLESS_BABY`**: Audio tenang, tetapi getaran kasur meningkat (bayi bolak-balik posisi atau merangkak tanpa menangis).
   - **`CRYING_AWAKE`**: Audio keras melampaui ambang batas tangisan (`audio_rms` tinggi) ATAU gabungan audio keras + getaran kasur tinggi (memicu alarm darurat di Edge 2).
   - **`CROWD_NOISE`**: Audio tinggi sesaat tapi tidak ada getaran kasur (misal suara pintu tertutup dari luar kamar).
   - Dilengkapi validasi keamanan **anti-stale timestamp** ($< 30\text{ detik}$) dan **anti-replay sequence number**.

---

## Cara Menjalankan

### 1. Laptop — Jalankan Central Detector & Dashboard
```bash
python -m pip install -r requirements.txt
cp .env.example .env
python detector.py
```
- Buka Dashboard di **`http://localhost:8000`**.
- Buka Halaman Sensor Browser (Tanpa Termux) di **`http://localhost:8000/edge`**.

### 2. Menjalankan Edge 1 & Edge 2

#### Opsi A: Via Browser Online (Tanpa Termux)
1. Buka `http://localhost:8000/edge` (atau deploy folder `web-edge/` ke Netlify Drop / GitHub Pages untuk akses HTTPS di 2 HP).
2. Pilih **Edge 1 — Baby Node** di HP 1 dan **Edge 2 — Parent Node** di HP 2.
3. Samakan `PROJECT_ID` dengan file `.env`, lalu tekan **Mulai Jalankan Node** dan izinkan akses Microphone & Motion Sensor.

#### Opsi B: Via Python CLI / Simulator / Termux
```bash
# Edge 2 (Parent Node)
python hp_pemilik.py --source simulator --scenario sleeping

# Edge 1 (Baby Node) - pilih skenario: sleeping | restless | crowd_noise | crying_awake
python hp_dijaga.py --source simulator --scenario crying_awake
```

### 3. Menjalankan Unit Tests
```bash
python -m unittest discover -s tests -v
```
