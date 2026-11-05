"""NODE 3 — Laptop: Smart Multimodal Baby Guardian ML detector + web dashboard.

  1. python train_model.py   (sekali, membuat baby_guardian_model.joblib)
  2. python detector.py
"""

from nodes.detector_service.main import main
from shared.dashboard_server import start_dashboard_server
from shared.mqtt_connection import project_id


def run():
    try:
        server, thread, url = start_dashboard_server()
    except OSError as exc:
        raise SystemExit(
            f"[DASHBOARD] Gagal membuka port dashboard: {exc}. "
            "Tutup aplikasi lain di port ini atau set DASHBOARD_PORT di .env."
        ) from exc

    print("\nSmart Multimodal Baby Guardian & Closed-Loop Safety Telemetry — NODE 3 / Laptop", flush=True)
    print(f"[DASHBOARD] {url}", flush=True)
    print(f"[WEB-EDGE]  {url}/edge  (sensor lewat browser, tanpa Termux)", flush=True)
    print(f"[CONFIG]    PROJECT_ID: {project_id()}", flush=True)
    print("[ML-DETECTOR] Menunggu telemetri dari Baby Node (edge1) dan Parent Node (edge2)...\n", flush=True)
    try:
        main()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    run()
