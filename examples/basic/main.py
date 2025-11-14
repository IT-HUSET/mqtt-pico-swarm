import json
import time

import network

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.client import PicoSwarmClient
from mqtt_pico_swarm.constants import COMMAND_TYPE_ACTION
from mqtt_pico_swarm.errors import ConnectionError

CONFIG_FILE = "config.json"
NETWORK_SSID = "ITH"
NETWORK_PASSWORD = "xxx"
PUBLISH_INTERVAL = 60


def connect_wifi(ssid, password, timeout=20):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print("Aktiverar WiFi...")
        wlan.active(True)
        wlan.connect(ssid, password)
        while not wlan.isconnected() and timeout > 0:
            print("Väntar på WiFi...", timeout)
            time.sleep(1)
            timeout -= 1
    if not wlan.isconnected():
        raise RuntimeError("Kunde inte ansluta till WiFi")
    ip, _, _, _ = wlan.ifconfig()
    print("WiFi ansluten, IP:", ip)
    return ip


def _load_config():
    with open(CONFIG_FILE, "r") as handle:
        return json.load(handle)


def main():
    connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)

    try:
        _ = _load_config()
    except OSError:
        print("config.json saknas. Kopiera config.json.example och fyll i MQTT-detaljer.")
        return

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    @client.on_command(COMMAND_TYPE_ACTION)
    def handle_action(command):
        print("Mottog action-kommando:", command)
        command_id = command.get("command_id")
        if command_id:
            client.acknowledge_command(
                command_id,
                "success",
                message="Åtgärd utförd på enhet",
            )

    try:
        client.connect()
        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Enheten är online",
        )

        print("Startar huvudloopen. Tryck Ctrl+C för att avsluta.")
        last_publish = 0
        heartbeat_interval = client.get_config().get("heartbeat_interval", 60)
        last_heartbeat = time.time()

        while True:
            now = time.time()

            # Säkerställ uppkoppling och processa inkommande kommandon
            try:
                client._connection_manager.ensure_connected()
                client._connection_manager.process_incoming()
            except ConnectionError:
                continue

            # Publicera sensordata enligt intervall
            if now - last_publish >= PUBLISH_INTERVAL:
                payload = {
                    "temperature": 22.5,
                    "humidity": 44.8,
                    "timestamp": now,
                }
                client.publish_data("environment", payload)
                last_publish = now

            # Skicka heartbeat enligt konfigurationen
            if now - last_heartbeat >= heartbeat_interval:
                client.send_heartbeat(now=now)
                last_heartbeat = now

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Avslutar klient")
    finally:
        client.stop()
        print("Klient nedstängd.")

if __name__ == "__main__":
    main()
