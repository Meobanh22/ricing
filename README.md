# 🌸 Sylveon & Serena Desktop Rice

Bộ công cụ custom desktop phong cách Sylveon & Serena (Pokemon) dành cho Windows 11.

---

## ⚡ Hướng Dẫn Sang Máy Mới (Chỉ 1 Click)

### 🪟 Trên Windows:
1. **Clone repository này về máy:**
   ```powershell
   git clone git@github.com:Meobanh22/sylveon-rice.git
   cd sylveon-rice
   ```
2. Chạy file cài đặt tự động:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup.ps1
   ```
3. **Xong!** Toàn bộ:
   - Phần mềm (AutoHotkey v2, Fastfetch) sẽ tự cài qua Winget.
   - Shortcut tự khởi động cùng Windows sẽ tự tạo trong `Startup`.
   - Cấu hình Fastfetch & ASCII Art độc quyền **Sylveon Chibi** sẽ tự sync vào `~/.config/fastfetch`.
   - Bộ đổi hình nền C++ & AHK sẽ tự kích hoạt.
   - Con trỏ chuột Sylveon Custom tự kích hoạt.

### 🐧 Trên Linux:
1. **Clone repository về máy:**
   ```bash
   git clone git@github.com:Meobanh22/sylveon-rice.git
   cd sylveon-rice
   ```
2. Chạy script setup:
   ```bash
   chmod +x ./setup_linux.sh
   ./setup_linux.sh
   ```
3. Script sẽ tự động:
   - Đồng bộ cấu hình Fastfetch và Sylveon Chibi ASCII logo vào `~/.config/fastfetch/`.
   - Symlink kho hình nền Sylveon vào `~/Pictures/wallpapers`.
   - Có thể dùng với `swww`, `hyprpaper`, `feh` hoặc daemon chuyển ảnh nền tuỳ Window Manager (Hyprland, i3, KDE, GNOME).

---

## 🎮 Phím Tắt Đổi Hình Nền (Hotkeys)

| Phím tắt | Tác dụng |
| :--- | :--- |
| `Ctrl + Alt + Space` | Đổi sang hình nền tiếp theo (Siêu dễ bấm) |
| `Ctrl + Alt + Right` | Đổi hình nền tiếp theo |
| `Ctrl + Alt + W` | Đổi hình nền tiếp theo |
| `Win + Alt + W` | Đổi hình nền tiếp theo |
| `F8` | Đổi hình nền tức thì |

---

## 🖱️ Bộ Con Trỏ Chuột (Cursors)

Thư mục `cursors/` cung cấp script `set_cursor.ps1` để chuyển đổi nhanh các bộ con trỏ chuột độc quyền (áp dụng tức thì không cần restart):

```powershell
# Bộ Sylveon Custom mới (Chibi ngồi + Nơ Link + Dải ruy băng Wait xoay vòng)
.\cursors\set_cursor.ps1 -Scheme sylveon-custom

# Các bộ khác:
.\cursors\set_cursor.ps1 -Scheme sylveon-paw       # Bàn chân mèo/Sylveon đệm hồng
.\cursors\set_cursor.ps1 -Scheme sylveon-chibi     # Sylveon Chibi tĩnh
.\cursors\set_cursor.ps1 -Scheme sylveon-animated  # Sylveon động (FaerEevee)
.\cursors\set_cursor.ps1 -Scheme pokemon           # Pokemon Trainer
.\cursors\set_cursor.ps1 -Scheme catppuccin        # Catppuccin Mocha Red
.\cursors\set_cursor.ps1 -Scheme default           # Mặc định của Windows
```

---

## 📁 Cấu Trúc Thư Mục

```text
C:\Users\DManh\Documents\Custom\
├── 📂 wallpapers/          # Thư mục chứa hình nền
├── 📂 fastfetch/           # Cấu hình Fastfetch & Sylveon Chibi ASCII logo
├── 📂 cursors/             # Bộ con trỏ chuột Catppuccin Mocha Red & script áp dụng
├── 📂 assets/              # Ảnh gốc, icon & sprite
├── 📂 scripts/             # Script Python sinh hình nền
├── 📂 profile/             # Ghi chú cá nhân & tài liệu mentor
├── ⚙️ wallpaper_switcher.exe  # Binary đổi hình nền (C++ siêu nhẹ)
├── ⚙️ wallpaper_hotkey.ahk   # Script AutoHotkey v2 bắt phím tắt
├── ⚙️ wallpaper_daemon.cpp   # Mã nguồn C++ Win32 API
├── 🚀 setup.ps1              # Script 1-click cài đặt toàn diện cho máy mới
├── 📖 README.md
└── 📄 .gitignore
```

