"""High-level PicoSwarm client orchestrating configuration, MQTT and command handling."""

import time

try:
    import gc
except ImportError:  # pragma: no cover
    gc = None

try:
    import machine  # type: ignore
except ImportError:  # pragma: no cover
    machine = None

from . import constants
from .commands import CommandHandler
from .config import ConfigManager
from .connection import ConnectionManager
from .errors import ConfigurationError, ConnectionError
from .messages import MessageBuilder
from .mqtt import MQTTAdapter
from .utils import json_loads, log


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

        # Debug-markör för att verifiera firmware-version på enheten
        log(self._debug, "connect() starting (client.py v1)")

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

    def publish_log(self, level, logger, message, context=None, timestamp=None):
        """Publish application/device log message."""
        self._ensure_connected()
        msg = self._message_builder.log(level, logger, message, context=context, timestamp=timestamp)
        self._connection_manager.publish(msg)
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

        broadcast_topics = [
            (constants.TOPIC_BROADCAST_TIME_SYNC, constants.QOS_BROADCAST_TIME),
        ]

        self._connection_manager = ConnectionManager(
            adapter=self._adapter,
            command_handler=self._command_handler,
            device_id=device_id,
            mqtt_config=self._config["mqtt"],
            reconnect_delay=self._config.get("reconnect_delay", 5),
            max_reconnect_attempts=self._config.get("max_reconnect_attempts", 10),
            debug=self._debug,
            broadcast_topics=broadcast_topics,
            broadcast_handler=self._handle_broadcast,
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

    def _handle_broadcast(self, topic, payload):
        if topic == constants.TOPIC_BROADCAST_TIME_SYNC:
            try:
                handled = self._apply_time_sync(payload)
                if handled:
                    log(self._debug, "Time-sync broadcast handled")
                return handled
            except Exception as error:
                log(self._debug, "Time-sync handler failed: {}".format(error))
                return False
        return False

    def _apply_time_sync(self, payload):
        if payload is None:
            log(self._debug, "Received empty time-sync payload")
            return False

        log(self._debug, "Processing time-sync payload")

        try:
            if isinstance(payload, str):
                payload_str = payload
            else:
                payload_bytes = self._payload_to_bytes(payload)
                payload_str = payload_bytes.decode("utf-8")
        except (UnicodeError, TypeError, ValueError) as error:
            log(self._debug, "Failed to decode time-sync payload: {}".format(error))
            return False

        try:
            data = json_loads(payload_str)
        except Exception as error:
            log(self._debug, "Failed to parse time-sync payload as JSON: {}".format(error))
            log(self._debug, "Payload content: {}".format(payload_str))
            return False

        epoch_ms = data.get("epoch_ms")
        timestamp_str = data.get("timestamp")
        epoch_seconds = None

        if isinstance(epoch_ms, (int, float)):
            epoch_seconds = int(epoch_ms / 1000)
        elif isinstance(epoch_ms, str):
            try:
                epoch_seconds = int(int(epoch_ms) / 1000)
            except ValueError:
                epoch_seconds = None

        if epoch_seconds is None and isinstance(timestamp_str, str):
            epoch_seconds = self._parse_iso8601(timestamp_str)

        if epoch_seconds is None:
            log(self._debug, "Time-sync payload missing epoch_ms or timestamp")
            return False

        if machine is None or not hasattr(machine, "RTC"):
            log(self._debug, "Machine RTC unavailable; cannot apply time sync")
            return False

        try:
            rtc = machine.RTC()
        except Exception as error:
            log(self._debug, "Failed to access RTC: {}".format(error))
            return False

        if not hasattr(rtc, "datetime"):
            log(self._debug, "RTC implementation lacks datetime() method")
            return False

        try:
            tm = self._time.gmtime(epoch_seconds)
        except Exception as error:
            log(self._debug, "gmtime() failed: {}".format(error))
            return False

        if tm is None:
            log(self._debug, "gmtime() returned None for epoch {}".format(epoch_seconds))
            return False

        try:
            weekday = tm[6] + 1 if len(tm) > 6 else 1
            rtc.datetime((tm[0], tm[1], tm[2], weekday, tm[3], tm[4], tm[5], 0))
            log(self._debug, "Applied time sync: epoch {}".format(epoch_seconds))
            return True
        except Exception as error:
            log(self._debug, "Failed to apply time sync: {}".format(error))
            return False

    def _parse_iso8601(self, value):
        # Minimal parser för YYYY-MM-DDTHH:MM:SSZ samt tidszon-offsetar
        try:
            if "T" not in value:
                return None
            date_part, time_part = value.split("T", 1)
            if len(date_part) != 10 or date_part[4] != "-" or date_part[7] != "-":
                return None
            year = int(date_part[0:4])
            month = int(date_part[5:7])
            day = int(date_part[8:10])
            offset_seconds = 0

            if time_part.endswith("Z") or time_part.endswith("z"):
                time_part = time_part[:-1]
            else:
                sign_index = max(time_part.rfind("+"), time_part.rfind("-"))
                if sign_index > 0:
                    offset_part = time_part[sign_index:]
                    time_part = time_part[:sign_index]
                    try:
                        offset_sign = 1 if offset_part[0] == "+" else -1
                        if ":" in offset_part:
                            offset_hours = int(offset_part[1:3])
                            offset_minutes = int(offset_part[4:6])
                        else:
                            offset_hours = int(offset_part[1:3])
                            offset_minutes = int(offset_part[3:5]) if len(offset_part) >= 5 else 0
                        offset_seconds = offset_sign * (offset_hours * 3600 + offset_minutes * 60)
                    except (ValueError, IndexError):
                        return None

            parts = time_part.split(":")
            if len(parts) < 2:
                return None
            hour = int(parts[0])
            minute = int(parts[1])
            second = int(float(parts[2])) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            return None

        if hasattr(self._time, "mktime"):
            try:
                base_seconds = int(self._time.mktime((year, month, day, hour, minute, second, 0, 0)))
                return base_seconds - offset_seconds
            except Exception:
                return None
        return None

    @staticmethod
    def _payload_to_bytes(payload):
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        if isinstance(payload, memoryview):
            return bytes(payload)
        if isinstance(payload, str):
            return payload.encode("utf-8")
        return str(payload).encode("utf-8")

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