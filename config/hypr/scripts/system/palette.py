#!/usr/bin/env python3
# palette.py — Python design tokens.
# NOTE: Generated automatically. Do not edit directly.

PALETTE = {
    "bg_window": "#201011",
    "bg_window_alpha": "rgba(32, 16, 17, 0.98)",
    "bg_window_hypr": "rgba(201011fa)",
    "bg_card": "#2A1A1E",
    "bg_card_alpha": "rgba(42, 26, 30, 0.95)",
    "bg_card_hypr": "rgba(2A1A1Ef2)",
    "bg_card_hover": "#3A222A",
    "bg_card_hover_alpha": "rgba(58, 34, 42, 0.98)",
    "bg_card_hover_hypr": "rgba(3A222Afa)",
    "bg_subtle": "#301F20",
    "bg_subtle_alpha": "rgba(48, 31, 32, 0.95)",
    "bg_subtle_hypr": "rgba(301F20f2)",
    "bg_ghost": "transparent",
    "bg_ghost_hover": "rgba(42, 26, 30, 0.50)",
    "border_window": "rgba(255, 255, 255, 0.12)",
    "border_window_hypr": "rgba(ffffff1f)",
    "border_card": "rgba(255, 255, 255, 0.12)",
    "border_card_hypr": "rgba(ffffff1f)",
    "border_card_hover": "rgba(220, 26, 54, 0.65)",
    "border_card_hover_hypr": "rgba(DC1A36a6)",
    "accent": "#DC1A36",
    "accent_hypr": "rgb(DC1A36)",
    "accent_hover": "#F02D4C",
    "accent_hover_hypr": "rgb(F02D4C)",
    "accent_dim": "rgba(220, 26, 54, 0.48)",
    "accent_subtle": "rgba(220, 26, 54, 0.20)",
    "accent_border": "rgba(220, 26, 54, 0.40)",
    "text_primary": "#FFF0F5",
    "text_primary_hypr": "rgb(FFF0F5)",
    "text_secondary": "#E8C2D0",
    "text_secondary_hypr": "rgb(E8C2D0)",
    "text_muted": "#A68595",
    "text_muted_hypr": "rgb(A68595)",
    "text_inverse": "#FFFFFF",
    "text_inverse_hypr": "rgb(FFFFFF)",
    "status_warning": "#FFB86C",
    "status_warning_hypr": "rgb(FFB86C)",
    "status_critical": "#DC1A36",
    "status_critical_hypr": "rgb(DC1A36)",
    "status_success": "#8FBC8F",
    "status_success_hypr": "rgb(8FBC8F)",
    "ribbon_blue": "#50A6FF",
    "ribbon_blue_alpha": "rgba(80, 166, 255, 0.95)",
    "ribbon_blue_hypr": "rgb(50A6FF)",
    "screen_cyan": "#87F0FF",
    "screen_cyan_alpha": "rgba(135, 240, 255, 0.55)",
    "screen_cyan_hypr": "rgb(87F0FF)",
    "bg_waybar": "#851733",
    "bg_waybar_hover": "#9C2241",
    "bg_waybar_hypr": "rgba(851733f2)",
    "border_waybar_3d": "#4D0A1C",
    "border_waybar_3d_hover": "#610E24",
    "border_waybar_3d_hypr": "rgb(4D0A1C)",
    "shadow_extrusion": "#4D0A1C",
    "shadow_extrusion_hover": "#610E24",
    "shadow_extrusion_hypr": "rgb(4D0A1C)",
    "border_tactile_white": "rgba(255, 255, 255, 0.65)",
    "border_tactile_white_bright": "rgba(255, 255, 255, 0.90)",
    "bg_tactile_cream": "rgba(255, 240, 245, 0.96)",
    "bg_tactile_cream_hypr": "rgba(FFF0F5f5)",
    "pokepuff_pink": "#FF5C8A",
    "pokepuff_pink_hypr": "rgb(FF5C8A)",
    "dark_wine": "#201011",
    "deep_wine": "#2A1A1E",
    "soft_wine": "#301F20",
    "light_wine": "#3A222A",
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
    "soft_green": "#8FBC8F"
}
TYPOGRAPHY = {
    "font_primary": "JetBrains Mono Nerd Font",
    "font_stack": "\"JetBrains Mono Nerd Font\", \"FiraCode Nerd Font\", \"Segoe UI\", sans-serif",
    "base_size": 13,
    "heading_size": 14,
    "caption_size": 11,
    "micro_size": 10,
    "hero_size": 54
}
GEOMETRY = {
    "radius_window": 16,
    "radius_card": 10,
    "radius_button": 8,
    "radius_badge": 4,
    "radius_scrollbar": 4,
    "width_control_center": 315,
    "width_shelf": 464,
    "width_rofi": 640
}

def hex_to_rgba(hex_code: str, alpha: float = 1.0):
    h = hex_code.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, float(alpha))

