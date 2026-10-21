"""NODE 2: owner's smartphone.

Sensors -> processing -> MQTT telemetry (reference for the detector),
and it receives alerts: vibrate + notification on Android.
"""

from shared.alarm import ring_alarm
from shared.edge_runner import run_edge

if __name__ == "__main__":
    run_edge("edge2", on_alert=ring_alarm)
