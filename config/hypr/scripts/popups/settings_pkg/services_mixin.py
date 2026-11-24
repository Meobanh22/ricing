#!/usr/bin/env python3
# settings_pkg/services_mixin.py — Asset loading and hardware/system polling for Settings.

import json
import os
import subprocess

import cairo

from services.audio import AudioService
from services.bluetooth import BluetoothService
from services.brightness import BrightnessService
from services.power import PowerService
from settings_pkg.constants import CACHE_FILE, SYSTEM_DIR
from ui_core import resolve_asset


class SettingsServicesMixin:
    """Asset resolution and hardware/media/notification polling."""

    def load_assets(self):
        def load_png(*names):
            for name in names:
                p = resolve_asset(name)
                if p:
                    try:
                        return cairo.ImageSurface.create_from_png(p)
                    except Exception:
                        pass
            return None

        self.asset_bow = load_png("serena_ribbon_bow_clean.png", "serena_ribbon_bow.png")
        self.asset_heart = load_png("serena_heart_button_clean.png", "serena_heart_button.png")
        self.asset_hinge = load_png("serena_hinge.png")
        self.asset_map = load_png("serena_kalos_map.png")
        self.asset_guide = load_png("serena_dendemille_guide.png")

    def refresh_all_services(self):
        try:
            self.volume = AudioService.get_volume()
            self.is_muted = AudioService.is_muted()
        except Exception:
            pass
        try:
            self.brightness = BrightnessService.get_brightness()
        except Exception:
            pass
        try:
            self.bt_enabled = BluetoothService.is_enabled()
        except Exception:
            pass
        try:
            self.power_mode = PowerService.get_power_mode()
        except Exception:
            pass
        self.update_ime()
        self.update_wifi()
        self.update_media()
        self.load_notifications()

    def update_ime(self):
        ime_sh = os.path.join(SYSTEM_DIR, "get_ime.sh")
        if os.path.exists(ime_sh):
            try:
                out = subprocess.check_output([ime_sh], text=True, timeout=1).strip()
                if "VIE" in out or "Tiếng Việt" in out:
                    self.ime_text = "Vietnamese"
                elif "ENG" in out:
                    self.ime_text = "English"
            except Exception:
                pass

    def update_wifi(self):
        try:
            res = subprocess.run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"], capture_output=True, text=True, timeout=1)
            active_ssid = None
            for line in res.stdout.strip().split("\n"):
                if line.startswith("yes:"):
                    active_ssid = line.split(":", 1)[1]
                    break
            self.wifi_ssid = active_ssid if active_ssid else "Offline"
        except Exception:
            self.wifi_ssid = "Offline"

    def update_media(self):
        try:
            stat = subprocess.check_output(["playerctl", "status"], text=True, timeout=1).strip()
            self.media_status = stat if stat else "Stopped"
            if self.media_status in ("Playing", "Paused"):
                t = subprocess.check_output(["playerctl", "metadata", "--format", "{{title}}"], text=True, timeout=1).strip()
                a = subprocess.check_output(["playerctl", "metadata", "--format", "{{artist}}"], text=True, timeout=1).strip()
                self.media_title = t if t else "Playing"
                self.media_artist = a if a else "Unknown Artist"
            else:
                self.media_title = "No music playing"
                self.media_artist = ""
        except Exception:
            self.media_status = "Stopped"
            self.media_title = "No music playing"
            self.media_artist = ""

    def load_notifications(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    self.notifications = json.load(f)
            except Exception:
                self.notifications = []
        else:
            self.notifications = []

    def periodic_poll(self):
        if self.anim_state != "closed":
            self.refresh_all_services()
            self.queue_draw()
        return True
