"""Multimodal sensor sources for Edge devices.

'--source simulator' : synthetic IMU + audio for 4 scenarios (runs anywhere).
'--source android'   : real accelerometer + gyroscope via Termux:API, with an audio-level
                       reading from termux-microphone-record when available, else a quiet fallback.

Simulator scenarios:
  - "sleeping"   : low motion, flat on back (~5° tilt), quiet audio
  - "restless"   : moderate rolling motion & jerk, ~25° tilt, quiet / sighing audio
  - "crying"     : loud high-frequency crying audio, moderate-to-high motion
  - "prone_risk" : face-down (~160° tilt), minimal movement, quiet audio
"""

import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import time
import wave
from typing import Protocol

from shared.processing import SensorSample


class SensorSource(Protocol):
    def read(self) -> SensorSample: ...


class Simulator:
    SCENARIO_ALIASES = {
        "still": "sleeping",
        "table_shake": "restless",
        "pickup": "crying",
        "crying_awake": "crying",
        "prone": "prone_risk",
    }
    SCENARIOS = ("sleeping", "restless", "crying", "prone_risk")

    def __init__(self, scenario: str = "sleeping", seed: int = 42):
        normalized = self.SCENARIO_ALIASES.get(scenario, scenario)
        if normalized not in self.SCENARIOS:
            raise ValueError(f"Unknown simulator scenario: {scenario}")
        self.scenario = normalized
        self.started = time.monotonic()
        self.step = 0
        self.random = random.Random(seed)

    def read(self) -> SensorSample:
        self.step += 1
        t = time.monotonic() - self.started
        noise = lambda scale: self.random.gauss(0.0, scale)
        alt = 1.0 if self.step % 2 == 0 else -1.0  # audio envelope oscillation

        if self.scenario == "crying":
            acceleration = (
                1.8 * math.sin(6.5 * t) + noise(0.12),
                1.4 * math.cos(5.5 * t) + noise(0.12),
                9.2 + 1.9 * math.cos(5.0 * t) + noise(0.12),
            )
            gyroscope = (0.75 + noise(0.05), 0.42 + noise(0.04), 0.30 + noise(0.04))
            audio = 0.64 + 0.14 * alt + noise(0.03)
            audio = max(0.35, min(1.0, audio))
        elif self.scenario == "restless":
            acceleration = (
                3.2 * math.sin(3.2 * t) + noise(0.08),
                2.5 * math.cos(2.8 * t) + noise(0.08),
                8.8 + 0.95 * math.cos(3.5 * t) + noise(0.08),
            )
            gyroscope = (0.35 + noise(0.03), 0.22 + noise(0.03), 0.15 + noise(0.02))
            audio = max(0.02, min(0.18, 0.08 + 0.025 * alt + noise(0.01)))
        elif self.scenario == "prone_risk":
            # Screen facing the mattress: gravity on -Z  ->  tilt ≈ 160°
            acceleration = (2.8 + noise(0.05), 1.5 + noise(0.05), -9.25 + noise(0.05))
            gyroscope = (noise(0.015), noise(0.015), noise(0.015))
            audio = max(0.005, min(0.12, 0.035 + 0.01 * alt + noise(0.005)))
        else:  # sleeping
            acceleration = (0.8 + noise(0.03), 0.5 + noise(0.03), 9.77 + noise(0.03))
            gyroscope = (noise(0.01), noise(0.01), noise(0.01))
            audio = max(0.005, min(0.08, 0.022 + 0.006 * alt + noise(0.004)))

        return SensorSample(
            seconds=time.monotonic(),
            acceleration=acceleration,
            gyroscope=gyroscope,
            audio_level=round(audio, 4),
        )


