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
        "display_name": "CPU temperature",
        "sensor_type": "temperature",
        "data_source": {"sensor_type": "temperature", "path": "data"},
        "measures": [
            {
                "key": "temperature_c",
                "display_name": "Temperature",
                "unit": "C",
                "value_type": "number",
                "precision": 2,
            }
        ],
    }
]


def _sanitize_text_for_display(text: str) -> str:
    """Convert text to something the 8x8 ASCII font can show.

    - Svenska tecken åäöÅÄÖ transliteras till a/o/A/O.
    - Alla andra tecken utanför ASCII 32-126 ger fel.
    """

    replacements = {
        "å": "a",
        "ä": "a",
        "ö": "o",
        "Å": "A",
        "Ä": "A",
        "Ö": "O",
    }

    result_chars = []
    for char in text:
        if char in replacements:
            char = replacements[char]
        code = ord(char)
        if 32 <= code <= 126:
            result_chars.append(char)
        else:
            raise ValueError("Text contains characters not supported by the display")
    return "".join(result_chars)


CAPABILITIES = {
    "sensors": CAPPABILITIES_SENSORS,
    "commands": [
        {
            "id": "trigger_data",
            "display_name": "Trigger measurement",
            "command_type": "trigger-data",
            "topic_suffix": "commands/trigger-data",
            "parameters": [],
        },
        {
            "id": "display_text",
            "display_name": "Display text",
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
                    "display_name": "Line (0-7)",
                    "type": "integer",
                    "required": False,
                    "default": 0,
                    "min": 0,
                    "max": 7,
                },
                {
                    "name": "clear",
                    "display_name": "Clear before writing",
                    "type": "boolean",
                    "required": False,
                    "default": True,
                },
            ],
        },
        {
            "id": "clear_display",
            "display_name": "Clear display",
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
                    "display_name": "State",
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
                "title": "CPU temperature",
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
                "title": "Control",
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
    try:
        _button_a = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
        _button_b = machine.Pin(17, machine.Pin.IN, machine.Pin.PULL_UP)
    except (ValueError, AttributeError):
        _button_a = None
        _button_b = None
else:
    _temperature_sensor = None
    _light_output = None
    _button_a = None
    _button_b = None

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
        raise RuntimeError("Internal temperature sensor is not available on this platform")
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
        _log("Enabling WiFi...")
        wlan.active(True)
        wlan.connect(ssid, password)
        while not wlan.isconnected() and timeout > 0:
            _log("Waiting for WiFi... {}".format(timeout))
            time.sleep(1)
            timeout -= 1
    if not wlan.isconnected():
        raise RuntimeError("Failed to connect to WiFi")
    ip, _, _, _ = wlan.ifconfig()
    _log("WiFi connected, IP: {}".format(ip))
    return ip


def _load_config(path: str = CONFIG_FILE):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    oled = OLED_1inch3()

    try:
        oled.clear()
        oled.text_line("MQTT Pico Swarm", 0)
        oled.text_line("WiFi: connect...", 1)
        oled.show()
    except Exception:
        pass

    try:
        ip_address = connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)
    except RuntimeError as error:
        _log("WiFi connection failed: {}".format(error))
        try:
            oled.clear()
            oled.text_line("WiFi: MISS", 0)
            oled.text_line("Check SSID/pwd", 1)
            oled.show()
        except Exception:
            pass
        return

    try:
        config = _load_config()
    except OSError:
        _log("config.json is missing. Copy config.json.example and fill in MQTT details.")
        try:
            oled.clear()
            oled.text_line("config.json", 0)
            oled.text_line("missing", 1)
            oled.show()
        except Exception:
            pass
        return

    device_id = str(config.get("device_id", ""))
    mqtt_broker = ""
    try:
        mqtt_broker = str(config.get("mqtt", {}).get("broker", ""))
    except Exception:
        mqtt_broker = ""

    current_page = 0
    last_temperature_c = None  # type: ignore[assignment]
    last_hub_text = ""
    last_hub_line = 3

    def render_status_page() -> None:
        oled.clear()
        oled.text_line("Status", 0)
        if device_id:
            oled.text_line("ID: {}".format(device_id), 1)
        if last_temperature_c is not None:
            oled.text_line("CPU: {:.1f} C".format(last_temperature_c), 2)
        if ip_address:
            oled.text_line(ip_address, 3)
        oled.show()

    def render_hub_page() -> None:
        oled.clear()
        oled.text_line("Hub text", 0)
        if last_hub_text:
            line = last_hub_line
            if line < 1:
                line = 1
            if line > 7:
                line = 7
            oled.text_line(last_hub_text, line)
        oled.show()

    def render_current_page() -> None:
        if current_page == 0:
            render_status_page()
        else:
            render_hub_page()

    render_status_page()

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    def publish_temperature_reading() -> None:
        nonlocal last_temperature_c
        try:
            temperature_c = read_internal_temperature(TEMPERATURE_CALIBRATION_OFFSET)
        except Exception as error:  # pragma: no cover
            _log("Failed to read CPU temperature: {}".format(error))
            return

        temperature_c = round(temperature_c, 2)
        last_temperature_c = temperature_c
        _log("Measuring internal temperature: {:.2f} °C".format(temperature_c))
        payload = {
            "temperature_c": temperature_c,
            "timestamp": current_timestamp(),
            "sensor": "pico_w_cpu",
        }
        try:
            client.publish_data("temperature", payload)
            client.publish_log(
                level="debug",
                logger="waveshare_oled.main",
                message="CPU temperature published",
                context={"temperature_c": temperature_c},
            )
        except ConnectionError as error:
            _log("MQTT publish failed: {}".format(error))
            try:
                oled.text_line("MQTT: MISS", 4)
                oled.show()
            except Exception:
                pass
            return
        if current_page == 0:
            try:
                render_status_page()
            except Exception:
                pass

    @client.on_command(COMMAND_TYPE_ACTION)
    def handle_action(command):  # type: ignore[no-untyped-def]
        nonlocal last_hub_text, last_hub_line
        if not isinstance(command, dict):
            _log("Ignoring action command without JSON payload: {}".format(command))
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
                    raise ValueError("Parameter 'text' is missing")
                text_str = str(text)
                if not text_str:
                    raise ValueError("Text must not be empty")
                if len(text_str) > MAX_TEXT_LENGTH:
                    raise ValueError(
                        "Text is too long (max {} characters)".format(MAX_TEXT_LENGTH)
                    )
                text_str = _sanitize_text_for_display(text_str)
                line = params.get("line", 0)
                try:
                    line = int(line)
                except (TypeError, ValueError):
                    raise ValueError("Line must be an integer between 0 and 7")
                if line < 0 or line > 7:
                    raise ValueError("Invalid line: {} (allowed 0-7)".format(line))
                last_hub_text = text_str
                last_hub_line = line
                if current_page == 1:
                    render_hub_page()
                handled = True
            elif action_type == "clear_display":
                oled.clear()
                handled = True
            else:
                status = "failed"
                message = "Unknown action type: {}".format(action_type or "<missing>")
        except Exception as error:  # pragma: no cover
            status = "failed"
            message = str(error)

        if not command_id:
            if status == "failed":
                _log(
                    "Action command failed without commandId: {}".format(
                        message or command
                    )
                )
            return handled

        if status == "success" and not message:
            message = "Display updated" if handled else "No change performed"

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
        _log("Trigger-data command received")
        publish_temperature_reading()
        if command_id:
            client.acknowledge_command(
                command_id,
                "success",
                message="CPU temperature published",
            )

    @client.on_command(COMMAND_TYPE_LIGHT)
    def handle_light(command):  # type: ignore[no-untyped-def]
        if not isinstance(command, dict):
            _log("Ignoring light command without JSON payload: {}".format(command))
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
                    "Light command failed without commandId: {}".format(
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
            message = "LED updated"

        client.acknowledge_command(
            command_id,
            status,
            message=message,
            result=result,
        )
        return handled

    try:
        try:
            line = "MQTT: connect..."
            if mqtt_broker:
                line = "MQTT: {}".format(mqtt_broker)
            oled.text_line(line, 4)
            oled.show()
        except Exception:
            pass

        try:
            client.connect()
        except ConnectionError as error:
            _log("MQTT connection failed: {}".format(error))
            try:
                oled.text_line("MQTT: MISS", 4)
                oled.show()
            except Exception:
                pass
            return

        try:
            oled.text_line("MQTT: OK", 4)
            oled.show()
        except Exception:
            pass

        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Waveshare OLED HAT online",
        )
        client.publish_log(
            level="info",
            logger="waveshare_oled.main",
            message="OLED client started and connected",
        )
        client.publish_capabilities(CAPABILITIES)

        _log("Starting main loop. Press Ctrl+C to exit.")
        heartbeat_interval = client.get_config().get("heartbeat_interval", 60)
        last_heartbeat = time.time()
        last_publish = 0.0
        button_a_last = _button_a.value() if _button_a is not None else 1
        button_b_last = _button_b.value() if _button_b is not None else 1
        connection = client._connection_manager  # pylint: disable=protected-access
        if connection is None:
            raise RuntimeError("MQTT connection manager is missing")

        mqtt_connected = True

        while True:
            now = time.time()

            try:
                connection.ensure_connected()
                connection.process_incoming()
            except ConnectionError as error:
                _log("MQTT keepalive failed: {}".format(error))
                try:
                    oled.text_line("MQTT: MISS", 4)
                    oled.show()
                except Exception:
                    pass
                mqtt_connected = False
            else:
                if not mqtt_connected:
                    try:
                        oled.text_line("MQTT: OK", 4)
                        oled.show()
                    except Exception:
                        pass
                mqtt_connected = True

            # Knapp A: växla sida (status <-> hub-text)
            if _button_a is not None:
                try:
                    value = _button_a.value()
                except Exception:
                    value = 1
                if value == 0 and button_a_last == 1:
                    current_page = 1 - current_page
                    render_current_page()
                button_a_last = value

            # Knapp B: trigga manuell CPU-mätning och skicka event
            if _button_b is not None:
                try:
                    value = _button_b.value()
                except Exception:
                    value = 1
                if value == 0 and button_b_last == 1:
                    _log("Button B: manual CPU measurement")
                    publish_temperature_reading()
                    try:
                        client.publish_event(
                            constants.EVENT_TYPE_INFO,
                            "button_trigger",
                            "Manual CPU temperature measurement via button B",
                            severity=constants.SEVERITY_INFO,
                        )
                    except Exception:
                        pass
                button_b_last = value

            if mqtt_connected and now - last_publish >= PUBLISH_INTERVAL:
                publish_temperature_reading()
                last_publish = now

            if mqtt_connected and now - last_heartbeat >= heartbeat_interval:
                client.send_heartbeat(now=now)
                last_heartbeat = now

            time.sleep(0.1)
    except KeyboardInterrupt:
        _log("Stopping client")
    finally:
        client.stop()
        _log("Client shut down.")


if __name__ == "__main__":
    main()

