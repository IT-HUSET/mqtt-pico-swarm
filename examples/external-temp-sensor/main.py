import json
import time

try:
    import network  # type: ignore
except ImportError:  # pragma: no cover
    network = None

try:
    import machine  # type: ignore
except ImportError:  # pragma: no cover
    machine = None

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.client import PicoSwarmClient
from mqtt_pico_swarm.constants import COMMAND_TYPE_LIGHT, COMMAND_TYPE_TRIGGER_DATA
from mqtt_pico_swarm.errors import ConnectionError
from mqtt_pico_swarm.utils import current_timestamp, log

from DS18B20 import DS18B20Sensor


CONFIG_FILE = "config.json"
NETWORK_SSID = "ITH"
NETWORK_PASSWORD = "xxx"
PUBLISH_INTERVAL = 60
DS18B20_PIN = 5

CAPABILITIES = {
    "sensors": [
        {
            "id": "external_temp",
            "display_name": "Extern temperatur",
            "sensor_type": "temperature",
            "data_source": {"sensor_type": "temperature", "path": "data"},
            "measures": [
                {
                    "key": "temperature_c",
                    "display_name": "Temperatur",
                    "unit": "C",
                    "value_type": "number",
                    "precision": 2,
                }
            ],
        }
    ],
    "commands": [
        {
            "id": "trigger_data",
            "display_name": "Trigga mätning nu",
            "command_type": "trigger-data",
            "topic_suffix": "commands/trigger-data",
            "parameters": [],
        },
        {
            "id": "light",
            "display_name": "Onboard LED",
            "command_type": "light",
            "topic_suffix": "commands/light",
            "parameters": [
                {
                    "name": "state",
                    "display_name": "Tillstånd",
                    "type": "enum",
                    "values": ["on", "off", "toggle"],
                    "required": True,
                    "default": "on",
                }
            ],
        },
    ],
    "ui_hints": {
        "layout": [
            {
                "type": "sensor_panel",
                "sensor_id": "external_temp",
                "title": "Extern temperatur",
                "primary_measure": "temperature_c",
                "chart": {
                    "enabled": True,
                    "window_minutes": 60,
                },
            },
            {
                "type": "commands_panel",
                "title": "Styrning",
                "commands": ["trigger_data", "light"],
            },
        ]
    },
}

if machine is not None:
    try:
        _light_output = machine.Pin("LED", machine.Pin.OUT)
    except (ValueError, AttributeError):
        try:
            _light_output = machine.Pin(25, machine.Pin.OUT)
        except (ValueError, AttributeError):
            _light_output = None
else:
    _light_output = None

try:
    _current_light_state = bool(_light_output.value()) if _light_output is not None else False
except Exception:  # pragma: no cover
    _current_light_state = False


def _log(message):
    log(True, message, prefix="[ExternalTemp]")


def _write_light_state(enabled):
    if _light_output is None:
        raise ValueError("Device has no controllable LED")
    try:
        _light_output.value(1 if enabled else 0)
    except Exception as error:
        raise ValueError("Failed to drive LED: {}".format(error)) from error
    global _current_light_state
    _current_light_state = bool(enabled)


def _apply_light_action(action, state):
    if _light_output is None:
        raise ValueError("Device has no controllable LED")

    if action == "toggle" or (action == "set" and state == "toggle"):
        _write_light_state(not _current_light_state)
        return True

    if action == "set":
        if state not in ("on", "off"):
            return False
        _write_light_state(state == "on")
        return True

    raise ValueError("Unknown action: {}".format(action))


def connect_wifi(ssid, password, timeout=20):
    if network is None:
        raise RuntimeError("network module is unavailable on this platform")

    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        _log("Aktiverar WiFi...")
        wlan.active(True)
        wlan.connect(ssid, password)
        while not wlan.isconnected() and timeout > 0:
            _log("Väntar på WiFi... {}".format(timeout))
            time.sleep(1)
            timeout -= 1
    if not wlan.isconnected():
        raise RuntimeError("Kunde inte ansluta till WiFi")
    ip, _, _, _ = wlan.ifconfig()
    _log("WiFi ansluten, IP: {}".format(ip))
    return ip


