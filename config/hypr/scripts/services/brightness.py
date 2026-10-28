#!/usr/bin/env python3
# brightness.py — Screen brightness service using brightnessctl and sysfs.

import subprocess
import shutil
import glob
import os

class BrightnessService:
    @staticmethod
    def get_brightness() -> int:
        """Returns the current screen brightness as an integer percentage (0-100)."""
        if shutil.which("brightnessctl"):
            try:
                res = subprocess.run(
                    ["brightnessctl", "-m"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0 and res.stdout.strip():
                    # Format: device,class,current,percentage%,max
                    line = res.stdout.strip().splitlines()[0]
                    parts = line.split(",")
                    if len(parts) >= 4:
                        pct_str = parts[3].replace("%", "").strip()
                        if pct_str.isdigit():
                            return int(pct_str)
            except Exception:
                pass

        # Fallback to sysfs direct reading
        for bpath in glob.glob("/sys/class/backlight/*"):
            try:
                with open(os.path.join(bpath, "brightness"), "r") as f:
                    cur = int(f.read().strip())
                with open(os.path.join(bpath, "max_brightness"), "r") as f:
                    mx = int(f.read().strip())
                if mx > 0:
                    return int((cur / mx) * 100)
            except Exception:
                pass

        return 50

    @staticmethod
    def set_brightness(pct: int):
        """Sets screen brightness percentage (0-100, min clamped to 5% to prevent black screen)."""
        pct = max(5, min(100, int(pct)))
        if shutil.which("brightnessctl"):
            try:
                subprocess.Popen(["brightnessctl", "set", f"{pct}%"])
                return
            except Exception:
                pass

    @staticmethod
    def step(delta: int):
        """Increases or decreases brightness by delta percent."""
        cur = BrightnessService.get_brightness()
        BrightnessService.set_brightness(cur + delta)

