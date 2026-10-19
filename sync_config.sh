#!/usr/bin/env bash
# ==============================================================================
# 🌸 SERENA RICE CONFIG SYNC & AUTOMATION TOOL
# ==============================================================================
# Hỗ trợ tự động hóa đồng bộ 2 chiều và nạp lại môi trường tức thì:
#   1. ./sync_config.sh          (Mặc định: Đồng bộ Repo -> ~/.config & Reload)
#   2. ./sync_config.sh --pull   (Kéo ngược thay đổi từ ~/.config -> Repo)
#   3. ./sync_config.sh --diff   (So sánh khác biệt giữa Repo và Live Config)
# ==============================================================================

set -e

# Xác định thư mục repo (hỗ trợ cả khi chạy qua symlink)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
DOTFILES_DIR="$SCRIPT_DIR/hyprland-serena"

# Màu sắc hiển thị
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
PINK='\033[1;35m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
NC='\033[0m'

# =====================================================
# HÀM ĐỒNG BỘ: REPO -> SYSTEM (PUSH)
# =====================================================
sync_push() {
    echo -e "${PINK}================================================================${NC}"
    echo -e "${RED}   🌸 ĐỒNG BỘ CONFIG: REPO ➔ HỆ THỐNG (~/.config)   ${NC}"
    echo -e "${PINK}================================================================${NC}\n"

    # 1. Tạo thư mục đích nếu chưa có
    mkdir -p "$HOME/.config/hypr/scripts"
    mkdir -p "$HOME/.config/waybar"
    mkdir -p "$HOME/.config/rofi"
    mkdir -p "$HOME/.config/kitty"
    mkdir -p "$HOME/.config/wlogout"
    mkdir -p "$HOME/.config/swaync"
    mkdir -p "$HOME/.config/btop/themes"
    mkdir -p "$HOME/.config/fastfetch"
    mkdir -p "$HOME/.icons"
    mkdir -p "$HOME/.local/share/icons"
    mkdir -p "$HOME/Pictures/wallpapers"

    # 2. Đồng bộ các thành phần chính
    echo -e "${YELLOW}📦 [1/4] Đồng bộ các tệp cấu hình...${NC}"

    # Hyprland
    cp -rf "$DOTFILES_DIR/hypr/"* "$HOME/.config/hypr/"
    chmod +x "$HOME/.config/hypr/scripts/"*.sh "$HOME/.config/hypr/scripts/"*.py 2>/dev/null || true
    echo -e "  ${GREEN}✔ Hyprland (hyprland.lua, hyprland.conf, hyprlock.conf, scripts/)${NC}"

    # Waybar
    cp -rf "$DOTFILES_DIR/waybar/"* "$HOME/.config/waybar/"
    echo -e "  ${GREEN}✔ Waybar (config.jsonc, style.css, palette.css)${NC}"

    # Rofi
    cp -rf "$DOTFILES_DIR/rofi/"* "$HOME/.config/rofi/"
    mkdir -p "$HOME/.config/rofiSearch" 2>/dev/null || true
    cp -f "$DOTFILES_DIR/rofi/config.rasi" "$HOME/.config/rofiSearch/config.rasi" 2>/dev/null || true
    echo -e "  ${GREEN}✔ Rofi (config.rasi, colors-rofi.rasi)${NC}"

    # Kitty Terminal
    cp -rf "$DOTFILES_DIR/kitty/"* "$HOME/.config/kitty/"
    echo -e "  ${GREEN}✔ Kitty Terminal (kitty.conf)${NC}"

    # Wlogout
    cp -rf "$DOTFILES_DIR/wlogout/"* "$HOME/.config/wlogout/"
    echo -e "  ${GREEN}✔ Wlogout (layout, style.css, icons/)${NC}"

    # SwayNC
    cp -rf "$DOTFILES_DIR/swaync/"* "$HOME/.config/swaync/"
    echo -e "  ${GREEN}✔ SwayNC (config.json, style.css)${NC}"

    # Btop
    cp -rf "$DOTFILES_DIR/btop/"* "$HOME/.config/btop/"
    echo -e "  ${GREEN}✔ Btop (btop.conf, obsidian-wine.theme)${NC}"

    # Fastfetch
    if [ -d "$SCRIPT_DIR/fastfetch" ]; then
        cp -rf "$SCRIPT_DIR/fastfetch/"* "$HOME/.config/fastfetch/"
        echo -e "  ${GREEN}✔ Fastfetch (config.jsonc, sylveon_chibi.txt)${NC}"
    fi

    # 3. Đồng bộ Cursors & Wallpapers
    echo -e "\n${YELLOW}🖱️  [2/4] Kiểm tra Con trỏ chuột & Hình nền...${NC}"
    if [ -d "$SCRIPT_DIR/cursors/sylveon-custom" ]; then
        cp -rf "$SCRIPT_DIR/cursors/sylveon-custom" "$HOME/.icons/"
        cp -rf "$SCRIPT_DIR/cursors/sylveon-custom" "$HOME/.local/share/icons/"
        echo -e "  ${GREEN}✔ Bộ con trỏ chuột Sylveon Custom đã cập nhật (~/.icons & ~/.local/share/icons)${NC}"
    fi

    if [ -d "$SCRIPT_DIR/wallpapers" ]; then
        cp -rn "$SCRIPT_DIR/wallpapers/"* "$HOME/Pictures/wallpapers/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Thư mục hình nền ~/Pictures/wallpapers/${NC}"
    fi

    # 4. Reload Live Compositor & Services
    echo -e "\n${YELLOW}⚡ [3/4] Tự động nạp lại giao diện trực tiếp...${NC}"
    if [ "$XDG_CURRENT_DESKTOP" = "Hyprland" ] || pgrep -x "Hyprland" &>/dev/null; then
        # Reload Hyprland
        hyprctl reload &>/dev/null || true
        echo -e "  ${GREEN}✔ Đã reload Hyprland thành công!${NC}"

        # Reload Waybar
        if pgrep -x "waybar" &>/dev/null; then
            pkill -SIGUSR2 waybar 2>/dev/null || (pkill -x waybar && sleep 0.3 && nohup waybar >/dev/null 2>&1 &)
            echo -e "  ${GREEN}✔ Đã reload Waybar thành công!${NC}"
        fi

        # Cập nhật cursor live
        hyprctl setcursor sylveon-custom 24 &>/dev/null || true
    fi

    echo -e "\n${PINK}================================================================${NC}"
    echo -e "${GREEN}✨ ĐỒNG BỘ HOÀN TẤT! Toàn bộ thay đổi đã có hiệu lực trên máy! ✨${NC}"
    echo -e "${PINK}================================================================${NC}\n"
}

