#!/usr/bin/env python3
# theme_manager.py — Theme manager and system palette synchronizer.

import os
import sys
import time
import json
import argparse
import colorsys
import subprocess

# Curated Presets
PRESETS = {
    "serena-wine": {
        "name": "Serena Wine",
        "desc": "Anime Minimalist Obsidian Wine & Cherry Pink",
        "colors": {
            "bg_window": "#201011",
            "bg_card": "#2A1A1E",
            "bg_card_hover": "#3A222A",
            "bg_subtle": "#301F20",
            "border_window": "rgba(255, 255, 255, 0.12)",
            "border_card": "rgba(255, 255, 255, 0.12)",
            "border_card_hover": "rgba(255, 42, 85, 0.65)",
            "accent": "#FF2A55",
            "accent_hover": "#FF597B",
            "ribbon_blue": "#50A6FF",
            "text_primary": "#FFF0F5",
            "text_secondary": "#E8C2D0",
            "text_muted": "#A68595",
            "text_inverse": "#FFFFFF",
            "status_warning": "#FFB86C",
            "status_critical": "#FF2A55",
            "status_success": "#8FBC8F",
        }
    },
    "sakura-pastel": {
        "name": "Sakura Pastel",
        "desc": "Soft Anime Sakura Pink & Sweet Rose",
        "colors": {
            "bg_window": "#241419",
            "accent": "#FF6088",
            "ribbon_blue": "#60A5FA",
            "text_primary": "#FFF5F7",
            "text_secondary": "#F7CAD7",
            "text_muted": "#C49AA8",
            "status_warning": "#FBBF24",
            "status_critical": "#F43F5E",
            "status_success": "#34D399",
        }
    },
    "kalos-cyber": {
        "name": "Kalos Cyber",
        "desc": "Pokédex High-Tech Neon Red & Cyan Glow",
        "colors": {
            "bg_window": "#140C12",
            "accent": "#FF1744",
            "ribbon_blue": "#00E5FF",
            "text_primary": "#F0FDF4",
            "text_secondary": "#BDEDF3",
            "text_muted": "#78909C",
            "status_warning": "#FFA000",
            "status_critical": "#FF1744",
            "status_success": "#00E676",
        }
    },
    "midnight-amethyst": {
        "name": "Midnight Amethyst",
        "desc": "Deep Twilight Violet & Lavender Ribbon",
        "colors": {
            "bg_window": "#16111D",
            "accent": "#E040FB",
            "ribbon_blue": "#7C4DFF",
            "text_primary": "#FBF7FF",
            "text_secondary": "#E2D4F0",
            "text_muted": "#9E8EB3",
            "status_warning": "#F59E0B",
            "status_critical": "#EC4899",
            "status_success": "#10B981",
        }
    },
    "matcha-sage": {
        "name": "Matcha Sage",
        "desc": "Subdued Japanese Dark Tea & Fresh Sage",
        "colors": {
            "bg_window": "#121814",
            "accent": "#4ADE80",
            "ribbon_blue": "#38BDF8",
            "text_primary": "#F2FBF5",
            "text_secondary": "#C7E8D3",
            "text_muted": "#8BA896",
            "status_warning": "#FBBF24",
            "status_critical": "#F43F5E",
            "status_success": "#4ADE80",
        }
    },
    "crimson-velvet": {
        "name": "Crimson Velvet",
        "desc": "Royal Velvet Ruby & Amber Gold",
        "colors": {
            "bg_window": "#1C0D11",
            "accent": "#FF3366",
            "ribbon_blue": "#F59E0B",
            "text_primary": "#FFF1F3",
            "text_secondary": "#F5CAD2",
            "text_muted": "#B38690",
            "status_warning": "#FCD34D",
            "status_critical": "#FF3366",
            "status_success": "#34D399",
        }
    },
    "ocean-breeze": {
        "name": "Ocean Breeze",
        "desc": "Deep Indigo Ocean & Cyan Breeze",
        "colors": {
            "bg_window": "#0E1520",
            "accent": "#06B6D4",
            "ribbon_blue": "#F472B6",
            "text_primary": "#F0F9FF",
            "text_secondary": "#BAE6FD",
            "text_muted": "#7899AC",
            "status_warning": "#FBBF24",
            "status_critical": "#EF4444",
            "status_success": "#10B981",
        }
    }
}


def hex_to_rgb(h: str):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


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


