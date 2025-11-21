"""MQTT-enabled example for Adafruit seesaw soil moisture sensor on a Pico W."""

import json
import time

try:  # pragma: no cover - network finns inte vid lokal test
    import network  # type: ignore
except ImportError:  # pragma: no cover
    network = None

try:  # pragma: no cover - machine-modulen saknas i CPython
    from machine import I2C, Pin  # type: ignore
except ImportError:  # pragma: no cover
    I2C = None
    Pin = None

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.client import PicoSwarmClient
from mqtt_pico_swarm.constants import COMMAND_TYPE_TRIGGER_DATA
from mqtt_pico_swarm.errors import ConnectionError
from mqtt_pico_swarm.utils import current_timestamp, log

from soil_sensor import StemmaSoilSensor


def const(x):
    return x


if hasattr(time, "sleep_ms"):
    sleep_ms = time.sleep_ms  # type: ignore[attr-defined]
else:
    def sleep_ms(ms: int) -> None:
        time.sleep(ms / 1000.0)


SENSOR_ADDRESS = const(0x36)
I2C_BUS_ID = 0
I2C_SCL_PIN = 1
I2C_SDA_PIN = 0
I2C_FREQUENCY = 100000

CONFIG_FILE = "config.json"
NETWORK_SSID = "ITH"
NETWORK_PASSWORD = "xxx"
PUBLISH_INTERVAL = 60  # seconds

# Replace these with your measured dry/wet reference points to enable calibration.
CALIBRATION_DRY = 325
CALIBRATION_WET = 1016


def _log(message):
    log(True, message, prefix="[SoilExample]")


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


def create_default_sensor():
    if I2C is None or Pin is None:
        raise RuntimeError("machine.I2C är inte tillgänglig på denna plattform")
    i2c = I2C(I2C_BUS_ID, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQUENCY)
    return StemmaSoilSensor(i2c, addr=SENSOR_ADDRESS)


def calibrate_moisture(raw_value, dry_point=CALIBRATION_DRY, wet_point=CALIBRATION_WET):
    if dry_point is None or wet_point is None:
        return None
    if wet_point <= dry_point:
        return None

    clamped = min(max(raw_value, dry_point), wet_point)
    span = wet_point - dry_point
    percentage = (clamped - dry_point) * 100.0 / span
    return percentage


def read_soil_sample(sensor):
    moisture = sensor.get_moisture()
    temperature_c = sensor.get_temp()
    percent = calibrate_moisture(moisture)
    return moisture, temperature_c, percent


def publish_soil_sample(client, moisture, temperature_c, percent):
    payload = {
        "moisture_raw": moisture,
        "temperature_c": round(temperature_c, 2),
        "timestamp": current_timestamp(),
    }
    if percent is not None:
        payload["moisture_percent"] = round(percent, 1)
    client.publish_data("soil", payload, unit="raw-moisture")


def main():
    connect_wifi(NETWORK_SSID, NETWORK_PASSWORD)

    try:
        _ = _load_config()
    except OSError:
        _log("config.json saknas. Kopiera config.json.example och fyll i MQTT-detaljer.")
        return

    sensor = create_default_sensor()
    chip_id = sensor.chip_id()
    _log("Seesaw chip id: 0x{:02X}".format(chip_id))

    client = PicoSwarmClient(config_file=CONFIG_FILE, debug=True)

    def publish_with_logging():
        moisture, temperature_c, percent = read_soil_sample(sensor)
        _log(
            "Mätning - fukt: {} / temp: {:.2f}°C{}".format(
                moisture,
                temperature_c,
                " / {}%".format(round(percent, 1)) if percent is not None else "",
            )
        )
        publish_soil_sample(client, moisture, temperature_c, percent)

    @client.on_command(COMMAND_TYPE_TRIGGER_DATA)
    def handle_trigger_data(command):
        command_id = None
        if isinstance(command, dict):
            command_id = command.get("command_id") or command.get("commandId")
        _log("Trigger-data kommando mottaget")
        publish_with_logging()
        if command_id:
            client.acknowledge_command(command_id, "success", message="Soil sample publicerad")

    try:
        client.connect()
        client.publish_event(
            constants.EVENT_TYPE_INFO,
            "boot",
            "Soil sensor online",
        )

        _log("Startar huvudloopen. Tryck Ctrl+C för att avsluta.")
        last_publish = 0
        heartbeat_interval = client.get_config().get("heartbeat_interval", 60)
        last_heartbeat = time.time()
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
                publish_with_logging()
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