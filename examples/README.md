# Examples

This directory contains runnable examples that demonstrate how to use the
`mqtt_pico_swarm` library on a Raspberry Pi Pico W.

## Structure

- `internal-temp-sensor/`
  - `config.json.example` – sample configuration file that can be copied to
    `config.json` and updated with your broker credentials.
  - `main.py` – MicroPython entry point showing hur du kopplar upp WiFi,
    initialiserar PicoSwarmClient, publicerar telemetri och lyssnar på kommandon.

## Getting Started

1. Kopiera innehållet i `basic/` till din Pico W (t.ex. via MicroPico eller
   Thonny).
2. Byt namn på `config.json.example` till `config.json` och uppdatera
   enhetens ID, MQTT-broker och övriga värden.
3. Placera biblioteket under `/lib/mqtt_pico_swarm` på enheten.
4. Öppna `main.py` och fyll i `WIFI_SSID` och `WIFI_PASSWORD`. WiFi-anslutningen
   sker alltid innan biblioteket används – koden demonstrerar detta tydligt.
5. Kör `main.py`. Programmet kopplar upp WiFi, ansluter sedan till MQTT,
   publicerar telemetri var 30:e sekund, skickar hjärtslag enligt konfigurationen
   och loggar inkommande kommandon.

> **Note:** Exemplet använder synkrona loopar och minimala beroenden för att hålla
> sig inom Pico W:s resurser. Justera intervall och nyttolaster efter dina sensorer
> eller aktuatorer.
