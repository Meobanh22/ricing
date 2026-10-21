#!/usr/bin/env python3
import subprocess
import os

def main():
    try:
        out = subprocess.check_output(["hyprctl", "cursorpos"], stderr=subprocess.DEVNULL).decode().strip()
        parts = out.split(",")
        if len(parts) != 2:
            return
        x = float(parts[0].strip())
        y = float(parts[1].strip())
    except Exception as e:
        return

    pill_left = 98.0
    pill_right = 372.0
    slot_width = (pill_right - pill_left) / 5.0

    if x <= pill_left:
        target_ws = 1
    elif x >= pill_right:
        target_ws = 5
    else:
        target_ws = int((x - pill_left) / slot_width) + 1
        target_ws = max(1, min(5, target_ws))

    try:
        with open("/tmp/ws_click.log", "a") as f:
            f.write(f"Right-click at x={x}, y={y} -> Moved active window to WS {target_ws}\n")
    except Exception:
        pass

    subprocess.run(["hyprctl", "dispatch", "movetoworkspace", str(target_ws)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
