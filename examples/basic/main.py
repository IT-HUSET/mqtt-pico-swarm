import json
import time

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.client import PicoSwarmClient
from mqtt_pico_swarm.constants import COMMAND_TYPE_ACTION

CONFIG_FILE = "config.json"
PUBLISH_INTERVAL = 30


def _load_config():
    with open(CONFIG_FILE, "r") as handle:
        return json.load(handle)


def main():
    try:
        config = _load_config()
    except OSError:
        print("config.json saknas. Kopiera config.json.example och försök igen.")
        return

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    @client.on_command(COMMAND_TYPE_ACTION)
    def _handle_action(command):
        print("Mottog action-kommando:")
        print(command)
        command_id = command.get("command_id", "")
        if command_id:
            client.acknowledge_command(command_id, "success", message="Utfört")

    try:
        client.connect()
        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Enheten är online",
        )

        last_publish = 0
        while True:
            now = time.time()
            if now - last_publish >= PUBLISH_INTERVAL:
                payload = {
                    "temperature": 22,
                    "humidity": 45,
                    "timestamp": now,
                }
                client.publish_data("environment", payload)
                last_publish = now

            # Hantera inkommande meddelanden och hjärtslag i huvudloopen.
            try:
                client.start()
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        print("Stoppar klient")
    finally:
        client.stop()


if __name__ == "__main__":
    main()
