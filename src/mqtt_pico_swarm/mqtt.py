"""MQTT adapter wrapping umqtt.simple2 for Pico Swarm."""

from .errors import ConnectionError

try:
    # Byt till umqtt.simple2 för bättre kompatibilitet på riktiga enheter.
    from umqtt import simple2 as _umqtt_module
except ImportError:  # pragma: no cover - desktop tester ersätter fabriken
    _umqtt_module = None


def _default_client_factory(client_id, server, port, user, password, keepalive, ssl, ssl_params):
    if _umqtt_module is None:
        raise ConnectionError("umqtt.simple2 is not available")
    # umqtt.simple2.MQTTClient har signaturen (client_id, server, port=1883, user=None, password=None, keepalive=0, ssl=False)
    return _umqtt_module.MQTTClient(
        client_id,
        server,
        port=port,
        user=user or None,
        password=password or None,
        keepalive=keepalive,
        ssl=ssl,
    )


class MQTTAdapter:
    """Tunn wrapper som ger konsekvent gränssnitt mot umqtt.robust2."""

    def __init__(self, client_factory=None):
        self._client_factory = client_factory or _default_client_factory
        self._client = None
        self._callback = None
        self._connected = False
        self._last_will = None

    @staticmethod
    def _topic_to_bytes(topic):
        if isinstance(topic, bytes):
            return topic
        if isinstance(topic, bytearray):
            return bytes(topic)
        if isinstance(topic, str):
            return topic.encode("utf-8")
        raise TypeError("Topic must be str or bytes-like, got {}".format(type(topic).__name__))

    @staticmethod
    def _payload_to_bytes(payload):
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        if isinstance(payload, memoryview):
            return bytes(payload)
        if isinstance(payload, str):
            return payload.encode("utf-8")
        # Fallback: str-konvertera och encoda
        return str(payload).encode("utf-8")

    def set_callback(self, callback):
        self._callback = callback
        if self._client is not None:
            self._client.set_callback(self._handle_message)

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
        if self._client is None:
            try:
                self._client = self._client_factory(
                    client_id,
                    broker,
                    port,
                    username,
                    password,
                    keepalive,
                    ssl,
                    ssl_params,
                )
            except Exception as error:
                print("Failed to create MQTT client:", error)
                raise ConnectionError("Failed to create MQTT client") from error

        if last_will:
            self._last_will = (
                last_will.get("topic"),
                last_will.get("payload"),
                last_will.get("retain", False),
                last_will.get("qos", 0),
            )

        if self._callback:
            self._client.set_callback(self._handle_message)

        if self._last_will:
            self.set_last_will(*self._last_will)

        try:
            self._client.connect(clean_session=clean_session)
            self._connected = True
        except Exception as error:
            self._connected = False
            raise ConnectionError("Failed to connect to MQTT broker") from error

    def disconnect(self):
        if self._client is None:
            return
        try:
            self._client.disconnect()
        except Exception as error:
            raise ConnectionError("Failed to disconnect MQTT client") from error
        finally:
            self._connected = False

    def publish(self, topic, payload, qos=0, retain=False):
        """Publish wrapper tolerant to different umqtt versions.

        Many umqtt.simple/robust2 variants expose publish(topic, msg) or
        publish(topic, msg, retain, qos=0). We only rely on topic/payload
        for compatibility and let the underlying client handle defaults.
        """
        self._ensure_client()
        topic = self._topic_to_bytes(topic)
        payload = self._payload_to_bytes(payload)
        topic_display = topic.decode("utf-8") if isinstance(topic, (bytes, bytearray)) else str(topic)
        # Debug-markör för version på enheten
        print("[MQTTAdapter] publish simple2", topic_display)
        try:
            # Anropa med retain/qos så att QoS 1 fungerar korrekt
            self._client.publish(topic, payload, retain=retain, qos=qos)
        except Exception as error:
            self._connected = False
            raise ConnectionError("Failed to publish message: {!r}".format(error)) from error

    def subscribe(self, topic, qos=0):
        self._ensure_client()
        topic = self._topic_to_bytes(topic)
        topic_display = topic.decode("utf-8") if isinstance(topic, (bytes, bytearray)) else str(topic)
        # Debug-markör för version på enheten
        print("[MQTTAdapter] subscribe simple2", topic_display)
        try:
            self._client.subscribe(topic, qos)
        except AttributeError:
            # Vissa versioner av umqtt.robust2/simple använder interna
            # attribut (t.ex. last_cpacket/MQTTException) som inte alltid
            # finns. För demo och kompatibilitet behandlar vi dessa som
            # icke-fatal fel och låter klienten fortsätta.
            return
        except Exception as error:
            self._connected = False
            raise ConnectionError("Failed to subscribe to topic") from error

    def wait_message(self):
        self._ensure_client()
        try:
            self._client.wait_msg()
        except Exception as error:
            self._connected = False
            raise ConnectionError("Failed while waiting for message") from error

    def check_message(self):
        self._ensure_client()
        try:
            self._client.check_msg()
        except Exception as error:
            self._connected = False
            raise ConnectionError("Failed while checking messages") from error

    def set_last_will(self, topic, payload, retain=False, qos=0):
        self._ensure_client(create=False)
        self._last_will = (topic, payload, retain, qos)
        if self._client is None:
            return
        try:
            self._client.set_last_will(topic, payload, retain=retain, qos=qos)
        except Exception as error:
            raise ConnectionError("Failed to set last will") from error

    def is_connected(self):
        return self._connected

    def _ensure_client(self, create=True):
        if self._client is None:
            if not create:
                return
            raise ConnectionError("MQTT client not created")

    def _handle_message(self, topic, msg):
        if isinstance(topic, bytes):
            topic = topic.decode("utf-8")
        if self._callback:
            self._callback(topic, msg)