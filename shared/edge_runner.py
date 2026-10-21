"""Common edge loop used by BOTH edge devices.

sensor -> 2 data processing -> JSON telemetry -> MQTT publish

Edge 1 and Edge 2 run exactly the same loop. The only difference is that
Edge 2 also passes `on_alert`, so it subscribes to the alerts topic.
"""

import argparse
import shutil
import json
import time
import uuid
from collections.abc import Callable

from shared.messages import Telemetry
from shared.mqtt_connection import create_client, topic
from shared.processing import extract_features
from shared.sensors import select_source

AlertHandler = Callable[[dict], None]


def _parse_args(device_id: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"PocketGuard {device_id}")
    parser.add_argument("--source", choices=["auto", "simulator", "android"], default="auto",
                        help="auto = sensor HP jika di Termux, simulator jika di laptop")
    parser.add_argument("--scenario", choices=["still", "pickup", "table_shake"], default="still",
                        help="Only used by --source simulator")
    parser.add_argument("--interval", type=float, default=None,
                        help="Approximate sample interval in seconds (default 0.5 on Android, 0.35 simulator)")
    parser.add_argument("--samples", type=int, default=5, help="Samples per processing window")
    args = parser.parse_args()
    if args.source == "auto":
        args.source = "android" if shutil.which("termux-sensor") else "simulator"
    if args.interval is None:
        args.interval = 0.5 if args.source == "android" else 0.35
    if args.interval <= 0 or args.samples < 2:
        parser.error("--interval must be positive and --samples >= 2")
    return args


def run_edge(device_id: str, on_alert: AlertHandler | None = None):
    args = _parse_args(device_id)
    label = device_id.upper()
    source = select_source(args.source, args.scenario)
    client = create_client(device_id)

    if on_alert is not None:
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code.is_failure:
                print(f"[{label}] MQTT connection rejected: {reason_code}")
                return
            client.subscribe(topic("alerts"), qos=1)
            print(f"[{label}] Subscribed to {topic('alerts')}")

        def on_message(client, userdata, message):
            try:
                alert = json.loads(message.payload)
                if not isinstance(alert, dict):
                    raise ValueError("alert must be a JSON object")
            except ValueError:
                print(f"[{label}] Ignored malformed alert: {message.payload[:200]!r}")
                return
            on_alert(alert)

        client.on_connect = on_connect
        client.on_message = on_message

    client.loop_start()
    boot_id = uuid.uuid4().hex
    sequence = 0
    telemetry_topic = topic(f"edge/{device_id}/telemetry")
    print(f"[{label}] Source: {args.source} / scenario: {args.scenario}")
    print(f"[{label}] Publishes to: {telemetry_topic}")

    try:
        while True:
            samples = []
            for _ in range(args.samples):
                samples.append(source.read())
                time.sleep(args.interval)
            features = extract_features(samples)
            telemetry = Telemetry.make(device_id, boot_id, sequence, features.motion_rms, features.rotation_rad)
            info = client.publish(telemetry_topic, telemetry.to_json(), qos=1)
            info.wait_for_publish(timeout=10)
            print(f"[{label}] #{sequence} motion={features.motion_rms:.3f} m/s² | rotation={features.rotation_rad:.3f} rad")
            sequence += 1
    except KeyboardInterrupt:
        print(f"[{label}] Stopped")
    finally:
        client.loop_stop()
        client.disconnect()
