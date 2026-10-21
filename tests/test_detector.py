import json
import unittest

from shared.messages import Telemetry
from nodes.detector_service.rules import TheftDetector

NOW_MS = 1_790_000_000_000


def sample(device, seq, motion=0.0, rotation=0.0, sent_at_ms=NOW_MS):
    return Telemetry(device, "boot-1", seq, sent_at_ms, motion, rotation)


class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = TheftDetector()

    def test_protected_moves_guardian_still(self):
        self.detector.accept(sample("edge2", 0), now_ms=NOW_MS)
        decision = self.detector.accept(sample("edge1", 0, motion=1.9), now_ms=NOW_MS)
        self.assertEqual(decision.status, "ALERT")

    def test_both_move_is_not_theft_alert(self):
        self.detector.accept(sample("edge2", 0, motion=1.5), now_ms=NOW_MS)
        decision = self.detector.accept(sample("edge1", 0, motion=1.9), now_ms=NOW_MS)
        self.assertEqual(decision.status, "COMMON_MOTION")

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
        self.assertEqual(self.detector.accept(sample("edge1", 0, motion=3), now_ms=NOW_MS).status, "DISARMED")

    def test_wrong_data_type_rejected(self):
        body = json.dumps({"device_id": "edge1", "boot_id": "abc", "sequence": 2, "sent_at_ms": NOW_MS, "motion_rms": "infinite", "rotation_rad": 0.0})
        with self.assertRaises(ValueError):
            Telemetry.from_json(body)


if __name__ == "__main__":
    unittest.main()
