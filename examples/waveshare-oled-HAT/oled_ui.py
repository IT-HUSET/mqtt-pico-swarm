class OledUI:
    """Encapsulate all OLED rendering and local UI state.

    The class knows about:
    - Current page (status vs hub text)
    - Last known CPU temperature
    - Last hub text and target line
    - Device id, IP address
    - MQTT status label ("MQTT: OK" / "MQTT: MISS" / etc.)
    """

    STATUS_PAGE = 0
    HUB_PAGE = 1

    def __init__(
        self,
        oled,
        device_id: str = "",
        ip_address: str = "",
        mqtt_broker: str = "",
    ) -> None:
        self._oled = oled
        self._device_id = device_id
        self._ip_address = ip_address
        self._mqtt_broker = mqtt_broker

        self._current_page = self.STATUS_PAGE
        # Last known values, kept untyped here for MicroPython compatibility
        self._last_temperature_c = None
        self._last_hub_text = ""
        self._last_hub_line = 3
        self._mqtt_status_label = ""

    # Boot / error screens -------------------------------------------------

    def show_boot_wifi_connecting(self) -> None:
        self._oled.clear()
        self._oled.text_line("MQTT Pico Swarm", 0)
        self._oled.text_line("WiFi: connect...", 1)
        self._oled.show()

    def show_wifi_failed(self) -> None:
        self._oled.clear()
        self._oled.text_line("WiFi: MISS", 0)
        self._oled.text_line("Check SSID/pwd", 1)
        self._oled.show()

    def show_config_missing(self) -> None:
        self._oled.clear()
        self._oled.text_line("config.json", 0)
        self._oled.text_line("missing", 1)
        self._oled.show()

    # State setters --------------------------------------------------------

    def set_device_id(self, device_id: str) -> None:
        self._device_id = device_id or ""

    def set_ip_address(self, ip_address: str) -> None:
        self._ip_address = ip_address or ""
        if self._current_page == self.STATUS_PAGE:
            self.render_status_page()

    def set_mqtt_broker(self, broker: str) -> None:
        self._mqtt_broker = broker or ""

    def set_temperature(self, temperature_c: float) -> None:
        self._last_temperature_c = temperature_c
        if self._current_page == self.STATUS_PAGE:
            self.render_status_page()

    def set_hub_text(self, text: str, line: int) -> None:
        self._last_hub_text = text
        self._last_hub_line = line
        if self._current_page == self.HUB_PAGE:
            self.render_hub_page()

    # MQTT status helpers --------------------------------------------------

    def show_mqtt_connecting(self) -> None:
        if self._mqtt_broker:
            label = f"MQTT: {self._mqtt_broker}"
        else:
            label = "MQTT: connect..."
        self._set_mqtt_status(label)

    def show_mqtt_ok(self) -> None:
        self._set_mqtt_status("MQTT: OK")

    def show_mqtt_miss(self) -> None:
        self._set_mqtt_status("MQTT: MISS")

    def _set_mqtt_status(self, label: str) -> None:
        self._mqtt_status_label = label
        self._render_mqtt_status_line()

    def _render_mqtt_status_line(self) -> None:
        if not self._mqtt_status_label:
            return
        # Only show MQTT status on the status page.
        if self._current_page != self.STATUS_PAGE:
            return
        # Only update line 4, keep the rest of the buffer as-is.
        self._oled.text_line(self._mqtt_status_label, 4)
        self._oled.show()

    # Page rendering -------------------------------------------------------

    def render_status_page(self) -> None:
        self._oled.clear()
        self._oled.text_line("Status", 0)
        if self._device_id:
            self._oled.text_line(f"ID: {self._device_id}", 1)
        if self._last_temperature_c is not None:
            self._oled.text_line(f"CPU: {self._last_temperature_c:.1f} C", 2)
        if self._ip_address:
            self._oled.text_line(self._ip_address, 3)
        self._oled.show()
        # Re-apply MQTT status indicator on line 4 if we have one
        self._render_mqtt_status_line()

    def render_hub_page(self) -> None:
        self._oled.clear()
        self._oled.text_line("Hub text", 0)
        if self._last_hub_text:
            line = self._last_hub_line
            if line < 1:
                line = 1
            if line > 7:
                line = 7
            self._oled.text_line(self._last_hub_text, line)
        self._oled.show()
        self._render_mqtt_status_line()

    def render_current_page(self) -> None:
        if self._current_page == self.STATUS_PAGE:
            self.render_status_page()
        else:
            self.render_hub_page()

    # Navigation / buttons -------------------------------------------------

    def toggle_page(self) -> None:
        if self._current_page == self.STATUS_PAGE:
            self._current_page = self.HUB_PAGE
        else:
            self._current_page = self.STATUS_PAGE
        self.render_current_page()
