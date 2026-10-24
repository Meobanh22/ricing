#!/usr/bin/env bash
# setup_linux.sh — Setup script for Linux desktop components.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\033[1;35m=========================================="
echo -e "   ✿ SETUP LINUX DESKTOP ✿         "
echo -e "==========================================\033[0m\n"

# 1. Đồng bộ Fastfetch
echo -e "\033[1;33m[1/2] Đồng bộ Fastfetch...\033[0m"
FASTFETCH_CONF_DIR="$HOME/.config/fastfetch"
mkdir -p "$FASTFETCH_CONF_DIR"

if [ -f "$SCRIPT_DIR/fastfetch/sylveon_chibi.txt" ]; then
    cp "$SCRIPT_DIR/fastfetch/sylveon_chibi.txt" "$FASTFETCH_CONF_DIR/"
    echo -e "  \033[1;32m✔ Đã copy sylveon_chibi.txt -> ~/.config/fastfetch/\033[0m"
fi

if [ -f "$SCRIPT_DIR/fastfetch/config.jsonc" ]; then
    cp "$SCRIPT_DIR/fastfetch/config.jsonc" "$FASTFETCH_CONF_DIR/"
    echo -e "  \033[1;32m✔ Đã cập nhật config.jsonc -> ~/.config/fastfetch/\033[0m"
fi

# 2. Wallpapers
echo -e "\n\033[1;33m[2/2] Thiết lập thư mục hình nền...\033[0m"
TARGET_WP_DIR="$HOME/Pictures/wallpapers"
mkdir -p "$HOME/Pictures"

if [ ! -d "$TARGET_WP_DIR" ]; then
    ln -s "$SCRIPT_DIR/wallpapers" "$TARGET_WP_DIR"
    echo -e "  \033[1;32m✔ Đã tạo symlink wallpapers -> $TARGET_WP_DIR\033[0m"
else
    echo -e "  \033[1;34mℹ Thư mục $TARGET_WP_DIR đã tồn tại. Bạn có thể dùng trực tiếp thư mục wallpapers/ trong repo.\033[0m"
fi

echo -e "\n\033[1;36m✨ HOÀN TẤT SETUP TRÊN LINUX! Chúc bạn rice máy xinh lung linh! ✨\033[0m\n"

