"""DATA PROCESSING (used by BOTH edge devices).

Processing A (Motion): Root Mean Square (RMS) of linear acceleration deviation from gravity
                       and integrated angular rotation (rad) from gyroscope.
Processing B (Audio):  Audio RMS / Short-Time Energy across the sampling window to measure
                       ambient noise and baby crying amplitude.
"""

from dataclasses import dataclass
from math import sqrt

GRAVITY = 9.81


@dataclass(frozen=True)
class SensorSample:
    seconds: float
    acceleration: tuple[float, float, float]
    gyroscope: tuple[float, float, float]
    audio_rms: float = 0.0


@dataclass(frozen=True)
class Features:
    motion_rms: float
    rotation_rad: float
    audio_rms: float = 0.0


def extract_features(samples: list[SensorSample]) -> Features:
    if len(samples) < 2:
        raise ValueError("At least 2 sensor samples are required")

    # Processing A1: Root Mean Square (RMS) of linear acceleration deviation from gravity
    acceleration_errors = []
    for sample in samples:
        x, y, z = sample.acceleration
        acceleration_magnitude = sqrt(x * x + y * y + z * z)
        acceleration_errors.append(acceleration_magnitude - GRAVITY)

    motion_rms = sqrt(sum(value ** 2 for value in acceleration_errors) / len(samples))

    # Processing A2: Integrated angular movement from gyroscope readings
    rotation_rad = 0.0
    for previous, current in zip(samples, samples[1:]):
        delta_seconds = max(0.0, current.seconds - previous.seconds)
        gx, gy, gz = current.gyroscope
        angular_speed = sqrt(gx * gx + gy * gy + gz * gz)
        rotation_rad += angular_speed * delta_seconds

    # Processing B: Audio RMS / Short-Time Energy over the time window
    audio_energy = sum(max(0.0, sample.audio_rms) ** 2 for sample in samples) / len(samples)
    window_audio_rms = sqrt(audio_energy)

    return Features(
        motion_rms=round(motion_rms, 4),
        rotation_rad=round(rotation_rad, 4),
        audio_rms=round(window_audio_rms, 4),
    )
