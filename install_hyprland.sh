#!/usr/bin/env bash
# install_hyprland.sh — Hyprland installer for Ubuntu 24.04.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[1;31m'
PINK='\033[1;35m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${PINK}================================================================${NC}"
echo -e "${RED}   ✿ HYPRLAND DESKTOP SETUP (UBUNTU 24.04)   ${NC}"
echo -e "${PINK}================================================================${NC}\n"

# =====================================================
# [1/6] TẠO THƯ MỤC CẤU HÌNH
# =====================================================
echo -e "${YELLOW}[1/6] Khởi tạo các thư mục cấu hình...${NC}"
mkdir -p "$HOME/.config/hypr/scripts"
mkdir -p "$HOME/.config/waybar"
mkdir -p "$HOME/.config/rofi/wallust"
mkdir -p "$HOME/.config/fastfetch"
mkdir -p "$HOME/.config/kitty"
mkdir -p "$HOME/.config/fcitx5"
mkdir -p "$HOME/.config/gtk-3.0"
mkdir -p "$HOME/.config/gtk-4.0"
mkdir -p "$HOME/.icons/default"
mkdir -p "$HOME/.local/share/icons"
mkdir -p "$HOME/Pictures/Screenshots"
mkdir -p "$HOME/Pictures/wallpapers"
mkdir -p "$HOME/.config/wlogout/icons"
echo -e "  ${GREEN}✔ Đã tạo xong tất cả thư mục!${NC}"

# =====================================================
# [2/6] CÀI ĐẶT CON TRỎ CHUỘT SYLVEON CUSTOM (HYPRCURSOR NATIVE + XCURSOR)
# =====================================================
echo -e "\n${YELLOW}[2/6] Cài đặt bộ con trỏ chuột Sylveon Custom...${NC}"
if [ ! -f "$SCRIPT_DIR/cursors/sylveon-custom/manifest.hl" ] || [ ! -d "$SCRIPT_DIR/cursors/sylveon-custom/hyprcursors" ]; then
    echo -e "  ${YELLOW}Đang biên dịch bộ cursor sang chuẩn Hyprcursor native...${NC}"
    python3 "$SCRIPT_DIR/scripts/build_linux_cursors.py"
fi

# Copy cursor theme vào tất cả vị trí hệ thống tìm kiếm
cp -rf "$SCRIPT_DIR/cursors/sylveon-custom" "$HOME/.icons/"
cp -rf "$SCRIPT_DIR/cursors/sylveon-custom" "$HOME/.local/share/icons/"
sudo cp -rf "$SCRIPT_DIR/cursors/sylveon-custom" /usr/share/icons/ 2>/dev/null || true

# Tạo file kế thừa mặc định cho X11/XWayland
cat > "$HOME/.icons/default/index.theme" << 'CURSOR_EOF'
[Icon Theme]
Name=Default
Comment=Default Cursor Theme
Inherits=sylveon-custom
CURSOR_EOF

# GTK 3 & GTK 4 cursor
cat > "$HOME/.config/gtk-3.0/settings.ini" << 'GTK3_EOF'
[Settings]
gtk-cursor-theme-name=sylveon-custom
gtk-cursor-theme-size=24
GTK3_EOF

cat > "$HOME/.config/gtk-4.0/settings.ini" << 'GTK4_EOF'
[Settings]
gtk-cursor-theme-name=sylveon-custom
gtk-cursor-theme-size=24
GTK4_EOF

gsettings set org.gnome.desktop.interface cursor-theme "sylveon-custom" 2>/dev/null || true
gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true

echo -e "  ${GREEN}✔ Đã cài đặt Sylveon Dual Theme (Hyprcursor .hlc + Xcursor) thành công!${NC}"

# =====================================================
# [3/6] ĐỒNG BỘ CONFIGS (Hyprland, Waybar, Rofi, Kitty, Fastfetch)
# =====================================================
echo -e "\n${YELLOW}[3/6] Đồng bộ giao diện Waybar, Hyprland & Apps...${NC}"

# Dọn dẹp config cũ
rm -f "$HOME/.config/waybar/config" "$HOME/.config/waybar/style.css"
rm -f "$HOME/.config/waybar/config.jsonc"

