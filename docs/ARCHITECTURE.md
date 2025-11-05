# Architecture: MQTT Pico Swarm

**Version:** 1.2  
**Date:** November 5, 2025

## System Overview

### Goal

Provide a lightweight, robust MicroPython library that abstracts away MQTT complexity and protocol details, allowing Pico W developers to focus on application logic.

### Key Design Principles

1. **Separation of Concerns** - Clear boundaries between connection management, message formatting, and application logic
2. **Low Resource Footprint** - Minimal memory usage (target: <25 KB with library + buffers)
3. **Robustness** - Automatic reconnection via umqtt.robust2, graceful error handling
4. **Protocol Compliance** - Strictly adheres to defined MQTT protocol
5. **Easy to Use** - High-level API that hides MQTT details
6. **Testable** - Modular design enables unit testing

### Architecture Layers

```
Application Layer
|  (User code: sensors, logic)
|
+-- API Layer
|   PicoSwarmClient (public API)
|
+-- Logic Layer
|   - MessageBuilder (protocol)
|   - CommandHandler (command logic)
|   - ConnectionManager (reconnect)
|
+-- Infrastructure Layer
|   - ConfigManager (configuration)
|   - MQTTAdapter (umqtt.robust2 wrapper)
|
+-- External Dependencies
|   - umqtt.robust2 (MQTT library with robust reconnection)
|   - MicroPython stdlib
|
+-- External Services (Network)
    - MQTT Broker (hub-side, e.g., Mosquitto)
    - WiFi network
```

## Why umqtt.robust2?

**umqtt.robust2** was chosen over alternatives because it:

1. **Built-in Reconnection** - Handles WiFi and MQTT reconnection automatically
2. **Queue Management** - Stores unsent messages during disconnections
3. **Auto-resubscription** - Automatically resubscribes to topics after reconnect
4. **Non-blocking** - Designed for embedded systems with single-threaded execution
5. **Proven** - Widely used in MicroPython IoT projects
6. **Minimal Overhead** - Lightweight implementation suitable for Pico W

### Installation

```bash
micropython -m upip install micropython-umqtt.robust2
```

## Module Structure

```
mqtt-pico-swarm/
|
+-- src/
|   +-- mqtt_pico_swarm.py       # Main client class
|   +-- message_builder.py       # Protocol message formatting
|   +-- connection_manager.py    # WiFi/MQTT connection handling
|   +-- config_manager.py        # Configuration file handling
|   +-- command_handler.py       # Command dispatch and callbacks
|   +-- mqtt_adapter.py          # Wrapper around umqtt.robust2
|   +-- errors.py                # Custom exceptions
|   +-- constants.py             # Constants and enums
|   +-- utils.py                 # Utility functions
|
+-- examples/
|   +-- basic_example.py
|   +-- temperature_sensor.py
|   +-- motion_detector.py
|   +-- relay_controller.py
|
+-- tests/
|   +-- test_message_builder.py
|   +-- test_config_manager.py
|   +-- test_command_handler.py
|
+-- docs/
    +-- README.md
    +-- API.md
    +-- PROTOCOL.md
    +-- ARCHITECTURE.md
    +-- SETUP.md
```

## Dependencies

### Runtime Dependencies

```
mqtt-pico-swarm/
  |
  +-- umqtt.robust2 (external, installed via upip)
  |    - Provides MQTTClient class
  |    - Handles reconnection logic
  |    - Manages message queue
  |
  +-- MicroPython stdlib
       +-- network (WiFi connection)
       +-- json (message parsing)
       +-- time (timestamps, delays)
       +-- gc (garbage collection)
       +-- machine (board-specific)
       +-- os (file operations)
```

### No Additional Dependencies

- **Mosquitto NOT a dependency** - It runs on the hub (external service)
- **No other MicroPython libraries needed** - Uses stdlib only
- **umqtt.robust2 is the ONLY external dependency**

## Core Classes

### 1. PicoSwarmClient

**File:** `mqtt_pico_swarm.py`

**Responsibility:** Main API and orchestration

**Key Methods:**
```python
def __init__(config_file="config.json", debug=False)
def connect() -> bool
def disconnect() -> None
def publish_data(sensor_type, data, unit=None) -> bool
def publish_event(event_type, code, message, severity) -> bool
def acknowledge_command(command_id, status, message="") -> bool
def on_command(command_type, callback) -> None
def start() -> None  # Blocking main loop
def stop() -> None
```

### 2. ConnectionManager

**File:** `connection_manager.py`

**Responsibility:** WiFi and MQTT connection management

**Uses:** umqtt.robust2 for automatic reconnection

**Reconnection Strategy:**
```
Connection Lost
  |
  v
Exponential Backoff (5s, 10s, 20s, 40s, max 60s)
  |
  v
Attempt Reconnect
  |
  +-- Success -> Resume ops
  +-- Failure -> Backoff again (up to max attempts)
```

### 3. ConfigManager

**File:** `config_manager.py`

**Responsibility:** Configuration persistence

**Config File Format:**
```json
{
  "device_id": "pico-001",
  "device_type": "sensor",
  "wifi": {"ssid": "...", "password": "..."},
  "mqtt": {"broker": "...", "port": 1883, "keepalive": 60},
  "heartbeat_interval": 60,
  "reconnect_delay": 5,
  "max_reconnect_attempts": 10
}
```

### 4. MessageBuilder

**File:** `message_builder.py`