def build_full_color_palette(base_colors: dict) -> dict:
    bg_win = base_colors["bg_window"]
    accent = base_colors["accent"]
    ribbon = base_colors.get("ribbon_blue", "#50A6FF")
    st_warn = base_colors.get("status_warning", "#FFB86C")
    st_crit = base_colors.get("status_critical", accent)
    st_succ = base_colors.get("status_success", "#8FBC8F")

    txt_pri = base_colors.get("text_primary", "#FFF0F5")
    txt_sec = base_colors.get("text_secondary", "#E8C2D0")
    txt_mut = base_colors.get("text_muted", "#A68595")
    txt_inv = base_colors.get("text_inverse", "#FFFFFF")

    # Automatically compute or use explicit derived color steps
    bg_card = base_colors.get("bg_card") or lighten_hsl(bg_win, 0.038)
    bg_card_hover = base_colors.get("bg_card_hover") or lighten_hsl(bg_win, 0.085)
    bg_subtle = base_colors.get("bg_subtle") or lighten_hsl(bg_win, 0.055)
    accent_hover = base_colors.get("accent_hover") or lighten_hsl(accent, 0.09)

    r_w, g_w, b_w = hex_to_rgb(bg_win)
    r_c, g_c, b_c = hex_to_rgb(bg_card)
    r_ch, g_ch, b_ch = hex_to_rgb(bg_card_hover)
    r_s, g_s, b_s = hex_to_rgb(bg_subtle)
    r_a, g_a, b_a = hex_to_rgb(accent)
    r_ah, g_ah, b_ah = hex_to_rgb(accent_hover)
    r_rb, g_rb, b_rb = hex_to_rgb(ribbon)
    r_sw, g_sw, b_sw = hex_to_rgb(st_warn)
    r_sc, g_sc, b_sc = hex_to_rgb(st_crit)
    r_ss, g_ss, b_ss = hex_to_rgb(st_succ)

    border_card_hover = base_colors.get("border_card_hover") or f"rgba({r_a}, {g_a}, {b_a}, 0.65)"

    return {
        "bg_window": bg_win,
        "bg_window_alpha": f"rgba({r_w}, {g_w}, {b_w}, 0.98)",
        "bg_window_hypr": f"rgba({bg_win.lstrip('#')}fa)",

        "bg_card": bg_card,
        "bg_card_alpha": f"rgba({r_c}, {g_c}, {b_c}, 0.95)",
        "bg_card_hypr": f"rgba({bg_card.lstrip('#')}f2)",

        "bg_card_hover": bg_card_hover,
        "bg_card_hover_alpha": f"rgba({r_ch}, {g_ch}, {b_ch}, 0.98)",
        "bg_card_hover_hypr": f"rgba({bg_card_hover.lstrip('#')}fa)",

        "bg_subtle": bg_subtle,
        "bg_subtle_alpha": f"rgba({r_s}, {g_s}, {b_s}, 0.95)",
        "bg_subtle_hypr": f"rgba({bg_subtle.lstrip('#')}f2)",

        "bg_ghost": "transparent",
        "bg_ghost_hover": f"rgba({r_c}, {g_c}, {b_c}, 0.50)",

        # Surface derived alphas
        "bg_card_soft": f"rgba({r_c}, {g_c}, {b_c}, 0.40)",
        "bg_card_subtle": f"rgba({r_c}, {g_c}, {b_c}, 0.70)",
        "bg_action": f"rgba({r_s}, {g_s}, {b_s}, 0.90)",
        "bg_action_hover": f"rgba({r_ch}, {g_ch}, {b_ch}, 0.98)",

        "border_window": "rgba(255, 255, 255, 0.12)",
        "border_window_hypr": "rgba(ffffff1f)",

        "border_card": "rgba(255, 255, 255, 0.12)",
        "border_card_hypr": "rgba(ffffff1f)",

        "border_card_hover": border_card_hover,
        "border_card_hover_hypr": f"rgba({accent.lstrip('#')}a6)",

        "accent": accent,
        "accent_hypr": f"rgb({accent.lstrip('#')})",

        "accent_hover": accent_hover,
        "accent_hover_hypr": f"rgb({accent_hover.lstrip('#')})",

        # Accent derived alphas for borders, sliders, badges, hover
        "accent_dim": f"rgba({r_a}, {g_a}, {b_a}, 0.48)",
        "accent_subtle": f"rgba({r_a}, {g_a}, {b_a}, 0.20)",
        "accent_soft": f"rgba({r_a}, {g_a}, {b_a}, 0.12)",
        "accent_border": f"rgba({r_a}, {g_a}, {b_a}, 0.40)",
        "accent_dash": f"rgba({r_a}, {g_a}, {b_a}, 0.45)",

        "text_primary": txt_pri,
        "text_primary_hypr": f"rgb({txt_pri.lstrip('#')})",

        "text_secondary": txt_sec,
        "text_secondary_hypr": f"rgb({txt_sec.lstrip('#')})",

        "text_muted": txt_mut,
        "text_muted_hypr": f"rgb({txt_mut.lstrip('#')})",

        "text_inverse": txt_inv,
        "text_inverse_hypr": f"rgb({txt_inv.lstrip('#')})",

        "status_warning": st_warn,
        "status_warning_hypr": f"rgb({st_warn.lstrip('#')})",

        "status_critical": st_crit,
        "status_critical_hypr": f"rgb({st_crit.lstrip('#')})",

        "status_success": st_succ,
        "status_success_hypr": f"rgb({st_succ.lstrip('#')})",

        "ribbon_blue": ribbon,
        "ribbon_blue_alpha": f"rgba({r_rb}, {g_rb}, {b_rb}, 0.95)",
        "ribbon_blue_hypr": f"rgb({ribbon.lstrip('#')})"
    }


def find_workspace_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)
    if os.path.isdir(os.path.join(parent, "config")):
        return parent
    if os.path.isdir(os.path.join(script_dir, "config")):
        return script_dir
    candidate = os.path.expanduser("~/custom")
    if os.path.isdir(os.path.join(candidate, "config")):
        return candidate
    return os.path.expanduser("~/.config")