# Hyprland
cp -r "$SCRIPT_DIR/hyprland-serena/hypr/"* "$HOME/.config/hypr/"
chmod +x "$HOME/.config/hypr/scripts/"* 2>/dev/null || true

# Kitty Terminal
cp "$SCRIPT_DIR/hyprland-serena/kitty/kitty.conf" "$HOME/.config/kitty/kitty.conf"

# Waybar (Bố cục ilyamiro chuẩn đẹp)
cp "$SCRIPT_DIR/hyprland-serena/waybar/palette.css" "$HOME/.config/waybar/palette.css" 2>/dev/null || true
cp "$SCRIPT_DIR/hyprland-serena/waybar/config.jsonc" "$HOME/.config/waybar/config"
cp "$SCRIPT_DIR/hyprland-serena/waybar/config.jsonc" "$HOME/.config/waybar/config.jsonc"
cp "$SCRIPT_DIR/hyprland-serena/waybar/style.css" "$HOME/.config/waybar/style.css"

# Rofi
cp "$SCRIPT_DIR/hyprland-serena/rofi/colors-rofi.rasi" "$HOME/.config/rofi/wallust/colors-rofi.rasi" 2>/dev/null || true
cp "$SCRIPT_DIR/hyprland-serena/rofi/colors-rofi.rasi" "$HOME/.config/rofi/colors-rofi.rasi" 2>/dev/null || true
cp "$SCRIPT_DIR/hyprland-serena/rofi/config.rasi" "$HOME/.config/rofi/config.rasi"
mkdir -p "$HOME/.config/rofiSearch"
cp "$SCRIPT_DIR/hyprland-serena/rofi/config.rasi" "$HOME/.config/rofiSearch/config.rasi" 2>/dev/null || true

# Fastfetch gọn gàng
cp "$SCRIPT_DIR/fastfetch/sylveon_chibi.txt" "$HOME/.config/fastfetch/"
cp "$SCRIPT_DIR/fastfetch/config.jsonc" "$HOME/.config/fastfetch/config.jsonc"
cp "$SCRIPT_DIR/fastfetch/config.jsonc" "$HOME/.config/fastfetch/config-compact.jsonc"
cp "$SCRIPT_DIR/fastfetch/config.jsonc" "$HOME/.config/fastfetch/config-v2.jsonc"
cp "$SCRIPT_DIR/fastfetch/config.jsonc" "$HOME/.config/fastfetch/config-pokemon.jsonc"
rm -f "$HOME/.config/fastfetch/ubuntu.png" 2>/dev/null || true

# Wlogout (Power Menu Tối giản 1 hàng 5 nút)
mkdir -p "$HOME/.config/wlogout/icons"
rm -f "$HOME/.config/wlogout/icons/"*
cp "$SCRIPT_DIR/hyprland-serena/wlogout/layout" "$HOME/.config/wlogout/layout"
cp "$SCRIPT_DIR/hyprland-serena/wlogout/style.css" "$HOME/.config/wlogout/style.css"
cp -r "$SCRIPT_DIR/hyprland-serena/wlogout/icons/"* "$HOME/.config/wlogout/icons/" 2>/dev/null || true

# SwayNC (Trung tâm thông báo im lặng, không popup ra ngoài)
mkdir -p "$HOME/.config/swaync"
cp "$SCRIPT_DIR/hyprland-serena/swaync/config.json" "$HOME/.config/swaync/config.json" 2>/dev/null || true
cp "$SCRIPT_DIR/hyprland-serena/swaync/style.css" "$HOME/.config/swaync/style.css" 2>/dev/null || true
pkill -x swaync 2>/dev/null || true
nohup swaync >/dev/null 2>&1 &

# Btop Task Manager Theme
mkdir -p "$HOME/.config/btop/themes"
cp "$SCRIPT_DIR/hyprland-serena/btop/themes/obsidian-wine.theme" "$HOME/.config/btop/themes/obsidian-wine.theme" 2>/dev/null || true
cp "$SCRIPT_DIR/hyprland-serena/btop/btop.conf" "$HOME/.config/btop/btop.conf" 2>/dev/null || true

echo -e "  ${GREEN}✔ Đã đồng bộ Hyprland, Waybar, Rofi, Fastfetch, Wlogout, SwayNC & Btop!${NC}"

