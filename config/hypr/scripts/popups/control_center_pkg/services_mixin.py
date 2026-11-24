#!/usr/bin/env python3
# control_center_pkg/services_mixin.py — Background hardware, Wi-Fi, IME, and notification polling.

import json
import os
import subprocess
import threading
import time

from gi.repository import GLib

from control_center_pkg.constants import CACHE_FILE, HAS_LAYER_SHELL, GtkLayerShell
from services.audio import AudioService
from services.bluetooth import BluetoothService
from services.brightness import BrightnessService
from services.power import PowerService
from services.wifi import WifiService


class ControlCenterServicesMixin:
    """Async status refresh, Wi-Fi management, and notification persistence."""

    def scan_wifi_networks(self, fast=True):
        if not self.wifi_radio_enabled or self.wifi_scanning:
            return
        self.wifi_scanning = True
        if not self.wifi_networks:
            self.wifi_status_msg = "Scanning networks..."
            self.queue_draw()

        def on_initial(nets, radio_on):
            def apply_initial():
                self.wifi_networks = nets
                self.wifi_radio_enabled = radio_on
                self._bake_content()
                self.queue_draw()
            GLib.idle_add(apply_initial)

        def on_complete(nets, radio_on):
            def apply_final():
                self.wifi_networks = nets
                self.wifi_scanning = False
                self.wifi_status_msg = ""
                self.wifi_radio_enabled = radio_on
                txt, wifi_ssid = WifiService.get_status()
                self.wifi_ssid = wifi_ssid
                self.wifi_text = txt
                self._bake_content()
                self.queue_draw()
            GLib.idle_add(apply_final)

        WifiService.scan_networks_async(fast=fast, on_initial=on_initial, on_complete=on_complete)

    def connect_to_network(self, ssid, password=None):
        if self.wifi_connecting:
            return
        self.wifi_connecting = True
        self.wifi_status_msg = f"Connecting to {ssid}..."
        self.queue_draw()

        def on_complete(success, err_msg):
            def apply_result():
                self.wifi_connecting = False
                if success:
                    self.wifi_password_prompt_ssid = None
                    self.wifi_password_input = ""
                    self.wifi_status_msg = f"Connected to {ssid}!"
                    self.wifi_ssid = ssid
                    self.wifi_text = "Connected"
                    GLib.timeout_add(1500, self.scan_wifi_networks)
                else:
                    self.wifi_status_msg = f"Failed: {err_msg[:20]}"
                self.queue_draw()
            GLib.idle_add(apply_result)

        WifiService.connect_async(ssid, password=password, on_complete=on_complete)

    def disconnect_wifi(self):
        self.wifi_status_msg = "Disconnecting..."
        self.queue_draw()

        def on_complete(success):
            def apply_disc():
                self.wifi_status_msg = "Disconnected"
                self.wifi_ssid = ""
                self.wifi_text = "Disconnected"
                GLib.timeout_add(1000, self.scan_wifi_networks)
                self.queue_draw()
            GLib.idle_add(apply_disc)

        WifiService.disconnect_async(on_complete=on_complete)

    def toggle_wifi_radio(self):
        new_state = not self.wifi_radio_enabled
        self.wifi_radio_enabled = new_state
        if not new_state:
            self.wifi_networks = []
            self.wifi_ssid = ""
            self.wifi_text = "Disabled"
            self.wifi_status_msg = ""
        else:
            self.wifi_text = "Disconnected"
            self.wifi_status_msg = "Enabling Wi-Fi..."
        self._bake_content()
        self.queue_draw()

        def worker():
            WifiService.set_radio(new_state)
            if new_state:
                time.sleep(1.0)
                self.scan_wifi_networks(fast=False)
            else:
                def apply_off():
                    self.wifi_radio_enabled = False
                    self.wifi_networks = []
                    self.wifi_ssid = ""
                    self.wifi_text = "Disabled"
                    self.wifi_status_msg = ""
                    self._bake_content()
                    self.queue_draw()
                GLib.idle_add(apply_off)

        threading.Thread(target=worker, daemon=True).start()

    def submit_wifi_password(self):
        ssid = self.wifi_password_prompt_ssid
        pwd = self.wifi_password_input
        if not ssid:
            return
        if HAS_LAYER_SHELL:
            try:
                GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
            except Exception:
                pass
        self.connect_to_network(ssid, password=pwd)

    def get_ime_status(self):
        try:
            out = subprocess.check_output(["fcitx5-remote", "-n"], stderr=subprocess.DEVNULL).decode().strip()
            if any(k in out.lower() for k in ("unikey", "bamboo", "ngosen")):
                return "Vietnamese"
            return "English"
        except Exception:
            return "English"

    def get_wifi_status(self):
        txt, ssid = WifiService.get_status()
        self.wifi_radio_enabled = (txt != "Disabled")
        return txt, ssid

    def async_refresh_status(self):
        try:
            vol = AudioService.get_volume() / 100.0
            bri = BrightnessService.get_brightness() / 100.0
            bt_on = BluetoothService.is_enabled()
            bt_dev = BluetoothService.get_connected_device_name() if bt_on else ""
            pwr = PowerService.get_power_mode()
            ime = self.get_ime_status()
            wifi_txt, wifi_ssid = self.get_wifi_status()

            if self.current_page == "wifi" and self.wifi_radio_enabled and not self.wifi_networks and not self.wifi_scanning:
                self.scan_wifi_networks(fast=True)

            def apply():
                now = time.time()
                if not self.dragging_slider and (now - self.last_slider_drag_time) > 2.0:
                    self.vol_val = vol
                    self.bri_val = bri
                changed = (
                    self.bt_enabled != bt_on
                    or self.bt_device != bt_dev
                    or self.power_mode != pwr
                    or self.ime_text != ime
                    or self.wifi_text != wifi_txt
                    or self.wifi_ssid != wifi_ssid
                )
                self.bt_enabled = bt_on
                self.bt_device = bt_dev
                self.power_mode = pwr
                self.ime_text = ime
                self.wifi_text = wifi_txt
                self.wifi_ssid = wifi_ssid
                if changed and self.anim_state == "open":
                    self._bake_content()
                    self.queue_draw()
                return False

            GLib.idle_add(apply)
        except Exception:
            pass

    def load_notifications(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def refresh_status_tick(self):
        if self.anim_state == "open":
            threading.Thread(target=self.async_refresh_status, daemon=True).start()
        return True