def sync_waybar_config(hypr_base: str, user_config: str, colors: dict):
    accent = colors['accent']
    txt_pri = colors['text_primary']
    txt_sec = colors['text_secondary']
    txt_mut = colors['text_muted']

    waybar_cfg_content = f"""{{
  "layer": "top",
  "position": "top",
  "margin-top": 8,
  "margin-left": 14,
  "margin-right": 14,
  "spacing": 8,

  "modules-left": [
    "custom/menu",
    "hyprland/workspaces",
    "custom/media"
  ],

  "modules-center": [
    "clock"
  ],

  "modules-right": [
    "custom/ime",
    "pulseaudio",
    "network",
    "battery",
    "custom/notification",
    "custom/power"
  ],

  "custom/menu": {{
    "format": "<span color='{accent}'>✿</span> <span color='{txt_pri}'><b>Apps</b></span>",
    "tooltip": "Application Menu (Super + Space)",
    "on-click": "~/.config/hypr/scripts/OpenApps.sh"
  }},

  "hyprland/workspaces": {{
    "disable-scroll": true,
    "all-outputs": true,
    "active-only": false,
    "format": "{{name}}",
    "persistent-workspaces": {{
      "*": 5
    }}
  }},

  "custom/media": {{
    "format": "{{}}",
    "return-type": "json",
    "exec": "python3 ~/.config/hypr/scripts/get_media.py",
    "interval": 1,
    "on-click": "bash ~/.config/hypr/scripts/toggle_music.sh",
    "on-click-right": "playerctl play-pause",
    "on-click-middle": "playerctl next",
    "escape": true
  }},

  "clock": {{
    "format": "<span color='{accent}'></span> <span color='{txt_pri}'><b>{{0:%H:%M}}</b></span>  <span color='{accent}'>·</span>  <span color='{txt_sec}'>{{0:%d/%m}}</span>",
    "format-alt": "<span color='{accent}'></span> <span color='{txt_pri}'><b>{{0:%H:%M:%S}}</b></span>  <span color='{accent}'>·</span>  <span color='{txt_sec}'>{{0:%A, %d/%m/%Y}}</span>",
    "interval": 1,
    "tooltip-format": "<tt><small>{{calendar}}</small></tt>",
    "tooltip": "Calendar & Dashboard (Super + S)",
    "on-click": "~/.config/hypr/scripts/toggle_dashboard.sh"
  }},

  "custom/ime": {{
    "exec": "~/.config/hypr/scripts/get_ime.sh",
    "interval": 1,
    "format": "{{}}",
    "tooltip": "Input Method VIE / ENG (Ctrl + Shift or Super + Shift + Space)",
    "on-click": "~/.config/hypr/scripts/toggle_vietnamese.sh"
  }},

  "pulseaudio": {{
    "format": "<span font='14.5px' color='{accent}'>{{icon}}</span> {{volume}}%",
    "format-muted": "<span font='14.5px' color='{txt_mut}'>󰖁</span> Muted",
    "format-icons": {{
      "headphone": "󰋋",
      "hands-free": "󰋋",
      "headset": "󰋋",
      "default": ["󰕿", "󰖀", "󰕾"]
    }},
    "max-volume": 100,
    "scroll-step": 5,
    "tooltip-format": "Volume: {{volume}}%\\n(Click: Pavucontrol | Right-click: Control Center)",
    "on-click": "pavucontrol",
    "on-click-right": "~/.config/hypr/scripts/toggle_control_center.sh"
  }},

  "network": {{
    "format-wifi": "<span color='{accent}'>󰖩</span> {{essid}}",
    "format-ethernet": "<span color='{accent}'>󰈀</span> Wired",
    "format-disconnected": "<span color='{txt_mut}'>󰖪</span> Offline",
    "tooltip-format": "Wi-Fi: {{essid}} ({{signalStrength}}%)\\n(Click: Network Settings | Right-click: Control Center)",
    "on-click": "nm-connection-editor",
    "on-click-right": "~/.config/hypr/scripts/toggle_control_center.sh"
  }},

  "battery": {{
    "states": {{
      "good": 95,
      "warning": 30,
      "critical": 15
    }},
    "format": "<span color='{accent}'>{{icon}}</span> {{capacity}}%",
    "format-charging": "<span color='{accent}'>󰂄</span> {{capacity}}%",
    "format-plugged": "<span color='{accent}'>󰚥</span> {{capacity}}%",
    "format-alt": "<span color='{accent}'>{{icon}}</span> {{time}}",
    "format-icons": ["󰂎", "󰁺", "󰁻", "󰁼", "󰁽", "󰁾", "󰁿", "󰂀", "󰂁", "󰂂", "󰁹"],
    "tooltip-format": "Battery: {{capacity}}% ({{time}})\\n(Right-click: Control Center)",
    "on-click-right": "~/.config/hypr/scripts/toggle_control_center.sh"
  }},

  "custom/notification": {{
    "format": "<span color='{accent}'>󰂚</span>",
    "tooltip": "Control Center & Notifications (Super + N)",
    "on-click": "~/.config/hypr/scripts/toggle_control_center.sh",
    "on-click-right": "~/.config/hypr/scripts/toggle_control_center.sh"
  }},

  "custom/power": {{
    "format": "󰐥",
    "tooltip": "Power Menu (Click to open)",
    "on-click": "~/.config/hypr/scripts/Wlogout.sh"
  }}
}}
"""
    for p in [os.path.join(hypr_base, "waybar", "config.jsonc"), os.path.join(user_config, "waybar", "config.jsonc")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(waybar_cfg_content)


def apply_theme_to_all_components(theme_name: str, colors: dict):
    root_dir = find_workspace_root()
    user_config = os.path.expanduser("~/.config")
    hypr_base = os.path.join(root_dir, "config") if os.path.isdir(os.path.join(root_dir, "config")) else user_config

    print(f"\n\033[1;35m✿ SYNCHRONIZING SYSTEM THEME: {theme_name} ✿\033[0m")

    # 1. Update tokens.json
    tokens_path = os.path.join(hypr_base, "theme", "tokens.json")
    if os.path.exists(tokens_path):
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
        except Exception:
            token_data = {}
    else:
        token_data = {}

    token_data["name"] = theme_name
    token_data["colors"] = colors

    os.makedirs(os.path.dirname(tokens_path), exist_ok=True)
    with open(tokens_path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)
    print("  ✔ [1/10] Update tokens.json")

    # Synchronize to ~/.config/hypr/theme/
    cfg_theme_dir = os.path.join(user_config, "hypr", "theme")
    os.makedirs(cfg_theme_dir, exist_ok=True)
    with open(os.path.join(cfg_theme_dir, "tokens.json"), "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

    # 2. Waybar palette.css & Waybar config.jsonc
    css_content = f"""/* palette.css — Color tokens. */
/* NOTE: Generated automatically by theme_manager.py. Do not edit directly. */

@define-color bg_window {colors['bg_window_alpha']};
@define-color bg_card {colors['bg_card_alpha']};
@define-color bg_card_hover {colors['bg_card_hover_alpha']};
@define-color bg_subtle {colors['bg_subtle_alpha']};
@define-color bg_ghost {colors['bg_ghost']};
@define-color bg_ghost_hover {colors['bg_ghost_hover']};

@define-color bg_card_soft {colors['bg_card_soft']};
@define-color bg_card_subtle {colors['bg_card_subtle']};
@define-color bg_action {colors['bg_action']};
@define-color bg_action_hover {colors['bg_action_hover']};

@define-color border_window {colors['border_window']};
@define-color border_card {colors['border_card']};
@define-color border_card_hover {colors['border_card_hover']};

@define-color accent {colors['accent']};
@define-color accent_hover {colors['accent_hover']};
@define-color accent_dim {colors['accent_dim']};
@define-color accent_subtle {colors['accent_subtle']};
@define-color accent_soft {colors['accent_soft']};
@define-color accent_border {colors['accent_border']};
@define-color accent_dash {colors['accent_dash']};

@define-color scrollbar_slider {colors['accent_dim']};
@define-color scrollbar_slider_hover {colors['accent']};

@define-color text_primary {colors['text_primary']};
@define-color text_secondary {colors['text_secondary']};
@define-color text_muted {colors['text_muted']};
@define-color text_inverse {colors['text_inverse']};
@define-color text_white {colors['text_inverse']};

@define-color status_warning {colors['status_warning']};
@define-color status_critical {colors['status_critical']};
@define-color status_success {colors['status_success']};

@define-color ribbon_blue {colors['ribbon_blue']};
"""
    # Write to Waybar
    for p in [os.path.join(hypr_base, "waybar", "palette.css"), os.path.join(user_config, "waybar", "palette.css")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(css_content)
    sync_waybar_config(hypr_base, user_config, colors)
    print("  ✔ [2/10] Synchronize Waybar palette.css & config.jsonc")

    # 3. Write to Hypr GTK Styles & System GTK 3 / 4
    for p in [
        os.path.join(hypr_base, "hypr", "styles", "palette.css"),
        os.path.join(user_config, "hypr", "styles", "palette.css"),
        os.path.join(hypr_base, "gtk-3.0", "palette.css"),
        os.path.join(user_config, "gtk-3.0", "palette.css"),
        os.path.join(hypr_base, "gtk-4.0", "palette.css"),
        os.path.join(user_config, "gtk-4.0", "palette.css")
    ]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(css_content)
    print("  ✔ [3/10] Synchronize GTK Apps palette.css (Control Center, Dashboard, Shelf, Visualizer, GTK-3/4)")

    # 4. Write to Wlogout & Swaync
    for p in [os.path.join(hypr_base, "wlogout", "palette.css"), os.path.join(user_config, "wlogout", "palette.css")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(css_content)
    for p in [os.path.join(hypr_base, "swaync", "palette.css"), os.path.join(user_config, "swaync", "palette.css")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(css_content)
    print("  ✔ [4/10] Synchronize Wlogout & Swaync palette.css")

    # 5. Hyprland palette.lua & palette.conf
    hypr_lua_content = f"""-- palette.lua — Color tokens for Hyprland (Lua engine).
-- NOTE: Generated automatically by theme_manager.py. Do not edit directly.

return {{
    bg_window            = "{colors['bg_window_hypr']}",
    bg_card              = "{colors['bg_card_hypr']}",
    bg_card_hover        = "{colors['bg_card_hover_hypr']}",
    bg_subtle            = "{colors['bg_subtle_hypr']}",
    border_window        = "{colors['border_window_hypr']}",
    border_card          = "{colors['border_card_hypr']}",
    border_card_hover    = "{colors['border_card_hover_hypr']}",
    accent               = "{colors['accent_hypr']}",
    accent_hover         = "{colors['accent_hover_hypr']}",
    text_primary         = "{colors['text_primary_hypr']}",
    text_secondary       = "{colors['text_secondary_hypr']}",
    text_muted           = "{colors['text_muted_hypr']}",
    text_inverse         = "{colors['text_inverse_hypr']}",
    status_warning       = "{colors['status_warning_hypr']}",
    status_critical      = "{colors['status_critical_hypr']}",
    status_success       = "{colors['status_success_hypr']}",
    ribbon_blue          = "{colors['ribbon_blue_hypr']}",
}}
"""
    for p in [os.path.join(hypr_base, "hypr", "palette.lua"), os.path.join(user_config, "hypr", "palette.lua")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(hypr_lua_content)

    hypr_conf_content = f"""# palette.conf — Color tokens for Hyprland.
# NOTE: Generated automatically by theme_manager.py. Do not edit directly.

$bg_window            = {colors['bg_window_hypr']}
$bg_card              = {colors['bg_card_hypr']}
$bg_card_hover        = {colors['bg_card_hover_hypr']}
$bg_subtle            = {colors['bg_subtle_hypr']}
$border_window        = {colors['border_window_hypr']}
$border_card          = {colors['border_card_hypr']}
$border_card_hover    = {colors['border_card_hover_hypr']}
$accent               = {colors['accent_hypr']}
$accent_hover         = {colors['accent_hover_hypr']}
$text_primary         = {colors['text_primary_hypr']}
$text_secondary       = {colors['text_secondary_hypr']}
$text_muted           = {colors['text_muted_hypr']}
$text_inverse         = {colors['text_inverse_hypr']}
$status_warning       = {colors['status_warning_hypr']}
$status_critical      = {colors['status_critical_hypr']}
$status_success       = {colors['status_success_hypr']}
$ribbon_blue          = {colors['ribbon_blue_hypr']}
"""
    for p in [os.path.join(hypr_base, "hypr", "palette.conf"), os.path.join(user_config, "hypr", "palette.conf")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(hypr_conf_content)
    print("  ✔ [5/10] Synchronize Hyprland palette.lua & palette.conf")

    # 6. Generate Rofi colors-rofi.rasi
    rofi_content = f"""/* colors-rofi.rasi — Color tokens for Rofi. */
/* NOTE: Generated automatically by theme_manager.py. Do not edit directly. */

* {{
    bg-window:          {colors['bg_window_alpha']};
    bg-card:            {colors['bg_card_alpha']};
    bg-card-hover:      {colors['bg_card_hover_alpha']};
    bg-subtle:          {colors['bg_subtle_alpha']};
    bg-ghost:           {colors['bg_ghost']};
    bg-ghost-hover:     {colors['bg_ghost_hover']};

    border-window:      {colors['border_window']};
    border-card:        {colors['border_card']};
    border-card-hover:  {colors['border_card_hover']};

    accent:             {colors['accent']};
    accent-hover:       {colors['accent_hover']};
    text-primary:       {colors['text_primary']};
    text-secondary:     {colors['text_secondary']};
    text-muted:         {colors['text_muted']};
    text-inverse:       {colors['text_inverse']};
    text-white:         {colors['text_inverse']};

    status-warning:     {colors['status_warning']};
    status-critical:    {colors['status_critical']};
    status-success:     {colors['status_success']};

    ribbon-blue:        {colors['ribbon_blue']};
}}
"""
    for p in [os.path.join(hypr_base, "rofi", "colors-rofi.rasi"), os.path.join(user_config, "rofi", "colors-rofi.rasi")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(rofi_content)
    print("  ✔ [6/10] Synchronize Rofi colors-rofi.rasi")

    # 7. Generate Python palette.py
    py_content = f"""#!/usr/bin/env python3
# palette.py — Python design tokens.
# NOTE: Generated automatically by theme_manager.py. Do not edit directly.

PALETTE = {json.dumps(colors, indent=4, ensure_ascii=False)}

def hex_to_rgba(hex_code: str, alpha: float = 1.0):
    h = hex_code.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

# Color hex constants
C_BG_WIN        = PALETTE.get("bg_window", "#201011")
C_BG_CARD       = PALETTE.get("bg_card", "#2A1A1E")
C_BG_CARD_HOVER = PALETTE.get("bg_card_hover", "#3A222A")
C_BG_SUBTLE     = PALETTE.get("bg_subtle", "#301F20")
C_ACCENT        = PALETTE.get("accent", "#FF2A55")
C_ACCENT_HOVER  = PALETTE.get("accent_hover", "#FF597B")
C_TEXT_PRI      = PALETTE.get("text_primary", "#FFF0F5")
C_TEXT_SEC      = PALETTE.get("text_secondary", "#E8C2D0")
C_TEXT_MUT      = PALETTE.get("text_muted", "#A68595")
C_TEXT_INV      = PALETTE.get("text_inverse", "#FFFFFF")
C_STATUS_WARN   = PALETTE.get("status_warning", "#FFB86C")
C_STATUS_CRIT   = PALETTE.get("status_critical", "#FF2A55")
C_STATUS_SUCC   = PALETTE.get("status_success", "#8FBC8F")
C_RIBBON        = PALETTE.get("ribbon_blue", "#50A6FF")

# Pre-computed Cairo RGBA tuples
BG_WINDOW_RGBA     = hex_to_rgba(C_BG_WIN, 0.98)
BG_CARD_RGBA       = hex_to_rgba(C_BG_CARD, 0.95)
BG_CARD_HOVER_RGBA = hex_to_rgba(C_BG_CARD_HOVER, 0.98)
BG_SUBTLE_RGBA     = hex_to_rgba(C_BG_SUBTLE, 0.95)
ACCENT_RGBA        = hex_to_rgba(C_ACCENT, 1.0)
ACCENT_HOVER_RGBA  = hex_to_rgba(C_ACCENT_HOVER, 1.0)
ACCENT_DIM_RGBA    = hex_to_rgba(C_ACCENT, 0.48)
ACCENT_SUBTLE_RGBA = hex_to_rgba(C_ACCENT, 0.20)
BORDER_WINDOW_RGBA = (1.0, 1.0, 1.0, 0.12)
BORDER_CARD_RGBA   = (1.0, 1.0, 1.0, 0.12)
"""
    for p in [os.path.join(hypr_base, "hypr", "scripts", "palette.py"), os.path.join(user_config, "hypr", "scripts", "palette.py")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(py_content)
    print("  ✔ [7/10] Synchronize Python palette.py")

    # 8. Generate Kitty Terminal kitty.conf
    kitty_content = f"""# kitty.conf — Terminal configuration and color tokens.
# NOTE: Generated automatically by theme_manager.py. Do not edit directly.

# === FONT & WINDOW ===
font_family JetBrainsMono Nerd Font
bold_font auto
italic_font auto
bold_italic_font auto
font_size 12.0

window_padding_width 12
remember_window_size no
initial_window_width 860
initial_window_height 540
background_opacity 0.94
dynamic_background_opacity yes
confirm_os_window_close 0
enable_audio_bell no
linux_display_server auto

# === CURSOR ===
cursor {colors['accent']}
cursor_text_color {colors['bg_window']}
cursor_shape beam
cursor_trail 1

# === COLORS ===
background {colors['bg_window']}
foreground {colors['text_primary']}
selection_background {colors['accent']}
selection_foreground {colors['text_inverse']}

# === ANSI COLORS ===
color0 {colors['bg_window']}
color8 {colors['bg_card_hover']}
color1 {colors['accent']}
color9 {colors['accent_hover']}
color2 {colors['ribbon_blue']}
color10 {colors['ribbon_blue']}
color3 {colors['accent_hover']}
color11 {colors['accent_hover']}
color4 {colors['ribbon_blue']}
color12 {colors['ribbon_blue']}
color5 {colors['text_secondary']}
color13 {colors['text_secondary']}
color6 {colors['ribbon_blue']}
color14 {colors['text_muted']}
color7 {colors['text_primary']}
color15 {colors['text_inverse']}
"""
    for p in [os.path.join(hypr_base, "kitty", "kitty.conf"), os.path.join(user_config, "kitty", "kitty.conf")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(kitty_content)
    print("  ✔ [8/10] Synchronize Kitty Terminal kitty.conf")

    # 8b. Synchronize VS Code Integrated Terminal
    for vsc_path in [
        os.path.join(user_config, "Code", "User", "settings.json"),
        os.path.join(os.path.dirname(root_dir), ".vscode", "settings.json")
    ]:
        if os.path.exists(vsc_path):
            try:
                with open(vsc_path, "r", encoding="utf-8") as f:
                    vsc_data = json.load(f)
            except Exception:
                vsc_data = {}
            vsc_data.update({
                "terminal.integrated.fontFamily": "'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace",
                "terminal.integrated.fontSize": 12,
                "terminal.integrated.lineHeight": 1.2,
                "terminal.integrated.cursorStyle": "line",
                "terminal.integrated.cursorBlinking": True,
                "terminal.integrated.cursorWidth": 2,
                "terminal.integrated.smoothScrolling": True,
                "terminal.integrated.gpuAcceleration": "on"
            })
            vsc_colors = vsc_data.setdefault("workbench.colorCustomizations", {})
            vsc_colors.update({
                "terminal.background": colors['bg_window'],
                "terminal.foreground": colors['text_primary'],
                "terminal.selectionBackground": f"{colors['accent']}4D",
                "terminal.selectionForeground": colors['text_inverse'],
                "terminalCursor.foreground": colors['accent'],
                "terminalCursor.background": colors['bg_window'],
                "terminal.ansiBlack": colors['bg_window'],
                "terminal.ansiBrightBlack": colors['bg_card_hover'],
                "terminal.ansiRed": colors['accent'],
                "terminal.ansiBrightRed": colors['accent_hover'],
                "terminal.ansiGreen": colors['status_success'],
                "terminal.ansiBrightGreen": colors['status_success'],
                "terminal.ansiYellow": colors['status_warning'],
                "terminal.ansiBrightYellow": colors['status_warning'],
                "terminal.ansiBlue": colors['ribbon_blue'],
                "terminal.ansiBrightBlue": colors['ribbon_blue'],
                "terminal.ansiMagenta": colors['text_secondary'],
                "terminal.ansiBrightMagenta": colors['text_secondary'],
                "terminal.ansiCyan": colors['ribbon_blue'],
                "terminal.ansiBrightCyan": colors['text_muted'],
                "terminal.ansiWhite": colors['text_primary'],
                "terminal.ansiBrightWhite": colors['text_inverse']
            })
            try:
                with open(vsc_path, "w", encoding="utf-8") as f:
                    json.dump(vsc_data, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
    print("  ✔ [8b/10] Synchronize VS Code Integrated Terminal (Font, Colors, Cursor)")

    # 9. btop theme
    btop_content = f"""# obsidian-wine.theme — Color tokens for btop.
theme[main_bg]="{colors['bg_window']}"
theme[main_fg]="{colors['text_primary']}"
theme[title]="{colors['accent']}"
theme[hi_fg]="{colors['accent_hover']}"
theme[selected_bg]="{colors['accent']}"
theme[selected_fg]="{colors['text_inverse']}"
theme[inactive_fg]="{colors['text_muted']}"
theme[graph_text]="{colors['text_secondary']}"
theme[meter_bg]="{colors['bg_card']}"
theme[proc_misc]="{colors['accent_hover']}"
theme[cpu_box]="{colors['accent']}"
theme[mem_box]="{colors['accent_hover']}"
theme[net_box]="{colors['text_secondary']}"
theme[proc_box]="{colors['text_muted']}"
theme[div_line]="{colors['bg_card_hover']}"
theme[temp_start]="{colors['text_secondary']}"
theme[temp_mid]="{colors['accent_hover']}"
theme[temp_end]="{colors['accent']}"
theme[cpu_start]="{colors['text_muted']}"
theme[cpu_mid]="{colors['accent_hover']}"
theme[cpu_end]="{colors['accent']}"
theme[free_start]="{colors['text_muted']}"
theme[free_mid]="{colors['text_secondary']}"
theme[free_end]="{colors['text_primary']}"
theme[cached_start]="{colors['text_muted']}"
theme[cached_mid]="{colors['text_secondary']}"
theme[cached_end]="{colors['text_primary']}"
theme[available_start]="{colors['text_muted']}"
theme[available_mid]="{colors['text_secondary']}"
theme[available_end]="{colors['text_primary']}"
theme[used_start]="{colors['text_muted']}"
theme[used_mid]="{colors['text_secondary']}"
theme[used_end]="{colors['text_primary']}"
theme[download_start]="{colors['text_muted']}"
theme[download_mid]="{colors['accent_hover']}"
theme[download_end]="{colors['accent']}"
theme[upload_start]="{colors['text_muted']}"
theme[upload_mid]="{colors['accent_hover']}"
theme[upload_end]="{colors['accent']}"
"""
    for p in [os.path.join(hypr_base, "btop", "themes", "obsidian-wine.theme"), os.path.join(user_config, "btop", "themes", "obsidian-wine.theme")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(btop_content)
    print("  ✔ [9/10] Synchronize btop monitor theme")

    # 10. Reload Live Compositor & Apps
    print("\n\033[1;33m⚡ RELOADING LIVE USER INTERFACE (HOT-RELOAD)...⚡\033[0m")
    subprocess.run(["hyprctl", "reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Restart Waybar cleanly to pick up new config.jsonc & palette.css
    subprocess.run("pkill -x waybar 2>/dev/null || true", shell=True)
    time.sleep(0.15)
    subprocess.Popen(["waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    # Reload Kitty
    subprocess.run("pkill -USR1 kitty 2>/dev/null || true", shell=True)
    # Reload Fcitx5
    subprocess.run("fcitx5-remote -r 2>/dev/null || true", shell=True)
    # Reload Swaync
    subprocess.run("swaync-client -R -rs 2>/dev/null || true", shell=True)
    # Terminate running GTK popups so their next launch uses new tokens immediately
    subprocess.run("pkill -f control_center.py 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f dashboard.py 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f shelf.py 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f music_visualizer.py 2>/dev/null || true", shell=True)
    for pf in ["/tmp/control_center.pid", "/tmp/dashboard.pid", "/tmp/shelf.pid", "/tmp/music_visualizer.pid"]:
        try:
            os.remove(pf)
        except OSError:
            pass
    print("  ✔ [10/10] Reloaded Hyprland, Waybar, Kitty, Fcitx5, SwayNC and popups")

    # Notify (English only per AGENTS.md rules)
    msg = f"Applied palette: {theme_name}\nAccent: {colors['accent']} | Background: {colors['bg_window']}"
    subprocess.run(["notify-send", "-i", "preferences-desktop-theme", "✿ System Theme Synchronized ✿", msg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"\033[1;32m✨ ENTIRE SYSTEM SYNCHRONIZED WITH THEME: {theme_name}! ✨\033[0m\n")


def run_interactive_menu():
    print("\033[1;35m" + "=" * 65 + "\033[0m")
    print("\033[1;31m   ✿ SERENA SYSTEM COLOR & THEME CONTROLLER ✿   \033[0m")
    print("\033[1;35m" + "=" * 65 + "\033[0m\n")

    preset_keys = list(PRESETS.keys())
    for idx, key in enumerate(preset_keys, 1):
        item = PRESETS[key]
        c = item["colors"]
        badge_bg = color_badge(c["bg_window"])
        badge_ac = color_badge(c["accent"])
        badge_rb = color_badge(c["ribbon_blue"])
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
        selected_key = preset_keys[int(choice) - 1]
        item = PRESETS[selected_key]
        full_colors = build_full_color_palette(item["colors"])
        apply_theme_to_all_components(item["name"], full_colors)
    elif choice == "8":
        print("\n\033[1;34m--- ENTER CUSTOM HEX COLORS (e.g. #FF2A55 or FF2A55) ---\033[0m")
        try:
            bg_in = input("1. Window Background Hex (Default: #201011): ").strip() or "#201011"
            if not bg_in.startswith("#"):
                bg_in = "#" + bg_in
            accent_in = input("2. Accent Hex (Default: #FF2A55): ").strip() or "#FF2A55"
            if not accent_in.startswith("#"):
                accent_in = "#" + accent_in
            ribbon_in = input("3. Ribbon Hex (Default: #50A6FF): ").strip() or "#50A6FF"
            if not ribbon_in.startswith("#"):
                ribbon_in = "#" + ribbon_in
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return

        custom_colors = build_full_color_palette({
            "bg_window": bg_in,
            "accent": accent_in,
            "ribbon_blue": ribbon_in
        })
        apply_theme_to_all_components(f"Custom ({accent_in})", custom_colors)
    else:
        print("Invalid choice.")


def run_rofi_menu():
    options = []
    keys = list(PRESETS.keys())
    for k in keys:
        p = PRESETS[k]
        options.append(f"{p['name']} ({p['colors']['accent']})")
    options.append("🎨 Custom (Enter Hex Code)...")

    input_text = "\n".join(options)
    rofi_cmd = ["rofi", "-dmenu", "-i", "-p", "✿ Select System Theme"]
    try:
        proc = subprocess.run(rofi_cmd, input=input_text, text=True, stdout=subprocess.PIPE)
        chosen = proc.stdout.strip()
    except Exception as e:
        print(f"Error running Rofi: {e}")
        return

    if not chosen:
        return

    for idx, opt in enumerate(options[:-1]):
        if chosen == opt:
            k = keys[idx]
            p = PRESETS[k]
            full_colors = build_full_color_palette(p["colors"])
            apply_theme_to_all_components(p["name"], full_colors)
            return

    if "Custom" in chosen:
        # Prompt for hex via rofi
        hex_prompt = ["rofi", "-dmenu", "-p", "Enter Accent Hex (e.g. #FF2A55)"]
        proc_hex = subprocess.run(hex_prompt, input="", text=True, stdout=subprocess.PIPE)
        custom_accent = proc_hex.stdout.strip()
        if custom_accent:
            if not custom_accent.startswith("#"):
                custom_accent = "#" + custom_accent
            custom_colors = build_full_color_palette({
                "bg_window": "#201011",
                "accent": custom_accent,
                "ribbon_blue": "#50A6FF"
            })
            apply_theme_to_all_components(f"Custom ({custom_accent})", custom_colors)


def main():
    parser = argparse.ArgumentParser(description="Serena Rice Theme & Palette Manager")
    parser.add_argument("preset_pos", nargs="?", default=None, help="Quick preset name (e.g. serena-wine, sakura-pastel, kalos-cyber)")
    parser.add_argument("--preset", "-p", type=str, help="Preset name (e.g. serena-wine, sakura-pastel, kalos-cyber, midnight-amethyst, matcha-sage, crimson-velvet, ocean-breeze)")
    parser.add_argument("--accent", "-a", type=str, help="Custom accent hex color (e.g. '#FF597B')")
    parser.add_argument("--bg", "-b", type=str, help="Custom background hex color (e.g. '#1C0D11')")
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
            with open(tokens_path) as f:
                d = json.load(f)
            c = d.get("colors", {})
            print(f"Current theme: \033[1;32m{d.get('name', 'N/A')}\033[0m")
            print(f"  Background: {color_badge(c.get('bg_window', '#000'))}")
            print(f"  Accent:     {color_badge(c.get('accent', '#000'))}")
            print(f"  Ribbon:     {color_badge(c.get('ribbon_blue', '#000'))}")
        return

    if args.rofi:
        run_rofi_menu()
        return

    if target_preset:
        preset_key = target_preset.lower().strip()
        if preset_key in PRESETS:
            p = PRESETS[preset_key]
            full_colors = build_full_color_palette(p["colors"])
            apply_theme_to_all_components(p["name"], full_colors)
        else:
            print(f"Preset '{preset_key}' not found. Available presets: {', '.join(PRESETS.keys())}")
        return

    if args.accent or args.bg:
        # Load current base
        root_dir = find_workspace_root()
        tokens_path = os.path.join(root_dir, "config", "theme", "tokens.json")
        if not os.path.exists(tokens_path):
            tokens_path = os.path.expanduser("~/.config/hypr/theme/tokens.json")
        cur_colors = {}
        if os.path.exists(tokens_path):
            with open(tokens_path) as f:
                cur_colors = json.load(f).get("colors", {})

        bg = args.bg if args.bg else cur_colors.get("bg_window", "#201011")
        if not bg.startswith("#"):
            bg = "#" + bg
        accent = args.accent if args.accent else cur_colors.get("accent", "#FF2A55")
        if not accent.startswith("#"):
            accent = "#" + accent
        ribbon = args.ribbon if args.ribbon else cur_colors.get("ribbon_blue", "#50A6FF")
        if not ribbon.startswith("#"):
            ribbon = "#" + ribbon

        custom_colors = build_full_color_palette({
            "bg_window": bg,
            "accent": accent,
            "ribbon_blue": ribbon
        })
        apply_theme_to_all_components(f"Custom ({accent})", custom_colors)
        return

    # Default to interactive CLI menu if no arguments provided
    run_interactive_menu()


if __name__ == "__main__":
    main()

