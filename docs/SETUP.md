# Setup Guide: MQTT Pico Swarm

**Version:** 1.2  
**Date:** November 5, 2025  
**Focus:** MicroPython Development

---

## Important Note

This guide focuses on **MicroPython development** for the mqtt-pico-swarm library. The official "Getting Started with Pico" guide covers C/C++ development, which is a different approach. This guide is specifically for Python developers using MicroPython.

**Not following C/C++ SDK?** That's intentional - we use MicroPython for this IoT library.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Development Environment Setup](#development-environment-setup)
4. [Pico W Setup](#pico-w-setup)
5. [Library Installation](#library-installation)
6. [Configuration](#configuration)
7. [First Device Deployment](#first-device-deployment)
8. [Testing and Verification](#testing-and-verification)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide helps you install and configure the **mqtt-pico-swarm** library on your Raspberry Pi Pico W device(s) using **MicroPython**. The library provides a high-level interface for communicating with a central MQTT hub.

### System Architecture

```
MQTT Broker (on hub)
        |
        |
   +----+-----+
   |          |
Pico W     Pico W
(Client)   (Client)
```

The **mqtt-pico-swarm** library runs on your Pico W devices and connects to an MQTT broker (typically Mosquitto running MQTT 3.1.1) on a hub server. The hub implementation is separate and can be in any language.

**This guide covers:** Pico W client setup with MicroPython only  
**Hub setup:** Refer to your hub implementation documentation  
**C/C++ development?** Refer to the official Getting Started with Pico guide

---

## Prerequisites

### Hardware

- **Raspberry Pi Pico W** (one or more devices)
- USB cable for flashing and power
- WiFi network (2.4 GHz)

### Software

- **MicroPython 1.20+** firmware (for Pico W)
- **Access to MQTT broker** - You need:
  - Broker IP address (e.g., `192.168.1.100`)
  - Broker port (default: `1883`)
  - WiFi SSID and password

### Development Tools

- **Visual Studio Code** v1.99.3 or later
- **Raspberry Pi Pico extension** (for VS Code)
- **MicroPico extension** (for MicroPython support in VS Code)

---

## Development Environment Setup

### 1. Install Visual Studio Code

Download and install VS Code from https://code.visualstudio.com/

### 2. Install Raspberry Pi Pico Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X or Cmd+Shift+X on macOS)
3. Search for **"Raspberry Pi Pico"** (official extension by Raspberry Pi)
4. Install the extension
5. The extension will guide you through dependency installation

**Extension ID:** `raspberry-pi.raspberry-pi-pico`

**Note:** The Pico extension supports both C/C++ and MicroPython development.

### 3. Install MicroPico Extension

1. Open VS Code Extensions
2. Search for **"MicroPico"**
3. Install the MicroPico extension by DavidHouchens
4. This enables MicroPython support in VS Code

**MicroPico features:**
- REPL connection
- File sync to Pico W
- Execute files directly
- Serial monitoring

### 4. Platform-Specific Requirements

#### Windows 10/11
No additional requirements - extensions handle everything automatically.

#### macOS (Sonoma 14.0+)
Install Xcode command line tools:
```bash
xcode-select --install
```

#### Linux (x64 or arm64)
Install required packages:
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install python3 python3-venv git

# Optional: For debugging
sudo apt install gdb-multiarch

# Optional: For OpenOCD (if using C/C++)
# Follow Pico extension troubleshooting for udev rules
```

### 5. Verify Installation

1. Open Command Palette (Ctrl+Shift+P or Cmd+Shift+P)
2. Type "Raspberry Pi Pico"
3. You should see various Pico-related commands
4. Type "MicroPico"
5. You should see MicroPico commands

---

## Pico W Setup

### 1. Install MicroPython Firmware

You need to flash your Pico W with MicroPython 1.20+.

#### Option A: Using VS Code (Recommended)

1. Connect Pico W to computer via USB
2. Hold **BOOTSEL** button on Pico W
3. While holding BOOTSEL, briefly press **RESET** button (or replug USB)
4. Release BOOTSEL - Pico W appears as USB drive called "RPI-RP2"
5. In VS Code, open Command Palette (Ctrl+Shift+P)
6. Type **"MicroPico: Flash MicroPython"** (if available) or manually:
   - Download firmware: https://micropython.org/download/rp2-pico-w/
   - Copy `.uf2` file to RPI-RP2 drive
   - Device reboots automatically

#### Option B: Manual Flashing (Universal)

1. Download latest MicroPython UF2 firmware for Pico W from:
   https://micropython.org/download/rp2-pico-w/
2. Hold **BOOTSEL** button on Pico W
3. While holding, connect USB cable (or press RESET)
4. Release BOOTSEL - Pico W appears as USB drive
5. Copy `.uf2` file to the RPI-RP2 drive
6. Device automatically reboots
7. MicroPython is now installed

### 2. Configure VS Code for MicroPython

1. Open Command Palette (Ctrl+Shift+P)
2. Select **"MicroPico: Configure Project"**
3. Select your Pico W device from the list (e.g., `/dev/ttyACM0` or `COM3`)
4. Wait for connection - you should see REPL prompt

### 3. Verify MicroPython Installation

Connect to Pico W REPL:

1. Command Palette â†’ **"MicroPico: Connect"**
2. In terminal, you should see `>>>`
3. Type these commands:

```python
import sys
print(sys.version)
# Should show: MicroPython v1.20+ ...

import network
print("WiFi:", hasattr(network, 'WLAN'))
# Should output: WiFi: True
```

If you see these confirmations, MicroPython is installed correctly.

---

## Library Installation

### 1. Create Project Folder

Create a folder for your mqtt-pico-swarm project:

```bash
mkdir my-pico-mqtt-project
cd my-pico-mqtt-project
code .
```

### 2. Configure MicroPico for Your Project

1. In VS Code, open Command Palette (Ctrl+Shift+P)
2. Select **"MicroPico: Configure Project"**
3. Select your Pico W device
4. VS Code creates `.vscode/` folder with settings

### 3. Install umqtt.robust2 Dependency

This library requires **umqtt.robust2** for MQTT functionality.

#### Install via MicroPico REPL:

1. Command Palette â†’ **"MicroPico: Connect"**
2. In REPL terminal, run:

```python
import upip
upip.install("micropython-umqtt.robust2")
```

Wait for installation to complete.

#### Alternative: Using mpremote (if installed)

```bash
mpremote connect /dev/ttyACM0 mip install umqtt.robust2
```

**Verify installation:**

In REPL:
```python
from umqtt.robust2 import MQTTClient
print("umqtt.robust2 installed successfully")
```

### 4. Clone mqtt-pico-swarm Repository

```bash
# In your project folder
git clone https://github.com/yourusername/mqtt-pico-swarm.git
cd mqtt-pico-swarm
```

Or download the latest release from GitHub.

### 5. Upload Library Files to Pico W

#### Using VS Code MicroPico:

1. In VS Code Explorer, navigate to `mqtt-pico-swarm/src/`
2. Right-click on each Python file
3. Select **"Upload to Pico"** (or "Sync to Device")

Files to upload:
- `mqtt_pico_swarm.py`
- `config_manager.py`
- `connection_manager.py`
- `message_builder.py`
- `command_handler.py`
- `mqtt_adapter.py`
- `errors.py`
- `constants.py`
- `utils.py`

#### Alternative: Upload Entire Folder

1. Right-click on `src/` folder
2. Select **"Upload to Pico"**
3. All `.py` files upload to root directory

### 6. Verify Library Installation

In MicroPico REPL:

```python
from mqtt_pico_swarm import PicoSwarmClient
print("mqtt-pico-swarm installed successfully!")
```

No errors = success!

---

## Configuration

### 1. Create config.json File

Create a new file in VS Code: `config.json`

```json
{
  "device_id": "pico-001",
  "device_type": "sensor",
  "firmware_version": "1.0.0",
  
  "wifi": {
    "ssid": "YourWiFiNetwork",
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

### 2. Upload config.json to Pico W

1. Right-click on `config.json` in VS Code Explorer
2. Select **"Upload to Pico"** (or "Sync to Device")
3. File is uploaded to Pico W root directory

### 3. Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `device_id` | Unique identifier for this device | `"pico-001"` |
| `device_type` | Type/purpose of device | `"temperature_sensor"` |
| `wifi.ssid` | WiFi network name | `"MyNetwork"` |
| `wifi.password` | WiFi password | `"secret123"` |
| `mqtt.broker` | Hub IP address | `"192.168.1.100"` |
| `mqtt.port` | MQTT broker port | `1883` |
| `heartbeat_interval` | Seconds between heartbeats | `60` |

---

## First Device Deployment

### 1. Create Test Script

Create a new file `main.py` in VS Code:

```python
from mqtt_pico_swarm import PicoSwarmClient
import time

print("=== MQTT Pico Swarm Test ===")

# Initialize client with debug enabled
client = PicoSwarmClient(config_file="config.json", debug=True)

# Connect to WiFi and MQTT broker
print("Connecting to hub...")
if not client.connect():
    print("ERROR: Connection failed!")
    raise RuntimeError("Cannot connect to hub")

print("Connected successfully!")

# Send test message
print("Sending test data...")
client.publish_data("test_sensor", {
    "message": "Hello from Pico W!",
    "value": 42
})

print("Test data sent. Starting main loop...")

# Start heartbeat and command listener
# This is a blocking call
try:
    client.start()
except KeyboardInterrupt:
    print("\nShutting down...")
    client.stop()
```

### 2. Upload and Run

1. Right-click on `main.py` â†’ **"Upload to Pico"**
2. Open Command Palette (Ctrl+Shift+P)
3. Select **"MicroPico: Run current file"**
4. Watch terminal for output

**Expected output:**

```
=== MQTT Pico Swarm Test ===
Connecting to hub...
Connected successfully!
Sending test data...
Test data sent. Starting main loop...
[Heartbeat messages every 60 seconds]
```

### 3. Auto-Start on Boot

To run automatically when Pico W powers on:

1. Name your script `main.py`
2. Upload to Pico W root directory
3. Pico W automatically runs `main.py` on boot

---

## Testing and Verification

### 1. Test WiFi Connection

Create a test file `test_wifi.py`:

```python
import network
import time

print("Scanning WiFi networks...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

print("Available networks:")
for net in wlan.scan():
    print(" -", net[0].decode())

print("\nConnecting to WiFi...")
wlan.connect("YourSSID", "YourPassword")

# Wait for connection
timeout = 15
while not wlan.isconnected() and timeout > 0:
    time.sleep(1)
    timeout -= 1
    print(".", end="")

if wlan.isconnected():
    print("\nWiFi connected!")
    print("IP address:", wlan.ifconfig()[0])
    print("Signal strength:", wlan.status('rssi'), "dBm")
else:
    print("\nWiFi connection failed!")
```

Run via: **MicroPico: Run current file** (Ctrl+Shift+P)

### 2. Test MQTT Connection

Create `test_mqtt.py`:

```python
from umqtt.robust2 import MQTTClient

print("Testing MQTT connection...")

try:
    client = MQTTClient(
        client_id="test",
        server="192.168.1.100",
        port=1883
    )
    
    print("Connecting to broker...")
    client.connect()
    print("Connected successfully!")
    
    # Try publishing
    client.publish("test/hello", "world")
    print("Published test message")
    
    client.disconnect()
    print("Disconnected")
    
except Exception as e:
    print(f"MQTT test failed: {e}")
```

### 3. Monitor Device Output

1. Command Palette â†’ **"MicroPico: Connect"**
2. All print statements appear in terminal in real-time
3. Can see all debug output, errors, heartbeats

### 4. Check Memory Usage

```python
import gc

gc.collect()
free = gc.mem_free()
total = gc.mem_alloc() + free

print(f"Free memory: {free} bytes ({free/1024:.1f} KB)")
print(f"Total memory: {total} bytes ({total/1024:.1f} KB)")
```

Should have at least 20-30 KB free.

---

## Troubleshooting

### VS Code Extension Issues

#### Problem: Pico W not appearing in MicroPico

**Solutions:**
1. Check USB cable connection
2. Manually set serial port:
   - Command Palette â†’ **"MicroPico: Select Serial Device"**
3. Try different USB port
4. Restart VS Code

#### Problem: Cannot connect to REPL

**Solutions:**
1. Verify MicroPython is flashed:
   - Should see BOOTSEL mode when holding button
2. Check serial port in VS Code settings:
   - `.vscode/settings.json` should have correct port
3. Try `mpremote` to verify connection:
   ```bash
   mpremote connect /dev/ttyACM0
   ```

### WiFi Connection Issues

#### Problem: Cannot connect to WiFi

**Check:**
- SSID and password are correct in `config.json`
- WiFi network is **2.4 GHz** (Pico W doesn't support 5 GHz)
- Pico W is within range of router
- No special characters in WiFi name

**Debug:**
```python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Scan available networks
for net in wlan.scan():
    print(net)

# Check signal strength
print("Signal:", wlan.status('rssi'))
```

### MQTT Connection Issues

#### Problem: Cannot connect to MQTT broker

**Check:**
- Broker IP is correct
- Broker is running (check hub system)
- Port 1883 is open (not blocked by firewall)
- Hub and Pico W on same network

**Debug:**
```python
from umqtt.robust2 import MQTTClient
import socket

# Test connection
try:
    sock = socket.socket()
    sock.connect(("192.168.1.100", 1883))
    print("Port 1883 is open")
    sock.close()
except Exception as e:
    print(f"Cannot reach broker: {e}")
```

### Memory Issues

#### Problem: Out of memory errors

**Solutions:**

1. **Reduce heartbeat frequency:**
```json
"heartbeat_interval": 120
```

2. **Collect garbage periodically:**
```python
import gc
client.publish_data(...)
gc.collect()
```

3. **Reduce message payload size**

### Import Errors

#### Problem: `ImportError: no module named 'mqtt_pico_swarm'`

**Solutions:**
- Verify all `.py` files uploaded to Pico W root
- Check file names match exactly
- Re-upload `src/` folder contents

#### Problem: `ImportError: no module named 'umqtt'`

**Solution:**
```python
import upip
upip.install("micropython-umqtt.robust2")
```

---

## VS Code Tips for MicroPython

### 1. Use Workspaces for Multiple Devices

Create `workspace.code-workspace`:

```json
{
  "folders": [
    {"path": "pico-001", "name": "Pico 001"},
    {"path": "pico-002", "name": "Pico 002"}
  ],
  "settings": {
    "MicroPico.syncFolder": ""
  }
}
```

### 2. Auto-Sync Files

Enable in settings (`.vscode/settings.json`):

```json
{
  "MicroPico.syncFolder": ".",
  "MicroPico.autoConnect": true
}
```

### 3. Serial Monitoring

Terminal shows all output from Pico W in real-time.

### 4. Debugging Workflow

1. Write test code
2. **MicroPico: Run** to test quickly
3. Add `debug=True` to client for detailed output
4. Use `print()` statements liberally
5. Check memory before final deployment

---

## Example Applications

### Temperature Sensor

```python
from mqtt_pico_swarm import PicoSwarmClient
from machine import Pin
from dht import DHT22
import time

sensor = DHT22(Pin(15))
client = PicoSwarmClient()
client.connect()

while True:
    try:
        sensor.measure()
        client.publish_data("DHT22", {
            "temperature": sensor.temperature(),
            "humidity": sensor.humidity()
        }, unit="celsius")
        print("Data sent")
        time.sleep(30)
    except Exception as e:
        print(f"Error: {e}")
```

---

## Next Steps

### 1. Read the Documentation

- **[API.md](API.md)** - Detailed API reference
- **[PROTOCOL.md](PROTOCOL.md)** - MQTT protocol (3.1.1)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design

### 2. Explore Examples

Check `examples/` folder in repository

### 3. Implement Commands

```python
@client.on_command("action")
def handle_command(payload):
    client.acknowledge_command(payload['command_id'], "success")
```

### 4. Deploy Multiple Devices

Use unique `device_id` for each Pico W

---

## Quick Reference

### MicroPico Commands

| Command | Shortcut |
|---------|----------|
| **Configure Project** | Ctrl+Shift+P â†’ MicroPico: Configure |
| **Connect** | Ctrl+Shift+P â†’ MicroPico: Connect |
| **Run File** | Ctrl+Shift+P â†’ MicroPico: Run current file |
| **Upload File** | Right-click file â†’ Upload to Pico |
| **Disconnect** | Ctrl+Shift+P â†’ MicroPico: Disconnect |

### Code Snippets

```python
# Initialize
client = PicoSwarmClient("config.json")

# Connect
client.connect()

# Publish
client.publish_data("sensor", {"temp": 22.5})

# Command handler
@client.on_command("type")
def handler(payload):
    client.acknowledge_command(payload['command_id'], "success")

# Start
client.start()
```

---

## Support

- **GitHub Issues:** Report bugs
- **VS Code Extensions:** Check extension documentation
- **Documentation:** See docs/ folder

---

**MicroPython setup for mqtt-pico-swarm is complete!** ðŸš€

This is a Python-first approach, different from C/C++ development but perfect for IoT applications.
