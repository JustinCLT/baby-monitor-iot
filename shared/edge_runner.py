"""Common multimodal edge pipeline for Baby Node (edge1) and Parent Node (edge2).

IMU + audio samples -> 6 multimodal features -> JSON telemetry on MQTT.
Nodes with an `on_alert` handler also subscribe to `alerts` and `status`.
"""

import argparse
import json
import time
import uuid
from collections.abc import Callable

from shared.messages import Telemetry
from shared.mqtt_connection import create_client, topic
from shared.processing import extract_features
from shared.sensors import select_source

AlertHandler = Callable[[dict], None]

NODE_LABELS = {
    "edge1": "BABY_NODE",
    "edge2": "PARENT_NODE",
}


def _parse_args(device_id: str, default_scenario: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Smart Multimodal Baby Guardian — {NODE_LABELS[device_id]}")
    parser.add_argument("--source", choices=["android", "simulator"], default="android",
                        help="android = real sensors via Termux:API (default); simulator = synthetic data")
    parser.add_argument("--scenario", default=default_scenario,
                        choices=["sleeping", "restless", "crying", "prone_risk"],
                        help="Scenario for --source simulator")
    parser.add_argument("--interval", type=float, default=None, help="Seconds between samples")
    parser.add_argument("--samples", type=int, default=6, help="Samples per feature window")
    parser.add_argument("--debug-sensors", action="store_true", help="Print raw IMU + audio samples")
    args = parser.parse_args()
    if args.interval is None:
        args.interval = 0.1 if args.source == "android" else 0.25
    if args.interval <= 0 or args.samples < 3:
        parser.error("--interval must be positive and --samples >= 3")
    return args


def run_edge(device_id: str, on_alert: AlertHandler | None = None, default_scenario: str = "sleeping"):
    args = _parse_args(device_id, default_scenario)
    label = NODE_LABELS[device_id]
    source = select_source(args.source, args.scenario)
    client = create_client(device_id)

    if on_alert is not None:
        alerts_topic = topic("alerts")
        status_topic = topic("status")

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code.is_failure:
                print(f"[{label}] MQTT connection rejected: {reason_code}", flush=True)
                return
            client.subscribe([(alerts_topic, 1), (status_topic, 1)])
            print(f"[{label}] Listening for alerts on {alerts_topic}", flush=True)

        def on_message(client, userdata, message):
            try:
                payload = json.loads(message.payload)
                if not isinstance(payload, dict):
                    raise ValueError("Payload must be a JSON object")
            except ValueError:
                print(f"[{label}] Ignored malformed message on {message.topic}", flush=True)
                return
            if message.topic == alerts_topic:
                on_alert(payload)
            else:
                print(f"[{label} | MONITOR] Status bayi: {payload.get('status', '?')} — {payload.get('reason', '')}",
                      flush=True)

        client.on_connect = on_connect
        client.on_message = on_message

    client.loop_start()
    boot_id = uuid.uuid4().hex
    sequence = 0
    telemetry_topic = topic(f"edge/{device_id}/telemetry")
    print(f"[{label}] Source  : {args.source}" + (f" (scenario={args.scenario})" if args.source == "simulator" else ""),
          flush=True)
    print(f"[{label}] Publish : {telemetry_topic}", flush=True)

    try:
        while True:
            samples = []
            for index in range(args.samples):
                sample = source.read()
                samples.append(sample)
                if args.debug_sensors:
                    print(f"[{label} | RAW] accel={tuple(round(v, 3) for v in sample.acceleration)} "
                          f"gyro={tuple(round(v, 3) for v in sample.gyroscope)} audio={sample.audio_level:.4f}",
                          flush=True)
                if index < args.samples - 1:
                    time.sleep(args.interval)

            f = extract_features(samples)
            telemetry = Telemetry.make(
                device_id, boot_id, sequence,
                motion_rms=f.motion_rms, jerk_metric=f.jerk_metric, tilt_angle=f.tilt_angle,
                audio_rms=f.audio_rms, spectral_centroid_approx=f.spectral_centroid_approx, zcr=f.zcr,
            )
            client.publish(telemetry_topic, telemetry.to_json(), qos=1).wait_for_publish(timeout=10)
            print(f"[{label}] #{sequence} motion={f.motion_rms:.3f} jerk={f.jerk_metric:.2f} "
                  f"tilt={f.tilt_angle:.1f}° audio={f.audio_rms:.3f} "
                  f"centroid={f.spectral_centroid_approx:.0f}Hz zcr={f.zcr:.3f}", flush=True)
            sequence += 1
    except KeyboardInterrupt:
        print(f"[{label}] Stopped", flush=True)
    finally:
        client.loop_stop()
        client.disconnect()
