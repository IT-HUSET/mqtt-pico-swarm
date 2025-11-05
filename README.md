# MQTT Pico Swarm

> A MicroPython MQTT client library for Raspberry Pi Pico W enabling seamless communication with MQTT hubs in distributed IoT systems.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MicroPython](https://img.shields.io/badge/MicroPython-1.20+-blue.svg)](https://micropython.org/)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20Pico%20W-red.svg)](https://www.raspberrypi.com/products/raspberry-pi-pico/)

## Overview

**MQTT Pico Swarm** is a lightweight, robust MicroPython library that provides high-level utilities for Raspberry Pi Pico W devices to communicate with MQTT brokers. It abstracts the complexity of MQTT connection management, message formatting, and protocol handling, allowing developers to focus on application logic.

### Key Features

- **Simple API**: High-level methods for sending and receiving messages according to a standardized protocol
- **Automatic Reconnection**: Robust WiFi and MQTT connection handling with exponential backoff (powered by umqtt.robust2)
- **Heartbeat Management**: Built-in periodic heartbeat mechanism for device monitoring
- **Configuration Management**: Easy device configuration with JSON-based config files
- **Protocol Compliance**: Implements a well-defined MQTT communication protocol (see [PROTOCOL.md](docs/PROTOCOL.md))
- **Error Handling**: Comprehensive error reporting and event publishing
- **Last Will Testament**: Automatic offline notification on unexpected disconnection
- **Resource Efficient**: Optimized for MicroPython on resource-constrained devices

### Use Cases

- IoT sensor networks with centralized monitoring (up to ~100 devices)
- Distributed device management systems
- Home automation with multiple Pico W nodes
- Industrial monitoring and control systems
- Smart building sensor arrays

## Architecture

```
MQTT Broker (e.g., Mosquitto on Hub)
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

- Raspberry Pi Pico W with MicroPython firmware (1.20+)
- Access to an MQTT broker (Mosquitto, HiveMQ, etc.) - typically on the hub
- WiFi network credentials

### Installation

1. **Install MicroPython on Pico W** (if not already installed):
   - Download from https://micropython.org/download/rp2-pico-w/
   - Use `rshell` or Thonny IDE to flash

2. **Install library dependencies**:
```bash
# Using mpremote or rshell
micropython -m upip install micropython-umqtt.robust2

# Or manually copy umqtt files to Pico W filesystem
```

3. **Copy library files to your Pico W**:
```bash
# Using mpremote (recommended)
mpremote connect /dev/ttyACM0 cp -r src/ :

# Or using Thonny IDE, upload the src/ folder
```

4. **Create a configuration file** (`config.json` on your Pico W):
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
+-- src/
|   +-- mqtt_pico_swarm.py       # Main client class
|   +-- config_manager.py        # Configuration handling
|   +-- connection_manager.py    # WiFi/MQTT management
|   +-- message_builder.py       # Protocol messaging
|   +-- command_handler.py       # Command dispatch
|   +-- mqtt_adapter.py          # umqtt.robust2 wrapper
|   +-- errors.py                # Custom exceptions
|   +-- constants.py             # Constants
|   +-- utils.py                 # Utilities
|
+-- examples/
|   +-- basic_example.py
|   +-- temperature_sensor.py
|   +-- motion_detector.py
|   +-- relay_controller.py
|
+-- docs/
|   +-- PROTOCOL.md              # MQTT protocol spec
|   +-- API.md                   # Detailed API docs
|   +-- ARCHITECTURE.md          # System design
|   +-- SETUP.md                 # Setup guide
|
+-- tests/
|   +-- test_message_builder.py
|   +-- test_config_manager.py
|
+-- README.md
+-- LICENSE
+-- requirements.txt
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

## Protocol

This library implements a standardized MQTT protocol for device-to-hub communication. The protocol defines:

- **Topic structure**: Hierarchical MQTT topics for organizing messages
- **Message formats**: JSON schemas for all message types
- **QoS strategy**: Quality of Service levels for different message types
- **Connection lifecycle**: Device registration, heartbeats, and graceful shutdown
- **Command/Response pattern**: Bidirectional communication with acknowledgments

For complete protocol specification, see [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Examples

See the `examples/` directory for complete, working examples:

- **basic_example.py** - Minimal setup and operation
- **temperature_sensor.py** - DHT22 temperature/humidity sensor
- **motion_detector.py** - PIR motion sensor with commands
- **relay_controller.py** - Relay control via hub commands

## Dependencies

### Runtime Dependencies

- **umqtt.robust2** - MicroPython MQTT client with robust reconnection
- **MicroPython standard library** - network, json, time, gc, machine

### Installation

```bash
# Install MicroPython packages
micropython -m upip install micropython-umqtt.robust2
```

## Performance

- **Memory footprint**: ~15-20 KB (library + buffers)
- **Heartbeat overhead**: ~100 bytes per message
- **Data message size**: Typically 200-500 bytes for sensor data
- **Connection time**: ~3-5 seconds (WiFi + MQTT)
- **Reconnection time**: 5-30 seconds (with exponential backoff)

## Troubleshooting

### Connection Issues

**Problem:** Pico W cannot connect to WiFi
- Verify SSID and password in `config.json`
- Check WiFi signal strength
- Ensure WiFi network is 2.4 GHz (Pico W doesn't support 5 GHz)

**Problem:** Cannot connect to MQTT broker
- Verify broker IP address and port
- Check that broker allows anonymous connections
- Test broker with `mosquitto_sub` command line tool

**Problem:** Device goes offline frequently
- Check WiFi signal strength
- Increase `keepalive` value in config
- Check hub connectivity and network stability

### Memory Issues

**Problem:** Out of memory errors
- Reduce `heartbeat_interval` to send fewer messages
- Reduce sensor data payload size
- Call `gc.collect()` periodically after sending messages

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on top of **umqtt.robust2** MicroPython MQTT library
- Inspired by the Raspberry Pi Pico W community
- Protocol design based on MQTT 5.0 specification

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Roadmap

- [ ] TLS/SSL support for secure connections
- [ ] MQTT 5.0 advanced features
- [ ] OTA (Over-The-Air) firmware updates
- [ ] Message compression
- [ ] Web-based configuration interface
- [ ] Power saving modes for battery-powered devices
- [ ] Integration examples for popular sensors

---

**Made with care for the Raspberry Pi Pico W community**
