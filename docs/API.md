# API Documentation: MQTT Pico Swarm

**Version:** 1.0  
**Date:** November 5, 2025

## Table of Contents

1. [Core Client Class](#core-client-class)
2. [Connection Management](#connection-management)
3. [Data Publishing](#data-publishing)
4. [Command Handling](#command-handling)
5. [Configuration Management](#configuration-management)
6. [Event Publishing](#event-publishing)
7. [Callbacks and Events](#callbacks-and-events)
8. [Error Handling](#error-handling)
9. [Utility Functions](#utility-functions)
10. [Constants and Enums](#constants-and-enums)

---

## Core Client Class

### `PicoSwarmClient`

The main class for MQTT communication with a central hub.

#### Constructor

```python
PicoSwarmClient(config_file="config.json", debug=False)
```

**Parameters:**
- `config_file` (str): Path to JSON configuration file (default: "config.json")
- `debug` (bool): Enable debug logging (default: False)

**Returns:** PicoSwarmClient instance

**Example:**
```python
client = PicoSwarmClient(config_file="config.json", debug=True)
```

**Raises:**
- `FileNotFoundError`: If config file does not exist
- `ValueError`: If config file is invalid JSON

---

## Connection Management

### `connect()`

Establish connections to WiFi and MQTT broker.

```python
connect() -> bool
```

**Returns:**
- `True` if successfully connected to both WiFi and MQTT
- `False` if connection failed

**Behavior:**
- Connects to WiFi network specified in config
- Connects to MQTT broker
- Subscribes to all command topics
- Publishes initial online status (retained)
- Sets up Last Will Testament (LWT)

**Raises:**
- `RuntimeError`: If connection fails after max retries

**Example:**
```python
client = PicoSwarmClient()
if client.connect():
    print("Connected successfully")
else:
    print("Connection failed")
```

### `disconnect()`

Gracefully disconnect from MQTT and WiFi.

```python
disconnect() -> None
```

**Behavior:**
- Publishes offline status to hub
- Unsubscribes from all topics
- Closes MQTT connection
- Disconnects from WiFi

**Example:**
```python
try:
    # Application logic
    pass
finally:
    client.disconnect()
```

### `is_connected()`

Check current connection status.

```python
is_connected() -> bool
```

**Returns:**
- `True` if connected to both WiFi and MQTT
- `False` if either connection is lost

**Example:**
```python
if client.is_connected():
    client.publish_data("sensor", {"value": 42})
else:
    print("Not connected to hub")
```

### `start()`

Start heartbeat timer and command listener (blocking call).

```python
start() -> None
```

**Behavior:**
- Starts periodic heartbeat messages (interval from config)
- Begins listening for incoming commands
- Automatically handles reconnections
- Runs indefinitely until `stop()` is called or exception occurs

**Must be called after** `connect()`

**Example:**
```python
client = PicoSwarmClient()
client.connect()

# This call blocks indefinitely
client.start()
```

### `stop()`

Stop heartbeat and disconnect from broker.

```python
stop() -> None
```

**Behavior:**
- Stops heartbeat timer
- Stops command listener
- Gracefully disconnects from MQTT and WiFi
- Publishes final offline status

**Example:**
```python
import signal

def signal_handler(sig, frame):
    print("Shutting down...")
    client.stop()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

client = PicoSwarmClient()
client.connect()
client.start()
```

---

## Capabilities

### `publish_capabilities(capabilities)`

Publish a structured capabilities specification describing the device's
sensors and supported commands. This message is **retained** on the broker so
the hub can reconstruct the current capabilities even if the device is
offline.

```python
publish_capabilities(capabilities: dict) -> bool
```

**Parameters:**
- `capabilities` (dict): A JSON-serialisable dictionary that follows the
  capabilities schema described in `PROTOCOL.md` (section "Device
  Capabilities Message"). At minimum it SHOULD contain:
  - `sensors`: list of sensor descriptors
  - `commands`: list of command descriptors

The library will automatically inject:

- `device_id` – from the active configuration
- `device_type` – from the active configuration
- `firmware_version` – from configuration (if present)
- `schema_version` – currently `1` if not already set

**Returns:**
- `True` if published successfully

**QoS:** 1 (At Least Once)

**Topic:** `hub/devices/{device_id}/capabilities` (retained)

**Example - Simple Capabilities:**

```python
CAPABILITIES = {
    "sensors": [
        {
            "id": "cpu_temp",
            "display_name": "CPU-temperatur",
            "sensor_type": "temperature",
            "data_source": {"sensor_type": "temperature", "path": "data"},
            "measures": [
                {
                    "key": "temperature_c",
                    "display_name": "Temperatur",
                    "unit": "°C",
                    "value_type": "number",
                    "precision": 2,
                }
            ],
        }
    ],
    "commands": [
        {
            "id": "trigger_data",
            "display_name": "Trigga mätning nu",
            "command_type": "trigger-data",
            "topic_suffix": "commands/trigger-data",
            "parameters": [],
        },
    ],
}

client.publish_capabilities(CAPABILITIES)
```

---

## Data Publishing

### `publish_data(sensor_type, data, unit=None, timestamp=None)`

Publish sensor or event data to the hub.

```python
publish_data(sensor_type: str, data: dict, unit: str = None, timestamp: str = None) -> bool
```

**Parameters:**
- `sensor_type` (str): Type of sensor (e.g., "DHT22", "DS18B20", "BME280")
- `data` (dict): Sensor readings as key-value pairs
- `unit` (str, optional): Unit of measurement (e.g., "celsius", "fahrenheit")
- `timestamp` (str, optional): ISO 8601 timestamp (auto-generated if not provided)

**Returns:**
- `True` if published successfully
- `False` if publish failed

**QoS:** 1 (At Least Once)

**Topic:** `hub/devices/{device_id}/data`

**Example - Temperature and Humidity:**
```python
client.publish_data("DHT22", {
    "temperature": 22.5,
    "humidity": 65.3
}, unit="celsius")
```

**Example - Motion Detection:**
```python
client.publish_data("PIR", {
    "motion": True,
    "confidence": 0.95
})
```

---

## Command Handling

### `on_command(command_type, callback)`

Register callback function for specific command type.

```python
on_command(command_type: str, callback: callable) -> None
```

**Parameters:**
- `command_type` (str): "config", "action", "restart", or custom type
- `callback` (callable): Function to handle the command

**Callback Signature:**
```python
def callback(payload: dict) -> None:
    # payload contains:
    # {
    #   "command_id": "cmd-12345",
    #   "device_id": "pico-001",
    #   "type": "action",
    #   "payload": { ... },
    #   "timestamp": "2025-11-05T10:37:30Z"
    # }
    pass
```

**Note:** Callback must call `acknowledge_command()` to notify hub of completion.

**Example - Config Command:**
```python
@client.on_command("config")
def handle_config(payload):
    print(f"Received config: {payload['payload']}")
    
    # Apply configuration
    new_interval = payload['payload'].get('heartbeat_interval', 60)
    
    # Acknowledge success
    client.acknowledge_command(payload['command_id'], "success")
```

**Example - Action Command:**
```python
@client.on_command("action")
def handle_action(payload):
    action = payload['payload']
    
    if action.get('type') == 'toggle_relay':
        relay.value(1 - relay.value())
        client.acknowledge_command(payload['command_id'], "success")
    else:
        client.acknowledge_command(payload['command_id'], "failed", "Unknown action")
```

### `acknowledge_command(command_id, status, message="")`

Send acknowledgment for received command.

```python
acknowledge_command(command_id: str, status: str, message: str = "") -> bool
```

**Parameters:**
- `command_id` (str): ID of the command being acknowledged
- `status` (str): "success" or "failed"
- `message` (str, optional): Additional details about execution

**Returns:**
- `True` if acknowledgment sent successfully
- `False` if send failed

**QoS:** 1 (At Least Once)

**Topic:** `hub/devices/{device_id}/commands/ack`

**Note:** MUST be called from within command callback to confirm command receipt and execution.

**Example:**
```python
@client.on_command("action")
def handle_command(payload):
    try:
        # Execute command
        perform_action(payload['payload'])
        
        # Acknowledge success
        client.acknowledge_command(
            payload['command_id'],
            "success",
            "Action completed successfully"
        )
    except Exception as e:
        # Acknowledge failure
        client.acknowledge_command(
            payload['command_id'],
            "failed",
            f"Error: {str(e)}"
        )
```

---

## Configuration Management

### `get_config()`

Get current device configuration.

```python
get_config() -> dict
```

**Returns:** Dictionary containing all configuration parameters

**Example:**
```python
config = client.get_config()
print(f"Device ID: {config['device_id']}")
print(f"Heartbeat interval: {config['heartbeat_interval']}")
```

### `update_config(new_config)`

Update device configuration and save to file.

```python
update_config(new_config: dict) -> bool
```

**Parameters:**
- `new_config` (dict): New configuration parameters (partial or complete)

**Returns:**
- `True` if configuration updated successfully
- `False` if update failed

**Behavior:**
- Merges new config with existing config
- Validates configuration
- Persists to JSON file
- Takes effect immediately

**Example:**
```python
# Update single parameter
client.update_config({
    "heartbeat_interval": 120
})

# Update multiple parameters
client.update_config({
    "heartbeat_interval": 120,
    "device_type": "advanced_sensor"
})
```

### `get_device_id()`

Get the device ID from configuration.

```python
get_device_id() -> str
```

**Returns:** Device ID string

**Example:**
```python
device_id = client.get_device_id()
print(f"This device is: {device_id}")
```

---

## Event Publishing

### `publish_event(event_type, event_code, message, severity="info", timestamp=None)`

Publish an event (error, warning, or info) to the hub.

```python
publish_event(event_type: str, event_code: str, message: str, 
              severity: str = "info", timestamp: str = None) -> bool
```

**Parameters:**
- `event_type` (str): "error", "warning", or "info"
- `event_code` (str): Machine-readable event code (e.g., "SENSOR_TIMEOUT")
- `message` (str): Human-readable description
- `severity` (str): "critical", "error", "warning", or "info" (default: "info")
- `timestamp` (str, optional): ISO 8601 timestamp (auto-generated if not provided)

**Returns:**
- `True` if published successfully
- `False` if publish failed

**QoS:** 1 (At Least Once)

**Topic:** `hub/devices/{device_id}/events`

**Example - Sensor Timeout:**
```python
def read_sensor():
    try:
        sensor.measure()
        return sensor.temperature()
    except TimeoutError:
        client.publish_event(
            event_type="error",
            event_code="SENSOR_TIMEOUT",
            message="DHT22 sensor did not respond",
            severity="warning"
        )
        return None
```

**Example - Memory Warning:**
```python
import gc

gc.collect()
free_mem = gc.mem_free()

if free_mem < 10000:  # Less than 10KB
    client.publish_event(
        event_type="warning",
        event_code="MEMORY_LOW",
        message=f"Only {free_mem} bytes free",
        severity="warning"
    )
```

---

## Logging

### `publish_log(level, logger, message, context=None, timestamp=None)`

Publish a structured log message from the device to the hub.

```python
publish_log(level: str, logger: str, message: str,
            context: dict | None = None, timestamp: str | None = None) -> bool
```

**Parameters:**
- `level` (str): Log level ("debug", "info", "warn", or "error").
- `logger` (str): Logical logger or class/source name (e.g. "soil_sensor.main").
- `message` (str): Human-readable log message.
- `context` (dict, optional): Additional structured metadata to include with the log.
- `timestamp` (str, optional): ISO 8601 timestamp (auto-generated if not provided).

**Returns:**
- `True` if published successfully

**QoS:** 0 (At Most Once)

**Topic:** `hub/devices/{device_id}/logs`

**Example - Simple Info Log:**
```python
client.publish_log(
    level="info",
    logger="soil_sensor.main",
    message="Soil moisture sample collected"
)
```

**Example - Log with Context:**
```python
client.publish_log(
    level="debug",
    logger="soil_sensor.main",
    message="Raw moisture value",
    context={"moisture_raw": raw_value}
)
```

---

## Callbacks and Events

### `on_connect(callback)`

Register callback for successful connection to MQTT broker.

```python
on_connect(callback: callable) -> None
```

**Callback Signature:**
```python
def on_connect() -> None:
    pass
```

**Example:**
```python
@client.on_connect
def on_connected():
    print("Successfully connected to MQTT broker")
    # Initialize sensors
    initialize_sensors()
```

### `on_disconnect(callback)`

Register callback for disconnection from MQTT broker.

```python
on_disconnect(callback: callable) -> None
```

**Callback Signature:**
```python
def on_disconnect() -> None:
    pass
```

**Example:**
```python
@client.on_disconnect
def on_disconnected():
    print("Disconnected from MQTT broker")
    print("Attempting to reconnect...")
```

### `set_heartbeat_callback(callback)`

Override default heartbeat data with custom callback.

```python
set_heartbeat_callback(callback: callable) -> None
```

**Callback Signature:**
```python
def custom_heartbeat() -> dict:
    # Return dict with custom heartbeat data
    return {
        "uptime_seconds": get_uptime(),
        "memory_free": gc.mem_free(),
        "temperature": read_onboard_temp(),
        "custom_metric": read_custom_sensor()
    }
```

**Example:**
```python
def enhanced_heartbeat():
    import gc
    return {
        "uptime_seconds": utime.time(),
        "memory_free": gc.mem_free(),
        "error_count": error_counter,
        "last_sensor_reading": last_temp
    }

client.set_heartbeat_callback(enhanced_heartbeat)
```

---

## Error Handling

### Exception Types

```
PicoSwarmException (base for all library exceptions)
  +-- ConnectionError
  +-- ConfigurationError
  +-- MessageError
  +-- TimeoutError
```

### Error Handling Best Practices

```python
import time

client = PicoSwarmClient()

try:
    client.connect()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
    exit(1)

try:
    client.start()
except KeyboardInterrupt:
    print("Interrupted by user")
except Exception as e:
    print(f"Unexpected error: {e}")
    client.publish_event("error", "FATAL_ERROR", str(e), "critical")
finally:
    client.disconnect()
```

---

## Utility Functions

### `get_device_status()`

Get current device status information.

```python
get_device_status() -> dict
```

**Returns:**
```python
{
    "device_id": "pico-001",
    "device_type": "temperature_sensor",
    "status": "online",
    "uptime_seconds": 3600,
    "memory_free": 45000,
    "error_count": 0,
    "wifi_signal_strength": -65,
    "timestamp": "2025-11-05T10:37:00Z"
}
```

**Example:**
```python
status = client.get_device_status()
print(f"Uptime: {status['uptime_seconds']} seconds")
```

### `get_connection_stats()`

Get MQTT connection statistics.

```python
get_connection_stats() -> dict
```

**Returns:**
```python
{
    "connected": True,
    "mqtt_connected": True,
    "wifi_connected": True,
    "messages_sent": 1234,
    "messages_received": 567,
    "last_message_time": "2025-11-05T10:37:15Z",
    "reconnect_count": 2
}
```

**Example:**
```python
stats = client.get_connection_stats()
print(f"Messages sent: {stats['messages_sent']}")
```

---

## Constants and Enums

### Command Types

```python
COMMAND_TYPE_CONFIG = "config"
COMMAND_TYPE_ACTION = "action"
COMMAND_TYPE_RESTART = "restart"
```

### Event Types

```python
EVENT_TYPE_ERROR = "error"
EVENT_TYPE_WARNING = "warning"
EVENT_TYPE_INFO = "info"
```

### Severity Levels

```python
SEVERITY_CRITICAL = "critical"
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"
```

### Common Event Codes

```python
EVENT_CODE_SENSOR_TIMEOUT = "SENSOR_TIMEOUT"
EVENT_CODE_WIFI_DISCONNECT = "WIFI_DISCONNECT"
EVENT_CODE_MQTT_DISCONNECT = "MQTT_DISCONNECT"
EVENT_CODE_INVALID_CONFIG = "INVALID_CONFIG"
EVENT_CODE_MEMORY_LOW = "MEMORY_LOW"
EVENT_CODE_COMMAND_FAILED = "COMMAND_FAILED"
EVENT_CODE_INVALID_MESSAGE_FORMAT = "INVALID_MESSAGE_FORMAT"
```

---

## Complete Example: Temperature Sensor

```python
from mqtt_pico_swarm import PicoSwarmClient
from machine import Pin
from dht import DHT22
import time
import gc

# Initialize hardware
sensor = DHT22(Pin(15))

# Initialize MQTT client
client = PicoSwarmClient(config_file="config.json", debug=False)

# Connection callbacks
@client.on_connect
def on_connected():
    print("Connected to MQTT hub!")
    gc.collect()

@client.on_disconnect
def on_disconnected():
    print("Lost connection, attempting to reconnect...")

# Command handlers
@client.on_command("config")
def handle_config(payload):
    try:
        interval = payload['payload'].get('heartbeat_interval', 60)
        client.update_config({"heartbeat_interval": interval})
        client.acknowledge_command(payload['command_id'], "success")
    except Exception as e:
        client.acknowledge_command(payload['command_id'], "failed", str(e))

@client.on_command("action")
def handle_action(payload):
    if payload['payload'].get('action') == 'read_now':
        try:
            sensor.measure()
            client.publish_data("DHT22", {
                "temperature": sensor.temperature(),
                "humidity": sensor.humidity()
            }, unit="celsius")
            client.acknowledge_command(payload['command_id'], "success")
        except Exception as e:
            client.publish_event("error", "SENSOR_READ_FAILED", str(e), "warning")
            client.acknowledge_command(payload['command_id'], "failed")

# Main application
def main():
    # Connect
    if not client.connect():
        client.publish_event("error", "CONNECTION_FAILED", "Could not connect", "error")
        return

    # Override heartbeat with custom data
    def custom_heartbeat():
        return {
            "uptime_seconds": time.time(),
            "memory_free": gc.mem_free(),
            "error_count": 0
        }

    client.set_heartbeat_callback(custom_heartbeat)

    # Publish startup event
    client.publish_event("info", "DEVICE_STARTED", "Sensor initialized", "info")

    # Main loop
    try:
        client.start()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        client.publish_event("info", "DEVICE_SHUTDOWN", "Device shutting down", "info")
        client.disconnect()

if __name__ == "__main__":
    main()
```

---

## See Also

- [README.md](../README.md) - Project overview
- [PROTOCOL.md](PROTOCOL.md) - MQTT protocol specification
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
