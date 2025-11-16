# Examples

This directory contains runnable examples that demonstrate how to use the
`mqtt_pico_swarm` library on a Raspberry Pi Pico W.

## Structure

- `internal-temp-sensor/`
  - `config.json.example` – sample configuration file that can be copied to
    `config.json` and updated with your broker credentials.
  - `main.py` – MicroPython entry point that demonstrates how to connect to WiFi,
    initialize PicoSwarmClient, publish telemetry, and listen for commands.

## Getting Started

1. From the repository root, run the deployment script (for example `python scripts/deploy_demo.py --port <serial> --install-umqtt internal-temp-sensor`) so that the example and the `umqtt` package are copied to the Pico W. Make sure you have already duplicated `config.json.example` to `config.json` and filled in your device ID, WiFi credentials, and broker settings.
2. Connect to the Pico with `mpremote` (e.g. `mpremote connect <serial> repl`). This opens a REPL session so you can see boot output.
3. At the REPL prompt, press Enter once and then run `import machine; machine.reset()` to reboot the board. The REPL session will disconnect while the Pico restarts.
4. Reconnect with `mpremote`. `main.py` is executed automatically on boot, so you can simply watch the log output as the device joins WiFi and MQTT, publishes telemetry, and handles commands.

> **Tip:** If you need to tweak intervals or payload sizes, adjust the constants in `main.py` before redeploying so the example stays within the Pico W's resource limits.

### Deployment script options

The `scripts/deploy_demo.py` helper accepts a few useful flags:

- `--port <serial>` – serial device name for your Pico (use `auto` to let mpremote decide).
- `--install-umqtt` – download and copy the `micropython-umqtt.simple2` package to `/lib/umqtt`.
- `--skip-config` – deploy code without overwriting the existing `config.json` on the device.

Run `python scripts/deploy_demo.py --help` for the full description.
