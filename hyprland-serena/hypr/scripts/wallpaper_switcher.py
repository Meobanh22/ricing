#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA WALLPAPER SWITCHER (DÙNG CHÍNH XÁC KHO ẢNH TRONG REPO)
# ==============================================================================
# Chuyển đổi qua lại mượt mà các hình nền trong thư mục wallpapers
# Thiết kế tối giản: KHÔNG popup thông báo

import os
import sys
import glob
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Đường dẫn chuẩn tới thư mục wallpapers của repo
REPO_WP_DIR = "/home/meobanh/custom/ricing/wallpapers"
FALLBACK_WP_DIR = os.path.expanduser("~/Pictures/wallpapers")

WALLPAPER_DIR = REPO_WP_DIR if os.path.isdir(REPO_WP_DIR) else FALLBACK_WP_DIR
STATE_FILE = os.path.join(WALLPAPER_DIR, ".current_wallpaper")

def get_wallpaper_list():
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(WALLPAPER_DIR, ext)))
    files.sort()
    return files

def get_current_wallpaper(files):
    if not files:
        return None
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                name = f.read().strip()
                for fp in files:
                    if os.path.basename(fp) == name:
                        return fp
        except Exception:
            pass
    return files[0]

def set_wallpaper(filepath):
    if not filepath or not os.path.isfile(filepath):
        print(f"Error: Wallpaper file not found: {filepath}")
        return

    filename = os.path.basename(filepath)
    print(f"🌸 Applying wallpaper: {filename}")

    # Ghi nhận trạng thái ảnh hiện tại
    try:
        with open(STATE_FILE, "w") as f:
            f.write(filename)
    except Exception:
        pass

    # 1. Đảm bảo swww-daemon đang chạy
    is_swww = subprocess.run(["which", "swww"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    if is_swww:
        check = subprocess.run(["swww", "query"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check.returncode != 0:
            subprocess.Popen(["swww-daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.6)

        # Chuyển cảnh quét góc mượt mà
        subprocess.run([
            "swww", "img", filepath,
            "--transition-type", "wipe",
            "--transition-angle", "45",
            "--transition-step", "90",
            "--transition-fps", "60"
        ], stderr=subprocess.DEVNULL)

    # 2. Cập nhật GNOME (để đồng bộ cả 2 nơi)
    if subprocess.run(["which", "gsettings"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        uri = f"file://{os.path.abspath(filepath)}"
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], stderr=subprocess.DEVNULL)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], stderr=subprocess.DEVNULL)

    # 3. Đồng bộ ảnh nền cho Hyprlock
    try:
        import shutil
        lock_wp = os.path.expanduser("~/.config/hypr/wallpaper_effects/.wallpaper_current")
        os.makedirs(os.path.dirname(lock_wp), exist_ok=True)
        shutil.copy2(filepath, lock_wp)
    except Exception:
        pass

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "next"
    files = get_wallpaper_list()
    if not files:
        print(f"No wallpapers found in {WALLPAPER_DIR}")
        return

    curr = get_current_wallpaper(files)
    idx = files.index(curr) if curr in files else 0

    if action == "next":
        idx = (idx + 1) % len(files)
        set_wallpaper(files[idx])
    elif action == "prev":
        idx = (idx - 1 + len(files)) % len(files)
        set_wallpaper(files[idx])
    elif action == "current":
        set_wallpaper(files[idx])
    elif action == "random":
        import random
        set_wallpaper(random.choice(files))
    else:
        print(f"Unknown action: {action}. Use next, prev, current, random.")

if __name__ == "__main__":
    main()
