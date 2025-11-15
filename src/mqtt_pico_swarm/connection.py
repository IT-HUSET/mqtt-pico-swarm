"""Connection management utilities for MQTT Pico Swarm."""

import time

from .errors import ConnectionError, NetworkUnavailableError
from .utils import is_network_available, log

_MAX_BACKOFF_SECONDS = 60


class ConnectionManager:
    """Handle MQTT connection lifecycle and reconnection strategy."""

    def __init__(
        self,
        adapter,
        command_handler,
        device_id,
        mqtt_config,
        reconnect_delay=5,
        max_reconnect_attempts=10,
        debug=False,
        broadcast_topics=None,
        broadcast_handler=None,
    ):
        self._adapter = adapter
        self._command_handler = command_handler
        self._device_id = device_id
        self._mqtt_config = mqtt_config
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._debug = debug
        self._connected = False
        self._last_will = None
        self._broadcast_topics = broadcast_topics or []
        self._broadcast_handler = broadcast_handler

    def configure_last_will(self, last_will):
        """Store last will payload to apply on connect."""
        self._last_will = last_will

    def connect(self):
        """Attempt to establish MQTT connection with backoff."""
        if not is_network_available():
            raise NetworkUnavailableError("Network interface is not connected")

        delay = self._reconnect_delay
        attempts = 0

        while True:
            attempts += 1
            try:
                if not is_network_available():
                    raise NetworkUnavailableError("Network interface is not connected")
                self._connect_once()
                self._connected = True
                log(self._debug, "MQTT connected")
                self._subscribe_commands()
                return True
            except NetworkUnavailableError:
                self._connected = False
                raise
            except ConnectionError as error:
                self._connected = False
                log(self._debug, "MQTT connect failed: " + str(error))
                if self._max_reconnect_attempts and attempts >= self._max_reconnect_attempts:
                    raise
                time.sleep(delay)
                delay = _next_backoff(delay)

    def _connect_once(self):
        cfg = self._mqtt_config
        last_will = None
        if self._last_will:
            last_will = {
                "topic": self._last_will["topic"],
                "payload": self._last_will["payload"],
                "retain": self._last_will.get("retain", False),
                "qos": self._last_will.get("qos", 0),
            }

        self._adapter.set_callback(self._handle_message)
        self._adapter.connect(
            cfg.get("broker"),
            cfg.get("port", 1883),
            cfg.get("client_id", self._device_id),
            keepalive=cfg.get("keepalive", 60),
            username=cfg.get("username", ""),
            password=cfg.get("password", ""),
            clean_session=False,
            ssl=cfg.get("ssl", False),
            ssl_params=cfg.get("ssl_params"),
            last_will=last_will,
        )

    def ensure_connected(self):
        if not self._adapter.is_connected():
            log(self._debug, "MQTT connection lost, reconnecting")
            self.connect()

    def disconnect(self):
        if not self._adapter.is_connected():
            return
        self._adapter.disconnect()
        self._connected = False

    def publish(self, message):
        """Publish message dictionary produced by MessageBuilder."""
        self.ensure_connected()
        self._adapter.publish(
            message["topic"],
            message["payload"],
            qos=message.get("qos", 0),
            retain=message.get("retain", False),
        )

    def process_incoming(self):
        """Non-blocking check for incoming MQTT messages."""
        try:
            self._adapter.check_message()
        except ConnectionError as error:
            self._connected = False
            log(self._debug, "process_incoming failed: {}".format(error))
            raise

    def wait_for_message(self):
        """Blocking wait for the next incoming message."""
        try:
            self._adapter.wait_message()
        except ConnectionError:
            self._connected = False
            raise

    def _subscribe_commands(self):
        for topic in self._command_handler.subscribed_topics(self._device_id):
            # QoS 0 för maximal kompatibilitet med olika umqtt-versioner
            self._adapter.subscribe(topic, qos=0)

        for topic, qos in self._broadcast_topics:
            try:
                self._adapter.subscribe(topic, qos=qos)
            except ConnectionError as error:
                log(self._debug, "Failed to subscribe to broadcast {}: {}".format(topic, error))

    def _handle_message(self, topic, payload):
        handled = False
        log(self._debug, "Dispatching topic: {}".format(topic))
        handled = False
        command_error = None

        try:
            handled = self._command_handler.dispatch(topic, payload)
        except Exception as error:
            command_error = error

        if not handled and self._broadcast_handler:
            try:
                handled = self._broadcast_handler(topic, payload) or handled
            except Exception as error:
                log(self._debug, "Broadcast handler error: " + str(error))

        if not handled:
            if command_error:
                log(self._debug, "Command handler skipped topic (no callback): " + str(command_error))
            log(self._debug, "Unhandled topic: " + topic)
        elif command_error:
            log(
                self._debug,
                "Command handler skipped for broadcast (topic: {}): {}".format(topic, command_error),
            )


def _next_backoff(current):
    next_delay = current * 2
    if next_delay > _MAX_BACKOFF_SECONDS:
        return _MAX_BACKOFF_SECONDS
    return next_delay