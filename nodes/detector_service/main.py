"""NODE 3: detector service subscribes to MQTT, applies rules, publishes alerts.

Topics (see docs/SETUP.md):
  subscribe  edge/+/telemetry   telemetry from both edges
  subscribe  control            ARM / DISARM from the owner or dashboard
  publish    alerts             only when status == ALERT (Edge 2 rings)
  publish    status (retained)  every decision, for the dashboard

This service CAN run on a laptop connected to a cloud broker.
For a fully cloud-deployed architecture, run the same service on a cloud VM.
"""

import json
import time

from nodes.detector_service.rules import TheftDetector
from shared.messages import Telemetry, status_json
from shared.mqtt_connection import create_client, topic


def main():
    detector = TheftDetector()
    status_topic = topic("status")
    offline = status_json("OFFLINE", "Detector disconnected", armed=False)
    client = create_client("detector", will=(status_topic, offline))
    telemetry_topic = topic("edge/+/telemetry")
    control_topic = topic("control")

    def publish_status(status: str, reason: str, score: float = 0.0, reading: Telemetry | None = None):
        payload = status_json(
            status, reason, detector.armed, score,
            device_id=reading.device_id if reading else None,
            sequence=reading.sequence if reading else None,
        )
        client.publish(status_topic, payload, qos=1, retain=True)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[DETECTOR] MQTT connection rejected: {reason_code}")
            return
        client.subscribe([(telemetry_topic, 1), (control_topic, 1)])
        print(f"[DETECTOR] Subscribed: {telemetry_topic} and {control_topic}")
        publish_status("ONLINE", "Detector started", 0.0)

    def handle_control(payload: bytes):
        command = payload.decode(errors="replace").strip().upper()
        if command not in ("ARM", "DISARM"):
            print(f"[DETECTOR] Ignored unknown control: {command[:40]}")
            return
        detector.set_armed(command == "ARM")
        print(f"[DETECTOR] Owner command: {command}")
        publish_status("ARMED" if detector.armed else "DISARMED", f"Owner sent {command}")

    def on_message(client, userdata, message):
        if message.topic == control_topic:
            handle_control(message.payload)
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
        # Edge 2 messages only refresh the reference; don't overwrite the
        # dashboard status with "WAITING" once both edges are online.
        if not (decision.status == "WAITING" and len(detector.latest) == 2):
            publish_status(decision.status, decision.reason, decision.score, reading)
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
        client.loop_start()
        try:
            info = client.publish(status_topic, status_json("OFFLINE", "Detector stopped", armed=False),
                                  qos=1, retain=True)
            info.wait_for_publish(timeout=3)
        except (RuntimeError, ValueError):
            pass
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
