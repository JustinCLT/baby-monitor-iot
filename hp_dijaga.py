"""NODE 1 — Baby Node (edge1): HP diletakkan di dekat bayi.

Membaca accelerometer, gyroscope, dan audio, mengekstrak 6 fitur multimodal
[motion_rms, jerk_metric, tilt_angle, audio_rms, spectral_centroid_approx, zcr]
lalu publish ke MQTT untuk dianalisis BabyGuardianMLDetector di laptop.

  HP (Termux):  python hp_dijaga.py
  Simulasi:     python hp_dijaga.py --source simulator --scenario sleeping|restless|crying|prone_risk
"""

from shared.edge_runner import run_edge


def main():
    print("=" * 66)
    print(" Smart Multimodal Baby Guardian — NODE 1: BABY NODE (edge1)")
    print(" Sensors: accelerometer + gyroscope + audio -> 6 multimodal features")
    print("=" * 66, flush=True)
    run_edge("edge1", default_scenario="sleeping")


if __name__ == "__main__":
    main()
