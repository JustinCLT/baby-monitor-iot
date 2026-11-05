"""NODE 3: Machine Learning inference + Temporal State Smoothing (BabyGuardianMLDetector).

Loads 'baby_guardian_model.joblib' (scikit-learn RandomForestClassifier) and classifies the
6-feature multimodal telemetry from Edge 1 (Baby Node):
  [motion_rms, jerk_metric, tilt_angle, audio_rms, spectral_centroid_approx, zcr]

ML class -> published status
  0 SLEEPING   -> NORMAL
  1 RESTLESS   -> RESTLESS
  2 CRYING     -> ALERT  (only after the hysteresis filter confirms it)
  3 PRONE_RISK -> ALERT  (only after the hysteresis filter confirms it)

Temporal State Smoothing (hysteresis):
  A buffer keeps the last 3 evaluations. ALERT is raised only when at least
  `min_consecutive_alerts` (default 2) of the most recent evaluations in a row are
  danger classes AND their danger probability is >= `alert_prob_threshold`.
  A single noisy spike is reported as RESTLESS ("verifying") instead of ALERT.
"""

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import time

import joblib
import numpy as np

from shared.messages import Telemetry

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "baby_guardian_model.joblib"

SLEEPING, RESTLESS, CRYING, PRONE_RISK = 0, 1, 2, 3
DANGER_CLASSES = (CRYING, PRONE_RISK)
CLASS_LABELS = {SLEEPING: "SLEEPING", RESTLESS: "RESTLESS", CRYING: "CRYING", PRONE_RISK: "PRONE_RISK"}


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    score: float = 0.0


class BabyGuardianMLDetector:
    def __init__(
        self,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        window_size: int = 3,
        alert_prob_threshold: float = 0.60,
        min_consecutive_alerts: int = 2,
    ):
        if not 2 <= min_consecutive_alerts <= window_size:
            raise ValueError("min_consecutive_alerts must be between 2 and window_size")
        self.model_path = Path(model_path)
        self.alert_prob_threshold = alert_prob_threshold
        self.min_consecutive_alerts = min_consecutive_alerts
        self.armed = True
        self.latest: dict[str, Telemetry] = {}
        self.last_seq: dict[tuple[str, str], int] = {}
        self.last_evaluated: tuple[str, int] | None = None

        # Temporal buffer: (predicted_class, danger_probability) for the last N evaluations
        self.history: deque[tuple[int, float]] = deque(maxlen=window_size)
        self.model = self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"[ML-DETECTOR] Model '{self.model_path.name}' tidak ditemukan di {self.model_path.parent}.\n"
                "              Jalankan dulu:  python train_model.py"
            )
        model = joblib.load(self.model_path)
        n_features = getattr(model, "n_features_in_", 6)
        if n_features != 6:
            raise ValueError(f"Model expects {n_features} features, but telemetry provides 6. Re-run train_model.py")
        return model

    def set_armed(self, armed: bool):
        self.armed = armed
        self.history.clear()

    def _consecutive_danger(self) -> tuple[int, float]:
        """Count trailing consecutive danger evaluations and their mean danger probability."""
        count, total = 0, 0.0
        for predicted, danger_prob in reversed(self.history):
            if predicted not in DANGER_CLASSES:
                break
            count += 1
            total += danger_prob
        return count, (total / count if count else 0.0)

    def accept(self, data: Telemetry, now_ms: int | None = None) -> Decision:
        current_ms = now_ms if now_ms is not None else int(time.time() * 1000)

        # 1. Anti-stale timestamp (max 30 s clock difference)
        if abs(current_ms - data.sent_at_ms) > 30_000:
            return Decision("REJECTED_STALE", "Timestamp outside the allowed 30-second window")

        # 2. Anti-replay sequence per (device_id, boot_id)
        key = (data.device_id, data.boot_id)
        if data.sequence <= self.last_seq.get(key, -1):
            return Decision("REJECTED_REPLAY", "Repeated/out-of-order sequence for this boot ID")
        self.last_seq[key] = data.sequence
        self.latest[data.device_id] = data

        if not self.armed:
            return Decision("DISARMED", "Baby Guardian monitoring paused by parent")
        if "edge1" not in self.latest:
            return Decision("WAITING", "Waiting for Baby Node (edge1) telemetry")

        baby = self.latest["edge1"]
        evaluated_id = (baby.boot_id, baby.sequence)
        if self.last_evaluated == evaluated_id:
            return Decision("WAITING", "Parent Node (edge2) online; awaiting next Baby Node telemetry")
        self.last_evaluated = evaluated_id

        # 3. ML inference
        features = np.asarray([baby.feature_vector()], dtype=float)
        predicted = int(self.model.predict(features)[0])
        proba = self.model.predict_proba(features)[0]
        class_index = {int(c): i for i, c in enumerate(self.model.classes_)}
        prob_of = lambda cls: float(proba[class_index[cls]]) if cls in class_index else 0.0
        confidence = prob_of(predicted)
        danger_prob = prob_of(CRYING) + prob_of(PRONE_RISK)

        self.history.append((predicted, danger_prob))
        streak, mean_danger = self._consecutive_danger()
        label = CLASS_LABELS.get(predicted, "UNKNOWN")
        detail = (
            f"motion={baby.motion_rms:.2f} m/s², jerk={baby.jerk_metric:.1f}, tilt={baby.tilt_angle:.0f}°, "
            f"audio={baby.audio_rms:.2f}, centroid={baby.spectral_centroid_approx:.0f} Hz, zcr={baby.zcr:.2f}"
        )

        # 4. Temporal State Smoothing / hysteresis
        if predicted in DANGER_CLASSES:
            if streak >= self.min_consecutive_alerts and mean_danger >= self.alert_prob_threshold:
                recent = [cls for cls, _ in list(self.history)[-streak:]]
                if recent.count(PRONE_RISK) >= recent.count(CRYING):
                    reason = f"[ML: PRONE_RISK {confidence:.0%}, {streak}x berturut-turut] Risiko posisi tengkurap! ({detail})"
                else:
                    reason = f"[ML: CRYING {confidence:.0%}, {streak}x berturut-turut] Bayi menangis kencang! ({detail})"
                return Decision("ALERT", reason, round(mean_danger, 3))
            return Decision(
                "RESTLESS",
                f"[Temporal filter {streak}/{self.min_consecutive_alerts}] Memverifikasi indikasi {label} "
                f"({confidence:.0%}) sebelum alarm ({detail})",
                round(danger_prob * 0.6, 3),
            )

        if predicted == RESTLESS:
            return Decision(
                "RESTLESS",
                f"[ML: RESTLESS {confidence:.0%}] Bayi bergerak gelisah / perlu dicek ({detail})",
                round(0.3 + 0.3 * confidence, 3),
            )

        return Decision(
            "NORMAL",
            f"[ML: SLEEPING {confidence:.0%}] Bayi tidur aman & nyenyak ({detail})",
            round(danger_prob, 3),
        )
