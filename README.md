# MQTT Pico Swarm

> A MicroPython MQTT client library for Raspberry Pi Pico W enabling seamless communication with MQTT hubs in distributed IoT systems.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MicroPython](https://img.shields.io/badge/MicroPython-1.20+-blue.svg)](https://micropython.org/)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20Pico%20W-red.svg)](https://www.raspberrypi.com/products/raspberry-pi-pico/)

## Overview

**MQTT Pico Swarm** is a lightweight, robust MicroPython library that provides high-level utilities for Raspberry Pi Pico W devices to communicate with MQTT brokers. It abstracts the complexity of MQTT connection management, message formatting, and protocol handling, allowing developers to focus on application logic.

### Key Features

- **Simple API**: High-level methods for sending and receiving messages according to a standardized protocol
- **Automatic Reconnection**: Robust WiFi and MQTT connection handling with exponential backoff
- **Heartbeat Management**: Built-in periodic heartbeat mechanism for device monitoring
- **Configuration Management**: Easy device configuration with JSON-based config files
- **Protocol Compliance**: Implements a well-defined MQTT communication protocol (see [PROTOCOL.md](docs/PROTOCOL.md))
- **Error Handling**: Comprehensive error reporting and event publishing
- **Last Will Testament**: Automatic offline notification on unexpected disconnection
- **Resource Efficient**: Optimized for MicroPython on resource-constrained devices

### Use Cases

- IoT sensor networks with centralized monitoring
- Distributed device management systems
- Home automation with multiple Pico W nodes
- Industrial monitoring and control systems
- Smart building sensor arrays

## Architecture

```
MQTT Broker (e.g., Mosquitto)
            |
            |
    +-------+--------+
    |                |
Pico W Device    Pico W Device
(Client 1)       (Client 2)
    |                |
mqtt-pico-swarm  mqtt-pico-swarm
   library          library
```

This library handles the **client-side** communication for Raspberry Pi Pico W devices. The Hub/Server implementation is **decoupled** and can be implemented in any language (Java, Python, Node.js, etc.) as long as it follows the defined MQTT protocol.

## Quick Start

### Prerequisites

- Raspberry Pi Pico W with MicroPython firmware
- Access to an MQTT broker (Mosquitto, HiveMQ, etc.)
- WiFi network credentials

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/mqtt-pico-swarm.git
cd mqtt-pico-swarm
```

2. **Copy library files to your Pico W:**
```bash
# Using mpremote (recommended)
mpremote connect /dev/ttyACM0 cp -r src/ :

# Or using Thonny IDE, upload the src/ folder to your Pico W
```

3. **Create a configuration file** (`config.json` on your Pico W):
```json
{
  "device_id": "pico-001",
  "device_type": "temperature_sensor",
  "wifi": {
    "ssid": "YourWiFiSSID",
    "password": "YourWiFiPassword"
  },
  "mqtt": {
    "broker": "192.168.1.100",
    "port": 1883,
    "keepalive": 60
  },
  "heartbeat_interval": 60
}
```

### Basic Example

```python
from mqtt_pico_swarm import PicoSwarmClient
import time

# Initialize the client
client = PicoSwarmClient(config_file="config.json")

# Connect to WiFi and MQTT broker
client.connect()

# Send sensor data
sensor_data = {
    "temperature": 22.5,
    "humidity": 65.3
}
client.publish_data("DHT22", sensor_data, unit="celsius")

# Listen for commands
@client.on_command("action")
def handle_action(payload):
    print(f"Received action command: {payload}")
    # Acknowledge the command
    client.acknowledge_command(payload["command_id"], "success")

# Start heartbeat and command listener
client.start()

# Keep running
while True:
    time.sleep(1)
```

## Library API

### Core Methods

#### `PicoSwarmClient(config_file="config.json")`
Initialize the client with a configuration file.

#### `connect()`
Connect to WiFi and MQTT broker. Automatically subscribes to command topics and publishes initial status.

#### `publish_data(sensor_type, data, unit=None)`
Publish sensor data to the hub.
- **sensor_type** (str): Type of sensor (e.g., "DHT22", "PIR")
- **data** (dict): Sensor readings
- **unit** (str, optional): Unit of measurement

#### `publish_event(event_type, event_code, message, severity="info")`
Publish an event (error, warning, info).
- **event_type** (str): "error", "warning", "info"
- **event_code** (str): Machine-readable event code
- **message** (str): Human-readable description
- **severity** (str): "critical", "error", "warning", "info"

#### `acknowledge_command(command_id, status, message="")`
Send acknowledgment for a received command.
- **command_id** (str): ID of the command being acknowledged
- **status** (str): "success" or "failed"
- **message** (str, optional): Additional details

#### `on_command(command_type, callback)`
Register a callback function for handling commands.
- **command_type** (str): "config", "action", "restart"
- **callback** (function): Function to handle the command

#### `start()`
Start the heartbeat timer and begin listening for commands.

#### `stop()`
Gracefully disconnect from MQTT and WiFi.

### Utility Functions

#### `get_device_status()`
Returns current device status information (uptime, memory, etc.).

#### `get_config()`
Returns the current device configuration.

#### `update_config(new_config)`
Update device configuration and save to file.

## Project Structure

```
mqtt-pico-swarm/
|
+-- src/                      # Library source code
|   +-- mqtt_pico_swarm.py    # Main client class
|   +-- config_manager.py     # Configuration handling
|   +-- connection_manager.py # WiFi/MQTT connection management
|   +-- message_builder.py    # Protocol message formatting
|   +-- utils.py              # Utility functions
|
+-- examples/                 # Example applications
|   +-- basic_example.py
|   +-- temperature_sensor.py
|   +-- motion_detector.py
|   +-- relay_controller.py
|
+-- docs/                     # Documentation
|   +-- PROTOCOL.md           # MQTT protocol specification
|   +-- SETUP.md              # Setup instructions
|   +-- API.md                # Detailed API documentation
|   +-- ARCHITECTURE.md       # System architecture
|
+-- tests/                    # Unit tests
|   +-- test_client.py
|   +-- test_message_builder.py
|
+-- README.md                 # This file
+-- LICENSE                   # MIT License
+-- requirements.txt          # MicroPython dependencies
+-- .gitignore
```

## Configuration

### Configuration File Format

The library uses a JSON configuration file stored on the Pico W filesystem. Here's a complete example:

```json
{
  "device_id": "pico-001",
  "device_type": "sensor",
  "firmware_version": "1.0.0",
  
  "wifi": {
    "ssid": "YourWiFiSSID",
    "password": "YourWiFiPassword",
    "timeout": 30,
    "max_retries": 5
  },
  
  "mqtt": {
    "broker": "192.168.1.100",
    "port": 1883,
    "keepalive": 60,
    "client_id": "pico-001",
    "clean_session": false
  },
  
  "heartbeat_interval": 60,
  "reconnect_delay": 5,
  "max_reconnect_attempts": 10
}
```

### Environment-Specific Configuration

For different environments (development, production), you can maintain multiple config files:
- `config.dev.json`
- `config.prod.json`

Then specify which to use:
```python
client = PicoSwarmClient(config_file="config.prod.json")
```

## Protocol

This library implements a standardized MQTT protocol for device-to-hub communication. The protocol defines:

- **Topic structure**: Hierarchical MQTT topics for organizing messages
- **Message formats**: JSON schemas for all message types
- **QoS strategy**: Quality of Service levels for different message types
- **Connection lifecycle**: Device registration, heartbeats, and graceful shutdown
- **Command/Response pattern**: Bidirectional communication with acknowledgments

For complete protocol specification, see [docs/PROTOCOL.md](docs/PROTOCOL.md).

### Protocol Highlights

**Topics Used:**
- `hub/devices/{device_id}/status` - Device online/offline status
- `hub/devices/{device_id}/heartbeat` - Periodic heartbeat
- `hub/devices/{device_id}/data` - Sensor/event data
- `hub/devices/{device_id}/events` - Error and warning events
- `hub/devices/{device_id}/commands/#` - Incoming commands from hub

**Message Types:**
1. Status messages (retained)
2. Heartbeat messages (QoS 0)
3. Data messages (QoS 1)
4. Event messages (QoS 1)
5. Command acknowledgments (QoS 1)

## Examples

### Temperature Sensor with DHT22

```python
from mqtt_pico_swarm import PicoSwarmClient
from machine import Pin
import dht
import time

# Initialize DHT22 sensor
sensor = dht.DHT22(Pin(15))

# Initialize MQTT client
client = PicoSwarmClient(config_file="config.json")
client.connect()

def read_and_publish():
    try:
        sensor.measure()
        temp = sensor.temperature()
        humidity = sensor.humidity()
        
        # Publish sensor data
        client.publish_data("DHT22", {
            "temperature": temp,
            "humidity": humidity
        }, unit="celsius")
        
    except Exception as e:
        # Publish error event
        client.publish_event("error", "SENSOR_READ_FAILED", str(e), "warning")

# Read and publish every 10 seconds
client.start()
while True:
    read_and_publish()
    time.sleep(10)
```

### Motion Detector with Command Handling

```python
from mqtt_pico_swarm import PicoSwarmClient
from machine import Pin
import time

# Initialize PIR sensor
pir = Pin(16, Pin.IN)
motion_detected = False

# Initialize MQTT client
client = PicoSwarmClient(config_file="config.json")
client.connect()

# Handle configuration commands
@client.on_command("config")
def handle_config(payload):
    print(f"Configuration update: {payload}")
    # Update settings based on payload
    client.acknowledge_command(payload["command_id"], "success")

# Handle action commands
@client.on_command("action")
def handle_action(payload):
    action = payload["payload"].get("action")
    if action == "trigger_test":
        # Simulate motion detection
        client.publish_data("PIR", {"motion": True})
        client.acknowledge_command(payload["command_id"], "success")

# Monitor PIR sensor
client.start()
while True:
    if pir.value() == 1 and not motion_detected:
        motion_detected = True
        client.publish_data("PIR", {"motion": True})
    elif pir.value() == 0 and motion_detected:
        motion_detected = False
        client.publish_data("PIR", {"motion": False})
    
    time.sleep(0.1)
```

### Relay Controller

```python
from mqtt_pico_swarm import PicoSwarmClient
from machine import Pin
import time

# Initialize relay
relay = Pin(17, Pin.OUT)
relay.value(0)  # Start OFF

# Initialize MQTT client
client = PicoSwarmClient(config_file="config.json")
client.connect()

# Handle relay control commands
@client.on_command("action")
def handle_relay_command(payload):
    action = payload["payload"]
    
    if "relay_id" in action and action["relay_id"] == 1:
        state = action.get("state", "off")
        
        if state == "on":
            relay.value(1)
            client.acknowledge_command(payload["command_id"], "success", "Relay turned ON")
        elif state == "off":
            relay.value(0)
            client.acknowledge_command(payload["command_id"], "success", "Relay turned OFF")
        else:
            client.acknowledge_command(payload["command_id"], "failed", "Invalid state")

client.start()

# Keep running
while True:
    time.sleep(1)
```

## Advanced Features

### Custom Heartbeat Logic

You can override the default heartbeat behavior:

```python
client = PicoSwarmClient(config_file="config.json")

def custom_heartbeat():
    # Add custom data to heartbeat
    return {
        "uptime_seconds": time.time(),
        "memory_free": gc.mem_free(),
        "custom_metric": read_custom_sensor()
    }

client.set_heartbeat_callback(custom_heartbeat)
client.connect()
client.start()
```

### Handling Connection Loss

The library automatically handles WiFi and MQTT disconnections with exponential backoff:

```python
client = PicoSwarmClient(config_file="config.json")

# Register callback for connection events
@client.on_connect
def on_connected():
    print("Successfully connected to MQTT broker")

@client.on_disconnect
def on_disconnected():
    print("Disconnected from MQTT broker. Reconnecting...")

client.connect()
client.start()
```

### Error Reporting

Automatically report errors to the hub:

```python
try:
    # Your application logic
    result = risky_operation()
except Exception as e:
    client.publish_event(
        event_type="error",
        event_code="OPERATION_FAILED",
        message=str(e),
        severity="error"
    )
```

## Testing

Run the test suite (requires `unittest` on desktop Python):

```bash
python -m unittest discover tests/
```

For on-device testing, use the examples in `examples/test_*.py`.

## Troubleshooting

### Connection Issues

**Problem:** Pico W cannot connect to WiFi
- Verify SSID and password in `config.json`
- Check WiFi signal strength
- Ensure WiFi network is 2.4 GHz (Pico W doesn't support 5 GHz)

**Problem:** Cannot connect to MQTT broker
- Verify broker IP address and port
- Check that broker allows anonymous connections (or configure credentials)
- Test broker with `mosquitto_sub` command line tool

### Message Issues

**Problem:** Messages not appearing on hub
- Check topic structure matches protocol
- Verify QoS levels
- Use MQTT Explorer to monitor topics

**Problem:** Commands not received
- Ensure device is subscribed to correct command topics
- Check command callback is registered
- Verify command JSON format

### Memory Issues

**Problem:** Out of memory errors
- Reduce heartbeat frequency
- Clear buffers after sending large messages
- Use `gc.collect()` periodically

## Performance

- **Memory footprint**: ~15-20 KB (library only)
- **Heartbeat overhead**: ~100 bytes per message (QoS 0)
- **Data message size**: Varies (typically 200-500 bytes for sensor data)
- **Connection time**: ~3-5 seconds (WiFi + MQTT)
- **Reconnection time**: 5-30 seconds (with exponential backoff)

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows MicroPython best practices
- All tests pass
- Documentation is updated
- Examples are provided for new features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on top of `umqtt.robust` MicroPython MQTT library
- Inspired by the Raspberry Pi Pico W community
- Protocol design based on MQTT 5.0 specification

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/mqtt-pico-swarm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/mqtt-pico-swarm/discussions)

## Roadmap

- [ ] TLS/SSL support for secure connections
- [ ] MQTT 5.0 feature support (user properties, request/response)
- [ ] OTA (Over-The-Air) firmware updates
- [ ] Web-based configuration interface
- [ ] Multi-sensor data batching
- [ ] Power saving modes for battery-powered devices
- [ ] Integration examples for popular sensors (BME280, DS18B20, etc.)

---

**Made with â¤ï¸ for the Raspberry Pi Pico W community**
