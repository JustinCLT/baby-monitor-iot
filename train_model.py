"""Standalone training & data-collection script for the Smart Multimodal Baby Guardian ML model.

Supports 3 modes:
  1. Train from synthetic dataset (default):
       python train_model.py
  2. Record real sensor telemetry from Edge 1 (HP) via MQTT into a CSV file:
       python train_model.py --record sleeping --count 30
       python train_model.py --record restless --count 30
       python train_model.py --record crying --count 30
       python train_model.py --record prone_risk --count 30
  3. Train model using your own recorded CSV dataset:
       python train_model.py --csv custom_dataset.csv

Features (6 dimensions, same order as Telemetry.feature_vector()):
  0: motion_rms               (m/s²)
  1: jerk_metric              (m/s³)
  2: tilt_angle               (degrees, 0° = flat on back, >110° = prone / face-down)
  3: audio_rms                (0.0 - 1.0 normalized amplitude)
  4: spectral_centroid_approx (Hz)
  5: zcr                      (0.0 - 1.0 zero-crossing rate)

Target classes:
  0: SLEEPING   — low motion, safe supine tilt, quiet audio
  1: RESTLESS   — moderate motion & jerk (repeated rolling), quiet / sighing audio
  2: CRYING     — loud high-frequency crying audio, with or without bed vibration
  3: PRONE_RISK — steep / inverted tilt angle (>110°), minimal movement
"""

import argparse
import csv
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

MODEL_PATH = Path(__file__).resolve().parent / "baby_guardian_model.joblib"
DEFAULT_CSV_PATH = Path(__file__).resolve().parent / "custom_dataset.csv"

FEATURE_NAMES = [
    "motion_rms",
    "jerk_metric",
    "tilt_angle",
    "audio_rms",
    "spectral_centroid_approx",
    "zcr",
]

CLASS_NAMES = {
    0: "SLEEPING",
    1: "RESTLESS",
    2: "CRYING",
    3: "PRONE_RISK",
}

NAME_TO_CLASS = {name.lower(): idx for idx, name in CLASS_NAMES.items()}

# Per-class Gaussian profile: feature -> (mean, std, min_clip, max_clip)
CLASS_PROFILES = {
    0: {  # SLEEPING
        "motion_rms": (0.06, 0.04, 0.005, 0.28),
        "jerk_metric": (0.45, 0.25, 0.02, 1.80),
        "tilt_angle": (8.0, 5.0, 0.0, 28.0),
        "audio_rms": (0.025, 0.015, 0.002, 0.10),
        "spectral_centroid_approx": (380.0, 90.0, 150.0, 750.0),
        "zcr": (0.08, 0.05, 0.01, 0.25),
    },
    1: {  # RESTLESS
        "motion_rms": (0.82, 0.22, 0.38, 1.60),
        "jerk_metric": (6.50, 2.00, 2.00, 13.00),
        "tilt_angle": (30.0, 12.0, 10.0, 75.0),
        "audio_rms": (0.08, 0.035, 0.01, 0.20),
        "spectral_centroid_approx": (720.0, 180.0, 350.0, 1350.0),
        "zcr": (0.15, 0.06, 0.04, 0.40),
    },
    2: {  # CRYING (loud high-frequency crying audio, with or without bed vibration)
        "motion_rms": (1.10, 0.85, 0.01, 3.50),
        "jerk_metric": (9.00, 7.50, 0.05, 28.00),
        "tilt_angle": (18.0, 14.0, 0.0, 75.0),
        "audio_rms": (0.60, 0.16, 0.30, 1.00),
        "spectral_centroid_approx": (3200.0, 500.0, 1800.0, 4400.0),
        "zcr": (0.76, 0.14, 0.38, 1.00),
    },
    3: {  # PRONE_RISK
        "motion_rms": (0.10, 0.07, 0.01, 0.42),
        "jerk_metric": (0.80, 0.45, 0.05, 2.50),
        "tilt_angle": (152.0, 14.0, 110.0, 180.0),
        "audio_rms": (0.04, 0.025, 0.002, 0.15),
        "spectral_centroid_approx": (440.0, 110.0, 180.0, 900.0),
        "zcr": (0.08, 0.05, 0.01, 0.30),
    },
}


def generate_synthetic_dataset(samples_per_class: int = 500, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y) with `samples_per_class` Gaussian-noise samples for each of the 4 classes."""
    if samples_per_class < 400:
        raise ValueError("samples_per_class must be at least 400")

    rng = np.random.default_rng(seed)
    feature_blocks = []
    label_blocks = []

    for class_id, profile in CLASS_PROFILES.items():
        columns = []
        for name in FEATURE_NAMES:
            mean, std, low, high = profile[name]
            columns.append(np.clip(rng.normal(mean, std, samples_per_class), low, high))
        feature_blocks.append(np.column_stack(columns))
        label_blocks.append(np.full(samples_per_class, class_id, dtype=int))

    return np.vstack(feature_blocks), np.concatenate(label_blocks)


def load_csv_dataset(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load recorded feature rows and labels from a CSV file."""
    if not csv_path.exists():
        raise FileNotFoundError(f"File CSV tidak ditemukan: {csv_path}")

    rows_x = []
    rows_y = []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_x.append([float(row[name]) for name in FEATURE_NAMES])
            rows_y.append(int(row["label"]))

    if len(rows_x) < 8:
        raise ValueError(f"Dataset CSV terlalu sedikit ({len(rows_x)} baris). Rekam minimal 8 sampel.")
    return np.asarray(rows_x, dtype=float), np.asarray(rows_y, dtype=int)


