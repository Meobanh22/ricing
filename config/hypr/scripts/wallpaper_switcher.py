#!/usr/bin/env python3
# wallpaper_switcher.py — Wallpaper switcher tool.

import os
import sys
import glob
import subprocess
import time
import shutil

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Wallpaper directory resolution: prioritize ~/Pictures/wallpapers, fallback to repo assets/wallpapers
USER_WP_DIR = os.path.expanduser("~/Pictures/wallpapers")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
REPO_WP_DIR = os.path.join(REPO_ROOT, "assets", "wallpapers")

WALLPAPER_DIR = USER_WP_DIR if os.path.isdir(USER_WP_DIR) else (REPO_WP_DIR if os.path.isdir(REPO_WP_DIR) else USER_WP_DIR)
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
    print(f"✿ Applying wallpaper: {filename}")

    # Record current wallpaper state
    try:
        with open(STATE_FILE, "w") as f:
            f.write(filename)
    except Exception:
        pass

    # 1. Ensure wallpaper daemon is running (awww or swww)
    cmd = "awww" if shutil.which("awww") else ("swww" if shutil.which("swww") else None)
    daemon_cmd = f"{cmd}-daemon" if cmd else None

    if cmd:
        check = subprocess.run([cmd, "query"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check.returncode != 0 and daemon_cmd:
            subprocess.Popen([daemon_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.6)

        # Smooth 45-degree wipe transition
        subprocess.run([
            cmd, "img", filepath,
            "--transition-type", "wipe",
            "--transition-angle", "45",
            "--transition-step", "90",
            "--transition-fps", "60"
        ], stderr=subprocess.DEVNULL)

    # 2. Update GNOME settings for consistency
    if subprocess.run(["which", "gsettings"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        uri = f"file://{os.path.abspath(filepath)}"
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], stderr=subprocess.DEVNULL)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], stderr=subprocess.DEVNULL)

    # 3. Synchronize wallpaper for Hyprlock
    try:
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
