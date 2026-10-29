"""NODE 3: Baby Monitor Decision Engine / State Classifier (pure Python).

Combines Motion (motion_rms, rotation_rad) and Audio (audio_rms) features from
Edge 1 (Baby Node) to classify 4 states:
  - SLEEPING_SOUNDLY : Audio quiet (low audio_rms), mattress calm (low motion_rms).
  - RESTLESS_BABY    : Audio quiet, but mattress vibration increases (baby turning/crawling without crying).
  - CRYING_AWAKE     : Loud crying audio above crying threshold OR combined loud audio + mattress vibration.
  - CROWD_NOISE      : Elevated audio momentarily without any mattress vibration (e.g. door closing outside).
"""

from dataclasses import dataclass
import time

from shared.messages import Telemetry


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    score: float = 0.0


class BabyMonitorDetector:
    def __init__(
        self,
        motion_threshold: float = 0.45,
        high_motion_threshold: float = 1.25,
        rotation_threshold: float = 0.20,
        high_rotation_threshold: float = 0.50,
        noise_audio_threshold: float = 0.15,
        cry_audio_threshold: float = 0.45,
    ):
        self.motion_threshold = motion_threshold
        self.high_motion_threshold = high_motion_threshold
        self.rotation_threshold = rotation_threshold
        self.high_rotation_threshold = high_rotation_threshold
        self.noise_audio_threshold = noise_audio_threshold
        self.cry_audio_threshold = cry_audio_threshold
        self.armed = True
        self.latest: dict[str, Telemetry] = {}
        self.last_seq: dict[tuple[str, str], int] = {}
        self.last_evaluated: tuple[str, int] | None = None

    def set_armed(self, armed: bool):
        self.armed = armed

    def _has_motion(self, data: Telemetry) -> bool:
        return (
            data.motion_rms >= self.motion_threshold
            or data.rotation_rad >= self.rotation_threshold
        )

    def _has_high_motion(self, data: Telemetry) -> bool:
        return (
            data.motion_rms >= self.high_motion_threshold
            or data.rotation_rad >= self.high_rotation_threshold
        )

    def _has_loud_audio(self, data: Telemetry) -> bool:
        return data.audio_rms >= self.noise_audio_threshold

    def _has_crying_audio(self, data: Telemetry) -> bool:
        return data.audio_rms >= self.cry_audio_threshold

    def _compute_risk_score(self, data: Telemetry) -> float:
        motion_ratio = data.motion_rms / (self.high_motion_threshold * 1.4)
        rotation_ratio = data.rotation_rad / (self.high_rotation_threshold * 1.4)
        audio_ratio = data.audio_rms / (self.cry_audio_threshold * 1.3)
        return round(min(1.0, max(motion_ratio, rotation_ratio, audio_ratio)), 3)

    def accept(self, data: Telemetry, now_ms: int | None = None) -> Decision:
        current_ms = now_ms if now_ms is not None else int(time.time() * 1000)

        # 1. Anti-stale timestamp validation (< 30 seconds)
        if abs(current_ms - data.sent_at_ms) > 30_000:
            return Decision("REJECTED_STALE", "Timestamp outside the allowed 30-second window")

        # 2. Anti-replay sequence validation per (device_id, boot_id)
        key = (data.device_id, data.boot_id)
        if data.sequence <= self.last_seq.get(key, -1):
            return Decision("REJECTED_REPLAY", "Repeated/out-of-order sequence for this boot ID")
        self.last_seq[key] = data.sequence
        self.latest[data.device_id] = data

        # 3. Armed check
        if not self.armed:
            return Decision("DISARMED", "Baby monitoring paused by parent")

        # 4. Require Baby Node (edge1) telemetry
        if "edge1" not in self.latest:
            return Decision("WAITING", "Waiting for Baby Node (edge1) telemetry")

        baby = self.latest["edge1"]
        evaluated_id = (baby.boot_id, baby.sequence)
        if data.device_id == "edge2" and self.last_evaluated == evaluated_id:
            return Decision("WAITING", "Parent Node (edge2) heartbeat updated; awaiting next Baby Node reading")
        self.last_evaluated = evaluated_id

        moving = self._has_motion(baby)
        high_moving = self._has_high_motion(baby)
        loud_audio = self._has_loud_audio(baby)
        crying_audio = self._has_crying_audio(baby)
        score = self._compute_risk_score(baby)

        # 5. Decision Engine / 4-State Classifier
        # State 1: CRYING_AWAKE — Loud crying above threshold OR combined loud audio + mattress motion (or intense thrashing)
        if crying_audio or (loud_audio and moving) or high_moving:
            return Decision(
                "CRYING_AWAKE",
                f"Bayi menangis/terbangun! (audio_rms={baby.audio_rms:.3f}, motion_rms={baby.motion_rms:.2f} m/s², rot={baby.rotation_rad:.2f} rad)",
                max(0.80, score),
            )

        # State 2: CROWD_NOISE — Elevated audio momentarily, but mattress is completely still
        if loud_audio and not moving:
            return Decision(
                "CROWD_NOISE",
                f"Suara bising di luar kasur tanpa pergerakan bayi (audio_rms={baby.audio_rms:.3f}, motion_rms={baby.motion_rms:.2f} m/s²)",
                max(0.35, score),
            )

        # State 3: RESTLESS_BABY — Audio quiet, but mattress vibration increases (baby turning/crawling)
        if moving and not loud_audio:
            return Decision(
                "RESTLESS_BABY",
                f"Bayi gelisah / bergerak tanpa menangis (motion_rms={baby.motion_rms:.2f} m/s², rot={baby.rotation_rad:.2f} rad, audio_rms={baby.audio_rms:.3f})",
                max(0.45, score),
            )

        # State 4: SLEEPING_SOUNDLY — Both audio and mattress are calm
        return Decision(
            "SLEEPING_SOUNDLY",
            f"Bayi tidur lelap & kamar hening (motion_rms={baby.motion_rms:.2f} m/s², audio_rms={baby.audio_rms:.3f})",
            score,
        )


# Backward-compatible alias
TheftDetector = BabyMonitorDetector
