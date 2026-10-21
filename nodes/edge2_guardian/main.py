"""NODE 2: owner's smartphone. Sensors -> processing -> MQTT; receives alerts."""

from shared.edge_runner import run_edge

if __name__ == "__main__":
    run_edge("edge2")
