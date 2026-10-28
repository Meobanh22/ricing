#!/usr/bin/env bash
# init_ime.sh — Initialize Vietnamese input method for Hyprland.

# Preload Unikey into IBus and GNOME to ensure readiness
gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'Unikey']" 2>/dev/null || true
gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us'), ('ibus', 'Unikey')]" 2>/dev/null || true

# Clean restart of ibus daemon
pkill -9 ibus-daemon 2>/dev/null || true
sleep 0.5
ibus-daemon -drxR
sleep 1.2
ibus engine Unikey 2>/dev/null || true