# =====================================================
# HÀM KÉO NGƯỢC: SYSTEM -> REPO (PULL)
# =====================================================
sync_pull() {
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${BLUE}   📥 KÉO THAY ĐỔI: HỆ THỐNG (~/.config) ➔ REPO   ${NC}"
    echo -e "${CYAN}================================================================${NC}\n"

    # Hyprland
    if [ -d "$HOME/.config/hypr" ]; then
        cp -rf "$HOME/.config/hypr/"* "$DOTFILES_DIR/hypr/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/hypr/ ➔ repo${NC}"
    fi

    # Waybar
    if [ -d "$HOME/.config/waybar" ]; then
        cp -rf "$HOME/.config/waybar/"* "$DOTFILES_DIR/waybar/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/waybar/ ➔ repo${NC}"
    fi

    # Rofi
    if [ -d "$HOME/.config/rofi" ]; then
        cp -rf "$HOME/.config/rofi/"* "$DOTFILES_DIR/rofi/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/rofi/ ➔ repo${NC}"
    fi

    # Kitty
    if [ -d "$HOME/.config/kitty" ]; then
        cp -rf "$HOME/.config/kitty/"* "$DOTFILES_DIR/kitty/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/kitty/ ➔ repo${NC}"
    fi

    # Wlogout
    if [ -d "$HOME/.config/wlogout" ]; then
        cp -rf "$HOME/.config/wlogout/"* "$DOTFILES_DIR/wlogout/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/wlogout/ ➔ repo${NC}"
    fi

    # SwayNC
    if [ -d "$HOME/.config/swaync" ]; then
        cp -rf "$HOME/.config/swaync/"* "$DOTFILES_DIR/swaync/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/swaync/ ➔ repo${NC}"
    fi

    # Btop
    if [ -d "$HOME/.config/btop" ]; then
        cp -rf "$HOME/.config/btop/"* "$DOTFILES_DIR/btop/"
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/btop/ ➔ repo${NC}"
    fi

    # Fastfetch
    if [ -d "$HOME/.config/fastfetch" ] && [ -d "$SCRIPT_DIR/fastfetch" ]; then
        cp -f "$HOME/.config/fastfetch/config.jsonc" "$SCRIPT_DIR/fastfetch/" 2>/dev/null || true
        cp -f "$HOME/.config/fastfetch/sylveon_chibi.txt" "$SCRIPT_DIR/fastfetch/" 2>/dev/null || true
        echo -e "  ${GREEN}✔ Đã kéo ~/.config/fastfetch/ ➔ repo${NC}"
    fi

    echo -e "\n${CYAN}================================================================${NC}"
    echo -e "${GREEN}✨ ĐÃ KÉO THAY ĐỔI VỀ REPO! Dùng 'git status' để xem diff. ✨${NC}"
    echo -e "${CYAN}================================================================${NC}\n"
}

# =====================================================
# HÀM SO SÁNH KHÁC BIỆT (DIFF)
# =====================================================
sync_diff() {
    echo -e "${YELLOW}🔍 So sánh khác biệt giữa Repo và ~/.config...${NC}\n"
    diff -rq "$DOTFILES_DIR/hypr" "$HOME/.config/hypr" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/waybar" "$HOME/.config/waybar" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/rofi" "$HOME/.config/rofi" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/kitty" "$HOME/.config/kitty" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/wlogout" "$HOME/.config/wlogout" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/swaync" "$HOME/.config/swaync" 2>/dev/null || true
    diff -rq "$DOTFILES_DIR/btop" "$HOME/.config/btop" 2>/dev/null || true
    echo -e "\n${GREEN}✔ Đã quét xong khác biệt!${NC}"
}

# =====================================================
# ROUTER LỆNH
# =====================================================
case "$1" in
    --pull|-p|pull)
        sync_pull
        ;;
    --diff|-d|diff)
        sync_diff
        ;;
    --help|-h|help)
        echo -e "${PINK}Cách dùng:${NC} $0 [tùy chọn]"
        echo -e "  ${GREEN}(không truyền cờ)${NC}  : Đẩy cấu hình từ Repo ➔ ~/.config và Reload ngay"
        echo -e "  ${YELLOW}--pull / pull${NC}     : Kéo thay đổi từ ~/.config ➔ Repo"
        echo -e "  ${BLUE}--diff / diff${NC}     : So sánh sự khác nhau giữa Repo và ~/.config"
        echo -e "  ${CYAN}--help / help${NC}     : Xem hướng dẫn này"
        ;;
    *)
        sync_push
        ;;
esac
