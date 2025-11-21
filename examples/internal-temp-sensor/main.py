import json
import time

import network

try:
    import machine
except ImportError:  # pragma: no cover - maskinmodul saknas vid lokal test
    machine = None

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.client import PicoSwarmClient
from mqtt_pico_swarm.constants import (
    COMMAND_TYPE_ACTION,
    COMMAND_TYPE_LIGHT,
    COMMAND_TYPE_TRIGGER_DATA,
)
from mqtt_pico_swarm.errors import ConnectionError
from mqtt_pico_swarm.utils import current_timestamp, log

CONFIG_FILE = "config.json"
NETWORK_SSID = "ITH"
NETWORK_PASSWORD = "xxx"
PUBLISH_INTERVAL = 60
TEMPERATURE_CALIBRATION_OFFSET = 0.0  # Justera vid behov för att kalibrera mot extern termometer

if machine is not None:
    _temperature_sensor = machine.ADC(4)
    try:
        _light_output = machine.Pin("LED", machine.Pin.OUT)
    except (ValueError, AttributeError):  # pragma: no cover - fallback för kort utan "LED"
        try:
            _light_output = machine.Pin(25, machine.Pin.OUT)
        except (ValueError, AttributeError):
            _light_output = None
else:
    _temperature_sensor = None
    _light_output = None

try:
    _current_light_state = bool(_light_output.value()) if _light_output is not None else False
except Exception:  # pragma: no cover - vissa implementationer saknar value()
    _current_light_state = False


def _log(message):
    """Write log messages with a consistent prefix so they stand out on serial output."""
    log(True, message, prefix="[Example]")


def _write_light_state(enabled):
    """Toggle the onboard LED pin and update our cached state."""
    if _light_output is None:
        raise ValueError("Device has no controllable LED")
    try:
        _light_output.value(1 if enabled else 0)
    except Exception as error:
        raise ValueError("Failed to drive LED: {}".format(error)) from error
    global _current_light_state
    _current_light_state = bool(enabled)


def _apply_light_action(action, state):
    """Apply the requested LED action ('set' or 'toggle') to the hardware."""
    if _light_output is None:
        raise ValueError("Device has no controllable LED")

    if action == "toggle":
        _write_light_state(not _current_light_state)
        return True

    if action == "set":
        if state not in ("on", "off"):
            return False
        _write_light_state(state == "on")
        return True

    raise ValueError("Unknown action: {}".format(action))


def connect_wifi(ssid, password, timeout=20):
    """Bring up WiFi STA mode, retrying for a short while until connected."""
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


def _load_config():
    """Read the Pico's config.json so the client knows how to reach the hub."""
    with open(CONFIG_FILE, "r") as handle:
        return json.load(handle)


def read_internal_temperature(offset=0.0):
    """Measure CPU temperature via the internal ADC and apply an optional offset."""
    if _temperature_sensor is None:
        raise RuntimeError("Intern temperaturgivare är inte tillgänglig på denna plattform")
    conversion_factor = 3.3 / 65535
    raw = _temperature_sensor.read_u16()
    voltage = raw * conversion_factor
    # Formel från Raspberry Pi-dokumentationen för RP2040
    temperature_c = 27 - (voltage - 0.706) / 0.001721
    return temperature_c + offset


def main():
    """Entry point for the demo: connect, register handlers, and run the MQTT loop."""
    connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)

    try:
        _ = _load_config()
    except OSError:
        _log("config.json saknas. Kopiera config.json.example och fyll i MQTT-detaljer.")
        return

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    def publish_temperature_reading():
        """Grab a temperature sample and send it to the hub as sensor data."""
        temperature_c = read_internal_temperature(TEMPERATURE_CALIBRATION_OFFSET)
        temperature_c = round(temperature_c, 2)
        _log("Mäter intern temperatur: {:.2f} °C".format(temperature_c))
        payload = {
            "temperature_c": temperature_c,
            "timestamp": current_timestamp(),
            "sensor": "pico_w_cpu",
        }
        client.publish_data("temperature", payload)
        try:
            now_rtc = time.localtime()
            _log(
                "Aktuell RTC-tid: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    now_rtc[0], now_rtc[1], now_rtc[2], now_rtc[3], now_rtc[4], now_rtc[5]
                )
            )
        except Exception:
            pass

    @client.on_command(COMMAND_TYPE_ACTION)
    def handle_action(command):
        """Ack simple action commands so the hub knows the device is alive."""
        _log("Mottog action-kommando: {}".format(command))
        command_id = command.get("command_id")
        if command_id:
            client.acknowledge_command(
                command_id,
                "success",
                message="Åtgärd utförd på enhet",
            )

    @client.on_command(COMMAND_TYPE_LIGHT)
    def handle_light(command):
        """Parse incoming light command JSON and update the LED state."""
        if not isinstance(command, dict):
            _log("Ignorerar light-kommando utan JSON-payload: {}".format(command))
            return False

        command_id = command.get("commandId") or command.get("command_id")
        action = str(command.get("action") or "set").lower()
        state = str(command.get("state") or "").lower()

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
                _log("Light-kommando misslyckades utan commandId: {}".format(message or command))
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
        """Allow the hub to request an immediate temperature publish."""
        command_id = None
        if isinstance(command, dict):
            command_id = command.get("command_id")
        if command_id:
            _log("Trigger-data kommando mottaget: {}".format(command_id))
        else:
            _log("Trigger-data kommando mottaget")
        publish_temperature_reading()

    try:
        client.connect()
        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Enheten är online",
        )

        _log("Startar huvudloopen. Tryck Ctrl+C för att avsluta.")
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
                publish_temperature_reading()
                last_publish = now

            # Skicka heartbeat enligt konfigurationen
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
