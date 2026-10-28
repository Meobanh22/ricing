#!/usr/bin/env bash
# toggle_vietnamese.sh — Toggle Vietnamese input method (Fcitx5 / IBus).

if command -v fcitx5-remote &>/dev/null && pgrep -x "fcitx5" > /dev/null; then
    fcitx5-remote -t 2>/dev/null || true
    exit 0
fi

# Fallback IBus
if ! pgrep -x "ibus-daemon" > /dev/null; then
    ibus-daemon -drxR
    sleep 0.8
fi

CURR=$(ibus engine 2>/dev/null || echo "")

if [ "$CURR" = "Unikey" ]; then
    ibus engine xkb:us::eng 2>/dev/null || true
else
    ibus engine Unikey 2>/dev/null || true
fi
