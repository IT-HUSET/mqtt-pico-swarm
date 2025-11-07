"""
MQTT Pico Swarm - MicroPython MQTT client library for Raspberry Pi Pico W

A lightweight, robust library for IoT communication using MQTT protocol.
"""

__version__ = "1.0.0"
__author__ = "IT-HUSET i Uppsala"
__license__ = "MIT"

# Public API exports
from .client import PicoSwarmClient
from .errors import (
    PicoSwarmException,
    ConnectionError,
    ConfigurationError,
    MessageError,
    TimeoutError
)
from .constants import (
    COMMAND_TYPE_CONFIG,
    COMMAND_TYPE_ACTION,
    COMMAND_TYPE_RESTART,
    EVENT_TYPE_ERROR,
    EVENT_TYPE_WARNING,
    EVENT_TYPE_INFO
)

# Expose main API
__all__ = [
    "PicoSwarmClient",
    "PicoSwarmException",
    "ConnectionError",
    "ConfigurationError",
    "MessageError",
    "TimeoutError",
    "COMMAND_TYPE_CONFIG",
    "COMMAND_TYPE_ACTION",
    "COMMAND_TYPE_RESTART",
    "EVENT_TYPE_ERROR",
    "EVENT_TYPE_WARNING",
    "EVENT_TYPE_INFO"
]
