# Changelog

<!-- cspell:ignore docstrings Pico -->

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-11-16

### Added

- Light command support throughout the stack (`COMMAND_TYPE_LIGHT`, QoS settings, and command handler subscription).
- On-device LED control in `examples/internal-temp-sensor/main.py`, including set/toggle actions and command acknowledgements.
- Beginner-friendly docstrings and logging clarifications in the example to ease onboarding.

### Changed

- Updated protocol documentation with the light command schema, example payloads, and acknowledgement expectations.
- Refined the examples README with an English-only getting-started guide, scripted deployment workflow, and option descriptions.

### Fixed

- Clarified deployment instructions and package installation flags to prevent confusion when copying the demo to a Pico W.

## [1.0.0] - 2025-11-12

<!-- markdownlint-disable-next-line MD024 -->
### Added

- Initial release of `mqtt_pico_swarm` according to architecture and protocol docs
- Full implementation of the nine core modules (constants, errors, utils, config,
  messages, commands, mqtt adapter, connection manager, PicoSwarmClient)
- Unit tests covering configuration, messaging, commands, client orchestration,
  and connection backoff/network handling
- Basic example project demonstrating WiFi setup ahead of MQTT usage and
  publishing telemetry/heartbeats
- Documentation updates for examples and public API exports

<!-- markdownlint-disable-next-line MD024 -->
### Changed

- N/A

<!-- markdownlint-disable-next-line MD024 -->
### Fixed

- N/A
