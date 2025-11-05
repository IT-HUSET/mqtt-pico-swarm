# MQTT Communication Protocol: Hub and Pico W IoT System

**Version:** 1.0  
**Date:** November 5, 2025  
**Scope:** Communication protocol between Raspberry Pi 5 Hub (Java) and Raspberry Pi Pico W clients (Python)

---

## Table of Contents

1. [Overview](#overview)
2. [Topic Structure](#topic-structure)
3. [Message Formats](#message-formats)
4. [Quality of Service (QoS) Strategy](#quality-of-service-qos-strategy)
5. [Connection Lifecycle](#connection-lifecycle)
6. [Heartbeat and Device Monitoring](#heartbeat-and-device-monitoring)
7. [Commands and Responses](#commands-and-responses)
8. [Error Handling](#error-handling)
9. [Examples](#examples)

---

## Overview

This document defines the MQTT protocol for communication between a central Hub (Raspberry Pi 5) and multiple Pico W client devices (up to ~100 devices). The communication is **event-driven** with periodic heartbeats for device status monitoring.

### Key Characteristics

- **Broker:** Mosquitto MQTT Broker on Raspberry Pi 5
- **Port:** 1883 (standard MQTT)
- **Protocol Version:** MQTT 5.0 compatible
- **Architecture:** Hub-and-Spoke with Last Will Testament support
- **Communication Pattern:** Bidirectional (Hub <-> Pico W)

---

## Topic Structure

### 1. General Topic Hierarchy

All topics follow a hierarchical structure to organize communication:

```
hub/
  devices/
    {device_id}/
      status
      data
      heartbeat
      events
      commands/
        {command_type}
    registry
    broadcast
  system/
    health
    metrics
```

### 2. Detailed Topic Definitions

#### **Device Status Topics** (Hub <- Pico W)

| Topic | Purpose | QoS | Retained | Frequency |
|-------|---------|-----|----------|-----------|
| `hub/devices/{device_id}/status` | Current device status (online/offline) | 1 | Yes | On change |
| `hub/devices/{device_id}/heartbeat` | Periodic heartbeat signal | 0 | No | Every 60 seconds |
| `hub/devices/{device_id}/data` | Sensor/event data from device | 1 | No | Event-driven |
| `hub/devices/{device_id}/events` | Device events (errors, warnings) | 1 | No | Event-driven |

#### **Device Command Topics** (Hub -> Pico W)

| Topic | Purpose | QoS | Retained | Direction |
|-------|---------|-----|----------|-----------|
| `hub/devices/{device_id}/commands/config` | Configuration updates | 2 | No | Hub -> Pico |
| `hub/devices/{device_id}/commands/action` | Action commands (on/off, start/stop) | 1 | No | Hub -> Pico |
| `hub/devices/{device_id}/commands/restart` | Restart device | 2 | No | Hub -> Pico |

#### **Broadcast Topics** (Hub -> All Pico W)

| Topic | Purpose | QoS |
|-------|---------|-----|
| `hub/broadcast/message` | Broadcast messages to all devices | 0 |
| `hub/broadcast/config-update` | System-wide configuration updates | 1 |

#### **System Topics**

| Topic | Purpose | QoS | Retained |
|-------|---------|-----|----------|
| `hub/system/health` | Hub health status | 1 | Yes |
| `hub/devices/registry` | Active devices list | 1 | Yes |

### 3. Topic Naming Conventions

- Use **lowercase** with **hyphens** for multi-word topics
- Use **{device_id}** as placeholder for actual device identifiers
- Device IDs: `pico-001`, `pico-002`, etc.
- Example: `hub/devices/pico-001/status`

---

## Message Formats

### 1. Device Status Message

**Topic:** `hub/devices/{device_id}/status`

**Payload (JSON):**
```json
{
  "device_id": "pico-001",
  "device_type": "temperature_sensor",
  "status": "online",
  "timestamp": "2025-11-05T10:37:00Z",
  "firmware_version": "1.2.0",
  "ip_address": "192.168.1.101",
  "signal_strength": -65
}
```

**Fields:**
- `device_id` (string): Unique device identifier
- `device_type` (string): Type of device (temperature_sensor, motion_detector, etc.)
- `status` (string): "online" or "offline"
- `timestamp` (ISO 8601): UTC timestamp
- `firmware_version` (string): Device firmware version
- `ip_address` (string): Device IP address
- `signal_strength` (int): WiFi signal strength in dBm

### 2. Heartbeat Message

**Topic:** `hub/devices/{device_id}/heartbeat`

**Payload (JSON):**
```json
{
  "device_id": "pico-001",
  "timestamp": "2025-11-05T10:37:00Z",
  "uptime_seconds": 3600,
  "memory_free": 45000,
  "error_count": 0
}
```

**Fields:**
- `device_id` (string): Unique device identifier
- `timestamp` (ISO 8601): UTC timestamp
- `uptime_seconds` (integer): Device uptime in seconds
- `memory_free` (integer): Free memory in bytes
- `error_count` (integer): Number of errors since last heartbeat

### 3. Sensor Data Message

**Topic:** `hub/devices/{device_id}/data`

**Payload (JSON) - Example for Temperature Sensor:**
```json
{
  "device_id": "pico-001",
  "sensor_type": "DHT22",
  "data": {
    "temperature": 22.5,
    "humidity": 65.3
  },
  "timestamp": "2025-11-05T10:37:15Z",
  "unit": "celsius"
}
```

**Generic Fields:**
- `device_id` (string): Unique device identifier
- `sensor_type` (string): Type of sensor
- `data` (object): Sensor-specific data (structure varies per sensor type)
- `timestamp` (ISO 8601): When measurement was taken
- `unit` (string): Unit of measurement (optional)

### 4. Event Message

**Topic:** `hub/devices/{device_id}/events`

**Payload (JSON):**
```json
{
  "device_id": "pico-001",
  "event_type": "error",
  "event_code": "SENSOR_TIMEOUT",
  "message": "Temperature sensor did not respond within timeout period",
  "severity": "warning",
  "timestamp": "2025-11-05T10:37:20Z"
}
```

**Fields:**
- `device_id` (string): Unique device identifier
- `event_type` (string): "error", "warning", "info"
- `event_code` (string): Machine-readable event identifier
- `message` (string): Human-readable description
- `severity` (string): "critical", "error", "warning", "info"
- `timestamp` (ISO 8601): When event occurred

### 5. Command Message

**Topic:** `hub/devices/{device_id}/commands/{command_type}`

**Payload (JSON) - Example Config Command:**
```json
{
  "command_id": "cmd-12345",
  "device_id": "pico-001",
  "type": "update_config",
  "payload": {
    "heartbeat_interval": 120,
    "sensor_sample_rate": 10,
    "max_retries": 3
  },
  "timestamp": "2025-11-05T10:37:30Z"
}
```

**Fields:**
- `command_id` (string): Unique command identifier for tracking
- `device_id` (string): Target device identifier
- `type` (string): Type of command
- `payload` (object): Command-specific parameters
- `timestamp` (ISO 8601): When command was issued

**Payload (JSON) - Example Action Command:**
```json
{
  "command_id": "cmd-12346",
  "device_id": "pico-001",
  "type": "toggle_relay",
  "payload": {
    "relay_id": 1,
    "state": "on"
  },
  "timestamp": "2025-11-05T10:37:35Z"
}
```

### 6. Command Acknowledgment

**Topic:** `hub/devices/{device_id}/commands/ack`

**Payload (JSON):**
```json
{
  "command_id": "cmd-12345",
  "device_id": "pico-001",
  "status": "acknowledged",
  "result": "success",
  "message": "Configuration updated successfully",
  "timestamp": "2025-11-05T10:37:45Z"
}
```

**Fields:**
- `command_id` (string): Reference to original command
- `device_id` (string): Device identifier
- `status` (string): "acknowledged", "processing", "success", "failed"
- `result` (string): "success" or "error"
- `message` (string): Optional details
- `timestamp` (ISO 8601): When acknowledgment was sent

### 7. Device Registry Message

**Topic:** `hub/devices/registry`

**Payload (JSON):**
```json
{
  "active_devices": [
    {
      "device_id": "pico-001",
      "device_type": "temperature_sensor",
      "status": "online",
      "last_seen": "2025-11-05T10:37:00Z",
      "firmware_version": "1.2.0"
    },
    {
      "device_id": "pico-002",
      "device_type": "motion_detector",
      "status": "online",
      "last_seen": "2025-11-05T10:36:55Z",
      "firmware_version": "1.1.5"
    }
  ],
  "total_devices": 2,
  "timestamp": "2025-11-05T10:37:00Z"
}
```

---

## Quality of Service (QoS) Strategy

### 1. QoS Levels Overview

According to MQTT 5.0 specification:

- **QoS 0 (At Most Once):** Message may be lost. No acknowledgment.
- **QoS 1 (At Least Once):** Message delivered at least once. Broker stores until acknowledged.
- **QoS 2 (Exactly Once):** Message delivered exactly once. Highest overhead.

### 2. QoS Assignment Strategy

| Message Type | QoS | Reasoning |
|--------------|-----|-----------|
| Heartbeat | 0 | Periodic; loss is acceptable (next heartbeat in 60s) |
| Status updates | 1 | Important for tracking device state |
| Sensor data | 1 | Data should be reliably delivered |
| Events | 1 | Error/warning events must be recorded |
| Configuration commands | 2 | Must be delivered exactly once, not duplicated |
| Restart commands | 2 | Critical; must not execute twice |
| Action commands | 1 | Important but not critical if missed by one heartbeat |
| Broadcast messages | 0 | Non-critical system messages |

### 3. Retained Messages

**Retained messages persist on the broker:**

| Topic | Retained | Reason |
|-------|----------|--------|
| `hub/devices/{device_id}/status` | Yes | Hub needs current status on connection |
| `hub/devices/registry` | Yes | System needs current device registry |
| `hub/system/health` | Yes | Track last known hub health |
| Heartbeats | No | No value retaining old heartbeats |
| Sensor data | No | Old data not useful |
| Events | No | Historical events in database |
| Commands | No | Commands are transient |

---

## Connection Lifecycle

### 1. Device Registration Flow

```
Pico W Starts Up
    |
    +-- Connect to WiFi
    |
    +-- Connect to MQTT Broker (port 1883)
    |
    +-- Subscribe to:
    |   - hub/devices/{device_id}/commands/config
    |   - hub/devices/{device_id}/commands/action
    |   - hub/broadcast/#
    |
    +-- Publish Status Message (QoS 1, Retained)
    |   Topic: hub/devices/{device_id}/status
    |
    +-- Start Heartbeat Timer (60 second interval)
    |
    +-- Ready for Commands
```

### 2. Connection Parameters

**Last Will Testament (LWT):**

When a Pico W connects, it registers a Last Will message that the broker will publish if the connection is lost:

```json
Topic: hub/devices/{device_id}/status
Payload: {
  "device_id": "pico-001",
  "status": "offline",
  "timestamp": "2025-11-05T10:38:00Z"
}
QoS: 1
Retained: Yes
```

**Connection Settings (Pico W):**
- Clean Session: False (retain session state)
- Keep Alive: 60 seconds
- Connection Timeout: 30 seconds
- Auto-Reconnect: Yes (with exponential backoff)

### 3. Graceful Shutdown

```
Pico W Shutdown Sequence:
  1. Stop publishing heartbeats
  2. Publish final status (status: "offline")
  3. Disconnect from MQTT
  4. Disconnect from WiFi
```

---

## Heartbeat and Device Monitoring

### 1. Heartbeat Strategy

Each Pico W device publishes a heartbeat message every **60 seconds**.

**Heartbeat Message:**
```json
{
  "device_id": "pico-001",
  "timestamp": "2025-11-05T10:37:00Z",
  "uptime_seconds": 3600,
  "memory_free": 45000,
  "error_count": 0
}
```

**Topic:** `hub/devices/{device_id}/heartbeat`  
**QoS:** 0 (fire and forget)  
**Retained:** No  
**Frequency:** Every 60 seconds

### 2. Hub Monitoring

The Hub tracks device status:

**Device Status Check Algorithm:**

```
FOR EACH device:
  IF (current_time - last_heartbeat > 180 seconds):
    Mark device as "OFFLINE"
    Publish offline status to registry
    Trigger alert
  ELSE IF (current_time - last_heartbeat > 120 seconds):
    Mark device as "SUSPECT"
    Log warning
  ELSE:
    Mark device as "ONLINE"
```

**Timeout Values:**
- **Heartbeat Expected Every:** 60 seconds
- **Grace Period (SUSPECT):** 120 seconds (2 missed heartbeats)
- **Offline Threshold:** 180 seconds (3 missed heartbeats)

### 3. Device Registry Update

The Hub maintains an active device registry topic:

**Topic:** `hub/devices/registry`  
**Update Frequency:** Every device status change or every 60 seconds  
**QoS:** 1  
**Retained:** Yes

---

## Commands and Responses

### 1. Command Flow

```
Hub Issues Command
    |
    +-- Publish to: hub/devices/{device_id}/commands/{type}
    |                  (QoS 2, not retained)
    |
Pico W Receives Command
    |
    +-- Parse and validate
    |
    +-- Execute command
    |
    +-- Publish Acknowledgment
         Topic: hub/devices/{device_id}/commands/ack
         (QoS 1, includes result status)
```

### 2. Command Types

#### **Config Command**
- **Topic:** `hub/devices/{device_id}/commands/config`
- **QoS:** 2
- **Purpose:** Update device configuration
- **Example Parameters:** heartbeat_interval, sensor_sample_rate, etc.

#### **Action Command**
- **Topic:** `hub/devices/{device_id}/commands/action`
- **QoS:** 1
- **Purpose:** Control device behavior
- **Example Parameters:** relay_state, led_control, etc.

#### **Restart Command**
- **Topic:** `hub/devices/{device_id}/commands/restart`
- **QoS:** 2
- **Purpose:** Restart the device
- **Payload:** Empty or timestamp

#### **Broadcast Command**
- **Topic:** `hub/broadcast/config-update`
- **QoS:** 1
- **Purpose:** Update multiple devices at once
- **Example:** Firmware update notification

### 3. Acknowledgment Protocol

All commands require acknowledgment:

**Pico W Acknowledgment:**
```json
{
  "command_id": "cmd-12345",
  "device_id": "pico-001",
  "status": "success",
  "timestamp": "2025-11-05T10:37:45Z"
}
```

**Possible Status Values:**
- `acknowledged`: Command received and being processed
- `processing`: Command in progress
- `success`: Command completed successfully
- `failed`: Command execution failed
- `timeout`: Command execution timed out

### 4. Hub Timeout for Acknowledgments

**Acknowledgment Timeout Algorithm:**

```
FOR EACH command sent:
  Start timer for 30 seconds
  
  IF acknowledgment received:
    Log success
    Clear timer
  
  ELSE IF timer expires:
    Mark command as "NO_ACK"
    Log warning
    Optionally retry or escalate
```

---

## Error Handling

### 1. Connection Errors

**Pico W Behavior:**

```
If connection lost:
  1. Stop all operations
  2. Attempt reconnect (every 5 seconds, max 10 times)
  3. If reconnect fails: Enter offline mode
  4. Resume operations when reconnected
  5. Last Will triggers on broker (marks offline)
```

**Hub Behavior:**

```
If Pico W goes offline:
  1. Last Will message received (via LWT)
  2. Update device status to "offline"
  3. Update device registry
  4. Log disconnection event
  5. Trigger monitoring alert
```

### 2. Message Errors

**Pico W - Receive Error:**

```json
{
  "device_id": "pico-001",
  "event_type": "error",
  "event_code": "INVALID_MESSAGE_FORMAT",
  "message": "Received malformed JSON on commands topic",
  "severity": "warning",
  "timestamp": "2025-11-05T10:38:00Z"
}
```

**Hub - Receive Error:**

```json
{
  "hub_event": "malformed_message",
  "source_device": "pico-001",
  "topic": "hub/devices/pico-001/data",
  "error": "JSON parsing failed",
  "timestamp": "2025-11-05T10:38:00Z"
}
```

### 3. Timeout Errors

**Command Timeout:**

If Pico W doesn't acknowledge within 30 seconds:

```json
{
  "command_id": "cmd-12345",
  "device_id": "pico-001",
  "status": "no_acknowledgment",
  "error": "No ACK received within 30 seconds",
  "timestamp": "2025-11-05T10:38:15Z"
}
```

### 4. Error Event Codes

**Common Error Codes:**

| Code | Severity | Description |
|------|----------|-------------|
| `SENSOR_TIMEOUT` | WARNING | Sensor not responding |
| `WIFI_DISCONNECT` | ERROR | WiFi connection lost |
| `MQTT_DISCONNECT` | ERROR | MQTT connection lost |
| `INVALID_CONFIG` | ERROR | Configuration parameter rejected |
| `MEMORY_LOW` | WARNING | Available memory critically low |
| `COMMAND_FAILED` | ERROR | Command execution failed |
| `INVALID_MESSAGE_FORMAT` | WARNING | Malformed message received |

---

## Examples

### Example 1: Complete Device Connection Sequence

```
Time: 10:30:00 - Pico W boots
  -> Connects to WiFi
  -> Connects to MQTT (client_id: pico-001, clean_session: false)
  -> Subscribes to: hub/devices/pico-001/commands/#
  -> Subscribes to: hub/broadcast/#

Time: 10:30:02 - Pico W sends status
  -> Publishes (QoS 1, Retained):
    Topic: hub/devices/pico-001/status
    Payload: {"device_id": "pico-001", "status": "online", ...}
  -> Sets LWT for status: offline

Time: 10:30:05 - Hub receives status
  -> Updates database: pico-001 = ONLINE
  -> Updates registry topic

Time: 10:31:00 - Pico W sends heartbeat
  -> Publishes (QoS 0):
    Topic: hub/devices/pico-001/heartbeat
    Payload: {"device_id": "pico-001", "timestamp": "...", ...}

Time: 10:32:00 - Hub sends config command
  -> Publishes (QoS 2):
    Topic: hub/devices/pico-001/commands/config
    Payload: {"command_id": "cmd-001", "type": "update_config", ...}

Time: 10:32:01 - Pico W receives and processes command
  -> Updates configuration
  -> Publishes (QoS 1):
    Topic: hub/devices/pico-001/commands/ack
    Payload: {"command_id": "cmd-001", "status": "success", ...}

Time: 10:32:02 - Hub receives acknowledgment
  -> Logs command success
  -> Updates command history in database
```

### Example 2: Device Timeout and Offline Detection

```
Time: 10:35:00 - Pico W last heartbeat
  -> Hub marks: ONLINE

Time: 10:36:30 - Pico W WiFi connection lost
  -> MQTT connection lost (Last Will triggered)
  -> Hub receives LWT message:
    Topic: hub/devices/pico-001/status
    Payload: {"device_id": "pico-001", "status": "offline", ...}

Time: 10:36:31 - Hub processes offline status
  -> Updates database: pico-001 = OFFLINE
  -> Updates registry topic
  -> Logs device disconnection
  -> Triggers monitoring alert

Time: 10:37:00 - Pico W reconnects
  -> Connects to WiFi
  -> Connects to MQTT
  -> Publishes new status (online)
  -> Hub detects reconnection
```

### Example 3: Sensor Data Collection (Event-Driven)

```
Time: 10:40:15 - Temperature sensor reports new reading
  -> Pico W reads: temp=22.5C, humidity=65%
  -> Publishes (QoS 1):
    Topic: hub/devices/pico-001/data
    Payload: {
      "device_id": "pico-001",
      "sensor_type": "DHT22",
      "data": {"temperature": 22.5, "humidity": 65.0},
      "timestamp": "2025-11-05T10:40:15Z"
    }

Time: 10:40:16 - Hub receives sensor data
  -> Validates JSON
  -> Stores in database
  -> Updates UI/dashboard
  -> Checks thresholds (trigger alerts if needed)
```

---

## Implementation Checklist

### Pico W Client Requirements

- [ ] WiFi connection with auto-reconnect
- [ ] MQTT connection with Last Will Testament
- [ ] Topic subscriptions for all command types
- [ ] JSON serialization/deserialization
- [ ] Heartbeat timer (60 second interval)
- [ ] Command acknowledgment mechanism
- [ ] Error event publishing
- [ ] Graceful reconnection handling
- [ ] Configuration persistence (JSON file)

### Hub Server Requirements

- [ ] MQTT client connection to Mosquitto
- [ ] Topic subscriptions for all device topics
- [ ] Device registry database table
- [ ] Heartbeat monitoring with timeout detection
- [ ] Command sending and acknowledgment tracking
- [ ] Last Will Testament handling
- [ ] Error event logging
- [ ] Device status dashboard
- [ ] Command history tracking

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-05 | Initial protocol specification |

---

## Document References

- MQTT 5.0 Specification: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- Raspberry Pi Pico W: https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html
- MicroPython: https://micropython.org/
- Eclipse Mosquitto: https://mosquitto.org/
