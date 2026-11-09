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
    "bg_card_soft": "rgba(42, 26, 30, 0.40)",
    "bg_card_subtle": "rgba(42, 26, 30, 0.70)",
    "bg_action": "rgba(48, 31, 32, 0.90)",
    "bg_action_hover": "rgba(58, 34, 42, 0.98)",
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
    "accent_soft": "rgba(220, 26, 54, 0.12)",
    "accent_border": "rgba(220, 26, 54, 0.40)",
    "accent_dash": "rgba(220, 26, 54, 0.45)",
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
    "bg_tactile_cream": "rgba(255, 240, 245, 0.96)"
}

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

# Gradient Design Tokens
GRADIENTS = {
    "sunset": "linear-gradient(to bottom, #A3183D 0%, #E53262 25%, #FF7299 50%, #EAA2C6 75%, #BE7AA8 100%)",
    "sunset_hover": "linear-gradient(to bottom, #B52048 0%, #F04070 25%, #FF80A6 50%, #F2B2D2 75%, #CA8BB4 100%)",
    "sunset_active": "linear-gradient(to bottom, #BA2246 0%, #FF3D71 25%, #FFCCD8 50%, #F0D5E7 75%, #C29BCA 100%)",
    "sunset_stops": [
        [
            "0%",
            "#A3183D"
        ],
        [
            "25%",
            "#E53262"
        ],
        [
            "50%",
            "#FF7299"
        ],
        [
            "75%",
            "#EAA2C6"
        ],
        [
            "100%",
            "#BE7AA8"
        ]
    ],
    "sunset_hover_stops": [
        [
            "0%",
            "#B52048"
        ],
        [
            "25%",
            "#F04070"
        ],
        [
            "50%",
            "#FF80A6"
        ],
        [
            "75%",
            "#F2B2D2"
        ],
        [
            "100%",
            "#CA8BB4"
        ]
    ]
}
SUNSET_STOPS = [
    (float(p.replace('%', '')) / 100.0, c)
    for p, c in GRADIENTS.get("sunset_stops", [
        ["0%", "#A3183D"], ["25%", "#E53262"], ["50%", "#FF7299"], ["75%", "#EAA2C6"], ["100%", "#BE7AA8"]
    ])
]
SUNSET_HOVER_STOPS = [
    (float(p.replace('%', '')) / 100.0, c)
    for p, c in GRADIENTS.get("sunset_hover_stops", [
        ["0%", "#B52048"], ["25%", "#F04070"], ["50%", "#FF80A6"], ["75%", "#F2B2D2"], ["100%", "#CA8BB4"]
    ])
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
BORDER_WINDOW_RGBA    = (1.0, 1.0, 1.0, 0.12)
BORDER_CARD_RGBA      = (1.0, 1.0, 1.0, 0.12)
