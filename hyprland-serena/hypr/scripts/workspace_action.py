#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA WORKSPACE ACTION DISPATCHER
# ==============================================================================
# Xử lý click chuột trên thanh Waybar tương thích chuẩn Hyprland 0.56+ (Lua Engine):
# - Chuột trái: Chuyển màn hình sang Workspace tương ứng (hl.dsp.focus)
# - Chuột phải: Di chuyển cửa sổ đang active sang Workspace tương ứng (hl.dsp.window.move)
# Hỗ trợ cả direct ID placeholder {id} lẫn auto fallback theo tọa độ chuột.
# ==============================================================================

import sys
import subprocess

def get_target_workspace():
    try:
        out = subprocess.check_output(["hyprctl", "cursorpos"], stderr=subprocess.DEVNULL).decode().strip()
        parts = out.split(",")
        if len(parts) != 2:
            return 1
        x = float(parts[0].strip())
    except Exception:
        return 1

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

    return target_ws

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "focus"
    
    target_ws = None
    if len(sys.argv) > 2:
        val = sys.argv[2].strip()
        if val.isdigit():
            target_ws = int(val)

    if target_ws is None:
        target_ws = get_target_workspace()

    if action == "move":
        # Chuột phải: chuyển cửa sổ active sang workspace
        cmd = f"hl.dsp.window.move({{ workspace = {target_ws} }})"
    else:
        # Chuột trái: chuyển sang workspace
        cmd = f"hl.dsp.focus({{ workspace = {target_ws} }})"

    subprocess.run(["hyprctl", "dispatch", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
