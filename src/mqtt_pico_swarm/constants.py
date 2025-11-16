"""Protocol constants for the MQTT Pico Swarm library.

This module centralises topic naming, QoS levels and command/event types so
other modules can import from a single source. Keeping these definitions here
helps us stay aligned with the specification in docs/PROTOCOL.md and avoids
string duplication throughout the codebase.
"""

# Base topic segments
TOPIC_ROOT = "hub"
TOPIC_DEVICES = TOPIC_ROOT + "/devices"
TOPIC_BROADCAST = TOPIC_ROOT + "/broadcast"
TOPIC_SYSTEM = TOPIC_ROOT + "/system"

# Device sub-topics
TOPIC_STATUS_SUFFIX = "/status"
TOPIC_DATA_SUFFIX = "/data"
TOPIC_HEARTBEAT_SUFFIX = "/heartbeat"
TOPIC_EVENTS_SUFFIX = "/events"
TOPIC_COMMANDS_SUFFIX = "/commands"
TOPIC_COMMAND_ACK_SUFFIX = "/commands/ack"

# Broadcast sub-topics
TOPIC_BROADCAST_MESSAGE = TOPIC_BROADCAST + "/message"
TOPIC_BROADCAST_CONFIG_UPDATE = TOPIC_BROADCAST + "/config-update"
TOPIC_BROADCAST_TIME_SYNC = TOPIC_BROADCAST + "/time-sync"

# System topics
TOPIC_SYSTEM_HEALTH = TOPIC_SYSTEM + "/health"
TOPIC_DEVICE_REGISTRY = TOPIC_DEVICES + "/registry"

# Command types (topic suffixes map directly to these values)
COMMAND_TYPE_CONFIG = "config"
COMMAND_TYPE_ACTION = "action"
COMMAND_TYPE_RESTART = "restart"
COMMAND_TYPE_TRIGGER_DATA = "trigger-data"
COMMAND_TYPE_LIGHT = "light"

# Event types
EVENT_TYPE_ERROR = "error"
EVENT_TYPE_WARNING = "warning"
EVENT_TYPE_INFO = "info"

# Event severity levels used in PROTOCOL.md
SEVERITY_CRITICAL = "critical"
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

# Default QoS values by message category
QOS_AT_MOST_ONCE = 0
QOS_AT_LEAST_ONCE = 1
QOS_EXACTLY_ONCE = 2

QOS_STATUS = QOS_AT_LEAST_ONCE
QOS_DATA = QOS_AT_LEAST_ONCE
QOS_EVENTS = QOS_AT_LEAST_ONCE
QOS_HEARTBEAT = QOS_AT_MOST_ONCE
QOS_COMMAND_CONFIG = QOS_EXACTLY_ONCE
QOS_COMMAND_ACTION = QOS_AT_LEAST_ONCE
QOS_COMMAND_RESTART = QOS_EXACTLY_ONCE
QOS_COMMAND_TRIGGER_DATA = QOS_AT_LEAST_ONCE
QOS_COMMAND_LIGHT = QOS_AT_LEAST_ONCE
QOS_COMMAND_ACK = QOS_AT_LEAST_ONCE
QOS_BROADCAST_MESSAGE = QOS_AT_MOST_ONCE
QOS_BROADCAST_CONFIG = QOS_AT_LEAST_ONCE
QOS_BROADCAST_TIME = QOS_AT_LEAST_ONCE

# Retain flags matching the protocol specification
RETAIN_STATUS = True
RETAIN_DATA = False
RETAIN_EVENTS = False
RETAIN_HEARTBEAT = False
RETAIN_COMMAND = False
RETAIN_COMMAND_ACK = False
RETAIN_BROADCAST_MESSAGE = False
RETAIN_BROADCAST_CONFIG = False
RETAIN_BROADCAST_TIME = True
RETAIN_DEVICE_REGISTRY = True
RETAIN_SYSTEM_HEALTH = True


def device_topic(device_id, suffix):
    """Return a device-specific MQTT topic.

    Args:
        device_id: Unique identifier for the Pico W device.
        suffix: Topic suffix such as ``TOPIC_STATUS_SUFFIX``.

    Returns:
        str: Fully qualified topic.
    """
    return TOPIC_DEVICES + "/" + device_id + suffix


def device_command_topic(device_id, command_type):
    """Return the topic used to receive a specific command type.

    Args:
        device_id: Unique identifier for the Pico W device.
        command_type: One of the ``COMMAND_TYPE_*`` constants.

    Returns:
        str: Fully qualified topic for the command subscription.
    """
    return TOPIC_DEVICES + "/" + device_id + TOPIC_COMMANDS_SUFFIX + "/" + command_type


def device_ack_topic(device_id):
    """Return the topic for publishing command acknowledgements."""
    return TOPIC_DEVICES + "/" + device_id + TOPIC_COMMAND_ACK_SUFFIX


def status_topic(device_id):
    """Return status topic for a device."""
    return device_topic(device_id, TOPIC_STATUS_SUFFIX)


def data_topic(device_id):
    """Return sensor data topic for a device."""
    return device_topic(device_id, TOPIC_DATA_SUFFIX)


def heartbeat_topic(device_id):
    """Return heartbeat topic for a device."""
    return device_topic(device_id, TOPIC_HEARTBEAT_SUFFIX)


def events_topic(device_id):
    """Return events topic for a device."""
    return device_topic(device_id, TOPIC_EVENTS_SUFFIX)
