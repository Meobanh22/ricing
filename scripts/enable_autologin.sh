#!/usr/bin/env bash
# enable_autologin.sh — Enable TTY1 autologin for seamless Hyprlock startup.

set -e

USER_NAME="${SUDO_USER:-$USER}"

if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo bash $0"
    exit 1
fi

TARGET_DIR="/etc/systemd/system/getty@tty1.service.d"
CONF_FILE="$TARGET_DIR/autologin.conf"

mkdir -p "$TARGET_DIR"
cat << EOF > "$CONF_FILE"
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty -o '-p -f -- \\u' --noclear --autologin $USER_NAME %I \$TERM
Type=idle
EOF

systemctl daemon-reload
echo "✔ TTY1 autologin enabled for '$USER_NAME'! Reboot to enjoy your Hyprlock boot screen."

