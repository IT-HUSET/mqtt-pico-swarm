"""Unit tests for CommandHandler."""

import json
import unittest

from mqtt_pico_swarm import constants
from mqtt_pico_swarm.commands import CommandHandler
from mqtt_pico_swarm.errors import MessageError


class CommandHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = CommandHandler()
        self.handled_payloads = []
        self.wildcard_calls = []

    def _register(self):
        def config_callback(payload):
            self.handled_payloads.append(("config", payload))

        self.handler.on(constants.COMMAND_TYPE_CONFIG, config_callback)

        def wildcard_callback(command_type, payload):
            self.wildcard_calls.append((command_type, payload))

        self.handler.on_any(wildcard_callback)

    def test_dispatch_calls_specific_and_wildcard(self):
        self._register()
        payload = {
            "command_id": "cmd-1",
            "device_id": "pico-1",
            "type": "update_config",
            "payload": {"heartbeat_interval": 120},
        }
        topic = constants.device_command_topic("pico-1", constants.COMMAND_TYPE_CONFIG)
        handled = self.handler.dispatch(topic, json.dumps(payload).encode("utf-8"))

        self.assertTrue(handled)
        self.assertEqual(len(self.handled_payloads), 1)
        self.assertEqual(self.handled_payloads[0][1]["payload"]["heartbeat_interval"], 120)
        self.assertEqual(len(self.wildcard_calls), 1)
        self.assertEqual(self.wildcard_calls[0][0], constants.COMMAND_TYPE_CONFIG)

    def test_dispatch_light_command_invokes_registered_callback(self):
        received = []

        def light_callback(payload):
            received.append(payload)

        self.handler.on(constants.COMMAND_TYPE_LIGHT, light_callback)
        topic = constants.device_command_topic("pico-1", constants.COMMAND_TYPE_LIGHT)
        payload = {"command_id": "cmd-light", "action": "toggle"}

        handled = self.handler.dispatch(topic, json.dumps(payload).encode("utf-8"))

        self.assertTrue(handled)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["action"], "toggle")

    def test_dispatch_unknown_command_invokes_wildcard_only(self):
        self._register()
        payload = {"command_id": "cmd-2", "payload": {}}
        topic = constants.device_command_topic("pico-1", "custom")

        handled = self.handler.dispatch(topic, json.dumps(payload))
        self.assertTrue(handled)
        self.assertEqual(len(self.handled_payloads), 0)
        self.assertEqual(len(self.wildcard_calls), 1)
        self.assertEqual(self.wildcard_calls[0][0], "custom")

    def test_dispatch_without_handlers_returns_false(self):
        payload = {"command_id": "cmd-3", "payload": {}}
        topic = constants.device_command_topic("pico-1", constants.COMMAND_TYPE_CONFIG)
        handled = self.handler.dispatch(topic, json.dumps(payload))
        self.assertFalse(handled)

    def test_duplicate_registration_overwrites_previous(self):
        calls = []

        def first(_payload):
            calls.append("first")

        def second(_payload):
            calls.append("second")

        self.handler.on(constants.COMMAND_TYPE_CONFIG, first)
        self.handler.on(constants.COMMAND_TYPE_CONFIG, second)

        payload = {"command_id": "cmd", "payload": {}}
        topic = constants.device_command_topic("pico-1", constants.COMMAND_TYPE_CONFIG)
        self.handler.dispatch(topic, json.dumps(payload))

        self.assertEqual(calls, ["second"])

    def test_register_non_callable_raises(self):
        with self.assertRaises(MessageError):
            self.handler.on(constants.COMMAND_TYPE_CONFIG, "not-callable")
        with self.assertRaises(MessageError):
            self.handler.on_any(None)

    def test_dispatch_with_invalid_json_raises(self):
        with self.assertRaises(MessageError):
            topic = constants.device_command_topic("pico-1", constants.COMMAND_TYPE_ACTION)
            self.handler.dispatch(topic, b"not-json")

    def test_dispatch_without_command_suffix_raises(self):
        with self.assertRaises(MessageError):
            self.handler.dispatch("hub/devices/pico-1/data", b"{}")


if __name__ == "__main__":
    unittest.main()