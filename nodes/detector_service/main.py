"""NODE 3: detector service subscribes to MQTT, applies rules, publishes alerts.

This service CAN run on a laptop connected to a cloud broker.
For a fully cloud-deployed architecture, run the same service on a cloud VM.
"""

import json
import time

from nodes.detector_service.rules import TheftDetector
from shared.messages import Telemetry
from shared.mqtt_connection import create_client, topic


def main():
    detector = TheftDetector()
    client = create_client("detector")
    telemetry_topic = topic("edge/+/telemetry")
    control_topic = topic("control")

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[DETECTOR] MQTT connection rejected: {reason_code}")
            return
        client.subscribe([(telemetry_topic, 1), (control_topic, 1)])
        print(f"[DETECTOR] Subscribed: {telemetry_topic} and {control_topic}")

    def on_message(client, userdata, message):
        if message.topic == control_topic:
            command = message.payload.decode(errors="replace").strip().upper()
            if command in ("ARM", "DISARM"):
                detector.set_armed(command == "ARM")
                print(f"[DETECTOR] Owner command: {command}")
            else:
                print(f"[DETECTOR] Ignored unknown control: {command}")
            return

        try:
            reading = Telemetry.from_json(message.payload)
            expected_topic = topic(f"edge/{reading.device_id}/telemetry")
            if message.topic != expected_topic:
                print("[DETECTOR] REJECTED: topic and device ID disagree")
                return
            decision = detector.accept(reading)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            print(f"[DETECTOR] REJECTED malformed payload: {exc}")
            return

        print(f"[DETECTOR] {reading.device_id} #{reading.sequence}: {decision.status} — {decision.reason}")
        if decision.status == "ALERT":
            alert = {
                "event": "suspicious_movement",
                "device_id": "edge1",
                "risk_score": decision.score,
                "reason": decision.reason,
                "detected_at_ms": int(time.time() * 1000),
            }
            client.publish(topic("alerts"), json.dumps(alert), qos=1, retain=False)

    client.on_connect = on_connect
    client.on_message = on_message
    print("[DETECTOR] Starting. Ctrl+C to stop")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[DETECTOR] Stopped")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
