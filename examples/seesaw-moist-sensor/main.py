"""Example reading an Adafruit seesaw soil moisture sensor on a Pico board."""

import time
from machine import I2C, Pin

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

# Replace these with your measured dry/wet reference points to enable calibration.
CALIBRATION_DRY = 325
CALIBRATION_WET = 1016


def create_default_sensor():
    """Instantiate the moisture sensor using the default Pico pins."""
    i2c = I2C(I2C_BUS_ID, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQUENCY)
    return StemmaSoilSensor(i2c, addr=SENSOR_ADDRESS)


def calibrate_moisture(raw_value, dry_point=CALIBRATION_DRY, wet_point=CALIBRATION_WET):
    """Return a percent value if calibration points are defined, otherwise None."""
    if dry_point is None or wet_point is None:
        return None
    if wet_point <= dry_point:
        return None

    clamped = min(max(raw_value, dry_point), wet_point)
    span = wet_point - dry_point
    percentage = (clamped - dry_point) * 100.0 / span
    return percentage


def format_sample(moisture, temperature_c):
    """Format the raw sensor readings for console output."""
    parts = ["Moisture: {}".format(moisture), "Temp: {:.2f} C".format(temperature_c)]
    percent = calibrate_moisture(moisture)
    if percent is not None:
        parts.append("Moisture%: {:.1f}".format(percent))
    return " | ".join(parts)


def main(sample_interval_ms=2000):
    """Initialize the sensor and print moisture readings until interrupted."""
    sensor = create_default_sensor()
    sensor.sw_reset()

    chip_id = sensor.chip_id()
    print("Seesaw chip id: 0x{:02X}".format(chip_id))
    print("Sampling moisture every {} ms. Press Ctrl+C to stop.".format(sample_interval_ms))

    try:
        while True:
            moisture = sensor.get_moisture()
            temperature_c = sensor.get_temp()
            print(format_sample(moisture, temperature_c))
            sleep_ms(sample_interval_ms)
    except KeyboardInterrupt:
        print("Measurement stopped by user.")


if __name__ == "__main__":
    main()