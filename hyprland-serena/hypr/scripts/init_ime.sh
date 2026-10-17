#!/usr/bin/env bash
# ==============================================================================
# 🇻🇳 KHỞI TẠO BỘ GÕ TIẾNG VIỆT CHO HYPRLAND
# ==============================================================================

# Cấu hình preload Unikey vào IBus và GNOME để luôn sẵn sàng
gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'Unikey']" 2>/dev/null || true
gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us'), ('ibus', 'Unikey')]" 2>/dev/null || true

# Khởi động lại ibus daemon sạch sẽ
pkill -9 ibus-daemon 2>/dev/null || true
sleep 0.5
ibus-daemon -drxR
sleep 1.2
ibus engine Unikey 2>/dev/null || true
