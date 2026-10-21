"""NODE 3: detection algorithm (pure Python, no MQTT dependency).

Make changes here when experimenting with thresholds or a new AI model.
The algorithm intentionally returns an *indication*, not proof of theft.
"""

from dataclasses import dataclass
import time

from shared.messages import Telemetry


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    score: float = 0.0


class TheftDetector:
    def __init__(self, motion_threshold: float = 0.7, rotation_threshold: float = 0.25):
        self.motion_threshold = motion_threshold
        self.rotation_threshold = rotation_threshold
        self.armed = True
        self.latest: dict[str, Telemetry] = {}
        self.last_seq: dict[tuple[str, str], int] = {}
        self.last_evaluated: tuple[str, int] | None = None

    def set_armed(self, armed: bool):
        self.armed = armed

    def _moving(self, data: Telemetry) -> bool:
        return data.motion_rms >= self.motion_threshold or data.rotation_rad >= self.rotation_threshold

    def accept(self, data: Telemetry, now_ms: int | None = None) -> Decision:
        current_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        if abs(current_ms - data.sent_at_ms) > 30_000:
            return Decision("REJECTED_STALE", "Timestamp outside the allowed 30-second window")

        key = (data.device_id, data.boot_id)
        if data.sequence <= self.last_seq.get(key, -1):
            return Decision("REJECTED_REPLAY", "Repeated/out-of-order sequence for this boot ID")
        self.last_seq[key] = data.sequence
        self.latest[data.device_id] = data

        if not self.armed:
            return Decision("DISARMED", "Monitoring paused by the owner")
        if "edge1" not in self.latest or "edge2" not in self.latest:
            return Decision("WAITING", "Waiting for both edge devices")

        protected = self.latest["edge1"]
        guardian = self.latest["edge2"]
        if abs(protected.sent_at_ms - guardian.sent_at_ms) > 5_000:
            return Decision("REFERENCE_OLD", "Cannot compare measurements from different time windows")

        evaluated_id = (protected.boot_id, protected.sequence)
        if self.last_evaluated == evaluated_id:
            return Decision("WAITING", "Protected-device window already evaluated")
        self.last_evaluated = evaluated_id

        if self._moving(protected) and not self._moving(guardian):
            score = min(1.0, max(
                protected.motion_rms / (self.motion_threshold * 3),
                protected.rotation_rad / (self.rotation_threshold * 3),
            ))
            return Decision("ALERT", "Protected phone moves while reference phone remains still", round(score, 3))
        if self._moving(protected) and self._moving(guardian):
            return Decision("COMMON_MOTION", "Both devices are moving; investigate shared vibration")
        return Decision("NORMAL", "No isolated suspicious motion on protected phone")