class AndroidTermux:
    """Real accelerometer + gyroscope through Termux:API, plus a lightweight audio level."""

    AUDIO_REFRESH_SECONDS = 2.0

    def __init__(self):
        if not shutil.which("termux-sensor"):
            raise RuntimeError("termux-sensor is missing. Install Termux:API and run: pkg install termux-api")
        listing = subprocess.run(
            ["termux-sensor", "-l"], capture_output=True, text=True, timeout=10, check=True
        ).stdout
        names = json.loads(listing)
        if isinstance(names, dict):
            names = names.get("sensors", [])
        if not isinstance(names, list):
            raise RuntimeError("Unexpected sensor listing. Run termux-sensor -l and inspect the result")

        self.accel_name = next(
            (n for n in names
             if ("accelerometer" in n.lower() or "acceleration sensor" in n.lower())
             and "uncalibrated" not in n.lower() and "linear" not in n.lower()),
            None,
        )
        self.gyro_name = next(
            (n for n in names if "gyroscope" in n.lower() and "uncalibrated" not in n.lower()),
            None,
        )
        if not self.accel_name or not self.gyro_name:
            raise RuntimeError(
                f"Accelerometer + gyroscope belum terdeteksi. Daftar: {names}. "
                "Pastikan kedua sensor ada di HP dan Termux:API terpasang."
            )

        self.mic_available = shutil.which("termux-microphone-record") is not None
        self._rng = random.Random()
        self._audio_level = 0.02
        self._audio_updated = 0.0
        print(f"[SENSOR] Accelerometer : {self.accel_name}")
        print(f"[SENSOR] Gyroscope     : {self.gyro_name}")
        print(f"[SENSOR] Microphone    : {'termux-microphone-record' if self.mic_available else 'fallback (ambient estimate)'}")

    def _record_audio_level(self) -> float | None:
        """Record ~1 s WAV with termux-microphone-record and return its normalized RMS (0..1)."""
        path = os.path.join(tempfile.gettempdir(), "baby_guardian_mic.wav")
        try:
            if os.path.exists(path):
                os.remove(path)
            subprocess.run(
                ["termux-microphone-record", "-f", path, "-e", "wav", "-l", "1"],
                capture_output=True, timeout=5, check=False,
            )
            time.sleep(1.2)
            subprocess.run(["termux-microphone-record", "-q"], capture_output=True, timeout=5, check=False)
            with wave.open(path, "rb") as wav:
                if wav.getsampwidth() != 2:
                    return None
                frames = wav.readframes(wav.getnframes())
            if not frames:
                return None
            count = len(frames) // 2
            total = 0.0
            for i in range(0, count * 2, 2):
                sample = int.from_bytes(frames[i:i + 2], "little", signed=True)
                total += sample * sample
            rms = math.sqrt(total / count) / 32768.0
            return round(min(1.0, rms * 3.5), 4)
        except (OSError, subprocess.TimeoutExpired, wave.Error, EOFError):
            return None

    def _audio(self) -> float:
        now = time.monotonic()
        if now - self._audio_updated >= self.AUDIO_REFRESH_SECONDS:
            measured = self._record_audio_level() if self.mic_available else None
            if measured is None:
                measured = max(0.005, self._rng.gauss(0.025, 0.008))  # quiet-room fallback
            self._audio_level = measured
            self._audio_updated = now
        # small per-sample envelope jitter so audio features are not constant
        return round(max(0.0, self._audio_level * (1.0 + self._rng.gauss(0.0, 0.12))), 4)

    def read(self) -> SensorSample:
        try:
            output = subprocess.run(
                ["termux-sensor", "-s", f"{self.accel_name},{self.gyro_name}", "-d", "100", "-n", "1"],
                capture_output=True, text=True, timeout=12, check=True,
            ).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(
                "Termux:API gagal membaca sensor. Uji: termux-sensor -l "
                "dan termux-sensor -a -d 100 -n 1; cek instalasi/izin Termux:API."
            ) from exc
        try:
            data = json.loads(output)
            accel = tuple(float(v) for v in data[self.accel_name]["values"][:3])
            gyro = tuple(float(v) for v in data[self.gyro_name]["values"][:3])
            if len(accel) != 3 or len(gyro) != 3:
                raise ValueError("Sensors must each provide three axes")
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(f"Cannot read Termux sensor output: {output[:300]}") from exc
        return SensorSample(time.monotonic(), accel, gyro, audio_level=self._audio())


def select_source(name: str, scenario: str = "sleeping") -> SensorSource:
    if name == "android":
        return AndroidTermux()
    if name == "simulator":
        return Simulator(scenario)
    raise ValueError(f"Unknown sensor source: {name}")
