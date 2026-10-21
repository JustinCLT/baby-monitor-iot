"""NODE 2: HP pemilik (edge2), bergetar saat ada alert.

Di HP (Termux):  python hp_pemilik.py
Di laptop:       python hp_pemilik.py   (simulasi diam)
"""

from shared.alarm import ring_alarm
from shared.edge_runner import run_edge

if __name__ == "__main__":
    run_edge("edge2", on_alert=ring_alarm)
