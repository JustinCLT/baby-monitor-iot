import json
import unittest

from nodes.detector_service.rules import BabyMonitorDetector
from shared.messages import Telemetry

NOW_MS = 1_790_000_000_000


def sample(device, seq, motion=0.0, rotation=0.0, audio_rms=0.02, sent_at_ms=NOW_MS):
    return Telemetry(device, "boot-1", seq, sent_at_ms, motion, rotation, audio_rms)


class BabyMonitorDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = BabyMonitorDetector()

    def test_sleeping_soundly_state(self):
        decision = self.detector.accept(sample("edge1", 0, motion=0.04, rotation=0.01, audio_rms=0.02), now_ms=NOW_MS)
        self.assertEqual(decision.status, "SLEEPING_SOUNDLY")

    def test_restless_baby_state(self):
        decision = self.detector.accept(sample("edge1", 0, motion=0.65, rotation=0.22, audio_rms=0.04), now_ms=NOW_MS)
        self.assertEqual(decision.status, "RESTLESS_BABY")

    def test_crying_awake_state(self):
        decision = self.detector.accept(sample("edge1", 0, motion=1.8, rotation=0.60, audio_rms=0.55), now_ms=NOW_MS)
        self.assertEqual(decision.status, "CRYING_AWAKE")
        self.assertGreaterEqual(decision.score, 0.80)

    def test_crowd_noise_state(self):
        decision = self.detector.accept(sample("edge1", 0, motion=0.03, rotation=0.01, audio_rms=0.28), now_ms=NOW_MS)
        self.assertEqual(decision.status, "CROWD_NOISE")

    def test_replay_rejected(self):
        reading = sample("edge1", 3)
        self.detector.accept(reading, now_ms=NOW_MS)
        decision = self.detector.accept(reading, now_ms=NOW_MS)
        self.assertEqual(decision.status, "REJECTED_REPLAY")

    def test_stale_timestamp_rejected(self):
        decision = self.detector.accept(sample("edge1", 0, sent_at_ms=NOW_MS - 31_000), now_ms=NOW_MS)
        self.assertEqual(decision.status, "REJECTED_STALE")

    def test_disarm(self):
        self.detector.set_armed(False)
        self.assertEqual(self.detector.accept(sample("edge1", 0, motion=3.0), now_ms=NOW_MS).status, "DISARMED")

    def test_wrong_data_type_rejected(self):
        body = json.dumps({
            "device_id": "edge1",
            "boot_id": "abc",
            "sequence": 2,
            "sent_at_ms": NOW_MS,
            "motion_rms": "infinite",
            "rotation_rad": 0.0,
            "audio_rms": 0.1,
        })
        with self.assertRaises(ValueError):
            Telemetry.from_json(body)


if __name__ == "__main__":
    unittest.main()
