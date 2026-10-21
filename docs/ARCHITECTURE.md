# Arsitektur IoT

Ada tiga node utama, berjalan **pada tiga perangkat fisik**: dua HP sebagai edge dan satu laptop sebagai detector/dashboard.

```mermaid
flowchart TB
    subgraph LAN["Satu jaringan Wi-Fi / hotspot"]
        subgraph E1["NODE 1 — HP A"]
            A1["Accelerometer + Gyroscope"] --> P1["RMS + rotasi"]
        end
        subgraph E2["NODE 2 — HP B"]
            A2["Accelerometer + Gyroscope"] --> P2["RMS + rotasi"]
        end
        subgraph LAPTOP["NODE 3 — Laptop"]
            D["Python Detector"]
            UI["Dashboard localhost:8000"]
        end
    end
    P1 -->|"MQTT TLS (Termux) / WSS (Browser)"| MQTT["Cloud MQTT Broker"]
    P2 -->|"MQTT TLS (Termux) / WSS (Browser)"| MQTT
    MQTT -->|"Subscribe telemetry"| D
    D -->|"Publish alerts dan status"| MQTT
    MQTT -->|"Subscribe alerts"| E2
    MQTT <-->|"MQTT WSS"| UI
```

## Peran node

| Node | Perangkat | Input | Processing | Output |
|---|---|---|---|---|
| Edge 1 | HP A | Accelerometer + gyroscope | RMS + integrasi rotasi | Telemetry MQTT |
| Edge 2 | HP B | Accelerometer + gyroscope | RMS + integrasi rotasi | Telemetry MQTT + terima alert |
| Detector | Laptop | Telemetry dari broker | Sensor fusion rule-based | Status / alert MQTT |
| Dashboard | Browser laptop | Status / telemetry MQTT | Visualisasi | Grafik & ARM/DISARM |
| Broker | Cloud | Publish MQTT | Routing topic | Pesan ke subscriber |

**Dua cara menjalankan edge asli:** Termux:API dengan Python atau browser melalui HTTPS dengan DeviceMotionEvent. Keduanya menghasilkan payload JSON identik. Source: `shared/processing.py` dan `web-edge/index.html`.

## Data flow

```mermaid
sequenceDiagram
    participant A as HP A - Edge 1
    participant B as HP B - Edge 2
    participant M as MQTT Cloud
    participant D as Laptop - Detector
    participant W as Laptop - Dashboard
    A->>M: telemetry edge1 (RMS, rotasi)
    B->>M: telemetry edge2 (RMS, rotasi)
    M->>D: subscribe edge/+/telemetry
    D->>D: Compare motion windows
    D->>M: publish alerts / status
    M->>B: deliver alert
    M->>W: deliver telemetry / status / alert
```

Catatan: dashboard localhost tidak bisa diakses lewat `localhost` HP. Browser edge harus memakai origin HTTPS dari hosting tersendiri.
