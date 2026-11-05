import json
import unittest
from unittest import mock

from nodes.detector_service.rules import (
    CRYING, PRONE_RISK, RESTLESS, SLEEPING, BabyGuardianMLDetector, DEFAULT_MODEL_PATH,
)
from shared.messages import Telemetry
from shared.processing import extract_features
from shared.sensors import Simulator
from train_model import train_and_save_model

NOW_MS = 1_790_000_000_000

PROFILES = {
    "sleeping": dict(motion_rms=0.06, jerk_metric=0.45, tilt_angle=8.0, audio_rms=0.025,
                     spectral_centroid_approx=380.0, zcr=0.08),
    "restless": dict(motion_rms=0.82, jerk_metric=6.5, tilt_angle=30.0, audio_rms=0.08,
                     spectral_centroid_approx=720.0, zcr=0.15),
    "crying": dict(motion_rms=1.6, jerk_metric=13.0, tilt_angle=20.0, audio_rms=0.62,
                   spectral_centroid_approx=3300.0, zcr=0.80),
    "prone_risk": dict(motion_rms=0.10, jerk_metric=0.8, tilt_angle=152.0, audio_rms=0.04,
                       spectral_centroid_approx=440.0, zcr=0.08),
}


def reading(seq, profile="sleeping", device="edge1", sent_at_ms=NOW_MS):
    return Telemetry(device, "boot-1", seq, sent_at_ms, **PROFILES[profile])


class BabyGuardianMLDetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DEFAULT_MODEL_PATH.exists():
            train_and_save_model(DEFAULT_MODEL_PATH)

    def setUp(self):
        self.detector = BabyGuardianMLDetector()

    def test_sleeping_is_normal(self):
        self.assertEqual(self.detector.accept(reading(0, "sleeping"), now_ms=NOW_MS).status, "NORMAL")

    def test_restless(self):
        self.assertEqual(self.detector.accept(reading(0, "restless"), now_ms=NOW_MS).status, "RESTLESS")

    def test_crying_needs_two_consecutive_windows(self):
        first = self.detector.accept(reading(0, "crying"), now_ms=NOW_MS)
        self.assertEqual(first.status, "RESTLESS")  # held by temporal filter
        second = self.detector.accept(reading(1, "crying"), now_ms=NOW_MS)
        self.assertEqual(second.status, "ALERT")
        self.assertIn("CRYING", second.reason)

    def test_prone_risk_needs_two_consecutive_windows(self):
        self.assertEqual(self.detector.accept(reading(0, "prone_risk"), now_ms=NOW_MS).status, "RESTLESS")
        second = self.detector.accept(reading(1, "prone_risk"), now_ms=NOW_MS)
        self.assertEqual(second.status, "ALERT")
        self.assertIn("PRONE_RISK", second.reason)

    def test_single_spike_does_not_alert(self):
        self.detector.accept(reading(0, "crying"), now_ms=NOW_MS)
        self.assertEqual(self.detector.accept(reading(1, "sleeping"), now_ms=NOW_MS).status, "NORMAL")
        # streak was broken, so another single spike still must not alert
        self.assertEqual(self.detector.accept(reading(2, "crying"), now_ms=NOW_MS).status, "RESTLESS")

    def test_parent_heartbeat_does_not_reevaluate(self):
        self.detector.accept(reading(0, "sleeping"), now_ms=NOW_MS)
        self.assertEqual(self.detector.accept(reading(0, "sleeping", device="edge2"), now_ms=NOW_MS).status,
                         "WAITING")

    def test_replay_rejected(self):
        self.detector.accept(reading(3), now_ms=NOW_MS)
        self.assertEqual(self.detector.accept(reading(3), now_ms=NOW_MS).status, "REJECTED_REPLAY")

    def test_stale_timestamp_rejected(self):
        decision = self.detector.accept(reading(0, sent_at_ms=NOW_MS - 31_000), now_ms=NOW_MS)
        self.assertEqual(decision.status, "REJECTED_STALE")

    def test_disarm(self):
        self.detector.set_armed(False)
        self.assertEqual(self.detector.accept(reading(0, "crying"), now_ms=NOW_MS).status, "DISARMED")


class SimulatorToModelTests(unittest.TestCase):
    """End-to-end: simulator samples -> extract_features -> model must agree with the scenario."""

    EXPECTED = {"sleeping": SLEEPING, "restless": RESTLESS, "crying": CRYING, "prone_risk": PRONE_RISK}

    @classmethod
    def setUpClass(cls):
        if not DEFAULT_MODEL_PATH.exists():
            train_and_save_model(DEFAULT_MODEL_PATH)
        cls.model = BabyGuardianMLDetector().model

    def test_each_scenario_is_classified_correctly(self):
        for scenario, expected in self.EXPECTED.items():
            with self.subTest(scenario=scenario):
                clock = iter(i * 0.125 for i in range(10_000))  # 0.25 s per read() (2 calls each)
                with mock.patch("shared.sensors.time.monotonic", side_effect=lambda: next(clock)):
                    sim = Simulator(scenario, seed=7)
                    windows = [[sim.read() for _ in range(6)] for _ in range(10)]
                vectors = [Telemetry("edge1", "b", 0, 0, **extract_features(w).__dict__).feature_vector()
                           for w in windows]
                predictions = list(self.model.predict(vectors))
                self.assertGreaterEqual(predictions.count(expected), 8, f"{scenario}: {predictions}")


class TelemetryTests(unittest.TestCase):
    def test_roundtrip(self):
        original = reading(5, "crying")
        self.assertEqual(Telemetry.from_json(original.to_json()), original)

    def test_backward_compatible_payload(self):
        old = json.dumps({"device_id": "edge1", "boot_id": "x", "sequence": 1,
                          "sent_at_ms": NOW_MS, "motion_rms": 0.2, "rotation_rad": 0.1})
        parsed = Telemetry.from_json(old)
        self.assertEqual(parsed.motion_rms, 0.2)
        self.assertEqual(parsed.zcr, 0.0)

    def test_wrong_data_type_rejected(self):
        body = reading(2).to_dict()
        body["motion_rms"] = "infinite"
        with self.assertRaises(ValueError):
            Telemetry.from_json(json.dumps(body))


if __name__ == "__main__":
    unittest.main()
