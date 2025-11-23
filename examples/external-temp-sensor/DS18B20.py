import time

try:
    import machine  # type: ignore
except ImportError:  # pragma: no cover
    machine = None

try:
    import onewire  # type: ignore
    import ds18x20  # type: ignore
except ImportError:  # pragma: no cover
    onewire = None
    ds18x20 = None


if hasattr(time, "sleep_ms"):
    sleep_ms = time.sleep_ms  # type: ignore[attr-defined]
else:
    def sleep_ms(ms: int) -> None:
        time.sleep(ms / 1000.0)


class DS18B20Sensor:
    """Tunn wrapper runt onewire.DS18X20 för en ensam DS18B20 på en GPIO."""

    def __init__(self, pin_number):
        if machine is None or onewire is None or ds18x20 is None:
            raise RuntimeError(
                "DS18B20Sensor kräver MicroPython med machine, onewire och ds18x20-moduler"
            )

        pin = machine.Pin(pin_number)
        ow = onewire.OneWire(pin)
        sensor = ds18x20.DS18X20(ow)

        roms = sensor.scan()
        if not roms:
            raise RuntimeError("Ingen DS18B20 hittades på pin {}".format(pin_number))

        self._sensor = sensor
        self._rom = roms[0]

    def read_temperature_c(self):
        self._sensor.convert_temp()
        sleep_ms(750)
        return self._sensor.read_temp(self._rom)
