# Architecture: MQTT Pico Swarm

**Version:** 1.0  
**Date:** November 5, 2025

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Module Structure](#module-structure)
4. [Core Classes and Components](#core-classes-and-components)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Design Patterns](#design-patterns)
7. [State Management](#state-management)
8. [Error Handling Strategy](#error-handling-strategy)
9. [Resource Management](#resource-management)
10. [Thread Safety and Concurrency](#thread-safety-and-concurrency)
11. [Extensibility Points](#extensibility-points)
12. [Design Decisions and Rationale](#design-decisions-and-rationale)

---

## System Overview

### Goal

Provide a lightweight, robust MicroPython library that abstracts away MQTT complexity and protocol details, allowing Pico W developers to focus on application logic.

### Key Design Principles

1. **Separation of Concerns** - Clear boundaries between connection management, message formatting, and application logic
2. **Low Resource Footprint** - Minimal memory usage suitable for resource-constrained microcontrollers
3. **Robustness** - Automatic reconnection, graceful error handling, event-driven architecture
4. **Protocol Compliance** - Strictly adheres to defined MQTT protocol (see PROTOCOL.md)
5. **Easy to Use** - High-level API that hides MQTT details
6. **Testable** - Modular design enables unit testing of components

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
|   - MQTTAdapter (umqtt wrapper)
|   - WiFiManager (network)
|
+-- External Dependencies
    - umqtt.robust (MQTT protocol)
    - MicroPython stdlib
    - Mosquitto broker
```

---

## High-Level Architecture

### Component Interaction

```
PicoSwarmClient (Main API)
|  - User-facing API
|  - Orchestrates all components
|
+-- MessageBuilder          ConnectionManager      ConfigManager        CommandHandler
|   - Format msgs           - WiFi/MQTT            - Config             - Callbacks
|   - Validate              - Reconnect            - Persist            - Dispatch
|   - Protocol OK           - Heartbeat            - Update             - ACK
|
+-- MQTTAdapter (umqtt.robust)
    - Connection mgmt
    - Pub/Sub
    |
    +-- WiFi/Network (machine.WLAN)
        |
        +-- Mosquitto Broker (Remote)
```

---

## Module Structure

### Directory Layout

```
mqtt-pico-swarm/
|
+-- src/
|   +-- mqtt_pico_swarm.py       # Main client class
|   +-- message_builder.py       # Protocol message formatting
|   +-- connection_manager.py    # WiFi/MQTT connection handling
|   +-- config_manager.py        # Configuration file handling
|   +-- command_handler.py       # Command dispatch and callbacks
|   +-- mqtt_adapter.py          # Wrapper around umqtt.robust
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
    +-- test_message_builder.py
    +-- test_config_manager.py
    +-- test_command_handler.py
```

### Module Dependencies

```
mqtt_pico_swarm.py (main)
  |
  +-- message_builder.py
  +-- connection_manager.py
  |    +-- mqtt_adapter.py
  |    +-- config_manager.py
  |    +-- utils.py
  +-- config_manager.py
  |    +-- constants.py
  |    +-- errors.py
  +-- command_handler.py
  |    +-- constants.py
  |    +-- errors.py
  +-- mqtt_adapter.py
  |    +-- umqtt.robust
  |    +-- utils.py
  |    +-- constants.py
  +-- errors.py (no internal dependencies)
  +-- constants.py (no internal dependencies)
  +-- utils.py (no internal dependencies)
```

---

## Core Classes and Components

### 1. PicoSwarmClient (Main API Class)

**Responsibility:** Orchestrate all components and provide public API

**Key Methods:**
- `__init__(config_file, debug)` - Initialize client
- `connect()` - Establish connections
- `disconnect()` - Clean shutdown
- `publish_data()` - Send sensor data
- `publish_event()` - Send events
- `acknowledge_command()` - Reply to commands
- `on_command()` - Register callbacks
- `start()` - Begin heartbeat and listening
- `stop()` - Stop operations

**Instance Variables:**
```python
self.config = None              # ConfigManager instance
self.mqtt_adapter = None        # MQTTAdapter instance
self.connection_mgr = None      # ConnectionManager instance
self.command_handler = None     # CommandHandler instance
self.message_builder = None     # MessageBuilder instance

self._callbacks = {}            # Event callbacks
self._running = False           # Main loop flag
self._debug = False             # Debug logging
```

**Example Usage:**
```python
client = PicoSwarmClient("config.json")
client.connect()
client.start()
```

---

### 2. ConnectionManager

**Responsibility:** Manage WiFi and MQTT connections with automatic reconnection

**Key Methods:**
- `connect_wifi()` - Establish WiFi connection
- `connect_mqtt()` - Establish MQTT connection
- `disconnect()` - Gracefully disconnect
- `is_connected()` - Check connection status
- `reconnect_if_needed()` - Auto-reconnect logic
- `get_connection_stats()` - Connection statistics

**Reconnection Strategy:**

```
Connection lost
  |
  v
Wait (exponential backoff)
  |
  +-- First attempt: 5s
  +-- Second attempt: 10s
  +-- Third attempt: 20s
  +-- Max delay: 60s
  |
  v
Attempt reconnect
  |
  +-- Success? -> Connected
  +-- Failed? -> Wait again (up to max retries)
```

---

### 3. ConfigManager

**Responsibility:** Load, validate, and persist device configuration

**Key Methods:**
- `load_config(filename)` - Load JSON config
- `get(key, default)` - Get config value
- `set(key, value)` - Set config value
- `save()` - Persist config to file
- `validate()` - Validate configuration

**Configuration File Format:**
```json
{
  "device_id": "pico-001",
  "device_type": "sensor",
  "wifi": {
    "ssid": "network",
    "password": "password"
  },
  "mqtt": {
    "broker": "192.168.1.100",
    "port": 1883,
    "keepalive": 60
  },
  "heartbeat_interval": 60
}
```

---

### 4. MessageBuilder

**Responsibility:** Format messages according to protocol specification

**Key Methods:**
- `build_status_message()` - Device status
- `build_heartbeat_message()` - Periodic heartbeat
- `build_data_message()` - Sensor data
- `build_event_message()` - Error/warning events
- `build_command_ack()` - Command acknowledgment
- `validate_json()` - JSON validation

**Message Format Strategy:**
- All messages are JSON
- Consistent structure across message types
- Timestamp always included
- Device ID always included
- Validated before transmission

---

### 5. CommandHandler

**Responsibility:** Dispatch incoming commands to registered callbacks

**Key Methods:**
- `register_callback(command_type, callback)` - Register handler
- `dispatch(command)` - Route command to handler
- `handle_config_command()` - Default config handler
- `handle_restart_command()` - Default restart handler

**Command Dispatch Flow:**

```
MQTT Message Received
  |
  v
Parse JSON (topic + payload)
  |
  v
Extract command_type
  |
  v
Lookup registered callback
  |
  +-- Found? -> Call callback
  |            +-- Callback calls acknowledge_command()
  |
  +-- Not found? -> Log warning
```

---

### 6. MQTTAdapter

**Responsibility:** Provide thin wrapper around umqtt.robust

**Key Methods:**
- `connect()` - Establish MQTT connection
- `disconnect()` - Close connection
- `publish()` - Publish message
- `subscribe()` - Subscribe to topic
- `is_connected()` - Check connection status
- `loop()` - Check for incoming messages

**Why Wrapper?**
- Isolate umqtt.robust dependency
- Easy to swap implementation if needed
- Custom error handling
- Consistent interface

---

## Data Flow Diagrams

### 1. Device Startup Flow

```
Start Application
  |
  v
Load Configuration (ConfigManager)
  |
  v
Create Client (PicoSwarmClient)
  |
  v
Connect WiFi (ConnectionManager -> WiFiManager)
  |
  +-- Success? -> Continue
  +-- Failure? -> Retry with backoff
  |
  v
Connect MQTT (ConnectionManager -> MQTTAdapter)
  |
  +-- Subscribe to command topics
  +-- Set up Last Will Testament
  +-- Success? -> Continue
  +-- Failure? -> Retry with backoff
  |
  v
Publish Status Message (MessageBuilder)
  Topic: hub/devices/{device_id}/status
  QoS: 1, Retained: Yes
  |
  v
Ready for Commands
  |
  v
Start Main Loop (client.start())
  |
  +-- Periodic heartbeat (every N seconds)
  +-- Command listener (blocking loop)
  +-- Auto-reconnect if needed
```

### 2. Sensor Data Publishing Flow

```
Application: read_sensor()
  |
  v
Collect sensor data (e.g., temp, humidity)
  |
  v
Call: client.publish_data("DHT22", {"temp": 22.5, "humidity": 65})
  |
  v
MessageBuilder.build_data_message()
  |
  +-- Validate input data
  +-- Add timestamp
  +-- Add device_id
  +-- Format as JSON
  +-- Return formatted message
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
Hub receives message
  |
  v
Return True (success) to application
```

### 3. Command Handling Flow

```
Hub publishes command
  Topic: hub/devices/{device_id}/commands/{type}
  |
  v
Pico W MQTT loop receives message
  |
  v
MQTTAdapter extracts topic and payload
  |
  v
CommandHandler.dispatch()
  |
  +-- Parse JSON payload
  +-- Extract command_type from topic
  +-- Lookup registered callback
  |
  v
Execute callback (user code)
  |
  +-- Perform action
  +-- Determine result (success/failed)
  +-- Call acknowledge_command()
  |
  v
MessageBuilder.build_command_ack()
  |
  v
MQTTAdapter.publish() ACK
  Topic: hub/devices/{device_id}/commands/ack
  QoS: 1
  |
  v
Hub receives acknowledgment
```

### 4. Connection Loss and Recovery Flow

```
MQTT Connection Active
  |
  v
[Network disruption]
  |
  v
Connection Lost
  |
  v
LastWillTestament triggered
  +-- Hub receives: {status: "offline"}
  |
  v
ConnectionManager detects loss
  |
  v
Start reconnection timer
  Delay: exponential backoff
  |
  v
Attempt reconnect to WiFi
  |
  +-- Success? -> Continue
  +-- Failure? -> Retry
  |
  v
Attempt reconnect to MQTT
  |
  +-- Success? -> Continue
  +-- Failure? -> Retry
  |
  v
Subscribe to command topics
  |
  v
Publish Status (online)
  |
  v
Trigger on_connect() callback
  |
  v
Resume normal operation
```

---

## Design Patterns

### 1. Callback/Observer Pattern

Used for event handling (commands, connection events).

```python
@client.on_command("action")
def handle_action(payload):
    # This is an observer callback
    pass

@client.on_connect
def on_connected():
    # Another observer
    pass
```

**Why:** Decouples event producers from consumers. Allows multiple handlers for same event.

### 2. Strategy Pattern

MessageBuilder uses different strategies for different message types.

```python
# Different strategies for formatting messages
MessageBuilder.build_status_message()
MessageBuilder.build_data_message()
MessageBuilder.build_event_message()
```

**Why:** Each message type has unique formatting rules. Strategy pattern keeps them separate.

### 3. Adapter Pattern

MQTTAdapter wraps umqtt.robust.

```python
class MQTTAdapter:
    def __init__(self, umqtt_client):
        self.client = umqtt_client  # Adapted library
```

**Why:** Isolate third-party library dependency. Easy to swap implementation.

### 4. Configuration Pattern

ConfigManager handles all configuration concerns.

```python
config = ConfigManager("config.json")
config.get("device_id")
config.set("heartbeat_interval", 120)
config.save()
```

**Why:** Centralize configuration logic. Easy to extend with new config sources.

---

## State Management

### Client States

```
[Uninitialized]
(Before connect())
    |
    | connect()
    v
[Connecting]
(WiFi + MQTT connecting)
    |
    +-- Success ---> [Connected]        Failure ---> [Failed]
                     (Ready to use)     (Retry loop)
                     |                  |
                     +-- Can use:       +-- Auto-reconnect
                     |   publish       |   with backoff
                     |   commands      |
                     |                 |
                     +-- disconnect()
                     |   or error
                     |                 |
                     +-- <reconnect> --+
                     |
                     v
                [Disconnected]
                (Offline/Shutdown)
```

---

## Error Handling Strategy

### Exception Hierarchy

```
PicoSwarmException (base)
  |
  +-- ConnectionError
  |    +-- WiFiConnectionError
  |    +-- MQTTConnectionError
  |
  +-- ConfigurationError
  |    +-- InvalidConfigFile
  |    +-- MissingConfigValue
  |
  +-- MessageError
  |    +-- InvalidMessageFormat
  |    +-- MessageTooLarge
  |
  +-- TimeoutError
       +-- ReconnectionTimeout
```

### Error Handling Flow

```
Operation attempted
  |
  v
Try execution
  |
  +-- Expected error? -> Catch, log, handle gracefully
  +-- Network error? -> Trigger reconnection
  +-- Config error? -> Publish event, continue if possible
  +-- Unexpected error? -> Log, publish critical event
  |
  v
Publish event (for critical errors)
  |
  v
Call error callback (if registered)
  |
  v
Continue operation or shutdown
```

---

## Resource Management

### Memory Optimization

**Target:** <20 KB for library + buffers

**Strategies:**
1. Minimal object allocation in loops
2. Use generators instead of lists where possible
3. Reuse buffers for repeated operations
4. Explicit garbage collection at strategic points

### Resource Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Topics per device | 5-10 | Subscriptions + publishes |
| Message size | ~1 KB | Typical sensor data |
| Callbacks | 5-10 | Command handlers + events |
| Config items | 20-30 | Configuration parameters |
| Memory buffer | 10-15 KB | MQTT buffers + queues |

---

## Design Decisions and Rationale

### 1. Why Blocking `start()` Instead of Async?

**Decision:** `client.start()` is a blocking call that runs the main loop indefinitely.

**Rationale:**
- Simpler for beginners (no async/await concepts)
- Lower memory overhead than asyncio
- Standard pattern in embedded systems

### 2. Why JSON for Messages?

**Decision:** All MQTT payloads are JSON.

**Rationale:**
- Human-readable for debugging
- Easy to parse on hub (any language)
- Extensible structure
- Good compromise between size and readability

### 3. Why Separate ConfigManager?

**Decision:** Configuration isolated in dedicated class.

**Rationale:**
- Testable independently
- Easy to extend with new config sources
- Centralized validation
- Persistent configuration on device

### 4. Why MessageBuilder Class?

**Decision:** All message formatting in dedicated class.

**Rationale:**
- Testable independently
- Consistent protocol implementation
- Easy to add new message types
- Centralized validation

### 5. Why Wrapper Around umqtt?

**Decision:** MQTTAdapter wraps umqtt.robust instead of using directly.

**Rationale:**
- Isolates external dependency
- Easy to add custom error handling
- Consistent error types
- Could swap implementations in future

### 6. Why Last Will Testament (LWT)?

**Decision:** All devices register LWT when connecting.

**Rationale:**
- Automatic offline detection
- Immediate notification when device disconnects
- Works even if device crashes
- Standard MQTT feature

### 7. Why QoS 1 for Data, QoS 0 for Heartbeat?

**Decision:** Different QoS levels for different message types.

**Rationale:**
- Heartbeat loss is acceptable (next one in 60s)
- Data loss must be minimized
- Reduces bandwidth for frequent heartbeats
- Balances reliability vs. efficiency

---

## Future Enhancements

### Phase 2: Advanced Features

- TLS/SSL support for secure connections
- MQTT 5.0 user properties
- Over-The-Air (OTA) firmware updates
- Batch message sending
- Local data buffering during offline periods
- Web-based configuration interface

### Phase 3: Performance

- Message compression
- Binary message format option
- Connection pooling for multiple clients
- Metrics collection
- Power consumption optimization

### Phase 4: Developer Experience

- Web dashboard for monitoring
- CLI tools for testing
- VS Code extension
- Web-based simulator

---

## See Also

- [README.md](../README.md) - Project overview
- [API.md](API.md) - Public API documentation
- [PROTOCOL.md](PROTOCOL.md) - MQTT protocol specification
- [SETUP.md](SETUP.md) - Installation guide
