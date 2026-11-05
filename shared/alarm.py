"""ACTUATOR: how the Parent Node (Edge 2) reacts to a Baby Guardian ALERT.

Android (Termux + Termux:API): vibrate + high-priority notification with sound.
Laptop: prints the alert only, so the same code runs anywhere.
"""

import shutil
import subprocess


def _run_quietly(command: list[str]):
    try:
        subprocess.run(command, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[ALARM] Could not run {command[0]}: {exc}")


def ring_alarm(alert: dict):
    if str(alert.get("status", "ALERT")).upper() != "ALERT":
        return

    reason = str(alert.get("reason", "Bayi menangis atau posisi tidur berbahaya!"))
    score = alert.get("risk_score", "?")
    print(f"\n[PARENT_NODE | ALERT] confidence={score} — {reason}\n", flush=True)

    if shutil.which("termux-vibrate"):
        _run_quietly(["termux-vibrate", "-d", "1500"])
    if shutil.which("termux-notification"):
        _run_quietly([
            "termux-notification",
            "--id", "babyguardian",
            "--title", "Baby Guardian ALERT: cek bayi sekarang!",
            "--content", f"Confidence {score}. {reason}",
            "--priority", "high",
            "--sound",
        ])
