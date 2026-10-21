# Arsitektur dan diagram Mermaid

## Alur lengkap

```mermaid
flowchart TB
  subgraph LOCAL["Wi-Fi yang sama - laboratorium"]
    E1["Edge 1: HP dilindungi"]
    E2["Edge 2: HP pemilik"]
    DET["Detector Service: Python"]
  end
  subgraph BROKER["Cloud"]
    MQTT["EMQX MQTT Broker (TLS: 8883)"]
  end
  E1 -->|"accelerometer + gyroscope -> RMS & rotasi -> JSON publish"| MQTT
  E2 -->|"accelerometer + gyroscope -> RMS & rotasi -> JSON publish"| MQTT
  MQTT -->|"MQTT subscribe: edge/+/telemetry"| DET
  DET -->|"bandingkan data + tentukan status"| DET
  DET -->|"MQTT publish: alerts"| MQTT
  MQTT -->|"MQTT subscribe: alerts"| E2
```

## Sequence ketika HP diangkat

```mermaid
sequenceDiagram
  participant A as Node 1: Protected HP
  participant B as Node 2: Owner HP
  participant M as EMQX Cloud
  participant D as Node 3: Detector
  D->>M: SUBSCRIBE pocketguard/<project>/edge/+/telemetry
  B->>M: SUBSCRIBE pocketguard/<project>/alerts
  B->>M: PUBLISH edge/edge2/telemetry (still)
  A->>M: PUBLISH edge/edge1/telemetry (moving)
  M-->>D: Deliver both telemetry messages
  D->>D: Rule: edge1 moving AND edge2 still?
  D->>M: PUBLISH alerts {event:suspicious_movement}
  M-->>B: Deliver alert
  B->>B: Print alarm in terminal
```

## Node responsibilities

| Node | Input | Process | Output | Source code |
|---|---|---|---|---|
| Edge 1 | Accelerometer & gyro | RMS & angular integration | MQTT telemetry Edge 1 | `nodes/edge1_protected/main.py` |
| Edge 2 | Accelerometer & gyro | RMS & angular integration | MQTT telemetry Edge 2, displays alerts | `nodes/edge2_guardian/main.py` |
| Detector service | Both MQTT topics | Pair latest readings + detection rule | MQTT alert | `nodes/detector_service/` |
| EMQX Cloud | MQTT packets | Routes publish to subscribers | MQTT packets | External managed broker |
| Monitor (optional) | Alert MQTT topic | Prints events | Terminal log | `nodes/monitor/main.py` |

**Interpretasi syarat satu network:** kedua edge pada hotspot/Wi-Fi yang sama. Cloud broker memang berada di luar LAN dan diakses via internet. Detector pada setup dasar berada di laptop, bukan VM cloud; bisa dipindahkan ke cloud jika perlu.
