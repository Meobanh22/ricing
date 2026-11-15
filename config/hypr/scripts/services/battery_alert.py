#!/usr/bin/env python3
# battery_alert.py — Low battery notification daemon.

import os
import sys
import time

# Add services directory and parent scripts directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
for p in (SCRIPT_DIR, PARENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from power import PowerService
except ImportError:
    from services.power import PowerService

PID_FILE = "/tmp/battery_alert.pid"

def acquire_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Check if process is running
            os.kill(old_pid, 0)
            # Already running, exit
            sys.exit(0)
        except (OSError, ValueError):
            pass
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

def main():
    acquire_pid()
    notified_warning = False
    notified_critical = False

    while True:
        try:
            info = PowerService.get_battery_info()
            if not info["has_battery"]:
                time.sleep(60)
                continue

            cap = info["capacity"]
            is_charging = info["is_charging"]

            if is_charging:
                # Reset notifications once user plugs in charger
                notified_warning = False
                notified_critical = False
            else:
                if cap <= 10 and not notified_critical:
                    PowerService.notify_low_battery(cap, level="critical")
                    notified_critical = True
                    notified_warning = True
                elif cap <= 20 and not notified_warning:
                    PowerService.notify_low_battery(cap, level="warning")
                    notified_warning = True
                elif cap > 22:
                    notified_warning = False
                    notified_critical = False

            time.sleep(30)
        except Exception:
            time.sleep(30)

if __name__ == "__main__":
    main()

