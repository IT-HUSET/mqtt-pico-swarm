"""Unit tests for ConfigManager."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mqtt_pico_swarm.config import ConfigManager
from mqtt_pico_swarm.errors import ConfigurationError


class ConfigManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        with self.config_path.open("w") as handle:
            json.dump(
                {
                    "device_id": "swarm-1",
                    "device_type": "sensor",
                    "mqtt": {"broker": "192.168.1.10"},
                },
                handle,
            )
        self.manager = ConfigManager(str(self.config_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_merges_defaults_and_sets_client_id(self):
        config = self.manager.get_config()
        self.assertEqual(config["device_id"], "swarm-1")
        self.assertEqual(config["heartbeat_interval"], 60)
        self.assertEqual(config["mqtt"]["client_id"], "swarm-1")
        self.assertEqual(config["mqtt"]["port"], 1883)

    def test_update_applies_changes_without_persist(self):
        updated = self.manager.update({"max_reconnect_attempts": 3}, persist=False)
        self.assertEqual(updated["max_reconnect_attempts"], 3)
        self.assertEqual(updated["device_id"], "swarm-1")

    def test_invalid_update_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            self.manager.update({"heartbeat_interval": 0}, persist=False)

    def test_invalid_file_content_raises_configuration_error(self):
        bad_path = Path(self.temp_dir.name) / "invalid.json"
        with bad_path.open("w") as handle:
            json.dump(
                {
                    "device_id": "",
                    "device_type": "sensor",
                    "mqtt": {"broker": "bad"},
                },
                handle,
            )
        manager = ConfigManager(str(bad_path))
        with self.assertRaises(ConfigurationError):
            manager.load()

    def test_malformed_json_raises_configuration_error(self):
        malformed_path = Path(self.temp_dir.name) / "malformed.json"
        malformed_path.write_text("{not: valid json}")
        manager = ConfigManager(str(malformed_path))
        with self.assertRaises(ConfigurationError):
            manager.load()

    def test_update_missing_required_field_raises(self):
        with self.assertRaises(ConfigurationError):
            self.manager.update({"device_id": ""}, persist=False)

    def test_update_persist_failure_raises_configuration_error(self):
        with patch("builtins.open", side_effect=OSError("disk full")):
            with self.assertRaises(ConfigurationError):
                self.manager.update({"heartbeat_interval": 120}, persist=True)


if __name__ == "__main__":
    unittest.main()