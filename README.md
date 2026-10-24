# ✿ Desktop Rice (Hyprland • Warm Obsidian-Wine & Ribbon Red)

Bộ công cụ tùy biến giao diện desktop phong cách tối giản hiện đại (Minimalist Anime Ricing) trên **Ubuntu 24.04 + Hyprland (Wayland)**.

---

## ⚡ Hướng Dẫn Cài Đặt (Chỉ 1 Click)

### 🐧 Trên Linux (Ubuntu 24.04 / Hyprland):
1. **Clone repository về máy:**
   ```bash
   git clone git@github.com:Meobanh22/ricing.git
   cd ricing
   ```

2. **Cài đặt trọn bộ giao diện (1-Click cho Hyprland):**
   ```bash
   chmod +x ./install_hyprland.sh
   ./install_hyprland.sh
   ```
   *Script tự động cài đặt và cấu hình Waybar, Control Center, Profile Dashboard, Hyprlock, Wlogout, Rofi, Kitty, Btop, Fcitx5-Unikey và Con trỏ chuột Sylveon Custom.*

3. **Đồng bộ tự động & Nạp lại ngay (khi đang chỉnh sửa / phát triển):**
   ```bash
   chmod +x ./sync_config.sh
   ./sync_config.sh           # Đẩy thay đổi từ Repo ➔ ~/.config & Reload
   ./sync_config.sh --pull    # Kéo thay đổi từ ~/.config ➔ Repo
   ./sync_config.sh --diff    # So sánh khác biệt giữa Repo và máy
   ```

4. **Hoặc chỉ cài Fastfetch & Wallpapers:**
   ```bash
   chmod +x ./setup_linux.sh
   ./setup_linux.sh
   ```

---

## 🎮 Các Phím Tắt Tiêu Biểu (Keybindings)

| Phím tắt | Tác dụng |
| :--- | :--- |
| `Super + B` | Mở Trình duyệt Web (Firefox Hardware-Accelerated) |
| `Super + Return` | Mở Terminal (Kitty) |
| `Super + Space` / `Super + A` | Mở Menu Ứng dụng (Rofi drun) |
| `Super + N` | Mở / Đóng Control Center |
| `Super + D` | Mở / Đóng Profile Dashboard |
| `Ctrl + Shift + Esc` | Mở Task Manager (Btop - Floating Wine Card) |
| `Super + L` | Khóa màn hình (Hyprlock) |
| `Super + Backspace` | Power Menu đăng xuất / tắt máy (Wlogout) |
| `Ctrl + Alt + W` / `Win + Alt + W` | Đổi hình nền tiếp theo |
| `Print` / `Super + Shift + S` | Chụp ảnh màn hình (Grim + Slurp + Swappy) |

---

## 🖱️ Bộ Con Trỏ Chuột (Cursors)

Thư mục `cursors/sylveon-custom` hỗ trợ chuẩn kép:
- **Hyprcursor native (.hlc)**: Tối ưu cho Wayland / Hyprland rendering mượt mà, sắc nét.
- **Xcursor (cursors/ + index.theme)**: Kế thừa hoàn hảo cho các ứng dụng GTK 3/4 và XWayland.

Để biên dịch lại bộ con trỏ từ assets:
```bash
python3 ./scripts/build_linux_cursors.py
```

---

## 📁 Cấu Trúc Thư Mục

```text
ricing/
├── 📂 hyprland-serena/     # Dotfiles nguồn (Hyprland, Waybar, Rofi, Kitty, Wlogout, SwayNC, Btop)
├── 📂 cursors/             # Bộ con trỏ chuột Sylveon Custom (Hyprcursor & Xcursor)
├── 📂 wallpapers/          # Kho hình nền anime tuyển chọn
├── 📂 assets/              # Avatar, icon và sprite ảnh nguồn
├── 📂 scripts/             # Script Python (build cursor, tạo wallpaper ASCII, tinh chỉnh)
├── 📂 fastfetch/           # Cấu hình Fastfetch & ASCII logo Sylveon Chibi
├── 📂 profile/             # Ghi chú cá nhân & Gemini Custom Gems
├── 🚀 install_hyprland.sh  # Script 1-click cài đặt và đồng bộ toàn bộ hệ thống
├── 🚀 setup_linux.sh       # Script đồng bộ nhanh Fastfetch & Wallpapers
└── 📖 README.md
```
