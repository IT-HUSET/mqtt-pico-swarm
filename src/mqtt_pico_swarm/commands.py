"""Command dispatch utilities for MQTT Pico Swarm."""

from . import constants
from .errors import MessageError
from .utils import json_loads


class CommandHandler:
    """Manage command callbacks and dispatch MQTT command messages."""

    def __init__(self):
        self._callbacks = {}
        self._wildcard_callback = None

    def on(self, command_type, callback):
        """Register a callback for a specific command type."""
        if not callable(callback):
            raise MessageError("Callback must be callable")
        self._callbacks[command_type] = callback
        return callback

    def on_any(self, callback):
        """Register wildcard callback for any command type."""
        if not callable(callback):
            raise MessageError("Callback must be callable")
        self._wildcard_callback = callback
        return callback

    def clear(self):
        self._callbacks = {}
        self._wildcard_callback = None

    def dispatch(self, topic, payload_bytes):
        """Parse incoming command and call registered callback.

        Returns:
            bool: True if a callback handled the command, False otherwise.
        """
        payload = _parse_payload(payload_bytes)
        command_type = _extract_command_type(topic)
        if command_type is None:
            raise MessageError("Could not determine command type for topic: " + topic)

        callback = self._callbacks.get(command_type)
        handled = False
        if callback:
            callback(payload)
            handled = True

        if self._wildcard_callback:
            self._wildcard_callback(command_type, payload)
            handled = True

        return handled

    def subscribed_topics(self, device_id):
        """Return list of command topics to subscribe to for device."""
        return [
            constants.device_command_topic(device_id, constants.COMMAND_TYPE_CONFIG),
            constants.device_command_topic(device_id, constants.COMMAND_TYPE_ACTION),
            constants.device_command_topic(device_id, constants.COMMAND_TYPE_RESTART),
            constants.device_command_topic(device_id, constants.COMMAND_TYPE_TRIGGER_DATA),
        ]


def _parse_payload(payload_bytes):
    if not payload_bytes:
        raise MessageError("Command payload is empty")
    try:
        if isinstance(payload_bytes, bytes):
            payload_bytes = payload_bytes.decode("utf-8")
        return json_loads(payload_bytes)
    except ValueError as error:
        raise MessageError("Failed to parse command payload") from error


def _extract_command_type(topic):
    if not topic or "/commands/" not in topic:
        return None
    return topic.rsplit("/", 1)[-1]
