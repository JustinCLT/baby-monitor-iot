"""NODE 1: HP yang dijaga (edge1).

Di HP (Termux):  python hp_dijaga.py
Di laptop:       python hp_dijaga.py --scenario pickup   (simulasi diangkat)
"""

from shared.edge_runner import run_edge

if __name__ == "__main__":
    run_edge("edge1")
