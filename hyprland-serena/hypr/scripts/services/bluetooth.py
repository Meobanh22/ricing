#!/usr/bin/env python3
# bluetooth.py — Bluetooth service using rfkill and bluetoothctl.

import subprocess
import shutil

class BluetoothService:
    @staticmethod
    def is_enabled() -> bool:
        """Returns True if Bluetooth is powered on and unblocked."""
        # 1. Check rfkill
        if shutil.which("rfkill"):
            try:
                res = subprocess.run(
                    ["rfkill", "list", "bluetooth"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0:
                    output = res.stdout.lower()
                    if "soft blocked: yes" in output or "hard blocked: yes" in output:
                        return False
                    if "soft blocked: no" in output:
                        return True
            except Exception:
                pass

        # 2. Check bluetoothctl
        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(
                    ["bluetoothctl", "show"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=1.0
                )
                if res.returncode == 0:
                    return "powered: yes" in res.stdout.lower()
            except Exception:
                pass

        return False

    @staticmethod
    def toggle_power() -> bool:
        """Toggles Bluetooth power and returns the new state."""
        currently_on = BluetoothService.is_enabled()
        target_state = not currently_on

        if target_state:
            # Turn ON
            if shutil.which("rfkill"):
                try:
                    subprocess.run(["rfkill", "unblock", "bluetooth"], check=False)
                except Exception:
                    pass
            if shutil.which("bluetoothctl"):
                try:
                    subprocess.Popen(["bluetoothctl", "power", "on"])
                except Exception:
                    pass
        else:
            # Turn OFF
            if shutil.which("bluetoothctl"):
                try:
                    subprocess.Popen(["bluetoothctl", "power", "off"])
                except Exception:
                    pass
            if shutil.which("rfkill"):
                try:
                    subprocess.run(["rfkill", "block", "bluetooth"], check=False)
                except Exception:
                    pass

        return target_state

    @staticmethod
    def get_connected_device_name() -> str:
        """Returns the name of the first connected Bluetooth device, or empty string."""
        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(
                    ["bluetoothctl", "devices", "Connected"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=1.0
                )
                if res.returncode == 0 and res.stdout.strip():
                    # Format: Device XX:XX:XX:XX:XX:XX DeviceName
                    line = res.stdout.strip().splitlines()[0]
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        return parts[2]
            except Exception:
                pass
        return ""

