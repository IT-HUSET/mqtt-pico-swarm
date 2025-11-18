"""Configuration management for MQTT Pico Swarm.

The ConfigManager reads, validates and persists device configuration stored in
JSON files. WiFi setup is handled by user code outside this library; the
configuration describes details required for MQTT communication and runtime
behaviour.
"""

import json

from .errors import ConfigurationError

DEFAULT_CONFIG = {
    "device_id": "pico-001",
    "device_type": "sensor",
    "mqtt": {
        "broker": "",
        "port": 1883,
        "keepalive": 60,
        "client_id": "",
        "username": "",
        "password": "",
    },
    "heartbeat_interval": 60,
    "reconnect_delay": 5,
    "max_reconnect_attempts": 10,
    "command_ack_timeout": 30,
}


class ConfigManager:
    """Load, validate and persist device configuration."""

    def __init__(self, path="config.json", defaults=None):
        self._path = path
        self._defaults = defaults or DEFAULT_CONFIG
        self._config = None

    def load(self):
        """Load configuration from disk and validate it."""
        config = _deep_copy(self._defaults)
        try:
            with open(self._path, "r") as handle:
                raw = json.load(handle)
        except OSError as error:
            raise ConfigurationError("Could not read config file: " + self._path) from error
        except ValueError as error:
            raise ConfigurationError("Config file is not valid JSON: " + self._path) from error

        if not isinstance(raw, dict):
            raise ConfigurationError("Config file must contain a JSON object")

        _merge_dicts(config, raw)
        self._config = _validate_config(config)
        return self._config

    def reload(self):
        """Discard cached data and reload from disk."""
        self._config = None
        return self.load()

    def get_config(self):
        """Return cached configuration, loading it if necessary."""
        if self._config is None:
            return self.load()
        return self._config

    def get(self, key, default=None):
        """Convenience accessor for configuration values."""
        return self.get_config().get(key, default)

    def get_device_id(self):
        """Return the configured device_id."""
        return self.get("device_id")

    def update(self, updates, persist=True):
        """Apply a partial configuration update.

        Args:
            updates: Dict containing new values.
            persist: Write file back to disk when True (default).
        """
        if updates is None:
            return self.get_config()

        config = _deep_copy(self.get_config())
        _merge_dicts(config, updates)
        self._config = _validate_config(config)
        if persist:
            self._write()
        return self._config

    def _write(self):
        if self._config is None:
            return
        try:
            with open(self._path, "w") as handle:
                json.dump(self._config, handle)
        except OSError as error:
            raise ConfigurationError("Failed to write config file: " + self._path) from error


def _deep_copy(source):
    result = {}
    for key, value in source.items():
        if isinstance(value, dict):
            result[key] = _deep_copy(value)
        else:
            result[key] = value
    return result


def _merge_dicts(target, updates):
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dicts(target[key], value)
        else:
            target[key] = value


def _validate_config(config):
    device_id = config.get("device_id")
    if not device_id or not isinstance(device_id, str):
        raise ConfigurationError("device_id must be a non-empty string")

    if not config.get("device_type") or not isinstance(config["device_type"], str):
        raise ConfigurationError("device_type must be a non-empty string")

    heartbeat = config.get("heartbeat_interval")
    if not isinstance(heartbeat, int) or heartbeat <= 0:
        raise ConfigurationError("heartbeat_interval must be positive integer")

    reconnect_delay = config.get("reconnect_delay")
    if not isinstance(reconnect_delay, int) or reconnect_delay <= 0:
        raise ConfigurationError("reconnect_delay must be positive integer")

    max_attempts = config.get("max_reconnect_attempts")
    if not isinstance(max_attempts, int) or max_attempts < 0:
        raise ConfigurationError("max_reconnect_attempts must be integer >= 0")

    ack_timeout = config.get("command_ack_timeout")
    if not isinstance(ack_timeout, int) or ack_timeout <= 0:
        raise ConfigurationError("command_ack_timeout must be positive integer")

    mqtt = config.get("mqtt")
    if not isinstance(mqtt, dict):
        raise ConfigurationError("mqtt section must be present")

    broker = mqtt.get("broker")
    if not isinstance(broker, str):
        raise ConfigurationError("mqtt.broker must be a string")

    port = mqtt.get("port")
    if not isinstance(port, int) or port <= 0:
        raise ConfigurationError("mqtt.port must be a positive integer")

    keepalive = mqtt.get("keepalive")
    if not isinstance(keepalive, int) or keepalive <= 0:
        raise ConfigurationError("mqtt.keepalive must be positive integer")

    if not mqtt.get("client_id"):
        mqtt["client_id"] = device_id

    return config
