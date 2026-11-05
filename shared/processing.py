"""MULTIMODAL SIGNAL PROCESSING AT THE EDGE (used by Python edges; mirrored in web-edge/index.html).

Processing A (IMU — accelerometer):
  - motion_rms  : RMS of acceleration-magnitude deviation from gravity (9.81 m/s²).
  - jerk_metric : mean |Δa| / Δt between consecutive samples (m/s³).
  - tilt_angle  : mean inclination vs. the vertical +Z axis in degrees (0° = on back, ~180° = face-down).

Processing B (Audio dynamics):
  - audio_rms                : RMS of audio levels in the window.
  - zcr                      : zero-crossing-rate approximation of the audio envelope,
                               weighted by signal energy so quiet noise stays low.
  - spectral_centroid_approx : spectral-centroid estimate (Hz) from amplitude, variance and dynamics.
"""

from dataclasses import dataclass
from math import atan2, degrees, hypot, sqrt

GRAVITY = 9.81


@dataclass(frozen=True)
class SensorSample:
    seconds: float
    acceleration: tuple[float, float, float]
    gyroscope: tuple[float, float, float]
    audio_level: float = 0.0


@dataclass(frozen=True)
class Features:
    motion_rms: float
    jerk_metric: float
    tilt_angle: float
    audio_rms: float
    spectral_centroid_approx: float
    zcr: float


def extract_features(samples: list[SensorSample]) -> Features:
    if len(samples) < 2:
        raise ValueError("At least 2 sensor samples are required")
    n = len(samples)

    # ---------- Processing A: IMU ----------
    deviations = []
    tilts = []
    for sample in samples:
        ax, ay, az = sample.acceleration
        deviations.append(sqrt(ax * ax + ay * ay + az * az) - GRAVITY)
        tilts.append(max(0.0, min(180.0, degrees(atan2(hypot(ax, ay), az)))))

    motion_rms = sqrt(sum(d * d for d in deviations) / n)
    tilt_angle = sum(tilts) / n

    jerks = []
    for previous, current in zip(samples, samples[1:]):
        dt = max(1e-3, current.seconds - previous.seconds)
        delta = [c - p for c, p in zip(current.acceleration, previous.acceleration)]
        jerks.append(sqrt(sum(d * d for d in delta)) / dt)
    jerk_metric = sum(jerks) / len(jerks)

    # ---------- Processing B: Audio ----------
    levels = [max(0.0, float(sample.audio_level)) for sample in samples]
    audio_rms = sqrt(sum(level * level for level in levels) / n)
    mean_level = sum(levels) / n
    centered = [level - mean_level for level in levels]
    std_dev = sqrt(sum(c * c for c in centered) / n)
    mean_diff = sum(abs(b - a) for a, b in zip(levels, levels[1:])) / (n - 1)

    crossings = sum(
        1 for a, b in zip(centered, centered[1:]) if (a >= 0.0) != (b >= 0.0)
    )
    raw_zcr = crossings / (n - 1)

    # Envelope crossings only count when there is real acoustic energy
    zcr = min(1.0, max(0.01, 0.4 * raw_zcr * min(1.0, audio_rms * 1.5) + 0.75 * audio_rms + 0.4 * std_dev))

    spectral_centroid_approx = min(
        4400.0,
        max(150.0, 240.0 + 3800.0 * audio_rms + 1500.0 * std_dev + 900.0 * mean_diff + 600.0 * zcr),
    )

    return Features(
        motion_rms=round(motion_rms, 4),
        jerk_metric=round(jerk_metric, 4),
        tilt_angle=round(tilt_angle, 2),
        audio_rms=round(audio_rms, 4),
        spectral_centroid_approx=round(spectral_centroid_approx, 2),
        zcr=round(zcr, 4),
    )
