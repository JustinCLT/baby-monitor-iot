"""OUTPUT / ACTUATOR: how the owner's phone reacts to an alert.

On Android (Termux + Termux:API) the phone vibrates and shows a notification.
On a laptop the same code only prints to the terminal, so it runs anywhere.
"""

import shutil
import subprocess


def _run_quietly(command: list[str]):
    try:
        subprocess.run(command, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[ALARM] Could not run {command[0]}: {exc}")


def ring_alarm(alert: dict):
    reason = str(alert.get("reason", "Gerakan mencurigakan"))
    score = alert.get("risk_score", "?")
    print(f"\n[EDGE2 | ALARM] HP yang dijaga bergerak! risk={score} — {reason}\n")

    if shutil.which("termux-vibrate"):
        _run_quietly(["termux-vibrate", "-d", "1500"])
    if shutil.which("termux-notification"):
        _run_quietly([
            "termux-notification",
            "--id", "pocketguard",
            "--title", "PocketGuard: HP kamu bergerak!",
            "--content", f"Risk score {score}. {reason}",
            "--priority", "high",
            "--sound",
        ])
