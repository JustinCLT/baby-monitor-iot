"""NODE 3: Central Baby Monitor Detector Service.

Topics:
  subscribe  edge/+/telemetry   telemetry from Baby Node (edge1) & Parent Node (edge2)
  subscribe  control            ARM / DISARM from parent or dashboard
  publish    alerts             published when status == CRYING_AWAKE (Parent Node Edge 2 vibrates)
  publish    status (retained)  every decision (SLEEPING_SOUNDLY, RESTLESS_BABY, CRYING_AWAKE, CROWD_NOISE)
"""

import json
import time

from nodes.detector_service.rules import BabyMonitorDetector
from shared.messages import Telemetry, status_json
from shared.mqtt_connection import create_client, topic


def main():
    detector = BabyMonitorDetector()
    status_topic = topic("status")
    offline = status_json("OFFLINE", "Baby Monitor Detector disconnected", armed=False)
    client = create_client("detector", will=(status_topic, offline))
    telemetry_topic = topic("edge/+/telemetry")
    control_topic = topic("control")

    def publish_status(status: str, reason: str, score: float = 0.0, reading: Telemetry | None = None):
        payload = status_json(
            status,
            reason,
            detector.armed,
            score,
            device_id=reading.device_id if reading else None,
            sequence=reading.sequence if reading else None,
            audio_rms=reading.audio_rms if reading else None,
        )
        client.publish(status_topic, payload, qos=1, retain=True)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[BABY-DETECTOR] MQTT connection rejected: {reason_code}", flush=True)
            return
        client.subscribe([(telemetry_topic, 1), (control_topic, 1)])
        print(f"[BABY-DETECTOR] Subscribed: {telemetry_topic} and {control_topic}", flush=True)
        publish_status("ONLINE", "Smart Baby Monitor Detector started", 0.0)

    def handle_control(payload: bytes):
        command = payload.decode(errors="replace").strip().upper()
        if command not in ("ARM", "DISARM"):
            print(f"[BABY-DETECTOR] Ignored unknown control: {command[:40]}", flush=True)
            return
        detector.set_armed(command == "ARM")
        print(f"[BABY-DETECTOR] Parent command: {command}", flush=True)
        publish_status("ARMED" if detector.armed else "DISARMED", f"Parent sent {command}")

    def on_message(client, userdata, message):
        if message.topic == control_topic:
            handle_control(message.payload)
            return

        try:
            reading = Telemetry.from_json(message.payload)
            expected_topic = topic(f"edge/{reading.device_id}/telemetry")
            if message.topic != expected_topic:
                print("[BABY-DETECTOR] REJECTED: topic and device ID disagree", flush=True)
                return
            decision = detector.accept(reading)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            print(f"[BABY-DETECTOR] REJECTED malformed payload: {exc}", flush=True)
            return

        print(
            f"[BABY-DETECTOR] {reading.device_id} #{reading.sequence} "
            f"(motion={reading.motion_rms:.2f}, rot={reading.rotation_rad:.2f}, audio={reading.audio_rms:.3f}): "
            f"{decision.status} — {decision.reason}",
            flush=True,
        )

        # Parent Node (edge2) messages only refresh parent heartbeat; don't overwrite
        # active Baby Node status with "WAITING" once edge1 is already reporting.
        if not (decision.status == "WAITING" and "edge1" in detector.latest):
            publish_status(decision.status, decision.reason, decision.score, reading)

        if decision.status == "CRYING_AWAKE":
            baby_reading = detector.latest.get("edge1", reading)
            alert = {
                "event": "baby_crying_or_awake",
                "status": "CRYING_AWAKE",
                "device_id": "edge1",
                "risk_score": decision.score,
                "motion_rms": baby_reading.motion_rms,
                "rotation_rad": baby_reading.rotation_rad,
                "audio_rms": baby_reading.audio_rms,
                "reason": decision.reason,
                "detected_at_ms": int(time.time() * 1000),
            }
            client.publish(topic("alerts"), json.dumps(alert), qos=1, retain=False)

    client.on_connect = on_connect
    client.on_message = on_message
    print("[BABY-DETECTOR] Starting Smart Dual-Zone Baby Monitor. Ctrl+C to stop", flush=True)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[BABY-DETECTOR] Stopped", flush=True)
    finally:
        client.loop_start()
        try:
            info = client.publish(
                status_topic,
                status_json("OFFLINE", "Detector stopped", armed=False),
                qos=1,
                retain=True,
            )
            info.wait_for_publish(timeout=3)
        except (RuntimeError, ValueError):
            pass
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
