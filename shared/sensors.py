"""Where raw physical sensor values come from.

'--source simulator' runs on any laptop with realistic baby motion + audio scenarios.
'--source android' calls the real Termux:API motion sensors on Android.

Light sensor is disabled/not used; only Motion (Accelerometer + Gyroscope) and Audio RMS are used.
"""

import json
import math
import random
import shutil
import subprocess
import time
from typing import Protocol

from shared.processing import SensorSample


class SensorSource(Protocol):
    def read(self) -> SensorSample: ...


class Simulator:
    """Simulates baby crib vibration (accelerometer + gyroscope) and room audio amplitude (audio_rms)."""

    SCENARIO_ALIASES = {
        "still": "sleeping",
        "pickup": "crying_awake",
        "table_shake": "restless",
    }

    def __init__(self, scenario: str = "sleeping", seed: int = 42):
        normalized = self.SCENARIO_ALIASES.get(scenario, scenario)
        if normalized not in ("sleeping", "restless", "crying_awake", "crowd_noise"):
            raise ValueError(f"Unknown simulator scenario: {scenario}")
        self.scenario = normalized
        self.started = time.monotonic()
        self.random = random.Random(seed)

    def read(self) -> SensorSample:
        elapsed = time.monotonic() - self.started
        noise = lambda scale: self.random.gauss(0.0, scale)

        if self.scenario == "crying_awake":
            # High crib motion + loud baby crying audio
            amplitude = 2.2
            acceleration = (
                amplitude * math.sin(6.0 * elapsed) + noise(0.08),
                0.8 * math.cos(5.0 * elapsed) + noise(0.08),
                9.81 + amplitude * math.cos(4.5 * elapsed) + noise(0.08),
            )
            gyroscope = (
                0.65 + noise(0.04),
                0.30 + noise(0.03),
                0.22 + noise(0.03),
            )
            audio_rms = max(0.0, 0.55 + noise(0.05))

        elif self.scenario == "restless":
            # Moderate mattress vibration (baby tossing/crawling), audio remains quiet
            amplitude = 0.85
            acceleration = (
                amplitude * math.sin(3.5 * elapsed) + noise(0.05),
                0.3 * math.cos(2.5 * elapsed) + noise(0.05),
                9.81 + amplitude * math.cos(3.0 * elapsed) + noise(0.05),
            )
            gyroscope = (
                0.24 + noise(0.02),
                0.10 + noise(0.02),
                0.08 + noise(0.02),
            )
            audio_rms = max(0.0, 0.04 + noise(0.01))

        elif self.scenario == "crowd_noise":
            # Sudden external noise (e.g., door slam / talking outside), but mattress is still
            acceleration = (noise(0.03), noise(0.03), 9.81 + noise(0.03))
            gyroscope = (noise(0.01), noise(0.01), noise(0.01))
            audio_rms = max(0.0, 0.28 + noise(0.03))

        else:
            # "sleeping": Quiet room audio and still mattress (baby sleeping soundly)
            acceleration = (noise(0.03), noise(0.03), 9.81 + noise(0.03))
            gyroscope = (noise(0.01), noise(0.01), noise(0.01))
            audio_rms = max(0.0, 0.02 + noise(0.005))

        return SensorSample(
            seconds=time.monotonic(),
            acceleration=acceleration,
            gyroscope=gyroscope,
            audio_rms=round(audio_rms, 4),
        )


class AndroidTermux:
    def __init__(self):
        if not shutil.which("termux-sensor"):
            raise RuntimeError("termux-sensor is missing. Install Termux:API and run: pkg install termux-api")
        names_output = subprocess.run(
            ["termux-sensor", "-l"], capture_output=True, text=True, timeout=10, check=True
        ).stdout
        names = json.loads(names_output)
        if isinstance(names, dict):
            names = names.get("sensors", [])
        if not isinstance(names, list):
            raise RuntimeError("Unexpected sensor listing. Run termux-sensor -l and inspect the result")

        self.accel_name = next(
            (
                name for name in names
                if ("accelerometer" in name.lower() or "acceleration sensor" in name.lower())
                and "uncalibrated" not in name.lower()
                and "linear" not in name.lower()
            ),
            None,
        )
        self.gyro_name = next(
            (
                name for name in names
                if "gyroscope" in name.lower()
                and "uncalibrated" not in name.lower()
            ),
            None,
        )

        if not self.accel_name or not self.gyro_name:
            raise RuntimeError(
                f"Accelerometer + gyroscope belum terdeteksi. Daftar: {names}. "
                "Pastikan kedua sensor ada di HP dan Termux:API terpasang."
            )

        print(f"[SENSOR] Accelerometer : {self.accel_name}")
        print(f"[SENSOR] Gyroscope     : {self.gyro_name}")

    def read(self) -> SensorSample:
        try:
            output = subprocess.run(
                [
                    "termux-sensor",
                    "-s",
                    f"{self.accel_name},{self.gyro_name}",
                    "-d",
                    "100",
                    "-n",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=12,
                check=True,
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
                raise ValueError("Accelerometer and gyroscope must each provide three axes")
            return SensorSample(time.monotonic(), accel, gyro, audio_rms=0.0)
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(f"Cannot read Termux sensor output: {output[:300]}") from exc


def select_source(name: str, scenario: str = "sleeping") -> SensorSource:
    if name == "android":
        return AndroidTermux()
    if name == "simulator":
        return Simulator(scenario)
    raise ValueError(f"Unknown sensor source: {name}")
