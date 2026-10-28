#!/usr/bin/env python3
# power.py — Power and battery service.

import os
import glob
import shutil
import subprocess

BAT_PATH = "/sys/class/power_supply/BAT0"

class PowerService:
    @staticmethod
    def get_battery_info() -> dict:
        """Returns battery status dictionary."""
        bat_dir = BAT_PATH
        if not os.path.exists(bat_dir):
            matches = glob.glob("/sys/class/power_supply/BAT*")
            if matches:
                bat_dir = matches[0]
            else:
                return {
                    "capacity": 100,
                    "status": "Unknown",
                    "is_charging": False,
                    "has_battery": False
                }

        try:
            with open(os.path.join(bat_dir, "capacity"), "r") as f:
                capacity = int(f.read().strip())
        except Exception:
            capacity = 100

        try:
            with open(os.path.join(bat_dir, "status"), "r") as f:
                status = f.read().strip()
        except Exception:
            status = "Unknown"

        is_charging = status.lower() in ["charging", "full"]

        return {
            "capacity": capacity,
            "status": status,
            "is_charging": is_charging,
            "has_battery": True
        }

    @staticmethod
    def get_power_mode() -> str:
        """Returns current power mode ('powersave', 'balanced', or 'performance')."""
        if os.path.exists("/tmp/serena_power_mode.txt"):
            try:
                with open("/tmp/serena_power_mode.txt", "r") as f:
                    mode = f.read().strip().lower()
                    if mode in ["powersave", "balanced", "performance"]:
                        return mode
            except Exception:
                pass

        if shutil.which("powerprofilesctl"):
            try:
                res = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return res.stdout.strip()
            except Exception:
                pass

        # Check CPU governor
        gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        if os.path.exists(gov_path):
            try:
                with open(gov_path, "r") as f:
                    return f.read().strip()
            except Exception:
                pass

        return "powersave"

    @staticmethod
    def set_power_mode(mode: str):
        """Sets power mode ('powersave', 'balanced', or 'performance')."""
        try:
            with open("/tmp/serena_power_mode.txt", "w") as f:
                f.write(mode.lower())
        except Exception:
            pass

        if shutil.which("powerprofilesctl"):
            try:
                subprocess.Popen(["powerprofilesctl", "set", mode])
                return
            except Exception:
                pass

        gov = "performance" if mode == "performance" else "powersave"
        for gov_file in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"):
            try:
                with open(gov_file, "w") as f:
                    f.write(gov)
            except Exception:
                pass

    @staticmethod
    def notify_low_battery(capacity: int, level: str = "warning"):
        """Triggers desktop notification for low battery."""
        if not shutil.which("notify-send"):
            return

        if level == "critical":
            subprocess.Popen([
                "notify-send",
                "-u", "critical",
                "-a", "Serena Power",
                "-i", "battery-empty",
                "⚠️ Battery Critical!",
                f"Battery level is at {capacity}%. Plug in charger immediately!"
            ])
            # Optional system bell / sound
            subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"], stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([
                "notify-send",
                "-u", "normal",
                "-a", "Serena Power",
                "-i", "battery-caution",
                "✿ Battery Low",
                f"Battery is at {capacity}%. Consider plugging in your charger."
            ])

