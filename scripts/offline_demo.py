"""No devices, broker, or accounts needed. Study the algorithm first!

IMPORTANT: Offline mode demonstrates the data processing and algorithm,
not the coursework's required cloud MQTT communication.
"""

from nodes.detector_service.rules import TheftDetector
from shared.messages import Telemetry
from shared.processing import SensorSample, extract_features

BASE_TIME_MS = 1_790_000_000_000


def make_telemetry(device: str, number: int, moving: bool) -> Telemetry:
    samples = []
    for i in range(5):
        samples.append(SensorSample(
            seconds=i * 0.25,
            acceleration=(1.8, 0, 12.0) if moving else (0, 0, 9.81),
            gyroscope=(0.65, 0.0, 0.0) if moving else (0.0, 0.0, 0.0),
        ))
    features = extract_features(samples)
    return Telemetry(device, "offline-demo", number, BASE_TIME_MS + number * 1_000,
                     features.motion_rms, features.rotation_rad)


def main():
    detector = TheftDetector()
    scenarios = [
        ("NORMAL: both devices still", False, False),
        ("ALERT: protected device picked up", True, False),
        ("COMMON MOTION: both phones shake", True, True),
        ("NORMAL: both devices still", False, False),
    ]
    for index, (title, edge1_moving, edge2_moving) in enumerate(scenarios):
        now_ms = BASE_TIME_MS + index * 1_000
        edge2 = make_telemetry("edge2", index, edge2_moving)
        edge1 = make_telemetry("edge1", index, edge1_moving)
        detector.accept(edge2, now_ms=now_ms)
        result = detector.accept(edge1, now_ms=now_ms)
        print(f"{index + 1}. {title}\n   -> {result.status}: {result.reason}\n")

    print("Offline demo done. Next: set up EMQX Cloud to fulfill the MQTT requirement.")


if __name__ == "__main__":
    main()
