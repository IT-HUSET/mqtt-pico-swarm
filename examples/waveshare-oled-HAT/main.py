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
from oled_profile import CAPABILITIES, MAX_TEXT_LENGTH, sanitize_text_for_display
from oled_ui import OledUI


CONFIG_FILE = "config.json"
NETWORK_SSID = "ITH"
NETWORK_PASSWORD = "xxx"
PUBLISH_INTERVAL = 60
TEMPERATURE_CALIBRATION_OFFSET = 0.0

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
    ui = OledUI(oled)

    try:
        ui.show_boot_wifi_connecting()
    except Exception:
        pass

    try:
        ip_address = connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)
    except RuntimeError as error:
        _log("WiFi connection failed: {}".format(error))
        try:
            ui.show_wifi_failed()
        except Exception:
            pass
        return

    try:
        config = _load_config()
    except OSError:
        _log("config.json is missing. Copy config.json.example and fill in MQTT details.")
        try:
            ui.show_config_missing()
        except Exception:
            pass
        return

    device_id = str(config.get("device_id", ""))
    mqtt_broker = ""
    try:
        mqtt_broker = str(config.get("mqtt", {}).get("broker", ""))
    except Exception:
        mqtt_broker = ""

    ui.set_device_id(device_id)
    ui.set_ip_address(ip_address)
    ui.set_mqtt_broker(mqtt_broker)
    ui.render_status_page()

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    def publish_temperature_reading() -> None:
        try:
            temperature_c = read_internal_temperature(TEMPERATURE_CALIBRATION_OFFSET)
        except Exception as error:  # pragma: no cover
            _log("Failed to read CPU temperature: {}".format(error))
            return

        temperature_c = round(temperature_c, 2)
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
                ui.show_mqtt_miss()
            except Exception:
                pass
            return
        try:
            ui.set_temperature(temperature_c)
        except Exception:
            pass

    @client.on_command(COMMAND_TYPE_ACTION)
    def handle_action(command):  # type: ignore[no-untyped-def]
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
                text_str = sanitize_text_for_display(text_str)
                line = params.get("line", 0)
                try:
                    line = int(line)
                except (TypeError, ValueError):
                    raise ValueError("Line must be an integer between 0 and 7")
                if line < 0 or line > 7:
                    raise ValueError("Invalid line: {} (allowed 0-7)".format(line))
                ui.set_hub_text(text_str, line)
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
            ui.show_mqtt_connecting()
        except Exception:
            pass

        try:
            client.connect()
        except ConnectionError as error:
            _log("MQTT connection failed: {}".format(error))
            try:
                ui.show_mqtt_miss()
            except Exception:
                pass
            return

        try:
            ui.show_mqtt_ok()
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
                try:
                    connection.ensure_connected()
                    connection.process_incoming()
                except ConnectionError as error:
                    _log("MQTT keepalive failed: {}".format(error))
                    try:
                        ui.show_mqtt_miss()
                    except Exception:
                        pass
                    mqtt_connected = False
                else:
                    if not mqtt_connected:
                        try:
                            ui.show_mqtt_ok()
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
                        ui.toggle_page()
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
                raise
            except Exception as error:
                _log("Unhandled error in main loop: {}".format(error))
                try:
                    ui.show_mqtt_miss()
                except Exception:
                    pass
                time.sleep(1)
    except KeyboardInterrupt:
        _log("Stopping client")
    finally:
        client.stop()
        _log("Client shut down.")


if __name__ == "__main__":
    main()

