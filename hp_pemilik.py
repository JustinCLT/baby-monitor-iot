"""NODE 2 — Parent Node (edge2 / hp_pemilik.py).

Dipegang orang tua di ruangan lain untuk memantau status kamar bayi dan
menerima notifikasi darurat (getar/suara via Termux) saat status CRYING_AWAKE.

Cara menjalankan:
  - Di HP Orang Tua (Termux):
      python hp_pemilik.py
  - Simulasi di Laptop:
      python hp_pemilik.py --source simulator --scenario sleeping
"""

from shared.alarm import ring_alarm
from shared.edge_runner import run_edge

NODE_ID = "edge2"
NODE_LABEL = "PARENT_NODE (Edge 2 - Orang Tua)"
DEFAULT_SCENARIO = "sleeping"


def main():
    print("=============================================================", flush=True)
    print(" Smart Dual-Zone Baby Monitor — NODE 2: PARENT NODE (edge2)", flush=True)
    print(" Mode: Telemetry + Emergency Alert Receiver (termux-vibrate)", flush=True)
    print("=============================================================", flush=True)
    run_edge(
        device_id=NODE_ID,
        on_alert=ring_alarm,
        default_scenario=DEFAULT_SCENARIO,
        node_label=NODE_LABEL,
    )


if __name__ == "__main__":
    main()