**Responsibility:** Protocol-compliant message formatting

**Outputs:** JSON strings for MQTT payloads

### 5. CommandHandler

**File:** `command_handler.py`

**Responsibility:** Command dispatch to callbacks

**Pattern:** Observer/callback pattern

### 6. MQTTAdapter

**File:** `mqtt_adapter.py`

**Responsibility:** Wrap umqtt.robust2

**Key Methods:**
```python
def connect(broker, port, client_id, keepalive=60)
def publish(topic, payload, qos=1, retain=False)
def subscribe(topic)
def set_last_will(topic, payload, qos=1, retain=True)
def check_msg()
def is_connected()
```

**Why Wrapper?**
- Isolates umqtt.robust2 dependency
- Custom error handling
- Consistent interface
- Easy to test and mock

## Data Flow: Device Startup

```
Start Application
  |
  v
Load config (ConfigManager)
  |
  v
Create PicoSwarmClient
  |
  v
client.connect()
  |
  +-- ConnectionManager.connect_wifi()
  |    +-- machine.WLAN()
  |    +-- Retry with backoff
  |
  +-- ConnectionManager.connect_mqtt()
       +-- MQTTAdapter.connect()
       |    +-- umqtt.robust2.MQTTClient
       +-- MQTTAdapter.set_last_will()
       +-- MQTTAdapter.subscribe(command_topics)
  |
  v
Publish Status (online)
  |
  v
client.start()
  |
  +-- Heartbeat loop (every N seconds)
  +-- Command listener loop (blocking)
  +-- Auto-reconnect if disconnected
```

## Data Flow: Publishing Sensor Data

```
User reads sensor (e.g., temp, humidity)
  |
  v
client.publish_data("DHT22", {"temp": 22.5})
  |
  v
MessageBuilder.build_data_message()
  |
  v
MQTTAdapter.publish()
  |
  +-- Check connection (reconnect if needed)
  +-- Publish to: hub/devices/{device_id}/data
  +-- QoS: 1 (At Least Once)
  +-- Retained: No
  |
  v
umqtt.robust2 handles delivery
  +-- Ensures delivery (QoS 1)
  +-- Retries on failure
  |
  v
Hub receives message
```

## Data Flow: Command Handling

```
Hub publishes command to:
  hub/devices/pico-001/commands/action
  |
  v
umqtt.robust2 receives message
  |
  v
CommandHandler.dispatch()
  |
  +-- Parse topic
  +-- Extract command_type
  +-- Lookup callback
  |
  v
User callback executed
  |
  v
client.acknowledge_command()
  |
  v
MessageBuilder.build_command_ack()
  |
  v
MQTTAdapter.publish() ACK
```

## State Machine

```
[Uninitialized]
  |
  | __init__()
  v
[Initialized]
  |
  | connect()
  v
[Connecting]
  |
  +-- Success -> [Connected]
  +-- Failure -> [Connecting] (retry)
  |
[Connected]
  |
  | start()
  v
[Running]
  - Heartbeat active
  - Command processing
  - Auto-reconnect enabled
  |
  | stop() or disconnect()
  v
[Disconnected]
```

## Design Patterns

### 1. Callback/Observer
```python
@client.on_command("action")
def handle(payload):
    pass
```

### 2. Adapter
```python
class MQTTAdapter:
    def __init__(self):
        self.client = MQTTClient(...)  # Wrap umqtt.robust2
```

### 3. Strategy
Different message formatting strategies in MessageBuilder

### 4. Facade
PicoSwarmClient simplifies complexity

## Error Handling

### Exception Types

```
PicoSwarmException
  +-- ConnectionError
  +-- ConfigurationError
  +-- MessageError
  +-- TimeoutError
```

### Strategy

1. **Network Errors** - Auto-reconnect (umqtt.robust2)
2. **Config Errors** - Fail fast
3. **Runtime Errors** - Publish event, continue
4. **Critical Errors** - Log and may require restart

## Resource Management

### Memory Target

**<25 KB** total (library + buffers)

### Optimization

- Reuse buffers
- No large allocations in loops
- Periodic `gc.collect()`
- umqtt.robust2 is lightweight

### Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Subscriptions | 5-10 | Topics |
| Message size | 1 KB | Typical |
| Callbacks | 5-10 | Handlers |
| Config params | 20-30 | Settings |

## Design Decisions

### 1. umqtt.robust2 (not umqtt.robust)
- Better reconnection handling
- Auto queue management
- Proven for IoT

### 2. Wrapper Pattern
- Isolate dependency
- Easier testing
- Future flexibility

### 3. JSON Messages
- Human-readable
- Language-agnostic
- Extensible

### 4. Last Will Testament
- Automatic offline detection
- Hub doesn't need timeout logic
- Standard MQTT

### 5. QoS 0 for Heartbeat, QoS 1 for Data
- Heartbeat loss acceptable
- Data must be reliable
- Balance bandwidth vs reliability

### 6. Blocking start()
- Simpler for embedded developers
- Single-threaded MicroPython
- Standard pattern

## Future Enhancements

### Phase 2
- TLS/SSL support
- MQTT 5.0 features
- OTA firmware updates
- Message buffering

### Phase 3
- Message compression
- Power saving modes
- Metrics collection
- Web dashboard

---

## See Also

- [README.md](../README.md) - Overview
- [API.md](API.md) - API documentation
- [PROTOCOL.md](PROTOCOL.md) - Protocol specification
