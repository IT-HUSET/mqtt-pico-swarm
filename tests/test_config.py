"""Tests for ConfigManager"""
import unittest
from mqtt_pico_swarm.config import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager("fixtures/config.json")
    
    def test_load_config(self):
        self.assertEqual(self.config.get("device_id"), "pico-001")
    
    def test_validation(self):
        # Test validation logic
        pass
