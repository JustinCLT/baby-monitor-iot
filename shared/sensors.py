"""Where raw physical sensor values come from.

'--source simulator' runs on any laptop.
'--source android' calls the real Termux:API sensors on Android.

Both sources produce the SAME SensorSample object. The processing logic
never needs to know which source generated the readings.
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
    def __init__(self, scenario: str = "still", seed: int = 42):
        self.scenario = scenario
        self.started = time.monotonic()
        self.random = random.Random(seed)

    def read(self) -> SensorSample:
        elapsed = time.monotonic() - self.started
        active = 3 <= elapsed <= 12 and self.scenario in ("pickup", "table_shake")
        noise = lambda scale: self.random.gauss(0, scale)

        if active:
            amplitude = 2.5 if self.scenario == "pickup" else 1.5
            acceleration = (
                amplitude * math.sin(5 * elapsed) + noise(0.07),
                noise(0.07),
                9.81 + amplitude * math.cos(4 * elapsed) + noise(0.07),
            )
            gyroscope = (0.65 + noise(0.03), 0.17, 0.12)
        else:
            acceleration = (noise(0.03), noise(0.03), 9.81 + noise(0.03))
            gyroscope = (noise(0.01), noise(0.01), noise(0.01))

        return SensorSample(time.monotonic(), acceleration, gyroscope)


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
        self.accel_name = next((name for name in names if "accelerometer" in name.lower()), None)
        self.gyro_name = next((name for name in names if "gyroscope" in name.lower()), None)
        if not self.accel_name or not self.gyro_name:
            raise RuntimeError(f"Need accelerometer and gyroscope, found: {names}")

    def read(self) -> SensorSample:
        output = subprocess.run(
            ["termux-sensor", "-s", f"{self.accel_name},{self.gyro_name}", "-n", "1"],
            capture_output=True, text=True, timeout=12, check=True,
        ).stdout
        try:
            data = json.loads(output)
            accel = tuple(float(v) for v in data[self.accel_name]["values"][:3])
            gyro = tuple(float(v) for v in data[self.gyro_name]["values"][:3])
            if len(accel) != 3 or len(gyro) != 3:
                raise ValueError("Sensors must each provide three axes")
            return SensorSample(time.monotonic(), accel, gyro)
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(f"Cannot read Termux sensor output: {output[:300]}") from exc


def select_source(name: str, scenario: str) -> SensorSource:
    if name == "android":
        return AndroidTermux()
    if name == "simulator":
        return Simulator(scenario)
    raise ValueError(f"Unknown sensor source: {name}")
