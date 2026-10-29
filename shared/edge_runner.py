"""Common edge pipeline for Baby Node (edge1) and Parent Node (edge2).

Real sensor -> two feature extractions (Motion RMS + Audio RMS) -> MQTT Cloud.
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
    "edge1": "BABY_NODE (Edge 1 - Kasur Bayi)",
    "edge2": "PARENT_NODE (Edge 2 - Orang Tua)",
}


def _parse_args(
    device_id: str,
    default_scenario: str = "sleeping",
    description: str | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=description or f"Smart Baby Monitor — {NODE_LABELS.get(device_id, device_id)}"
    )
    parser.add_argument(
        "--source",
        choices=["android", "simulator"],
        default="android",
        help="Default: real Android sensors via Termux:API. Use simulator only for testing.",
    )
    parser.add_argument(
        "--scenario",
        choices=["sleeping", "restless", "crying_awake", "crowd_noise", "still", "pickup", "table_shake"],
        default=default_scenario,
        help="Scenario used when --source simulator is selected.",
    )
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument(
        "--debug-sensors",
        action="store_true",
        help="Print raw accelerometer, gyroscope, and audio RMS values before processing.",
    )
    args = parser.parse_args()
    if args.interval is None:
        args.interval = 0.1 if args.source == "android" else 0.35
    if args.interval <= 0 or args.samples < 2:
        parser.error("--interval must be positive and --samples >= 2")
    return args


def run_edge(
    device_id: str,
    on_alert: AlertHandler | None = None,
    default_scenario: str = "sleeping",
    node_label: str | None = None,
):
    args = _parse_args(device_id, default_scenario=default_scenario, description=node_label)
    label = node_label or NODE_LABELS.get(device_id, device_id.upper())
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
            print(f"[{label}] Subscribed to {alerts_topic} & {status_topic}", flush=True)

        def on_message(client, userdata, message):
            try:
                payload = json.loads(message.payload)
                if not isinstance(payload, dict):
                    raise ValueError("Payload must be a JSON object")
            except ValueError:
                print(f"[{label}] Ignored malformed MQTT message on {message.topic}", flush=True)
                return

            if message.topic == alerts_topic:
                on_alert(payload)
            elif message.topic == status_topic:
                status_val = payload.get("status", "UNKNOWN")
                reason_val = payload.get("reason", "")
                print(f"[{label} | MONITOR] Status Kamar Bayi: {status_val} — {reason_val}", flush=True)

        client.on_connect = on_connect
        client.on_message = on_message

    client.loop_start()
    boot_id = uuid.uuid4().hex
    sequence = 0
    telemetry_topic = topic(f"edge/{device_id}/telemetry")
    print(f"[{label}] Source   : {args.source} (scenario={args.scenario})", flush=True)
    print(f"[{label}] Publish  : {telemetry_topic}", flush=True)

    try:
        while True:
            samples = []
            for sample_index in range(args.samples):
                sample = source.read()
                samples.append(sample)
                if args.debug_sensors:
                    print(
                        f"[{label} | RAW] accel={sample.acceleration} m/s² "
                        f"gyro={sample.gyroscope} rad/s "
                        f"audio_rms={sample.audio_rms:.4f}",
                        flush=True,
                    )
                if sample_index < args.samples - 1:
                    time.sleep(args.interval)

            features = extract_features(samples)
            telemetry = Telemetry.make(
                device_id=device_id,
                boot_id=boot_id,
                sequence=sequence,
                motion_rms=features.motion_rms,
                rotation_rad=features.rotation_rad,
                audio_rms=features.audio_rms,
            )
            info = client.publish(telemetry_topic, telemetry.to_json(), qos=1)
            info.wait_for_publish(timeout=10)
            print(
                f"[{label}] #{sequence} "
                f"motion_rms={features.motion_rms:.3f} m/s², "
                f"rotation={features.rotation_rad:.3f} rad, "
                f"audio_rms={features.audio_rms:.3f}",
                flush=True,
            )
            sequence += 1
    except KeyboardInterrupt:
        print(f"[{label}] Stopped", flush=True)
    finally:
        client.loop_stop()
        client.disconnect()