def record_live_samples(label_name: str, count: int, csv_path: Path = DEFAULT_CSV_PATH):
    """Subscribe to Edge 1 telemetry on MQTT and append `count` labeled rows to `csv_path`."""
    from shared.messages import Telemetry
    from shared.mqtt_connection import create_client, topic

    class_id = NAME_TO_CLASS[label_name.lower()]
    telemetry_topic = topic("edge/edge1/telemetry")
    file_exists = csv_path.exists()
    collected = 0

    print("==================================================================")
    print(f" LIVE DATA RECORDER — Kelas {class_id}: {CLASS_NAMES[class_id]}")
    print(f" Menunggu {count} paket telemetri dari Edge 1 ({telemetry_topic})...")
    print(f" File tujuan: {csv_path}")
    print("==================================================================", flush=True)

    handle = csv_path.open("a", newline="", encoding="utf-8")
    writer = csv.writer(handle)
    if not file_exists:
        writer.writerow([*FEATURE_NAMES, "label", "label_name"])
        handle.flush()

    client = create_client("trainer-recorder")

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(telemetry_topic, qos=1)
        print(f"[RECORDER] Terhubung ke MQTT. Silakan peragakan kondisi '{CLASS_NAMES[class_id]}' di HP Edge 1!", flush=True)

    def on_message(client, userdata, message):
        nonlocal collected
        try:
            reading = Telemetry.from_json(message.payload)
        except ValueError:
            return
        vector = reading.feature_vector()
        writer.writerow([*vector, class_id, CLASS_NAMES[class_id]])
        handle.flush()
        collected += 1
        print(
            f"[RECORDER {collected}/{count}] Disimpan -> motion={reading.motion_rms:.3f}, "
            f"jerk={reading.jerk_metric:.2f}, tilt={reading.tilt_angle:.1f}°, "
            f"audio={reading.audio_rms:.3f}, centroid={reading.spectral_centroid_approx:.0f}Hz, zcr={reading.zcr:.3f}",
            flush=True,
        )
        if collected >= count:
            print(f"\n[SELESAI] {count} sampel kelas {CLASS_NAMES[class_id]} berhasil disimpan ke {csv_path}!")
            client.disconnect()

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[RECORDER] Dihentikan oleh user.")
    finally:
        handle.close()


def train_and_save_model(
    output_path: Path = MODEL_PATH,
    samples_per_class: int = 500,
    csv_path: Path | None = None,
    n_estimators: int = 100,
    max_depth: int = 8,
) -> RandomForestClassifier:
    print("==================================================================")
    print(" Smart Multimodal Baby Guardian — ML Model Trainer (Random Forest)")
    print("==================================================================")
    if csv_path is not None:
        X, y = load_csv_dataset(csv_path)
        print(f"[DATASET]  Loaded {len(X)} recorded samples from {csv_path}")
    else:
        X, y = generate_synthetic_dataset(samples_per_class=samples_per_class, seed=42)
        print(f"[DATASET]  {len(X)} synthetic samples ({samples_per_class} per class, {X.shape[1]} features)")
    print(f"[FEATURES] {FEATURE_NAMES}")

    unique_classes, counts = np.unique(y, return_counts=True)
    stratify = y if len(unique_classes) > 1 and np.min(counts) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=stratify, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth, random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    present_labels = sorted(np.unique(np.concatenate([y_test, y_pred])).tolist())
    target_names = [f"{idx}: {CLASS_NAMES.get(idx, str(idx))}" for idx in present_labels]

    print(f"\n[EVALUATION] Test accuracy: {accuracy * 100:.2f}%\n")
    print(classification_report(y_test, y_pred, labels=present_labels, target_names=target_names, digits=4))

    importances = sorted(zip(FEATURE_NAMES, model.feature_importances_), key=lambda item: -item[1])
    print("[FEATURE IMPORTANCE]")
    for name, value in importances:
        print(f"  {name:<26} {value:.4f}")

    joblib.dump(model, output_path)
    print(f"\n[SAVED] Model saved to: {output_path}")
    return model


def main():
    parser = argparse.ArgumentParser(description="Train or record data for Smart Multimodal Baby Guardian")
    parser.add_argument(
        "--record",
        choices=list(NAME_TO_CLASS.keys()),
        help="Rekam data sensor langsung dari Edge 1 via MQTT untuk kelas tertentu ke CSV",
    )
    parser.add_argument("--count", type=int, default=30, help="Jumlah sampel yang direkam saat --record (default: 30)")
    parser.add_argument("--csv", type=Path, default=None, help="Path file CSV hasil rekaman untuk dilatih")
    parser.add_argument("--samples-per-class", type=int, default=500, help="Jumlah sampel sintetis per kelas (>= 400)")
    parser.add_argument("--trees", type=int, default=100, help="Jumlah pohon Random Forest (n_estimators)")
    parser.add_argument("--max-depth", type=int, default=8, help="Kedalaman maksimum pohon (max_depth)")
    args = parser.parse_args()

    if args.record:
        csv_target = args.csv if args.csv is not None else DEFAULT_CSV_PATH
        record_live_samples(args.record, args.count, csv_target)
        return

    train_and_save_model(
        output_path=MODEL_PATH,
        samples_per_class=args.samples_per_class,
        csv_path=args.csv,
        n_estimators=args.trees,
        max_depth=args.max_depth,
    )


if __name__ == "__main__":
    main()
