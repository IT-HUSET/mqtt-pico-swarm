try:
    from machine import Pin, SPI  # type: ignore
except ImportError:  # pragma: no cover - machine-modulen saknas i CPython
    Pin = None  # type: ignore[assignment]
    SPI = None  # type: ignore[assignment]

import framebuf
import time


DC_PIN = 8
RST_PIN = 12
MOSI_PIN = 11
SCK_PIN = 10
CS_PIN = 9


class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        if Pin is None or SPI is None:  # type: ignore[truthy-function]
            raise RuntimeError("machine.Pin/SPI is not available on this platform")

        self.width = 128
        self.height = 64

        self.cs = Pin(CS_PIN, Pin.OUT)
        self.rst = Pin(RST_PIN, Pin.OUT)

        self.cs(1)
        self.spi = SPI(1, baudrate=20_000_000, polarity=0, phase=0, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=None)
        self.dc = Pin(DC_PIN, Pin.OUT)
        self.dc(1)

        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)

        self.white = 0xFFFF
        self.black = 0x0000

        self.init_display()

    def write_cmd(self, cmd: int) -> None:
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, value: int) -> None:
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([value]))
        self.cs(1)

    def init_display(self) -> None:
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)

        self.write_cmd(0xAE)

        self.write_cmd(0x00)
        self.write_cmd(0x10)

        self.write_cmd(0xB0)

        self.write_cmd(0xDC)
        self.write_cmd(0x00)
        self.write_cmd(0x81)
        self.write_cmd(0x6F)
        self.write_cmd(0x21)

        self.write_cmd(0xA0)
        self.write_cmd(0xC0)
        self.write_cmd(0xA4)

        self.write_cmd(0xA6)
        self.write_cmd(0xA8)
        self.write_cmd(0x3F)

        self.write_cmd(0xD3)
        self.write_cmd(0x60)

        self.write_cmd(0xD5)
        self.write_cmd(0x41)

        self.write_cmd(0xD9)
        self.write_cmd(0x22)

        self.write_cmd(0xDB)
        self.write_cmd(0x35)

        self.write_cmd(0xAD)
        self.write_cmd(0x8A)
        self.write_cmd(0xAF)

    def show(self) -> None:  # type: ignore[override]
        self.write_cmd(0xB0)
        for page in range(0, 64):
            column = 63 - page
            self.write_cmd(0x00 + (column & 0x0F))
            self.write_cmd(0x10 + (column >> 4))
            index = page * 16
            for offset in range(0, 16):
                self.write_data(self.buffer[index + offset])

    def clear(self, color: int = 0x0000) -> None:
        self.fill(color)
        self.show()

    def text_line(self, text: str, line: int, color: int | None = None, clear_line: bool = True) -> None:
        if color is None:
            color = self.white
        if line < 0:
            line = 0
        if line > 7:
            line = 7
        y = line * 8
        if clear_line:
            self.fill_rect(0, y, self.width, 8, self.black)
        self.text(text, 0, y, color)
