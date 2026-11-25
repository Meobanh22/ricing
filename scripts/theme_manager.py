#!/usr/bin/env python3
# theme_manager.py — Theme manager and system palette synchronizer.

import argparse
import colorsys
import json
import os
import shutil
import subprocess
import sys
import time

# Canonical presets aligned with config/theme/tokens.json primitive schema
PRESETS = {
    "serena-wine": {
        "name": "Serena Wine",
        "desc": "Anime Minimalist Obsidian Wine & Cherry Pink",
        "colors": {
            "dark_wine": "#201011",
            "deep_wine": "#2A1A1E",
            "soft_wine": "#301F20",
            "light_wine": "#3A222A",
            "plum_slate": "#241C20",
            "dark_ruby": "#4D0A1C",
            "wine_red": "#851733",
            "vivid_red": "#DC1A36",
            "light_red": "#F02D4C",
            "vivid_pink": "#FF5C8A",
            "soft_pink": "#E8C2D0",
            "muted_pink": "#A68595",
            "cream_white": "#FFF0F5",
            "pure_white": "#FFFFFF",
            "sky_blue": "#50A6FF",
            "light_cyan": "#87F0FF",
            "warm_yellow": "#FFB86C",
            "soft_green": "#8FBC8F",
        },
    }
}


def hex_to_rgb(h: str):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return f"#{max(0, min(255, int(round(r)))):02X}{max(0, min(255, int(round(g)))):02X}{max(0, min(255, int(round(b)))):02X}"


def lighten_hsl(hex_code: str, delta_l: float) -> str:
    r, g, b = (c / 255.0 for c in hex_to_rgb(hex_code))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l + delta_l))
    nr, ng, nb = (c * 255.0 for c in colorsys.hls_to_rgb(h, l, s))
    return rgb_to_hex(nr, ng, nb)


def color_badge(hex_code: str) -> str:
    r, g, b = hex_to_rgb(hex_code)
    return f"\033[48;2;{r};{g};{b}m   \033[0m {hex_code}"


def find_workspace_root():
    curr = os.path.dirname(os.path.abspath(__file__))
    while curr and curr != "/":
        if os.path.isdir(os.path.join(curr, "config")):
            return curr
        curr = os.path.dirname(curr)
    candidate = os.path.expanduser("~/custom")
    if os.path.isdir(os.path.join(candidate, "config")):
        return candidate
    return os.path.expanduser("~/.config")


def build_primitive_colors(overrides: dict, existing_colors: dict) -> dict:
    """Merge custom overrides into the canonical tokens.json primitive color schema."""
    base = dict(PRESETS["serena-wine"]["colors"])
    base.update({k: v for k, v in existing_colors.items() if k in base})

    bg_win = overrides.get("dark_wine")
    if bg_win:
        base["dark_wine"] = bg_win
        base["deep_wine"] = overrides.get("deep_wine") or lighten_hsl(bg_win, 0.038)
        base["soft_wine"] = overrides.get("soft_wine") or lighten_hsl(bg_win, 0.055)
        base["light_wine"] = overrides.get("light_wine") or lighten_hsl(bg_win, 0.085)

    accent = overrides.get("vivid_red")
    if accent:
        base["vivid_red"] = accent
        base["light_red"] = overrides.get("light_red") or lighten_hsl(accent, 0.09)

    ribbon = overrides.get("sky_blue")
    if ribbon:
        base["sky_blue"] = ribbon

    for k, v in overrides.items():
        if k in base and v:
            base[k] = v
    return base


