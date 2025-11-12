"""Tests for ConnectionManager network handling."""

import unittest
from unittest.mock import patch

from mqtt_pico_swarm.connection import ConnectionManager, _next_backoff
from mqtt_pico_swarm.errors import ConnectionError, NetworkUnavailableError


class FakeAdapter:
    def __init__(self):
        self.connected = False
        self.callback = None
        self.connect_calls = 0
        self.publish_exception = None
        self.check_message_exception = None
        self.connect_exception = None

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
        clean_session=False,
        ssl=False,
        ssl_params=None,
        last_will=None,
    ):
        self.connect_calls += 1
        if self.connect_exception:
            self.connected = False
            raise self.connect_exception
        if broker is None:
            raise ConnectionError("missing broker")
        self.connected = True

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def subscribe(self, *_args, **_kwargs):  # pragma: no cover - not needed here
        pass

    def publish(self, *_args, **_kwargs):
        if self.publish_exception:
            self.connected = False
            raise self.publish_exception

    def check_message(self):
        if self.check_message_exception:
            self.connected = False
            raise self.check_message_exception

    def wait_message(self):  # pragma: no cover - not needed here
        pass


class DummyCommandHandler:
    def subscribed_topics(self, _device_id):
        return []

    def dispatch(self, topic, payload):  # pragma: no cover
        return False


class ConnectionManagerNetworkTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FakeAdapter()
        self.handler = DummyCommandHandler()
        self.mqtt_config = {
            "broker": "test-broker",
            "port": 1883,
            "client_id": "pico-001",
            "keepalive": 30,
        }

    def _manager(self):
        return ConnectionManager(
            adapter=self.adapter,
            command_handler=self.handler,
            device_id="pico-001",
            mqtt_config=self.mqtt_config,
            reconnect_delay=5,
            max_reconnect_attempts=1,
            debug=False,
        )

    def test_connect_raises_when_network_unavailable(self):
        manager = self._manager()
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=False):
            with self.assertRaises(NetworkUnavailableError):
                manager.connect()
        self.assertEqual(self.adapter.connect_calls, 0)

    def test_connect_succeeds_when_network_available(self):
        manager = self._manager()
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            self.assertTrue(manager.connect())
        self.assertEqual(self.adapter.connect_calls, 1)

    def test_network_loss_during_retry_raises_network_unavailable(self):
        manager = self._manager()
        with patch(
            "mqtt_pico_swarm.connection.is_network_available",
            side_effect=[True, False],
        ):
            with self.assertRaises(NetworkUnavailableError):
                manager.connect()
        self.assertEqual(self.adapter.connect_calls, 0)

    def test_publish_failure_breaks_connection(self):
        manager = self._manager()
        self.adapter.publish_exception = ConnectionError("publish failed")
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            manager.connect()
            with self.assertRaises(ConnectionError):
                manager.publish({"topic": "t", "payload": "x"})
        self.assertFalse(self.adapter.is_connected())

    def test_process_incoming_failure_marks_disconnected(self):
        manager = self._manager()
        self.adapter.check_message_exception = ConnectionError("check failed")
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            manager.connect()
            with self.assertRaises(ConnectionError):
                manager.process_incoming()
        self.assertFalse(self.adapter.is_connected())

    def test_ensure_connected_reconnects_when_adapter_lost(self):
        manager = self._manager()
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            manager.connect()
            self.adapter.connected = False
            manager.ensure_connected()
        self.assertEqual(self.adapter.connect_calls, 2)
        self.assertTrue(self.adapter.is_connected())

    def test_ensure_connected_raises_when_reconnect_fails(self):
        manager = self._manager()
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            manager.connect()
        self.adapter.connected = False
        self.adapter.connect_exception = ConnectionError("reconnect failed")
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            with self.assertRaises(ConnectionError):
                manager.ensure_connected()
        self.assertEqual(self.adapter.connect_calls, 2)
        self.assertFalse(self.adapter.is_connected())

    def test_ensure_connected_noop_when_still_connected(self):
        manager = self._manager()
        with patch("mqtt_pico_swarm.connection.is_network_available", return_value=True):
            manager.connect()
            manager.ensure_connected()
        self.assertEqual(self.adapter.connect_calls, 1)

    def test_backoff_sequence_reaches_cap(self):
        delay = 5
        sequence = []
        for _ in range(5):
            sequence.append(delay)
            delay = _next_backoff(delay)
        self.assertEqual(sequence, [5, 10, 20, 40, 60])
        self.assertEqual(delay, 60)


if __name__ == "__main__":
    unittest.main()