def _load_config(path=CONFIG_FILE):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)

    try:
        _ = _load_config()
    except OSError:
        _log("config.json saknas. Kopiera config.json.example och fyll i MQTT-detaljer.")
        return

    sensor = DS18B20Sensor(DS18B20_PIN)

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    def publish_temperature_reading():
        try:
            temperature_c = sensor.read_temperature_c()
        except Exception as error:  # pragma: no cover
            _log("Misslyckades att läsa extern temperatur: {}".format(error))
            return

        temperature_c = round(temperature_c, 2)
        _log("Mäter extern temperatur: {:.2f} °C".format(temperature_c))
        payload = {
            "temperature_c": temperature_c,
            "timestamp": current_timestamp(),
            "sensor": "external_ds18b20",
        }
        try:
            client.publish_data("temperature", payload)
            client.publish_log(
                level="debug",
                logger="external_temp.main",
                message="Temperaturmätning utförd",
                context={"temperature_c": temperature_c},
            )
        except ConnectionError as error:
            _log("MQTT publish failed: {}".format(error))
            return
        except Exception as error:  # pragma: no cover
            _log("Unexpected error during publish: {}".format(error))
            return

    @client.on_command(COMMAND_TYPE_LIGHT)
    def handle_light(command):
        if not isinstance(command, dict):
            _log("Ignorerar light-kommando utan JSON-payload: {}".format(command))
            return False

        command_id = command.get("commandId") or command.get("command_id")
        raw_action = command.get("action")
        state = str(command.get("state") or "").lower()

        if raw_action is not None:
            action = str(raw_action).lower()
        else:
            if state == "toggle":
                action = "toggle"
            else:
                action = "set"

        status = "success"
        message = ""
        handled = False

        try:
            handled = _apply_light_action(action, state)
        except ValueError as error:
            status = "failed"
            message = str(error)
        else:
            if not handled:
                status = "failed"
                message = "Unsupported state value" if action == "set" else "Toggle failed"

        if not command_id:
            if status == "failed":
                _log(
                    "Light-kommando misslyckades utan commandId: {}".format(
                        message or command
                    )
                )
            return handled

        result = {"current_state": "on" if _current_light_state else "off"}
        if "brightness" in command:
            result["current_brightness"] = command.get("brightness")
        if "color" in command:
            result["current_color"] = command.get("color")

        if status == "success" and not message:
            message = "LED uppdaterad"

        client.acknowledge_command(
            command_id,
            status,
            message=message,
            result=result,
        )
        return handled

    @client.on_command(COMMAND_TYPE_TRIGGER_DATA)
    def handle_trigger_data(command):
        command_id = None
        if isinstance(command, dict):
            command_id = command.get("command_id") or command.get("commandId")
        _log("Trigger-data kommando mottaget")
        publish_temperature_reading()
        if command_id:
            client.acknowledge_command(
                command_id,
                "success",
                message="Temperaturmätning publicerad",
            )

    try:
        client.connect()
        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Extern temperatursensor online",
        )
        client.publish_log(
            level="info",
            logger="external_temp.main",
            message="Klient uppstartad och ansluten",
        )
        client.publish_capabilities(CAPABILITIES)

        _log("Startar huvudloopen. Tryck Ctrl+C för att avsluta.")
        last_publish = 0
        heartbeat_interval = client.get_config().get("heartbeat_interval", 60)
        last_heartbeat = time.time()
        connection = client._connection_manager  # pylint: disable=protected-access
        if connection is None:
            raise RuntimeError("MQTT connection manager saknas")

        mqtt_connected = True

        while True:
            now = time.time()

            try:
                try:
                    connection.ensure_connected()
                    connection.process_incoming()
                except ConnectionError as error:
                    _log("MQTT keepalive failed: {}".format(error))
                    mqtt_connected = False
                else:
                    mqtt_connected = True

                if mqtt_connected and now - last_publish >= PUBLISH_INTERVAL:
                    publish_temperature_reading()
                    last_publish = now

                if mqtt_connected and now - last_heartbeat >= heartbeat_interval:
                    client.send_heartbeat(now=now)
                    last_heartbeat = now

                time.sleep(0.1)
            except KeyboardInterrupt:
                raise
            except Exception as error:  # pragma: no cover
                _log("Unhandled error in main loop: {}".format(error))
                time.sleep(1)
    except KeyboardInterrupt:
        _log("Avslutar klient")
    finally:
        client.stop()
        _log("Klient nedstängd.")


if __name__ == "__main__":
    main()