def sync_generated_to_user_config(hypr_base: str, user_config: str):
    """Copy compiled theme outputs from repo config/ to ~/.config/."""
    pairs = [
        ("theme/tokens.json", "hypr/theme/tokens.json"),
        ("waybar/palette.css", "waybar/palette.css"),
        ("hypr/styles/palette.css", "hypr/styles/palette.css"),
        ("gtk-3.0/palette.css", "gtk-3.0/palette.css"),
        ("gtk-4.0/palette.css", "gtk-4.0/palette.css"),
        ("swaync/palette.css", "swaync/palette.css"),
        ("wlogout/palette.css", "wlogout/palette.css"),
        ("hypr/palette.conf", "hypr/palette.conf"),
        ("hypr/palette.lua", "hypr/palette.lua"),
        ("rofi/colors-rofi.rasi", "rofi/colors-rofi.rasi"),
        ("hypr/scripts/system/palette.py", "hypr/scripts/system/palette.py"),
        ("btop/themes/obsidian-wine.theme", "btop/themes/obsidian-wine.theme"),
        ("cava/config", "cava/config"),
        ("fastfetch/config.jsonc", "fastfetch/config.jsonc"),
        ("kitty/kitty.conf", "kitty/kitty.conf"),
    ]
    for src_rel, dst_rel in pairs:
        src = os.path.join(hypr_base, src_rel)
        dst = os.path.join(user_config, dst_rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def sync_vscode_terminal(root_dir: str, user_config: str, colors: dict):
    """Update VS Code integrated terminal palette when settings exist."""
    bg_win = colors["dark_wine"]
    bg_card_hover = colors["light_wine"]
    accent = colors["vivid_red"]
    accent_hover = colors["light_red"]
    txt_pri = colors["cream_white"]
    txt_sec = colors["soft_pink"]
    txt_mut = colors["muted_pink"]
    txt_inv = colors["pure_white"]
    ribbon = colors["sky_blue"]
    st_warn = colors["warm_yellow"]
    st_succ = colors["soft_green"]

    for vsc_path in [
        os.path.join(user_config, "Code", "User", "settings.json"),
        os.path.join(root_dir, ".vscode", "settings.json"),
    ]:
        if not os.path.exists(vsc_path):
            continue
        try:
            with open(vsc_path, "r", encoding="utf-8") as f:
                vsc_data = json.load(f)
        except Exception:
            continue
        vsc_colors = vsc_data.setdefault("workbench.colorCustomizations", {})
        vsc_colors.update(
            {
                "terminal.background": bg_win,
                "terminal.foreground": txt_pri,
                "terminal.selectionBackground": f"{accent}4D",
                "terminal.selectionForeground": txt_inv,
                "terminalCursor.foreground": accent,
                "terminalCursor.background": bg_win,
                "terminal.ansiBlack": bg_win,
                "terminal.ansiBrightBlack": bg_card_hover,
                "terminal.ansiRed": accent,
                "terminal.ansiBrightRed": accent_hover,
                "terminal.ansiGreen": st_succ,
                "terminal.ansiBrightGreen": st_succ,
                "terminal.ansiYellow": st_warn,
                "terminal.ansiBrightYellow": st_warn,
                "terminal.ansiBlue": ribbon,
                "terminal.ansiBrightBlue": ribbon,
                "terminal.ansiMagenta": txt_sec,
                "terminal.ansiBrightMagenta": txt_sec,
                "terminal.ansiCyan": ribbon,
                "terminal.ansiBrightCyan": txt_mut,
                "terminal.ansiWhite": txt_pri,
                "terminal.ansiBrightWhite": txt_inv,
            }
        )
        try:
            with open(vsc_path, "w", encoding="utf-8") as f:
                json.dump(vsc_data, f, indent=4, ensure_ascii=False)
                f.write("\n")
        except Exception:
            pass


def apply_theme_to_all_components(theme_name: str, colors: dict):
    root_dir = find_workspace_root()
    user_config = os.path.expanduser("~/.config")
    hypr_base = os.path.join(root_dir, "config") if os.path.isdir(os.path.join(root_dir, "config")) else user_config
    scripts_dir = os.path.join(root_dir, "scripts")

    print(f"\n\033[1;35m✿ SYNCHRONIZING SYSTEM THEME: {theme_name} ✿\033[0m")

    # 1. Update tokens.json while preserving gradient, typography, and geometry
    tokens_path = os.path.join(hypr_base, "theme", "tokens.json")
    token_data = {}
    if os.path.exists(tokens_path):
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
        except Exception:
            token_data = {}

    token_data["name"] = theme_name
    token_data["colors"] = colors

    os.makedirs(os.path.dirname(tokens_path), exist_ok=True)
    with open(tokens_path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("  ✔ [1/5] Updated config/theme/tokens.json")

    # 2. Delegate compilation to Single Source of Truth builders
    build_script = os.path.join(scripts_dir, "build_theme.py")
    if os.path.exists(build_script):
        subprocess.run([sys.executable, build_script], check=True)
    print("  ✔ [2/5] Compiled palette artifacts via build_theme.py")

    pokepuff_script = os.path.join(scripts_dir, "generate_pokepuffs.py")
    if os.path.exists(pokepuff_script):
        subprocess.run([sys.executable, pokepuff_script], check=False)
    print("  ✔ [3/5] Regenerated Waybar Poké Puff icons")

    # 3. Sync compiled artifacts to ~/.config and VS Code
    if hypr_base != user_config:
        sync_generated_to_user_config(hypr_base, user_config)
    sync_vscode_terminal(root_dir, user_config, colors)
    print("  ✔ [4/5] Synchronized compiled theme files to ~/.config")

    # 4. Reload Live Compositor & Apps
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or subprocess.run(
        ["pgrep", "-x", "Hyprland"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0:
        subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -SIGUSR2 waybar 2>/dev/null || true", shell=True)
        subprocess.run("pkill -USR1 kitty 2>/dev/null || true", shell=True)
        subprocess.run("fcitx5-remote -r 2>/dev/null || true", shell=True)
        subprocess.run("swaync-client -R -rs 2>/dev/null || true", shell=True)
        for proc in ["control_center.py", "settings.py", "shelf.py", "desktop_widgets.py"]:
            subprocess.run(f"pkill -f {proc} 2>/dev/null || true", shell=True)
        for pf in ["/tmp/control_center.pid", "/tmp/settings.pid", "/tmp/shelf.pid"]:
            try:
                os.remove(pf)
            except OSError:
                pass
        msg = f"Applied palette: {theme_name}\nAccent: {colors['vivid_red']} | Background: {colors['dark_wine']}"
        subprocess.run(
            ["notify-send", "-i", "preferences-desktop-theme", "✿ System Theme Synchronized ✿", msg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print("  ✔ [5/5] Live reload step complete")
    print(f"\033[1;32mSystem synchronized with theme: {theme_name}\033[0m\n")


def load_existing_colors() -> dict:
    root_dir = find_workspace_root()
    for p in [
        os.path.join(root_dir, "config", "theme", "tokens.json"),
        os.path.expanduser("~/.config/hypr/theme/tokens.json"),
    ]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f).get("colors", {})
            except Exception:
                pass
    return {}


def run_interactive_menu():
    print("\033[1;35m" + "=" * 65 + "\033[0m")
    print("\033[1;31m   ✿ SERENA SYSTEM COLOR & THEME CONTROLLER ✿   \033[0m")
    print("\033[1;35m" + "=" * 65 + "\033[0m\n")

    preset_keys = list(PRESETS.keys())
    for idx, key in enumerate(preset_keys, 1):
        item = PRESETS[key]
        c = item["colors"]
        badge_bg = color_badge(c["dark_wine"])
        badge_ac = color_badge(c["vivid_red"])
        badge_rb = color_badge(c["sky_blue"])
        print(f"  \033[1;36m{idx}.\033[0m \033[1m{item['name']}\033[0m — {item['desc']}")
        print(f"     Background: {badge_bg}  | Accent: {badge_ac}  | Ribbon: {badge_rb}\n")

    print("  \033[1;36m8.\033[0m \033[1m🎨 Custom Hex Color Input\033[0m")
    print("  \033[1;30m0. Exit\033[0m\n")

    try:
        choice = input("\033[1;33m👉 Enter choice (1-8, 0 to exit): \033[0m").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return

    if choice == "0" or not choice:
        print("Goodbye!")
        return

    if choice.isdigit() and 1 <= int(choice) <= len(preset_keys):
        item = PRESETS[preset_keys[int(choice) - 1]]
        apply_theme_to_all_components(item["name"], dict(item["colors"]))
    elif choice == "8":
        print("\n\033[1;34m--- ENTER CUSTOM HEX COLORS (e.g. #DC1A36 or DC1A36) ---\033[0m")
        try:
            bg_in = input("1. Window Background Hex (Default: #201011): ").strip() or "#201011"
            if not bg_in.startswith("#"):
                bg_in = "#" + bg_in
            accent_in = input("2. Accent Hex (Default: #DC1A36): ").strip() or "#DC1A36"
            if not accent_in.startswith("#"):
                accent_in = "#" + accent_in
            ribbon_in = input("3. Ribbon Hex (Default: #50A6FF): ").strip() or "#50A6FF"
            if not ribbon_in.startswith("#"):
                ribbon_in = "#" + ribbon_in
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return

        custom_colors = build_primitive_colors(
            {"dark_wine": bg_in, "vivid_red": accent_in, "sky_blue": ribbon_in},
            load_existing_colors(),
        )
        apply_theme_to_all_components(f"Custom ({accent_in})", custom_colors)
    else:
        print("Invalid choice.")


def run_rofi_menu():
    keys = list(PRESETS.keys())
    options = [f"{PRESETS[k]['name']} ({PRESETS[k]['colors']['vivid_red']})" for k in keys]
    options.append("🎨 Custom (Enter Hex Code)...")

    try:
        proc = subprocess.run(["rofi", "-dmenu", "-i", "-p", "✿ Select System Theme"], input="\n".join(options), text=True, stdout=subprocess.PIPE)
        chosen = proc.stdout.strip()
    except Exception as e:
        print(f"Error running Rofi: {e}")
        return

    if not chosen:
        return

    for idx, opt in enumerate(options[:-1]):
        if chosen == opt:
            p = PRESETS[keys[idx]]
            apply_theme_to_all_components(p["name"], dict(p["colors"]))
            return

    if "Custom" in chosen:
        proc_hex = subprocess.run(["rofi", "-dmenu", "-p", "Enter Accent Hex (e.g. #DC1A36)"], input="", text=True, stdout=subprocess.PIPE)
        custom_accent = proc_hex.stdout.strip()
        if custom_accent:
            if not custom_accent.startswith("#"):
                custom_accent = "#" + custom_accent
            custom_colors = build_primitive_colors({"vivid_red": custom_accent}, load_existing_colors())
            apply_theme_to_all_components(f"Custom ({custom_accent})", custom_colors)


def main():
    parser = argparse.ArgumentParser(description="Serena Rice Theme & Palette Manager")
    parser.add_argument("preset_pos", nargs="?", default=None, help="Theme preset name (serena-wine)")
    parser.add_argument("--preset", "-p", type=str, help="Theme preset name (serena-wine)")
    parser.add_argument("--accent", "-a", type=str, help="Custom accent hex color (e.g. '#F02D4C')")
    parser.add_argument("--bg", "-b", type=str, help="Custom background hex color (e.g. '#201011')")
    parser.add_argument("--ribbon", "-r", type=str, help="Custom ribbon hex color (e.g. '#50A6FF')")
    parser.add_argument("--rofi", action="store_true", help="Open theme selector menu with Rofi")
    parser.add_argument("--list", "-l", action="store_true", help="List all available presets")
    parser.add_argument("--current", "-c", action="store_true", help="Show current color palette")

    args = parser.parse_args()
    target_preset = args.preset or args.preset_pos

    if args.list:
        print("\033[1;35m✿ AVAILABLE THEME PRESETS ✿\033[0m")
        for k, v in PRESETS.items():
            print(f"  • \033[1;36m{k:<18}\033[0m : {v['name']} — {v['desc']}")
        return

    if args.current:
        root_dir = find_workspace_root()
        tokens_path = os.path.join(root_dir, "config", "theme", "tokens.json")
        if not os.path.exists(tokens_path):
            tokens_path = os.path.expanduser("~/.config/hypr/theme/tokens.json")
        if os.path.exists(tokens_path):
            with open(tokens_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            c = d.get("colors", {})
            bg = c.get("dark_wine", "#000000")
            ac = c.get("vivid_red", "#000000")
            rb = c.get("sky_blue", "#000000")
            print(f"Current theme: \033[1;32m{d.get('name', 'N/A')}\033[0m")
            print(f"  Background: {color_badge(bg)}")
            print(f"  Accent:     {color_badge(ac)}")
            print(f"  Ribbon:     {color_badge(rb)}")
        return

    if args.rofi:
        run_rofi_menu()
        return

    if target_preset:
        preset_key = target_preset.lower().strip()
        if preset_key in PRESETS:
            p = PRESETS[preset_key]
            apply_theme_to_all_components(p["name"], dict(p["colors"]))
        else:
            print(f"Preset '{preset_key}' not found. Available presets: {', '.join(PRESETS.keys())}")
        return

    if args.accent or args.bg or args.ribbon:
        overrides = {}
        if args.bg:
            overrides["dark_wine"] = args.bg if args.bg.startswith("#") else f"#{args.bg}"
        if args.accent:
            overrides["vivid_red"] = args.accent if args.accent.startswith("#") else f"#{args.accent}"
        if args.ribbon:
            overrides["sky_blue"] = args.ribbon if args.ribbon.startswith("#") else f"#{args.ribbon}"
        custom_colors = build_primitive_colors(overrides, load_existing_colors())
        label = overrides.get("vivid_red") or overrides.get("dark_wine") or overrides.get("sky_blue") or "Custom"
        apply_theme_to_all_components(f"Custom ({label})", custom_colors)
        return

    run_interactive_menu()


if __name__ == "__main__":
    main()
