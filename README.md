# Serena Dotfiles — Anime Minimalist Hyprland Rice

Anime minimalist dotfiles configuration system inspired by Serena, running on **EndeavourOS / Arch Linux** (and Ubuntu 24.04) powered by the **Hyprland Native Lua Engine (v0.56+/v0.57+)**.

---

## Installation Guide (One-Click)

### Recommended: EndeavourOS / Arch Linux
1. **Clone repository:**
   ```bash
   git clone https://github.com/Meobanh22/ricing.git ~/custom
   cd ~/custom
   ```

2. **Run the automated setup installer:**
   ```bash
   chmod +x ./install/setup_endeavouros.sh
   ./install/setup_endeavouros.sh
   ```
   *Installs all required dependencies via Pacman & Yay, deploys dotfiles directly to `~/.config/`, installs the Sylveon Custom dual cursor theme, downloads wallpapers, and activates the default color palette.*

---

## Synchronization & Theme Manager

### 1. Two-way Dotfiles Synchronization (`./sync.sh`)
```bash
./sync.sh           # Push repository configs -> ~/.config & Hot-Reload live
./sync.sh --pull    # Pull changes from ~/.config -> repository
./sync.sh --diff    # Compare differences between repository and ~/.config
```

### 2. System-wide Theme Switching (`./change_theme.sh`)
Synchronizes and live reloads all 10 component targets (Waybar, Hyprland Lua, GTK 3/4, Popups, Kitty, VS Code, btop, Rofi, Wlogout, SwayNC):
```bash
./change_theme.sh --list                    # List available theme presets
./change_theme.sh midnight-amethyst         # Switch to Midnight Amethyst
./change_theme.sh matcha-sage               # Switch to Matcha Sage
./change_theme.sh crimson-velvet            # Switch to Crimson Velvet
./change_theme.sh sakura-pastel             # Switch to Sakura Pastel
./change_theme.sh serena-wine               # Switch to default Serena Wine
./change_theme.sh --rofi                    # Open interactive Rofi palette selector
```

---

## System Keybindings

| Keybinding | Action |
| :--- | :--- |
| `Super + Return` | Launch Kitty Terminal |
| `Super + B` | Launch Browser (Firefox) |
| `Super + Space` | Open Application Launcher (Rofi) |
| `Super + E` | Open File Manager (Thunar) |
| `Super + C` | Launch Visual Studio Code |
| `Super + N` | Toggle Control Center (Quick Settings & Alerts) |
| `Super + S` | Toggle Dashboard (Clock, Serena Profile, Calendar, Weather) |
| `Super + M` | Toggle Music Visualizer |
| `Super + V` | Toggle Serena Shelf (Clipboard History) |
| `Super + D` | Toggle Serena Shelf (File Pinning Shelf) |
| `Super + W` | Switch to Next Wallpaper |
| `Super + Shift + Space` | Toggle Vietnamese Input Method (Fcitx5) |
| `Super + L` | Lock Screen (Hyprlock Serena) |
| `Super + Escape` | Open Power Menu (Wlogout) |
| `Ctrl + Shift + Esc` | Open System Monitor (btop) |
| `Print` / `Super + Shift + S` | Capture Screenshot (Grim + Slurp) |

---

## Standardized Directory Structure

```text
custom/ (Repository Root)
├── config/                 # Clean 1:1 mapping to ~/.config/
│   ├── hypr/               # Hyprland Lua Engine (hyprland.lua, hyprlock, popups)
│   ├── waybar/             # Main status bar (config.jsonc, style.css, palette.css)
│   ├── rofi/               # Application launcher & theme switcher
│   ├── kitty/              # Terminal emulator configuration
│   ├── swaync/             # Notification center
│   ├── wlogout/            # Power / session menu
│   ├── btop/               # Hardware monitor
│   ├── fastfetch/          # System info & ASCII art
│   ├── gtk-3.0/ & gtk-4.0/ # GTK themes importing palette.css
│   ├── fcitx5/             # Input method configuration
│   └── Thunar/             # Custom file manager actions
├── assets/                 # Production ready assets
│   ├── wallpapers/         # Curated HD wallpapers
│   ├── avatars/            # Serena profile & Sylveon avatars
│   └── cursors/            # Sylveon Custom dual cursor theme
├── scripts/                # Administration tools (theme_manager.py, sync.sh, change_theme.sh)
├── install/                # Automated installer scripts (setup_endeavouros.sh, setup_ubuntu.sh)
├── dev_tools/              # Asset generators & cursor builders
├── archive/                # Safely archived legacy configs & drafts
├── AGENTS.md               # UI/UX design tokens and component specification
└── README.md               # Project documentation
```
