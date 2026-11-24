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

## Synchronization (`./sync.sh`)

### Two-way Dotfiles Synchronization
```bash
./sync.sh           # Push repository configs -> ~/.config & Hot-Reload live
./sync.sh --pull    # Pull changes from ~/.config -> repository
./sync.sh --diff    # Compare differences between repository and ~/.config
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
| `Super + P` | Toggle Settings & Device Status Popup |
| `Super + M` | Toggle Music Visualizer |
| `Super + V` | Toggle Serena Shelf (Clipboard History) |
| `Super + D` | Toggle Serena Shelf (File Pinning Shelf) |
| `Super + W` | Switch to Next Wallpaper |
| `Ctrl + Shift + Space` | Toggle Vietnamese Input Method (Ngó Sen / Fcitx5) |
| `Super + L` | Lock Screen (Hyprlock Serena) |
| `Super + Escape` | Open Power Menu (Wlogout) |
| `Ctrl + Shift + Esc` | Open System Monitor (btop) |
| `Print` / `Super + Shift + S` | Capture Screenshot (Grim + Slurp) |
| `Super + Shift + R` / `Super + Alt + R` | Record Screen (Area / Full) |

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
│   ├── cava/               # Terminal audio visualizer
│   ├── fastfetch/          # System info & ASCII art
│   ├── firefox/            # Firefox userChrome, userContent & user.js
│   ├── starship/           # Starship prompt configuration
│   ├── applications/       # Desktop entriesa
│   ├── gtk-3.0/ & gtk-4.0/ # GTK themes importing palette.css
│   ├── fcitx5/             # Input method configuration
│   └── Thunar/             # Custom file manager actions
├── assets/                 # Production ready assets
│   ├── wallpapers/         # Curated HD wallpapers
│   ├── avatars/            # Serena profile & Sylveon avatars
│   ├── icons/              # Vector & PNG icons
│   ├── illustrations/      # Minimalist illustrations
│   ├── pokemon/            # Pokémon sprites
│   ├── banners/            # Cover banners
│   └── cursors/            # Sylveon Custom dual cursor theme
├── scripts/                # Administration tools (build_theme.py, theme_manager.py, generate_pokepuffs.py, sync.sh)
├── sync.sh                 # Root symlink to scripts/sync.sh
├── install/                # Automated installer scripts (setup_endeavouros.sh, setup_ubuntu.sh)
├── dev_tools/              # Asset generators & cursor builders
├── archive/                # Safely archived legacy configs & drafts
├── AGENTS.md               # UI/UX design tokens and component specification
└── README.md               # Project documentation
```
