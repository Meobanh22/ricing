#!/usr/bin/env bash
# toggle_vietnamese.sh — Toggle Vietnamese input method (Fcitx5).

if command -v fcitx5-remote &>/dev/null; then
    if ! pgrep -x "fcitx5" > /dev/null; then
        fcitx5 -d 2>/dev/null || true
        sleep 0.5
    fi
    fcitx5-remote -t 2>/dev/null || true
    exit 0
fi
