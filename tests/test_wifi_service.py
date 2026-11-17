#!/usr/bin/env python3
# test_wifi_service.py — Unit tests for WifiService nmcli parsing and state handling.

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "config", "hypr", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from services.wifi import WifiService


class TestWifiService(unittest.TestCase):
    def test_parse_empty_wifi_lines(self):
        result = WifiService.parse_wifi_lines("")
        self.assertEqual(result, [])

    def test_parse_wifi_lines_basic(self):
        sample_output = (
            "*:HomeNet:85:WPA2\n"
            " :CoffeeShop:42:WPA2 802.1X\n"
            " :PublicGuest:30:\n"
            " :--:99:WPA2\n"  # should be ignored
        )
        saved = {"HomeNet", "CoffeeShop"}
        nets = WifiService.parse_wifi_lines(sample_output, saved)

        self.assertEqual(len(nets), 3)
        # Active connected network should be first
        self.assertEqual(nets[0]["ssid"], "HomeNet")
        self.assertTrue(nets[0]["in_use"])
        self.assertTrue(nets[0]["saved"])
        self.assertEqual(nets[0]["signal"], 85)

        # Saved network CoffeeShop should come before unsaved PublicGuest
        self.assertEqual(nets[1]["ssid"], "CoffeeShop")
        self.assertFalse(nets[1]["in_use"])
        self.assertTrue(nets[1]["saved"])

        self.assertEqual(nets[2]["ssid"], "PublicGuest")
        self.assertFalse(nets[2]["saved"])

    def test_parse_wifi_lines_escaped_colon(self):
        sample_output = " :My\\:Special\\:WiFi:60:WPA2\n"
        nets = WifiService.parse_wifi_lines(sample_output)
        self.assertEqual(len(nets), 1)
        self.assertEqual(nets[0]["ssid"], "My:Special:WiFi")

    def test_parse_wifi_lines_deduplication(self):
        # Multiple BSSIDs broadcasting the same SSID (e.g. Mesh network)
        sample_output = (
            " :MeshWiFi:50:WPA2\n"
            "*:MeshWiFi:70:WPA2\n"
            " :MeshWiFi:85:WPA2\n"
        )
        nets = WifiService.parse_wifi_lines(sample_output)
        self.assertEqual(len(nets), 1)
        # In-use BSSID takes precedence
        self.assertTrue(nets[0]["in_use"])

    def test_get_status_type(self):
        status, ssid = WifiService.get_status()
        self.assertIsInstance(status, str)
        self.assertIsInstance(ssid, str)
        self.assertIn(status, ["Connected", "Disconnected", "Disabled"])

    def test_is_radio_enabled_type(self):
        enabled = WifiService.is_radio_enabled()
        self.assertIsInstance(enabled, bool)

    def test_get_wifi_device_type(self):
        dev = WifiService.get_wifi_device()
        self.assertIsInstance(dev, str)
        self.assertTrue(len(dev) > 0)


if __name__ == "__main__":
    unittest.main()
