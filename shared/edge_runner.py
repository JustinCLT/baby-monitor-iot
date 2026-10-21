"""Common edge loop. Only the ROLE differs between Edge 1 and Edge 2."""

import argparse
import time
import uuid

from shared.messages import Telemetry
from shared.mqtt_connection import create_client, topic
from shared.processing import extract_features
from shared.sensors import select_source


def run_edge(device_id: str):
    parser = argparse.ArgumentParser(description=f"PocketGuard {device_id}")
    parser.add_argument("--source", choices=["simulator", "android"], default="simulator")
    parser.add_argument("--scenario", choices=["still", "pickup", "table_shake"], default="still")
    parser.add_argument("--interval", type=float, default=0.35, help="Approximate sample interval (seconds)")
    parser.add_argument("--samples", type=int, default=5, help="Samples per processing window")
    args = parser.parse_args()
    if args.interval <= 0 or args.samples < 2:
        parser.error("--interval must be positive and --samples >= 2")

    source = select_source(args.source, args.scenario)
    client = create_client(device_id)

    if device_id == "edge2":
        def on_connect(client, userdata, flags, reason_code, properties):
            if not reason_code.is_failure:
                client.subscribe(topic("alerts"), qos=1)
                print("[EDGE 2 | OWNER] Subscribed to alerts")

        def on_message(client, userdata, message):
            print(f"\n[EDGE 2 | OWNER ALARM] {message.payload.decode(errors='replace')}\n")

        client.on_connect = on_connect
        client.on_message = on_message

    client.loop_start()
    boot_id = uuid.uuid4().hex
    sequence = 0
    print(f"[{device_id.upper()}] Source: {args.source} / scenario: {args.scenario}")
    print(f"[{device_id.upper()}] Publishes to: {topic(f'edge/{device_id}/telemetry')}")

    try:
        while True:
            samples = []
            for _ in range(args.samples):
                samples.append(source.read())
                time.sleep(args.interval)
            features = extract_features(samples)
            telemetry = Telemetry.make(device_id, boot_id, sequence, features.motion_rms, features.rotation_rad)
            info = client.publish(topic(f"edge/{device_id}/telemetry"), telemetry.to_json(), qos=1)
            info.wait_for_publish(timeout=10)
            print(f"[{device_id.upper()}] #{sequence} motion={features.motion_rms:.3f} m/s² | rotation={features.rotation_rad:.3f} rad")
            sequence += 1
    except KeyboardInterrupt:
        print(f"[{device_id.upper()}] Stopped")
    finally:
        client.loop_stop()
        client.disconnect()
