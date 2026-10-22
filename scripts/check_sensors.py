"""Sensor-only diagnostic. Does NOT require an MQTT broker or .env.

Run this on Android Termux:
    python -m scripts.check_sensors --readings 12

Move and rotate your phone while values print. If the numbers change,
sensor access works and any remaining issue is after sensor acquisition.
"""

import argparse
import math
import time

from shared.processing import extract_features
from shared.sensors import AndroidTermux


def main():
    parser = argparse.ArgumentParser(description="Check Android motion sensors")
    parser.add_argument("--readings", type=int, default=12)
    args = parser.parse_args()
    if args.readings < 2:
        parser.error("--readings must be >= 2")

    print("[CHECK] Starting Termux:API sensor test; NO MQTT required.", flush=True)
    source = AndroidTermux()
    samples = []
    for number in range(args.readings):
        reading = source.read()
        samples.append(reading)
        magnitude = math.sqrt(sum(axis * axis for axis in reading.acceleration))
        angular_speed = math.sqrt(sum(axis * axis for axis in reading.gyroscope))
        print(
            f"[CHECK] {number + 1}/{args.readings} "
            f"accel={tuple(round(v, 3) for v in reading.acceleration)} m/s² "
            f"|gyro={tuple(round(v, 3) for v in reading.gyroscope)} rad/s "
            f"|a_magnitude={magnitude:.3f} |angular_speed={angular_speed:.3f}",
            flush=True,
        )
        if number < args.readings - 1:
            time.sleep(0.1)

    features = extract_features(samples)
    print(
        f"[PROCESSING] motion_rms={features.motion_rms:.4f} m/s² "
        f"rotation_rad={features.rotation_rad:.4f} rad"
    )
    print("[CHECK] If values reacted to motion, the Android sensor path works.")


if __name__ == "__main__":
    main()
