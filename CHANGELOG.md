# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-11-12

### Added
- Initial release of `mqtt_pico_swarm` according to architecture and protocol docs
- Full implementation of the nine core modules (constants, errors, utils, config,
  messages, commands, mqtt adapter, connection manager, PicoSwarmClient)
- Unit tests covering configuration, messaging, commands, client orchestration,
  and connection backoff/network handling
- Basic example project demonstrating WiFi setup ahead of MQTT usage and
  publishing telemetry/heartbeats
- Documentation updates for examples and public API exports

### Changed
- N/A

### Fixed
- N/A
