#!/usr/bin/env python3
# wifi.py — NetworkManager Wi-Fi service interface via nmcli.
# Provides synchronous and asynchronous network scanning, connection, and radio management.

import subprocess
import shutil
import threading
import time
from typing import List, Dict, Set, Tuple, Optional, Callable


class WifiService:
    """Manages Wi-Fi networking state, scanning, and connections via nmcli."""

    @staticmethod
    def _is_available() -> bool:
        return shutil.which("nmcli") is not None

    @staticmethod
    def get_wifi_device() -> str:
        """Finds the primary Wi-Fi interface name (e.g., 'wlan0')."""
        if not WifiService._is_available():
            return "wlan0"
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE", "dev"],
                capture_output=True, text=True, timeout=1.0, check=False
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 2 and parts[1] == "wifi":
                    return parts[0].strip()
        except Exception:
            pass
        return "wlan0"

    @staticmethod
    def is_radio_enabled() -> bool:
        """Returns True if Wi-Fi radio is enabled."""
        if not WifiService._is_available():
            return False
        try:
            res = subprocess.run(
                ["nmcli", "radio", "wifi"],
                capture_output=True, text=True, timeout=1.5, check=False
            )
            return res.stdout.strip().lower() == "enabled"
        except Exception:
            return False

    @staticmethod
    def set_radio(enabled: bool) -> bool:
        """Enables or disables Wi-Fi radio."""
        if not WifiService._is_available():
            return False
        try:
            state_str = "on" if enabled else "off"
            res = subprocess.run(
                ["nmcli", "radio", "wifi", state_str],
                capture_output=True, text=True, timeout=5.0, check=False
            )
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def toggle_radio() -> bool:
        """Toggles Wi-Fi radio state and returns the new state."""
        currently_on = WifiService.is_radio_enabled()
        target = not currently_on
        WifiService.set_radio(target)
        return target

    @staticmethod
    def get_status() -> Tuple[str, str]:
        """
        Returns (status_text, ssid).
        Possible states: ("Connected", "<ssid>"), ("Disconnected", ""), ("Disabled", "").
        """
        if not WifiService._is_available() or not WifiService.is_radio_enabled():
            return ("Disabled", "")

        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"],
                capture_output=True, text=True, timeout=1.0, check=False
            )
            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[1] == "wifi" and parts[2] == "connected":
                    ssid = parts[3].strip()
                    return ("Connected", ssid if ssid else "Connected")
        except Exception:
            pass

        return ("Disconnected", "")

    @staticmethod
    def get_saved_connections() -> Set[str]:
        """Returns set of known/saved Wi-Fi connection SSIDs."""
        saved = set()
        if not WifiService._is_available():
            return saved

        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                capture_output=True, text=True, timeout=3.0, check=False
            )
            for line in res.stdout.strip().splitlines():
                if not line:
                    continue
                parts = line.replace(r"\:", "__COLON__").split(":")
                parts = [p.replace("__COLON__", ":") for p in parts]
                if len(parts) >= 2 and parts[1] == "802-11-wireless":
                    saved.add(parts[0].strip())
        except Exception:
            pass
        return saved

    @staticmethod
    def parse_wifi_lines(output: str, saved_set: Optional[Set[str]] = None) -> List[Dict]:
        """
        Parses colon-separated Wi-Fi listing from:
        `nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi list`
        Deduplicates networks by SSID and sorts by active/saved/signal.
        """
        saved = saved_set if saved_set is not None else set()
        net_map = {}

        for line in output.strip().splitlines():
            if not line:
                continue
            parts = line.replace(r"\:", "__COLON__").split(":")
            parts = [p.replace("__COLON__", ":") for p in parts]
            if len(parts) >= 4:
                in_use = (parts[0].strip() == "*")
                ssid = parts[1].strip()
                try:
                    signal = int(parts[2])
                except ValueError:
                    signal = 0
                security = parts[3].strip()

                if not ssid or ssid == "--":
                    continue

                if ssid not in net_map:
                    net_map[ssid] = {
                        "ssid": ssid,
                        "in_use": in_use,
                        "signal": signal,
                        "security": security,
                        "saved": (ssid in saved)
                    }
                else:
                    was_in_use = net_map[ssid]["in_use"] or in_use
                    if in_use or signal > net_map[ssid]["signal"]:
                        net_map[ssid] = {
                            "ssid": ssid,
                            "in_use": was_in_use,
                            "signal": max(signal, net_map[ssid]["signal"]),
                            "security": security,
                            "saved": (ssid in saved)
                        }
                    else:
                        net_map[ssid]["in_use"] = was_in_use

        return sorted(
            net_map.values(),
            key=lambda x: (not x["in_use"], not x["saved"], -x["signal"])
        )

    @staticmethod
    def scan_networks(fast: bool = True) -> List[Dict]:
        """
        Scans nearby Wi-Fi networks synchronously.
        If fast is False or cached list is empty, performs a hardware rescan.
        """
        if not WifiService._is_available() or not WifiService.is_radio_enabled():
            return []

        saved = WifiService.get_saved_connections()
        nets = []
        try:
            # 1. Quick initial scan from nmcli cache
            res_fast = subprocess.run(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                capture_output=True, text=True, timeout=4.0, check=False
            )
            nets_initial = WifiService.parse_wifi_lines(res_fast.stdout, saved)

            # 2. Hardware rescan if requested or if cached list is sparse
            if not fast or len(nets_initial) <= 1:
                try:
                    subprocess.run(
                        ["nmcli", "dev", "wifi", "rescan"],
                        capture_output=True, timeout=3.0, check=False
                    )
                    time.sleep(1.2)
                except Exception:
                    pass
                res_full = subprocess.run(
                    ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                    capture_output=True, text=True, timeout=4.0, check=False
                )
                nets_full = WifiService.parse_wifi_lines(res_full.stdout, saved)
                nets = nets_full if nets_full else nets_initial
            else:
                nets = nets_initial
        except Exception:
            pass

        return nets

    @staticmethod
    def scan_networks_async(
        fast: bool = True,
        on_initial: Optional[Callable[[List[Dict], bool], None]] = None,
        on_complete: Optional[Callable[[List[Dict], bool], None]] = None
    ):
        """
        Performs network scan in a background thread to prevent GUI freezing.
        Calls on_initial(networks, radio_on) when cache is ready,
        then calls on_complete(networks, radio_on) when full scan finishes.
        """
        def worker():
            radio_on = WifiService.is_radio_enabled()
            if not radio_on:
                if on_complete:
                    on_complete([], False)
                return

            saved = WifiService.get_saved_connections()
            nets_initial = []
            try:
                res_fast = subprocess.run(
                    ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                    capture_output=True, text=True, timeout=4.0, check=False
                )
                nets_initial = WifiService.parse_wifi_lines(res_fast.stdout, saved)
                if on_initial and nets_initial:
                    on_initial(nets_initial, radio_on)
            except Exception:
                pass

            nets = nets_initial
            if not fast or len(nets_initial) <= 1:
                try:
                    subprocess.run(
                        ["nmcli", "dev", "wifi", "rescan"],
                        capture_output=True, timeout=3.0, check=False
                    )
                    time.sleep(1.2)
                    res_full = subprocess.run(
                        ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                        capture_output=True, text=True, timeout=4.0, check=False
                    )
                    nets_full = WifiService.parse_wifi_lines(res_full.stdout, saved)
                    if nets_full:
                        nets = nets_full
                except Exception:
                    pass

            if on_complete:
                on_complete(nets, radio_on)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def connect(ssid: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Connects to a Wi-Fi network synchronously.
        Returns (success: bool, error_message: str).
        """
        if not WifiService._is_available():
            return False, "nmcli is not installed"

        try:
            if password is not None:
                res = subprocess.run(
                    ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
                    capture_output=True, text=True, timeout=25.0, check=False
                )
            else:
                # Try connection up first
                res = subprocess.run(
                    ["nmcli", "con", "up", "id", ssid],
                    capture_output=True, text=True, timeout=15.0, check=False
                )
                if res.returncode != 0:
                    res = subprocess.run(
                        ["nmcli", "dev", "wifi", "connect", ssid],
                        capture_output=True, text=True, timeout=15.0, check=False
                    )

            success = (res.returncode == 0)
            err_msg = "" if success else (res.stderr.strip() or "Connection failed")
            return success, err_msg
        except Exception as e:
            return False, str(e)

    @staticmethod
    def connect_async(
        ssid: str,
        password: Optional[str] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ):
        """Connects to a network in background thread, calling on_complete(success, err_msg)."""
        def worker():
            success, err_msg = WifiService.connect(ssid, password)
            if on_complete:
                on_complete(success, err_msg)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def disconnect(device: Optional[str] = None) -> bool:
        """Disconnects the active Wi-Fi interface."""
        if not WifiService._is_available():
            return False
        dev = device or WifiService.get_wifi_device()
        try:
            res = subprocess.run(
                ["nmcli", "dev", "disconnect", dev],
                capture_output=True, timeout=5.0, check=False
            )
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def disconnect_async(device: Optional[str] = None, on_complete: Optional[Callable[[bool], None]] = None):
        """Disconnects in background thread, calling on_complete(success)."""
        def worker():
            success = WifiService.disconnect(device)
            if on_complete:
                on_complete(success)

        threading.Thread(target=worker, daemon=True).start()
