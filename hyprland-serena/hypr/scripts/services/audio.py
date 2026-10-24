#!/usr/bin/env python3
# audio.py — Audio service abstraction using pamixer and wpctl.

import subprocess
import shutil

class AudioService:
    @staticmethod
    def get_volume() -> int:
        """Returns the current master volume as an integer (0-100)."""
        if shutil.which("pamixer"):
            try:
                res = subprocess.run(
                    ["pamixer", "--get-volume"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    return int(res.stdout.strip())
            except Exception:
                pass

        if shutil.which("wpctl"):
            try:
                res = subprocess.run(
                    ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0:
                    # Output format: Volume: 0.65 [MUTED]
                    parts = res.stdout.strip().split()
                    if len(parts) >= 2:
                        return int(float(parts[1]) * 100)
            except Exception:
                pass

        return 50

    @staticmethod
    def set_volume(val: int):
        """Sets the master volume to an integer (0-100)."""
        val = max(0, min(100, int(val)))
        if shutil.which("pamixer"):
            try:
                subprocess.Popen(["pamixer", "--set-volume", str(val)])
                return
            except Exception:
                pass

        if shutil.which("wpctl"):
            try:
                subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{val/100:.2f}"])
            except Exception:
                pass

    @staticmethod
    def is_muted() -> bool:
        """Returns True if master audio is muted."""
        if shutil.which("pamixer"):
            try:
                res = subprocess.run(
                    ["pamixer", "--get-mute"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0:
                    return res.stdout.strip().lower() == "true"
            except Exception:
                pass

        if shutil.which("wpctl"):
            try:
                res = subprocess.run(
                    ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0:
                    return "[MUTED]" in res.stdout
            except Exception:
                pass

        return False

    @staticmethod
    def toggle_mute():
        """Toggles audio mute state."""
        if shutil.which("pamixer"):
            try:
                subprocess.Popen(["pamixer", "-t"])
                return
            except Exception:
                pass

        if shutil.which("wpctl"):
            try:
                subprocess.Popen(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
            except Exception:
                pass

