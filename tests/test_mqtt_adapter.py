"""Negative tests for MQTTAdapter error handling paths."""

import unittest

from mqtt_pico_swarm.errors import ConnectionError
from mqtt_pico_swarm.mqtt import MQTTAdapter


class FailingFactory:
    def __call__(
        self,
        client_id,
        server,
        port,
        user,
        password,
        keepalive,
        ssl,
        ssl_params,
    ):
        raise RuntimeError("factory boom")


class FakeClient:
    def __init__(self, fail_on=None):
        self.fail_on = fail_on or set()
        self.connected = False
        self.last_will = None
        self.callback = None

    def set_callback(self, callback):
        self.callback = callback
        if "set_callback" in self.fail_on:
            raise RuntimeError("callback failed")

    def connect(self, clean_session=False):
        if "connect" in self.fail_on:
            raise RuntimeError("connect failed")
        self.connected = True

    def disconnect(self):
        if "disconnect" in self.fail_on:
            raise RuntimeError("disconnect failed")
        self.connected = False

    def publish(self, *_args, **_kwargs):
        if "publish" in self.fail_on:
            raise RuntimeError("publish failed")

    def subscribe(self, *_args, **_kwargs):
        if "subscribe" in self.fail_on:
            raise RuntimeError("subscribe failed")

    def wait_msg(self):
        if "wait" in self.fail_on:
            raise RuntimeError("wait failed")

    def check_msg(self):
        if "check" in self.fail_on:
            raise RuntimeError("check failed")

    def set_last_will(self, topic, payload, retain=False, qos=0):
        if "last_will" in self.fail_on:
            raise RuntimeError("last will failed")
        self.last_will = (topic, payload, retain, qos)


class MQTTAdapterNegativeTests(unittest.TestCase):
    def _adapter(self, client):
        return MQTTAdapter(client_factory=lambda *_args, **_kwargs: client)

    def test_factory_failure_raises_connection_error(self):
        adapter = MQTTAdapter(client_factory=FailingFactory())
        with self.assertRaises(ConnectionError):
            adapter.connect(
                broker="broker",
                port=1883,
                client_id="cid",
                username="",
                password="",
            )

    def test_connect_failure_leaves_adapter_disconnected(self):
        client = FakeClient(fail_on={"connect"})
        adapter = self._adapter(client)
        with self.assertRaises(ConnectionError):
            adapter.connect("broker", 1883, "cid")
        self.assertFalse(adapter.is_connected())

    def test_publish_failure_marks_disconnected(self):
        client = FakeClient()
        adapter = self._adapter(client)
        adapter.connect("broker", 1883, "cid")
        client.fail_on.add("publish")
        with self.assertRaises(ConnectionError):
            adapter.publish("topic", b"payload")
        self.assertFalse(adapter.is_connected())

    def test_subscribe_failure_marks_disconnected(self):
        client = FakeClient(fail_on={"subscribe"})
        adapter = self._adapter(client)
        adapter.connect("broker", 1883, "cid")
        with self.assertRaises(ConnectionError):
            adapter.subscribe("topic", qos=0)
        self.assertFalse(adapter.is_connected())

    def test_wait_message_failure_marks_disconnected(self):
        client = FakeClient(fail_on={"wait"})
        adapter = self._adapter(client)
        adapter.connect("broker", 1883, "cid")
        with self.assertRaises(ConnectionError):
            adapter.wait_message()
        self.assertFalse(adapter.is_connected())

    def test_check_message_failure_marks_disconnected(self):
        client = FakeClient(fail_on={"check"})
        adapter = self._adapter(client)
        adapter.connect("broker", 1883, "cid")
        with self.assertRaises(ConnectionError):
            adapter.check_message()
        self.assertFalse(adapter.is_connected())

    def test_set_last_will_propagates_failure(self):
        client = FakeClient(fail_on={"last_will"})
        adapter = self._adapter(client)
        adapter.connect("broker", 1883, "cid")
        with self.assertRaises(ConnectionError):
            adapter.set_last_will("topic", b"payload")

    def test_disconnect_failure_raises(self):
        client = FakeClient(fail_on={"disconnect"})
        adapter = self._adapter(client)
        adapter.connect("broker", 1883, "cid")
        with self.assertRaises(ConnectionError):
            adapter.disconnect()


if __name__ == "__main__":
    unittest.main()
