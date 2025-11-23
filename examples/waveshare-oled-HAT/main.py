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
from mqtt_pico_swarm.constants import COMMAND_TYPE_ACTION, COMMAND_TYPE_LIGHT, COMMAND_TYPE_TRIGGER_DATA
from mqtt_pico_swarm.errors import ConnectionError
from mqtt_pico_swarm.utils import current_timestamp, log

from oled_driver import OLED_1inch3


CONFIG_FILE = "config.json"
NETWORK_SSID = "kumliens"
NETWORK_PASSWORD = "xxx"
PUBLISH_INTERVAL = 60
TEMPERATURE_CALIBRATION_OFFSET = 0.0
MAX_TEXT_LENGTH = 16


CAPPABILITIES_SENSORS = [
    {
        "id": "cpu_temp",
        "display_name": "CPU-temperatur",
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
]


CAPABILITIES = {
    "sensors": CAPPABILITIES_SENSORS,
    "commands": [
        {
            "id": "trigger_data",
            "display_name": "Trigga mätning nu",
            "command_type": "trigger-data",
            "topic_suffix": "commands/trigger-data",
            "parameters": [],
        },
        {
            "id": "display_text",
            "display_name": "Visa text",
            "command_type": "action",
            "topic_suffix": "commands/action",
            "parameters": [
                {
                    "name": "text",
                    "display_name": "Text",
                    "type": "string",
                    "required": True,
                },
                {
                    "name": "line",
                    "display_name": "Rad (0-7)",
                    "type": "integer",
                    "required": False,
                    "default": 0,
                    "min": 0,
                    "max": 7,
                },
                {
                    "name": "clear",
                    "display_name": "Rensa före skrivning",
                    "type": "boolean",
                    "required": False,
                    "default": True,
                },
            ],
        },
        {
            "id": "clear_display",
            "display_name": "Rensa display",
            "command_type": "action",
            "topic_suffix": "commands/action",
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
                "sensor_id": "cpu_temp",
                "title": "CPU-temperatur",
                "primary_measure": "temperature_c",
                "chart": {
                    "enabled": True,
                    "window_minutes": 60,
                },
            },
            {
                "type": "commands_panel",
                "title": "Display",
                "commands": ["display_text", "clear_display"],
            },
            {
                "type": "commands_panel",
                "title": "Styrning",
                "commands": ["light"],
            },
        ]
    },
}

if machine is not None:
    try:
        _temperature_sensor = machine.ADC(4)
    except (ValueError, AttributeError):
        _temperature_sensor = None
    try:
        _light_output = machine.Pin("LED", machine.Pin.OUT)
    except (ValueError, AttributeError):
        try:
            _light_output = machine.Pin(25, machine.Pin.OUT)
        except (ValueError, AttributeError):
            _light_output = None
else:
    _temperature_sensor = None
    _light_output = None

try:
    _current_light_state = bool(_light_output.value()) if _light_output is not None else False
except Exception:  # pragma: no cover
    _current_light_state = False


def _log(message: str) -> None:
    log(True, message, prefix="[OLEDExample]")


def _write_light_state(enabled: bool) -> None:
    if _light_output is None:
        raise ValueError("Device has no controllable LED")
    try:
        _light_output.value(1 if enabled else 0)
    except Exception as error:
        raise ValueError("Failed to drive LED: {}".format(error)) from error
    global _current_light_state
    _current_light_state = bool(enabled)


def read_internal_temperature(offset: float = 0.0) -> float:
    if _temperature_sensor is None:
        raise RuntimeError("Intern temperaturgivare är inte tillgänglig på denna plattform")
    conversion_factor = 3.3 / 65535
    raw = _temperature_sensor.read_u16()
    voltage = raw * conversion_factor
    temperature_c = 27 - (voltage - 0.706) / 0.001721
    return temperature_c + offset


def _apply_light_action(action: str, state: str) -> bool:
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


def connect_wifi(ssid: str, password: str, timeout: int = 20) -> str:
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


