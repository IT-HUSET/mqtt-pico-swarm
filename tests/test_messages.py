"""Unit tests for MessageBuilder."""

import json
import unittest

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.messages import MessageBuilder


class MessageBuilderTests(unittest.TestCase):
    def setUp(self):
        self.builder = MessageBuilder(
            device_id="pico-123",
            device_type="temperature_sensor",
            firmware_version="1.2.3",
        )

    def _decode(self, message):
        return message["topic"], json.loads(message["payload"]), message["qos"], message["retain"]

    def test_status_online_includes_device_info(self):
        topic, payload, qos, retain = self._decode(
            self.builder.status_online(ip_address="192.168.1.50", signal_strength=-60, timestamp="2025-01-01T00:00:00Z")
        )
        self.assertEqual(topic, constants.status_topic("pico-123"))
        self.assertEqual(payload["status"], "online")
        self.assertEqual(payload["ip_address"], "192.168.1.50")
        self.assertEqual(payload["signal_strength"], -60)
        self.assertEqual(qos, constants.QOS_STATUS)
        self.assertTrue(retain)

    def test_status_offline(self):
        topic, payload, qos, retain = self._decode(
            self.builder.status_offline(timestamp="2025-01-01T01:00:00Z")
        )
        self.assertEqual(payload["status"], "offline")
        self.assertEqual(payload["timestamp"], "2025-01-01T01:00:00Z")
        self.assertTrue(retain)

    def test_sensor_data_with_unit(self):
        message = self.builder.sensor_data(
            "DHT22",
            {"temperature": 22.5, "humidity": 55},
            unit="celsius",
            timestamp="2025-01-01T02:00:00Z",
        )
        topic, payload, qos, retain = self._decode(message)
        self.assertEqual(topic, constants.data_topic("pico-123"))
        self.assertEqual(payload["data"]["temperature"], 22.5)
        self.assertEqual(payload["unit"], "celsius")
        self.assertEqual(qos, constants.QOS_DATA)
        self.assertFalse(retain)

    def test_event_building(self):
        message = self.builder.event(
            constants.EVENT_TYPE_ERROR,
            "SENSOR_TIMEOUT",
            "Sensor did not respond",
            constants.SEVERITY_WARNING,
            timestamp="2025-01-01T03:00:00Z",
        )
        topic, payload, qos, retain = self._decode(message)
        self.assertEqual(topic, constants.events_topic("pico-123"))
        self.assertEqual(payload["event_code"], "SENSOR_TIMEOUT")
        self.assertEqual(qos, constants.QOS_EVENTS)
        self.assertFalse(retain)

    def test_log_building(self):
        message = self.builder.log(
            "info",
            "sensor.main",
            "Startup complete",
            context={"extra": 1},
            timestamp="2025-01-01T03:30:00Z",
        )
        topic, payload, qos, retain = self._decode(message)
        self.assertEqual(topic, constants.logs_topic("pico-123"))
        self.assertEqual(payload["level"], "info")
        self.assertEqual(payload["logger"], "sensor.main")
        self.assertEqual(payload["message"], "Startup complete")
        self.assertEqual(payload["context"]["extra"], 1)
        self.assertEqual(qos, constants.QOS_LOGS)
        self.assertFalse(retain)

    def test_capabilities_building(self):
        spec = {
            "device_type": "soil_sensor",
            "sensors": [
                {
                    "id": "soil",
                    "measures": [
                        {"key": "moisture_percent", "value_type": "number"},
                    ],
                }
            ],
        }
        message = self.builder.capabilities(spec)
        topic, payload, qos, retain = self._decode(message)
        self.assertEqual(topic, constants.capabilities_topic("pico-123"))
        self.assertEqual(payload["device_id"], "pico-123")
        self.assertEqual(payload["device_type"], "temperature_sensor")
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("sensors", payload)
        self.assertEqual(qos, constants.QOS_CAPABILITIES)
        self.assertTrue(retain)

    def test_command_ack_includes_status(self):
        message = self.builder.command_ack(
            command_id="cmd-42",
            status="success",
            message="Done",
            result="success",
            timestamp="2025-01-01T04:00:00Z",
        )
        topic, payload, qos, retain = self._decode(message)
        self.assertEqual(topic, constants.device_ack_topic("pico-123"))
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["message"], "Done")
        self.assertEqual(qos, constants.QOS_COMMAND_ACK)
        self.assertFalse(retain)


if __name__ == "__main__":
    unittest.main()