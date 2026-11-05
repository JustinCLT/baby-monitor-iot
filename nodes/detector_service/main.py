"""NODE 3: Smart Multimodal Baby Guardian — ML detector service (MQTT).

Topics (prefix pocketguard/<PROJECT_ID>/):
  subscribe  edge/+/telemetry   6-feature telemetry from Baby Node (edge1) & Parent Node (edge2)
  subscribe  control            ARM / DISARM from parent or dashboard
  publish    alerts             only when status == ALERT  -> Parent Node vibrates + alarm
  publish    status (retained)  every decision (NORMAL / RESTLESS / ALERT / ...) for dashboard & parent
"""

import json
import time

from nodes.detector_service.rules import BabyGuardianMLDetector
from shared.messages import Telemetry, status_json
from shared.mqtt_connection import create_client, topic

ALERT_COOLDOWN_SECONDS = 5.0  # avoid flooding the parent phone while ALERT persists


def main():
    try:
        detector = BabyGuardianMLDetector()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    status_topic = topic("status")
    alerts_topic = topic("alerts")
    telemetry_topic = topic("edge/+/telemetry")
    control_topic = topic("control")
    offline = status_json("OFFLINE", "Baby Guardian ML detector disconnected", armed=False)
    client = create_client("detector", will=(status_topic, offline))
    last_alert_at = 0.0

    def publish_status(status: str, reason: str, score: float = 0.0, reading: Telemetry | None = None):
        payload = status_json(
            status, reason, detector.armed, score,
            device_id=reading.device_id if reading else None,
            sequence=reading.sequence if reading else None,
        )
        client.publish(status_topic, payload, qos=1, retain=True)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[ML-DETECTOR] MQTT connection rejected: {reason_code}", flush=True)
            return
        client.subscribe([(telemetry_topic, 1), (control_topic, 1)])
        print(f"[ML-DETECTOR] Subscribed: {telemetry_topic} & {control_topic}", flush=True)
        publish_status("ONLINE", "Baby Guardian ML detector started (Random Forest + temporal smoothing)")

    def handle_control(payload: bytes):
        command = payload.decode(errors="replace").strip().upper()
        if command not in ("ARM", "DISARM"):
            print(f"[ML-DETECTOR] Ignored unknown control: {command[:40]}", flush=True)
            return
        detector.set_armed(command == "ARM")
        print(f"[ML-DETECTOR] Parent command: {command}", flush=True)
        publish_status("ARMED" if detector.armed else "DISARMED", f"Parent sent {command}")

    def on_message(client, userdata, message):
        nonlocal last_alert_at
        if message.topic == control_topic:
            handle_control(message.payload)
            return

        try:
            reading = Telemetry.from_json(message.payload)
            if message.topic != topic(f"edge/{reading.device_id}/telemetry"):
                print("[ML-DETECTOR] REJECTED: topic and device ID disagree", flush=True)
                return
            decision = detector.accept(reading)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            print(f"[ML-DETECTOR] REJECTED malformed payload: {exc}", flush=True)
            return

        print(
            f"[ML-DETECTOR] {reading.device_id} #{reading.sequence} -> {decision.status} "
            f"(score={decision.score:.2f}) — {decision.reason}",
            flush=True,
        )

        # Parent-node heartbeats should not overwrite the baby status with WAITING
        if not (decision.status == "WAITING" and "edge1" in detector.latest):
            publish_status(decision.status, decision.reason, decision.score, reading)

        now = time.monotonic()
        if decision.status == "ALERT" and now - last_alert_at >= ALERT_COOLDOWN_SECONDS:
            last_alert_at = now
            baby = detector.latest["edge1"]
            alert = {
                "event": "baby_safety_alert",
                "status": "ALERT",
                "device_id": "edge1",
                "risk_score": decision.score,
                "reason": decision.reason,
                **{k: v for k, v in baby.to_dict().items() if k not in ("device_id", "boot_id", "sequence", "sent_at_ms")},
                "detected_at_ms": int(time.time() * 1000),
            }
            client.publish(alerts_topic, json.dumps(alert), qos=1, retain=False)
            print(f"[ML-DETECTOR] ALERT published to {alerts_topic}", flush=True)

    client.on_connect = on_connect
    client.on_message = on_message
    print("[ML-DETECTOR] Starting Smart Multimodal Baby Guardian. Ctrl+C to stop", flush=True)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[ML-DETECTOR] Stopped", flush=True)
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
