"""Protocol message construction utilities for MQTT Pico Swarm."""

from . import constants
from .utils import current_timestamp, json_dumps


def _ensure_timestamp(timestamp):
    if timestamp:
        return timestamp
    return current_timestamp()


class MessageBuilder:
    """Build protocol-compliant MQTT payloads.

    Args:
        device_id: Identifier for the Pico device.
        device_type: Human-readable device type.
        firmware_version: Optional firmware identifier included in status.
    """

    def __init__(self, device_id, device_type, firmware_version=""):
        self._device_id = device_id
        self._device_type = device_type
        self._firmware_version = firmware_version

    def status_online(self, ip_address="", signal_strength=None, timestamp=None):
        payload = {
            "device_id": self._device_id,
            "device_type": self._device_type,
            "status": "online",
            "timestamp": _ensure_timestamp(timestamp),
            "firmware_version": self._firmware_version,
        }
        if ip_address:
            payload["ip_address"] = ip_address
        if signal_strength is not None:
            payload["signal_strength"] = signal_strength

        return _build_message(
            constants.status_topic(self._device_id),
            payload,
            constants.QOS_STATUS,
            constants.RETAIN_STATUS,
        )

    def status_offline(self, timestamp=None):
        payload = {
            "device_id": self._device_id,
            "status": "offline",
            "timestamp": _ensure_timestamp(timestamp),
        }
        return _build_message(
            constants.status_topic(self._device_id),
            payload,
            constants.QOS_STATUS,
            constants.RETAIN_STATUS,
        )

    def heartbeat(self, uptime_seconds, memory_free, error_count=0, timestamp=None):
        payload = {
            "device_id": self._device_id,
            "timestamp": _ensure_timestamp(timestamp),
            "uptime_seconds": uptime_seconds,
            "memory_free": memory_free,
            "error_count": error_count,
        }
        return _build_message(
            constants.heartbeat_topic(self._device_id),
            payload,
            constants.QOS_HEARTBEAT,
            constants.RETAIN_HEARTBEAT,
        )

    def sensor_data(self, sensor_type, data, unit="", timestamp=None):
        payload = {
            "device_id": self._device_id,
            "sensor_type": sensor_type,
            "data": data,
            "timestamp": _ensure_timestamp(timestamp),
        }
        if unit:
            payload["unit"] = unit

        return _build_message(
            constants.data_topic(self._device_id),
            payload,
            constants.QOS_DATA,
            constants.RETAIN_DATA,
        )

    def event(self, event_type, event_code, message, severity, timestamp=None):
        payload = {
            "device_id": self._device_id,
            "event_type": event_type,
            "event_code": event_code,
            "message": message,
            "severity": severity,
            "timestamp": _ensure_timestamp(timestamp),
        }
        return _build_message(
            constants.events_topic(self._device_id),
            payload,
            constants.QOS_EVENTS,
            constants.RETAIN_EVENTS,
        )

    def log(self, level, logger, message, context=None, timestamp=None):
        payload = {
            "device_id": self._device_id,
            "level": level,
            "logger": logger,
            "message": message,
            "timestamp": _ensure_timestamp(timestamp),
        }
        if context:
            payload["context"] = context

        return _build_message(
            constants.logs_topic(self._device_id),
            payload,
            constants.QOS_LOGS,
            constants.RETAIN_LOGS,
        )

    def command_ack(self, command_id, status, message="", result="", timestamp=None):
        payload = {
            "command_id": command_id,
            "device_id": self._device_id,
            "status": status,
            "timestamp": _ensure_timestamp(timestamp),
        }
        if message:
            payload["message"] = message
        if result:
            payload["result"] = result

        return _build_message(
            constants.device_ack_topic(self._device_id),
            payload,
            constants.QOS_COMMAND_ACK,
            constants.RETAIN_COMMAND_ACK,
        )

    def last_will(self):
        """Return topic/payload tuple for LWT offline status."""
        return self.status_offline()


def _build_message(topic, payload_dict, qos, retain):
    return {
        "topic": topic,
        "payload": json_dumps(payload_dict),
        "qos": qos,
        "retain": retain,
    }