# =====================================================
# [4/6] HÌNH NỀN DESKTOP
# =====================================================
echo -e "\n${YELLOW}[4/6] Đồng bộ hình nền...${NC}"
cp -r "$SCRIPT_DIR/wallpapers/"* "$HOME/Pictures/wallpapers/" 2>/dev/null || true
echo -e "  ${GREEN}✔ Đã đồng bộ hình nền vào ~/Pictures/wallpapers${NC}"

# =====================================================
# [5/6] THIẾT LẬP BỘ GÕ TIẾNG VIỆT (FCITX5 / IBUS)
# =====================================================
echo -e "\n${YELLOW}[5/6] Cấu hình bộ gõ Tiếng Việt...${NC}"
if command -v fcitx5 &>/dev/null; then
    # Cấu hình sẵn profile Fcitx5 với Unikey
    cat > "$HOME/.config/fcitx5/profile" << 'FCITX_EOF'
[Groups/0]
Name=Default
Default Layout=us
DefaultIM=unikey

[Groups/0/Items/0]
Name=keyboard-us
Layout=

[Groups/0/Items/1]
Name=unikey
Layout=

[GroupOrder]
0=Default
FCITX_EOF

    # Tắt hoàn toàn thông báo OSD và desktop notification khi đổi bộ gõ
    cat > "$HOME/.config/fcitx5/config" << 'FCITX_CFG_EOF'
[Behavior]
ActiveByDefault=False
ShareInputState=No
ShowInputMethodInformation=False
compactInputMethodInformation=True
ShowFirstInputMethodInformation=False

[Addons/notifications]
Enabled=False
FCITX_CFG_EOF

    pkill -9 fcitx5 2>/dev/null || true
    sleep 0.3
    fcitx5 -d --replace &>/dev/null &
    echo -e "  ${GREEN}✔ Đã kích hoạt Fcitx5-Unikey thành công (Dùng Ctrl + Space để bật/tắt)!${NC}"
else
    # Fallback IBus nếu chưa có fcitx5
    gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'Unikey']" 2>/dev/null || true
    gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us'), ('ibus', 'Unikey')]" 2>/dev/null || true
    pkill -9 ibus-daemon 2>/dev/null || true
    sleep 0.3
    ibus-daemon -drxR &>/dev/null &
    sleep 1.2
    ibus engine Unikey 2>/dev/null || true
    echo -e "  ${GREEN}✔ Đã khởi động IBus-Unikey!${NC}"
fi

# =====================================================
# [6/6] LÀM MỚI HYPRLAND & WAYBAR TRỰC TIẾP
# =====================================================
echo -e "\n${YELLOW}[6/6] Làm mới giao diện trực tiếp trên màn hình...${NC}"
if [ "$XDG_CURRENT_DESKTOP" = "Hyprland" ] || pgrep -x "Hyprland" &>/dev/null; then

    # Nạp con trỏ chuột Sylveon Custom trực tiếp vào Hyprland
    hyprctl setcursor sylveon-custom 24 &>/dev/null || true
    echo -e "  ${GREEN}✔ Con trỏ chuột Sylveon Custom đã được nạp!${NC}"

    # Đổi hình nền chuẩn repo
    python3 "$HOME/.config/hypr/scripts/wallpaper_switcher.py" current &>/dev/null || true

    # Reload Hyprland
    hyprctl reload &>/dev/null || true
    echo -e "  ${GREEN}✔ Hyprland đã reload!${NC}"

    # Khởi động lại Waybar
    pkill -x waybar 2>/dev/null || true
    sleep 0.8
    nohup waybar > "$HOME/.cache/waybar.log" 2>&1 &
    sleep 0.8

    if pgrep -x waybar &>/dev/null; then
        echo -e "  ${GREEN}✔ Waybar đã khởi động thành công!${NC}"
    else
        echo -e "  ${RED}⚠️ Waybar chưa hiển thị. Chi tiết từ log:${NC}"
        tail -5 "$HOME/.cache/waybar.log" 2>/dev/null || true
    fi

    pkill -f dashboard.py 2>/dev/null || true
fi

echo -e "\n${PINK}================================================================${NC}"
echo -e "${GREEN}✨ HOÀN TẤT CẬP NHẬT THEME DESKTOP! ✨${NC}"
echo -e "${PINK}================================================================${NC}\n"
