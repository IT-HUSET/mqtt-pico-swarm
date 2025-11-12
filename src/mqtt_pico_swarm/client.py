"""High-level PicoSwarm client orchestrating configuration, MQTT and command handling."""

import time

try:
    import gc
except ImportError:  # pragma: no cover
    gc = None

from . import constants
from .commands import CommandHandler
from .config import ConfigManager
from .connection import ConnectionManager
from .errors import ConfigurationError, ConnectionError
from .messages import MessageBuilder
from .mqtt import MQTTAdapter
from .utils import log


class PicoSwarmClient:
    """Main user-facing API for MQTT Pico Swarm devices."""

    def __init__(
        self,
        config_file="config.json",
        debug=False,
        mqtt_adapter=None,
        time_module=None,
    ):
        self._config_manager = ConfigManager(config_file)
        self._config = None

        self._debug = debug
        self._time = time_module or time
        self._adapter = mqtt_adapter or MQTTAdapter()

        self._command_handler = CommandHandler()
        self._connection_manager = None
        self._message_builder = None

        self._connected = False
        self._connected_since = None
        self._running = False
        self._error_count = 0

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def connect(self):
        """Establish MQTT connection and publish initial status."""
        if self._connected:
            return True

        self._config = self._config_manager.get_config()
        self._initialise_components()

        try:
            self._connection_manager.connect()
        except ConnectionError:
            self._connected = False
            raise

        self._connected = True
        self._connected_since = self._time.time()
        self._publish_status_online()
        log(self._debug, "Client connected")
        return True

    def disconnect(self):
        """Gracefully disconnect and publish offline status."""
        if not self._connection_manager:
            return

        if self._connected:
            try:
                self._publish_status_offline()
            except ConnectionError:
                log(self._debug, "Failed to publish offline status before disconnect")

        try:
            self._connection_manager.disconnect()
        finally:
            self._connected = False
            self._running = False
            log(self._debug, "Client disconnected")

    def start(self):
        """Blocking loop handling heartbeats and incoming commands."""
        if not self._connected:
            raise RuntimeError("connect() must be called before start()")

        heartbeat_interval = self._config.get("heartbeat_interval", 60)
        last_heartbeat = 0
        self._running = True

        while self._running:
            self._connection_manager.ensure_connected()
            try:
                self._connection_manager.process_incoming()
            except ConnectionError:
                # Backoff handled by connection manager; continue looping.
                continue

            now = self._time.time()
            if now - last_heartbeat >= heartbeat_interval:
                self._send_heartbeat(now)
                last_heartbeat = now

            sleep = getattr(self._time, "sleep", None)
            if sleep:
                sleep(0.1)

    def stop(self):
        """Stop the main loop and disconnect."""
        self._running = False
        self.disconnect()

    def publish_data(self, sensor_type, data, unit=None, timestamp=None):
        """Publish sensor data payload."""
        self._ensure_connected()
        message = self._message_builder.sensor_data(sensor_type, data, unit or "", timestamp=timestamp)
        self._connection_manager.publish(message)
        return True

    def publish_event(self, event_type, event_code, message, severity=constants.SEVERITY_INFO, timestamp=None):
        """Publish device event."""
        self._ensure_connected()
        payload = self._message_builder.event(event_type, event_code, message, severity, timestamp=timestamp)
        self._connection_manager.publish(payload)
        return True

    def acknowledge_command(self, command_id, status, message="", result="", timestamp=None):
        """Publish command acknowledgement."""
        self._ensure_connected()
        ack = self._message_builder.command_ack(command_id, status, message=message, result=result, timestamp=timestamp)
        self._connection_manager.publish(ack)
        return True

    def send_heartbeat(self, now=None):
        """Publish a heartbeat immediately. Requires active MQTT connection."""
        self._ensure_connected()
        self._send_heartbeat(now)
        return True

    def on_command(self, command_type, callback=None):
        """Register a callback for a specific command type. Supports decorator usage."""
        def register(func):
            wrapped = self._wrap_command_callback(func)
            self._command_handler.on(command_type, wrapped)
            return func

        if callback is None:
            return register
        register(callback)
        return callback

    def get_config(self):
        """Return current configuration."""
        return self._config_manager.get_config()

    def update_config(self, updates, persist=True):
        """Update configuration (only allowed while disconnected)."""
        if self._connected:
            raise ConfigurationError("Disconnect before updating configuration")

        self._config = self._config_manager.update(updates, persist=persist)
        return self._config

    def is_connected(self):
        """Return True if underlying MQTT connection is active."""
        if not self._connection_manager:
            return False
        return self._adapter.is_connected()

    def get_error_count(self):
        """Errors raised by registered command callbacks."""
        return self._error_count

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _initialise_components(self):
        device_id = self._config["device_id"]
        device_type = self._config["device_type"]

        firmware_version = self._config.get("firmware_version", "")
        self._message_builder = MessageBuilder(device_id, device_type, firmware_version)

        self._connection_manager = ConnectionManager(
            adapter=self._adapter,
            command_handler=self._command_handler,
            device_id=device_id,
            mqtt_config=self._config["mqtt"],
            reconnect_delay=self._config.get("reconnect_delay", 5),
            max_reconnect_attempts=self._config.get("max_reconnect_attempts", 10),
            debug=self._debug,
        )

        # Configure MQTT Last Will (offline status message).
        last_will = self._message_builder.status_offline()
        self._connection_manager.configure_last_will(last_will)

    def _ensure_connected(self):
        if not self._connected:
            raise ConnectionError("Client is not connected")

    def _publish_status_online(self):
        message = self._message_builder.status_online()
        self._connection_manager.publish(message)

    def _publish_status_offline(self):
        message = self._message_builder.status_offline()
        self._connection_manager.publish(message)

    def _send_heartbeat(self, now=None):
        now = now or self._time.time()
        uptime_seconds = 0
        if self._connected_since is not None:
            uptime_seconds = int(now - self._connected_since)

        memory_free = self._memory_free()
        heartbeat = self._message_builder.heartbeat(
            uptime_seconds=uptime_seconds,
            memory_free=memory_free,
            error_count=self._error_count,
        )
        self._connection_manager.publish(heartbeat)

    def _wrap_command_callback(self, callback):
        def wrapped(payload):
            try:
                return callback(payload)
            except Exception:
                self._error_count += 1
                raise

        return wrapped

    def _memory_free(self):
        if gc and hasattr(gc, "mem_free"):
            try:
                return gc.mem_free()
            except Exception:  # pragma: no cover
                return 0
        return 0