# Typography & Geometry constants
FONT_PRIMARY         = TYPOGRAPHY.get("font_primary", "JetBrains Mono Nerd Font")
FONT_STACK           = TYPOGRAPHY.get("font_stack", "\"JetBrains Mono Nerd Font\", \"FiraCode Nerd Font\", \"Segoe UI\", sans-serif")
FONT_BASE_SIZE       = int(TYPOGRAPHY.get("base_size", 13))
FONT_HEADING_SIZE    = int(TYPOGRAPHY.get("heading_size", 14))
FONT_CAPTION_SIZE    = int(TYPOGRAPHY.get("caption_size", 11))
FONT_MICRO_SIZE      = int(TYPOGRAPHY.get("micro_size", 10))
FONT_HERO_SIZE       = int(TYPOGRAPHY.get("hero_size", 54))

RADIUS_WINDOW        = int(GEOMETRY.get("radius_window", 16))
RADIUS_CARD          = int(GEOMETRY.get("radius_card", 10))
RADIUS_BUTTON        = int(GEOMETRY.get("radius_button", 8))
RADIUS_BADGE         = int(GEOMETRY.get("radius_badge", 4))
RADIUS_SCROLLBAR     = int(GEOMETRY.get("radius_scrollbar", 4))
WIDTH_CONTROL_CENTER = int(GEOMETRY.get("width_control_center", 315))
WIDTH_SHELF          = int(GEOMETRY.get("width_shelf", 464))
WIDTH_ROFI           = int(GEOMETRY.get("width_rofi", 640))

# Color hex constants
C_BG_WIN        = PALETTE.get("bg_window", "#201011")
C_BG_CARD       = PALETTE.get("bg_card", "#2A1A1E")
C_BG_CARD_HOVER = PALETTE.get("bg_card_hover", "#3A222A")
C_BG_SUBTLE     = PALETTE.get("bg_subtle", "#301F20")
C_ACCENT        = PALETTE.get("accent", "#DC1A36")
C_ACCENT_HOVER  = PALETTE.get("accent_hover", "#F02D4C")
C_TEXT_PRI      = PALETTE.get("text_primary", "#FFF0F5")
C_TEXT_SEC      = PALETTE.get("text_secondary", "#E8C2D0")
C_TEXT_MUT      = PALETTE.get("text_muted", "#A68595")
C_TEXT_INV      = PALETTE.get("text_inverse", "#FFFFFF")
C_STATUS_WARN   = PALETTE.get("status_warning", "#FFB86C")
C_STATUS_CRIT   = PALETTE.get("status_critical", "#DC1A36")
C_STATUS_SUCC   = PALETTE.get("status_success", "#8FBC8F")
C_RIBBON        = PALETTE.get("ribbon_blue", "#50A6FF")
C_SCREEN_CYAN   = PALETTE.get("screen_cyan", "#87F0FF")
C_BG_CREAM      = PALETTE.get("bg_tactile_cream", "rgba(255, 240, 245, 0.96)")
C_BG_WAYBAR     = PALETTE.get("bg_waybar", "#851733")
C_BG_WAYBAR_HOV = PALETTE.get("bg_waybar_hover", "#9C2241")
C_BORDER_3D     = PALETTE.get("border_waybar_3d", "#4D0A1C")
C_SHADOW_EXTR   = PALETTE.get("shadow_extrusion", "#4D0A1C")
C_SHADOW_EXTR_H = PALETTE.get("shadow_extrusion_hover", "#610E24")
C_POKEPUFF_PINK = PALETTE.get("pokepuff_pink", "#FF5C8A")
C_SUNSET_PINK   = "#FF7299"
C_SUNSET_PASTEL = "#EAA2C6"

# Gradient Design Tokens
GRADIENTS = {
    "sunset": "linear-gradient(to bottom, #A3183D 0%, #E53262 25%, #FF7299 50%, #EAA2C6 75%, #BE7AA8 100%)"
}
SUNSET_STOPS = [
    (0.00, "#A3183D"),
    (0.25, "#E53262"),
    (0.50, "#FF7299"),
    (0.75, "#EAA2C6"),
    (1.00, "#BE7AA8")
]

# Pre-computed Cairo RGBA tuples
BG_WINDOW_RGBA        = hex_to_rgba(C_BG_WIN, 0.98)
BG_CARD_RGBA          = hex_to_rgba(C_BG_CARD, 0.95)
BG_CARD_HOVER_RGBA    = hex_to_rgba(C_BG_CARD_HOVER, 0.98)
BG_SUBTLE_RGBA        = hex_to_rgba(C_BG_SUBTLE, 0.95)
BG_WAYBAR_RGBA        = hex_to_rgba(C_BG_WAYBAR, 1.0)
SHADOW_EXTRUSION_RGBA = hex_to_rgba(C_SHADOW_EXTR, 1.0)
ACCENT_RGBA           = hex_to_rgba(C_ACCENT, 1.0)
ACCENT_HOVER_RGBA     = hex_to_rgba(C_ACCENT_HOVER, 1.0)
ACCENT_DIM_RGBA       = hex_to_rgba(C_ACCENT, 0.48)
ACCENT_SUBTLE_RGBA    = hex_to_rgba(C_ACCENT, 0.20)
POKEPUFF_PINK_RGBA    = hex_to_rgba(C_POKEPUFF_PINK, 1.0)
BORDER_WINDOW_RGBA    = (1.0, 1.0, 1.0, 0.12)
BORDER_CARD_RGBA      = (1.0, 1.0, 1.0, 0.12)