def _load_config(path: str = CONFIG_FILE):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)

    try:
        _ = _load_config()
    except OSError:
        _log("config.json saknas. Kopiera config.json.example och fyll i MQTT-detaljer.")
        return

    oled = OLED_1inch3()
    oled.clear()
    oled.text_line("MQTT Pico Swarm", 0)
    oled.text_line("OLED HAT online", 1)
    oled.show()

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    def publish_temperature_reading() -> None:
        try:
            temperature_c = read_internal_temperature(TEMPERATURE_CALIBRATION_OFFSET)
        except Exception as error:  # pragma: no cover
            _log("Misslyckades att läsa CPU-temperatur: {}".format(error))
            return

        temperature_c = round(temperature_c, 2)
        _log("Mäter intern temperatur: {:.2f} °C".format(temperature_c))
        payload = {
            "temperature_c": temperature_c,
            "timestamp": current_timestamp(),
            "sensor": "pico_w_cpu",
        }
        client.publish_data("temperature", payload)
        client.publish_log(
            level="debug",
            logger="waveshare_oled.main",
            message="CPU-temperatur publicerad",
            context={"temperature_c": temperature_c},
        )
        try:
            oled.text_line("CPU: {:.1f} C".format(temperature_c), 2)
            oled.show()
        except Exception:
            pass

    @client.on_command(COMMAND_TYPE_ACTION)
    def handle_action(command):  # type: ignore[no-untyped-def]
        if not isinstance(command, dict):
            _log("Ignorerar action-kommando utan JSON-payload: {}".format(command))
            return False

        command_id = command.get("command_id") or command.get("commandId")
        action_type = str(command.get("type") or "")

        params = command.get("payload")
        if not isinstance(params, dict):
            params = command

        status = "success"
        message = ""
        handled = False

        try:
            if action_type == "display_text":
                text = params.get("text")
                if text is None:
                    raise ValueError("Parameter 'text' saknas")
                text_str = str(text)
                if not text_str:
                    raise ValueError("Text får inte vara tom")
                if len(text_str) > MAX_TEXT_LENGTH:
                    raise ValueError(
                        "Text är för lång (max {} tecken)".format(MAX_TEXT_LENGTH)
                    )
                line = params.get("line", 0)
                try:
                    line = int(line)
                except (TypeError, ValueError):
                    raise ValueError("Rad måste vara ett heltal mellan 0 och 7")
                if line < 0 or line > 7:
                    raise ValueError("Ogiltig rad: {} (tillåtet 0-7)".format(line))
                clear_before = params.get("clear", True)
                clear_flag = bool(clear_before)
                oled.text_line(text_str, line, clear_line=clear_flag)
                oled.show()
                handled = True
            elif action_type == "clear_display":
                oled.clear()
                handled = True
            else:
                status = "failed"
                message = "Okänd action-typ: {}".format(action_type or "<saknas>")
        except Exception as error:  # pragma: no cover
            status = "failed"
            message = str(error)

        if not command_id:
            if status == "failed":
                _log(
                    "Action-kommando misslyckades utan commandId: {}".format(
                        message or command
                    )
                )
            return handled

        if status == "success" and not message:
            message = "Display uppdaterad" if handled else "Ingen ändring utförd"

        result = {"handled": handled, "action_type": action_type}

        client.acknowledge_command(
            command_id,
            status,
            message=message,
            result=result,
        )
        return handled

    @client.on_command(COMMAND_TYPE_TRIGGER_DATA)
    def handle_trigger_data(command):  # type: ignore[no-untyped-def]
        command_id = None
        if isinstance(command, dict):
            command_id = command.get("command_id") or command.get("commandId")
        _log("Trigger-data kommando mottaget")
        publish_temperature_reading()
        if command_id:
            client.acknowledge_command(
                command_id,
                "success",
                message="CPU-temperatur publicerad",
            )

    @client.on_command(COMMAND_TYPE_LIGHT)
    def handle_light(command):  # type: ignore[no-untyped-def]
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

    try:
        client.connect()
        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Waveshare OLED HAT online",
        )
        client.publish_log(
            level="info",
            logger="waveshare_oled.main",
            message="OLED-klient uppstartad och ansluten",
        )
        client.publish_capabilities(CAPABILITIES)

        _log("Startar huvudloopen. Tryck Ctrl+C för att avsluta.")
        heartbeat_interval = client.get_config().get("heartbeat_interval", 60)
        last_heartbeat = time.time()
        last_publish = 0.0
        connection = client._connection_manager  # pylint: disable=protected-access
        if connection is None:
            raise RuntimeError("MQTT connection manager saknas")

        while True:
            now = time.time()

            try:
                connection.ensure_connected()
                connection.process_incoming()
            except ConnectionError:
                continue

            if now - last_publish >= PUBLISH_INTERVAL:
                publish_temperature_reading()
                last_publish = now

            if now - last_heartbeat >= heartbeat_interval:
                client.send_heartbeat(now=now)
                last_heartbeat = now

            time.sleep(0.1)
    except KeyboardInterrupt:
        _log("Avslutar klient")
    finally:
        client.stop()
        _log("Klient nedstängd.")


if __name__ == "__main__":
    main()

