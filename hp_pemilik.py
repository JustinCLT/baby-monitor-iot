"""NODE 2 — Parent Node (edge2): HP dipegang orang tua.

Subscribe ke pocketguard/<PROJECT_ID>/alerts dan status. Saat ALERT diterima dari
BabyGuardianMLDetector: termux-vibrate + notifikasi darurat (lihat shared/alarm.py).

  HP (Termux):  python hp_pemilik.py
  Simulasi:     python hp_pemilik.py --source simulator
"""

from shared.alarm import ring_alarm
from shared.edge_runner import run_edge


def main():
    print("=" * 66)
    print(" Smart Multimodal Baby Guardian — NODE 2: PARENT NODE (edge2)")
    print(" Closed-loop alert receiver: termux-vibrate + notification on ALERT")
    print("=" * 66, flush=True)
    run_edge("edge2", on_alert=ring_alarm, default_scenario="sleeping")


if __name__ == "__main__":
    main()
