"""Custom exception hierarchy for the MQTT Pico Swarm client."""


class PicoSwarmException(Exception):
    """Base class for all library-specific exceptions."""


class ConfigurationError(PicoSwarmException):
    """Raised when configuration values are missing or invalid."""


class ConnectionError(PicoSwarmException):
    """Raised when the MQTT connection encounters a fatal error."""


class MessageError(PicoSwarmException):
    """Raised when a protocol message cannot be built or parsed."""


class TimeoutError(PicoSwarmException):
    """Raised when an operation exceeds the allowed time budget."""


class NetworkUnavailableError(PicoSwarmException):
    """Raised when the network interface is not connected."""
