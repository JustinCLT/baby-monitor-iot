"""NODE 1: protected smartphone. Real/simulated sensors -> processing -> MQTT."""

from shared.edge_runner import run_edge

if __name__ == "__main__":
    run_edge("edge1")
