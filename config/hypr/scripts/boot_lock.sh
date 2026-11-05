#!/usr/bin/env bash
# boot_lock.sh — Display Hyprlock as the initial startup / lock screen.

# Bypass if disabled by user flag
if [ -f "$HOME/.config/hypr/.no_boot_lock" ]; then
    exit 0
fi

# Run hyprlock if not already running
if ! pidof hyprlock >/dev/null; then
    hyprlock
fi

