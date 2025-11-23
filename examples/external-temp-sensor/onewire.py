# 1-Wire driver for MicroPython (vendored from upstream)
# MIT license; Copyright (c) 2016 Damien P. George

try:
    from micropython import const  # type: ignore
except ImportError:  # pragma: no cover - fallback for CPython tools
    def const(x):  # type: ignore
        return x

import _onewire as _ow  # type: ignore


class OneWireError(Exception):
    pass


class OneWire:
    SEARCH_ROM = const(0xF0)
    MATCH_ROM = const(0x55)
    SKIP_ROM = const(0xCC)

    def __init__(self, pin):
        # På rp2-porten finns OPEN_DRAIN och PULL_UP-attribut.
        pin.init(pin.OPEN_DRAIN, pin.PULL_UP)
        self.pin = pin

    def reset(self, required=False):
        reset = _ow.reset(self.pin)
        if required and not reset:
            raise OneWireError
        return reset

    def readbit(self):
        return _ow.readbit(self.pin)

    def readbyte(self):
        return _ow.readbyte(self.pin)

    def readinto(self, buf):
        for i in range(len(buf)):
            buf[i] = _ow.readbyte(self.pin)

    def writebit(self, value):
        return _ow.writebit(self.pin, value)

    def writebyte(self, value):
        return _ow.writebyte(self.pin, value)

    def write(self, buf):
        for b in buf:
            _ow.writebyte(self.pin, b)

    def select_rom(self, rom):
        self.reset(True)
        self.writebyte(self.MATCH_ROM)
        self.write(rom)

    def scan(self):
        devices = []
        diff = 65
        rom = None
        for _ in range(0xFF):
            rom, diff = self._search_rom(rom, diff)
            if rom:
                devices.append(rom)
            if diff == 0:
                break
        return devices

    def _search_rom(self, l_rom, diff):
        if not self.reset():
            return None, 0
        self.writebyte(self.SEARCH_ROM)
        if not l_rom:
            l_rom = bytearray(8)
        rom = bytearray(8)
        next_diff = 0
        i = 64
        for byte in range(8):
            r_b = 0
            for bit in range(8):
                b = self.readbit()
                if self.readbit():
                    if b:
                        # inga enheter eller fel på bussen
                        return None, 0
                else:
                    if not b:
                        # kollision, två enheter med olika bit
                        if diff > i or ((l_rom[byte] & (1 << bit)) and diff != i):
                            b = 1
                            next_diff = i
                self.writebit(b)
                if b:
                    r_b |= 1 << bit
                i -= 1
            rom[byte] = r_b
        return rom, next_diff

    def crc8(self, data):
        return _ow.crc8(data)
