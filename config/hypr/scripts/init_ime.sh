#!/usr/bin/env bash
# init_ime.sh — Initialize Vietnamese input method for Hyprland.

pkill -x fcitx5 2>/dev/null || true
sleep 0.5
fcitx5 -d --replace 2>/dev/null || fcitx5 -d
