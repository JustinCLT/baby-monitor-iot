"""OUTPUT / ACTUATOR: how the Parent Node (Edge 2) reacts to an emergency baby alert.

On Android (Termux + Termux:API) the parent's phone vibrates and shows a high-priority notification.
On a laptop the same code prints to the terminal, so it runs anywhere.
"""

import shutil
import subprocess


def _run_quietly(command: list[str]):
    try:
        subprocess.run(command, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[ALARM] Could not run {command[0]}: {exc}")


def ring_alarm(alert: dict):
    status = str(alert.get("status", "CRYING_AWAKE")).upper()
    if status not in ("CRYING_AWAKE", "ALERT") and alert.get("event") not in ("baby_crying_or_awake", "suspicious_movement", None):
        return

    reason = str(alert.get("reason", "Bayi terbangun atau menangis aktif!"))
    score = alert.get("risk_score", "?")
    audio_rms = alert.get("audio_rms")
    audio_info = f" | audio_rms={audio_rms}" if audio_rms is not None else ""

    print(
        f"\n[PARENT_NODE | EDGE2 | EMERGENCY ALERT] "
        f"Status={status} | Risk={score}{audio_info} — {reason}\n",
        flush=True,
    )

    if shutil.which("termux-vibrate"):
        _run_quietly(["termux-vibrate", "-d", "1500"])
    if shutil.which("termux-notification"):
        _run_quietly([
            "termux-notification",
            "--id", "babymonitor",
            "--title", "Baby Monitor ALERT: Bayi Menangis / Terbangun!",
            "--content", f"Risk score {score}. {reason}",
            "--priority", "high",
            "--sound",
        ])
