"""ONE shared MQTT connection implementation, used by ALL nodes."""

import os
import uuid

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()


def project_id() -> str:
    value = os.getenv("PROJECT_ID", "kelas_iot_demo")
    if not value.replace("_", "").replace("-", "").isalnum():
        raise ValueError("PROJECT_ID may only contain letters, numbers, - and _")
    return value


def topic(suffix: str) -> str:
    return f"pocketguard/{project_id()}/{suffix}"


def create_client(role: str, will: tuple[str, str] | None = None) -> mqtt.Client:
    """Connect to the broker from .env. `will` = (topic, payload) the broker
    publishes (retained) if this client disconnects unexpectedly."""
    host = os.getenv("MQTT_HOST")
    if not host or host == "YOUR_EMQX_HOST":
        raise RuntimeError("Configure MQTT_HOST in .env first. See docs/SETUP.md")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{project_id()}-{role}-{uuid.uuid4().hex[:8]}",
        protocol=mqtt.MQTTv311,
    )
    username = os.getenv("MQTT_USERNAME", "")
    password = os.getenv("MQTT_PASSWORD", "")
    if username:
        client.username_pw_set(username, password)

    use_tls = os.getenv("MQTT_TLS", "true").lower() == "true"
    if use_tls:
        client.tls_set()
    else:
        if os.getenv("ALLOW_INSECURE_LOCAL") != "true":
            raise RuntimeError("TLS disabled. Only allow this for local development via ALLOW_INSECURE_LOCAL=true")

    if will is not None:
        client.will_set(will[0], will[1], qos=1, retain=True)

    port = int(os.getenv("MQTT_PORT", "8883" if use_tls else "1883"))
    client.connect(host, port, keepalive=30)
    return client
