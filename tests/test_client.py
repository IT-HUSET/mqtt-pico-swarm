"""Unit tests for PicoSwarmClient."""

import json
import tempfile
import unittest
from pathlib import Path

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.client import PicoSwarmClient
from mqtt_pico_swarm.errors import ConfigurationError, ConnectionError


class FakeTime:
    def __init__(self):
        self._now = 0

    def time(self):
        return self._now

    def sleep(self, seconds):
        self._now += seconds


class FakeAdapter:
    def __init__(self):
        self.connected = False
        self.callback = None
        self.connect_args = None
        self.published_messages = []
        self.subscriptions = []
        self.last_will = None

    def set_callback(self, callback):
        self.callback = callback

    def connect(
        self,
        broker,
        port,
        client_id,
        keepalive=60,
        username="",
        password="",
        ssl=False,
        ssl_params=None,
        clean_session=False,
        last_will=None,
    ):
        self.connected = True
        self.connect_args = {
            "broker": broker,
            "port": port,
            "client_id": client_id,
            "keepalive": keepalive,
            "username": username,
            "password": password,
            "ssl": ssl,
            "ssl_params": ssl_params,
            "clean_session": clean_session,
            "last_will": last_will,
        }
        if last_will:
            self.set_last_will(
                last_will.get("topic"),
                last_will.get("payload"),
                retain=last_will.get("retain", False),
                qos=last_will.get("qos", 0),
            )

    def disconnect(self):
        self.connected = False

    def publish(self, topic, payload, qos=0, retain=False):
        self.published_messages.append((topic, payload, qos, retain))

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))

    def wait_msg(self):
        return None

    def check_msg(self):
        return None

    def set_last_will(self, topic, payload, retain=False, qos=0):
        self.last_will = (topic, payload, retain, qos)

    def is_connected(self):
        return self.connected

    def emit(self, topic, payload):
        if not self.callback:
            raise RuntimeError("No callback registered")
        self.callback(topic, payload)


class PicoSwarmClientTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        with self.config_path.open("w") as handle:
            json.dump(
                {
                    "device_id": "pico-001",
                    "device_type": "temperature_sensor",
                    "mqtt": {
                        "broker": "test-broker",
                        "port": 1883,
                        "keepalive": 60,
                        "username": "",
                        "password": "",
                    },
                    "heartbeat_interval": 5,
                },
                handle,
            )

        self.adapter = FakeAdapter()
        self.clock = FakeTime()
        self.client = PicoSwarmClient(
            config_file=str(self.config_path),
            debug=True,
            mqtt_adapter=self.adapter,
            time_module=self.clock,
        )

    def tearDown(self):
        self.client.disconnect()
        self.temp_dir.cleanup()

    def test_connect_configures_adapter_and_publishes_online_status(self):
        self.client.connect()

        self.assertTrue(self.adapter.connected)
        subscriptions = [topic for topic, _ in self.adapter.subscriptions]
        self.assertIn(
            constants.device_command_topic("pico-001", constants.COMMAND_TYPE_CONFIG),
            subscriptions,
        )
        self.assertIn(
            constants.device_command_topic("pico-001", constants.COMMAND_TYPE_LIGHT),
            subscriptions,
        )
        last_topic, payload, qos, retain = self.adapter.published_messages[-1]
        self.assertEqual(last_topic, constants.status_topic("pico-001"))
        self.assertTrue(retain)
        self.assertEqual(qos, constants.QOS_STATUS)

        lw_topic, _, _, _ = self.adapter.last_will
        self.assertEqual(lw_topic, constants.status_topic("pico-001"))

    def test_publish_data_uses_message_builder(self):
        self.client.connect()
        self.client.publish_data("DHT22", {"temperature": 22.5})

        topic, payload, qos, retain = self.adapter.published_messages[-1]
        data = json.loads(payload)
        self.assertEqual(topic, constants.data_topic("pico-001"))
        self.assertEqual(data["data"]["temperature"], 22.5)
        self.assertEqual(qos, constants.QOS_DATA)
        self.assertFalse(retain)

    def test_acknowledge_command_publishes_ack(self):
        self.client.connect()
        self.client.acknowledge_command("cmd-1", "success", message="done")

        topic, payload, qos, retain = self.adapter.published_messages[-1]
        ack = json.loads(payload)
        self.assertEqual(topic, constants.device_ack_topic("pico-001"))
        self.assertEqual(ack["status"], "success")
        self.assertEqual(qos, constants.QOS_COMMAND_ACK)
        self.assertFalse(retain)

    def test_light_command_callback_publishes_ack_with_result(self):
        self.client.connect()

        @self.client.on_command(constants.COMMAND_TYPE_LIGHT)
        def handle_light(payload):
            command_id = payload.get("commandId") or payload.get("command_id")
            self.client.acknowledge_command(
                command_id,
                "success",
                result={"current_state": payload.get("state", "off")},
            )

        payload = json.dumps(
            {"commandId": "cmd-light", "action": "set", "state": "on"}
        )
        topic = constants.device_command_topic("pico-001", constants.COMMAND_TYPE_LIGHT)
        self.adapter.emit(topic, payload)

        topic, payload, qos, retain = self.adapter.published_messages[-1]
        ack = json.loads(payload)
        self.assertEqual(topic, constants.device_ack_topic("pico-001"))
        self.assertEqual(ack["command_id"], "cmd-light")
        self.assertEqual(ack["status"], "success")
        self.assertEqual(ack["result"]["current_state"], "on")
        self.assertEqual(qos, constants.QOS_COMMAND_ACK)
        self.assertFalse(retain)

    def test_on_command_invokes_registered_callback(self):
        self.client.connect()

        received = []

        def handler(payload):
            received.append(payload)

        self.client.on_command(constants.COMMAND_TYPE_CONFIG, handler)

        payload = json.dumps(
            {
                "command_id": "cmd-1",
                "device_id": "pico-001",
                "type": "update_config",
                "payload": {"heartbeat_interval": 120},
            }
        )
        topic = constants.device_command_topic("pico-001", constants.COMMAND_TYPE_CONFIG)
        self.adapter.emit(topic, payload)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["command_id"], "cmd-1")

    def test_on_command_error_increments_error_count(self):
        self.client.connect()

        @self.client.on_command(constants.COMMAND_TYPE_ACTION)
        def failing_handler(payload):
            raise ValueError("boom")

        payload = json.dumps({"command_id": "cmd-2", "payload": {}})
        topic = constants.device_command_topic("pico-001", constants.COMMAND_TYPE_ACTION)
        self.adapter.emit(topic, payload)

        self.assertEqual(self.client.get_error_count(), 1)

    def test_disconnect_publishes_offline_status(self):
        self.client.connect()
        self.client.disconnect()

        topic, payload, qos, retain = self.adapter.published_messages[-1]
        data = json.loads(payload)
        self.assertEqual(topic, constants.status_topic("pico-001"))
        self.assertEqual(data["status"], "offline")
        self.assertTrue(retain)
        self.assertFalse(self.adapter.connected)

    def test_get_config_returns_loaded_config(self):
        config = self.client.get_config()
        self.assertEqual(config["device_id"], "pico-001")

    def test_update_config_disallowed_when_connected(self):
        self.client.connect()
        with self.assertRaises(ConfigurationError):
            self.client.update_config({"device_id": "pico-002"})

    def test_send_heartbeat_uses_internal_metrics(self):
        self.client.connect()
        self.clock.sleep(10)
        self.client._send_heartbeat()

        topic, payload, qos, retain = self.adapter.published_messages[-1]
        data = json.loads(payload)
        self.assertEqual(topic, constants.heartbeat_topic("pico-001"))
        self.assertEqual(data["uptime_seconds"], 10)
        self.assertEqual(qos, constants.QOS_HEARTBEAT)

    def test_publish_requires_connection(self):
        with self.assertRaises(ConnectionError):
            self.client.publish_data("DHT22", {"temperature": 25})

    def test_send_heartbeat_requires_connection(self):
        with self.assertRaises(ConnectionError):
            self.client.send_heartbeat()

    def test_connect_is_idempotent(self):
        self.client.connect()
        self.assertTrue(self.client.connect())
        # Säkerställ att vi inte får dubbelpublicering av status
        status_messages = [topic for topic, _, _, _ in self.adapter.published_messages if topic == constants.status_topic("pico-001")]
        self.assertEqual(len(status_messages), 1)