"""NODE 1 — Baby Node (edge1 / hp_dijaga.py).

Diletakkan di dekat kasur/bayi untuk memantau getaran kasur (accelerometer + gyroscope)
dan amplitudo audio lingkungan / suara tangisan bayi (audio_rms).

Cara menjalankan:
  - Di HP Bayi (Termux):
      python hp_dijaga.py
  - Simulasi di Laptop:
      python hp_dijaga.py --source simulator --scenario sleeping
      python hp_dijaga.py --source simulator --scenario restless
      python hp_dijaga.py --source simulator --scenario crying_awake
      python hp_dijaga.py --source simulator --scenario crowd_noise
"""

from shared.edge_runner import run_edge

NODE_ID = "edge1"
NODE_LABEL = "BABY_NODE (Edge 1 - Kasur Bayi)"
DEFAULT_SCENARIO = "sleeping"


def main():
    print("==========================================================", flush=True)
    print(" Smart Dual-Zone Baby Monitor — NODE 1: BABY NODE (edge1)", flush=True)
    print(" Sensor: Motion (Accelerometer + Gyroscope) & Audio RMS  ", flush=True)
    print("==========================================================", flush=True)
    run_edge(
        device_id=NODE_ID,
        on_alert=None,
        default_scenario=DEFAULT_SCENARIO,
        node_label=NODE_LABEL,
    )


if __name__ == "__main__":
    main()
