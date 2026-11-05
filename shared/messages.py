"""MQTT message schema: 6-feature multimodal telemetry contract between Edge nodes and the ML detector."""

from dataclasses import asdict, dataclass
import json
import math
import time

FEATURE_FIELDS = (
    "motion_rms",
    "jerk_metric",
    "tilt_angle",
    "audio_rms",
    "spectral_centroid_approx",
    "zcr",
)


@dataclass(frozen=True)
class Telemetry:
    device_id: str
    boot_id: str
    sequence: int
    sent_at_ms: int
    motion_rms: float
    jerk_metric: float = 0.0
    tilt_angle: float = 0.0
    audio_rms: float = 0.0
    spectral_centroid_approx: float = 0.0
    zcr: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def feature_vector(self) -> list[float]:
        """Feature order MUST match train_model.FEATURE_NAMES."""
        return [float(getattr(self, name)) for name in FEATURE_FIELDS]

    @staticmethod
    def _non_negative_float(value: dict, key: str, required: bool) -> float:
        if key not in value:
            if required:
                raise ValueError(f"Missing {key}")
            return 0.0  # backward compatibility with older payloads
        number = value[key]
        # bool is a subclass of int; reject it explicitly
        if isinstance(number, bool) or type(number) not in (float, int):
            raise ValueError(f"Invalid {key}")
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"Invalid {key}")
        return float(number)

    @staticmethod
    def from_json(payload: str | bytes) -> "Telemetry":
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError("Telemetry must be a JSON object")
        for key in ("device_id", "boot_id"):
            if not isinstance(value.get(key), str) or not value[key]:
                raise ValueError(f"Invalid {key}")
        if value["device_id"] not in ("edge1", "edge2"):
            raise ValueError("Unknown edge device")

        sequence = value.get("sequence")
        timestamp = value.get("sent_at_ms")
        if type(sequence) is not int or sequence < 0:
            raise ValueError("Invalid sequence")
        if type(timestamp) is not int or timestamp < 0:
            raise ValueError("Invalid timestamp")

        features = {
            name: Telemetry._non_negative_float(value, name, required=(name == "motion_rms"))
            for name in FEATURE_FIELDS
        }
        return Telemetry(
            device_id=value["device_id"],
            boot_id=value["boot_id"],
            sequence=sequence,
            sent_at_ms=timestamp,
            **features,
        )

    @staticmethod
    def make(
        device_id: str,
        boot_id: str,
        sequence: int,
        motion_rms: float,
        jerk_metric: float = 0.0,
        tilt_angle: float = 0.0,
        audio_rms: float = 0.0,
        spectral_centroid_approx: float = 0.0,
        zcr: float = 0.0,
    ) -> "Telemetry":
        return Telemetry(
            device_id=device_id,
            boot_id=boot_id,
            sequence=sequence,
            sent_at_ms=int(time.time() * 1000),
            motion_rms=motion_rms,
            jerk_metric=jerk_metric,
            tilt_angle=tilt_angle,
            audio_rms=audio_rms,
            spectral_centroid_approx=spectral_centroid_approx,
            zcr=zcr,
        )


def status_json(
    status: str,
    reason: str,
    armed: bool,
    score: float = 0.0,
    device_id: str | None = None,
    sequence: int | None = None,
    now_ms: int | None = None,
) -> str:
    """Latest detector decision, published (retained) for the dashboard and Parent Node."""
    return json.dumps({
        "status": status,
        "reason": reason,
        "armed": armed,
        "risk_score": score,
        "device_id": device_id,
        "sequence": sequence,
        "at_ms": now_ms if now_ms is not None else int(time.time() * 1000),
    })
