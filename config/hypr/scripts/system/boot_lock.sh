#!/usr/bin/env bash
# boot_lock.sh — Boot transition into Hyprlock with Plymouth handover.

if [ -f "$HOME/.config/hypr/.no_boot_lock" ]; then
    sudo /usr/bin/plymouth quit --retain-splash 2>/dev/null || true
    exit 0
fi

if ! pidof hyprlock >/dev/null; then
    # Launch hyprlock immediately
    hyprlock --immediate-render &
    HYPRLOCK_PID=$!

    # Pause to allow Hyprlock initial frame presentation
    sleep 0.2
    # Quit Plymouth cleanly retaining splash buffer
    sudo /usr/bin/plymouth quit --retain-splash 2>/dev/null || true

    wait "$HYPRLOCK_PID"
fi
