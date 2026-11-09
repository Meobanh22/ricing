#!/usr/bin/env bash
""":"
python3 "$0" "$@"
exit $?
":"""
# generate_pokepuffs.py — Authentic Pokémon Amie Sweet Poké Puff icons for Waybar (clean matte anime cel-shaded, no white highlight curves).
import os
import subprocess

COMMON_DEFS = """
    <!-- Single Shared Authentic Poké Puff Silhouette -->
    <path id="puff-silhouette" d="
      M 50 14
      C 76 14, 95 24, 92 48
      C 91 66, 78 80, 64 82
      L 36 82
      C 22 80, 9 66, 8 48
      C 5 24, 24 14, 50 14
      Z" />
"""

SVG_ACTIVE = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
{COMMON_DEFS}
  </defs>

  <!-- BOLD 3D Cel-shaded Bottom Border: shared silhouette offset down by 11px -->
  <use href="#puff-silhouette" y="11" fill="#4D0A1C" />

  <!-- Lower Pastry Bun Base (fill only) -->
  <path d="
    M 8 48
    C 9 66, 22 80, 36 82
    L 64 82
    C 78 80, 91 66, 92 48
    Z"
    fill="#E8C2D0" />

  <!-- Lower Bun Cel-shading Shadow Tone -->
  <path d="
    M 14 66
    C 20 76, 28 82, 36 82
    L 64 82
    C 72 82, 80 76, 86 66
    C 76 74, 60 77, 50 77
    C 40 77, 24 74, 14 66
    Z"
    fill="#A68595" />

  <!-- Cream Filling (Soft wavy cream layer sandwiched in middle) -->
  <path d="
    M 8 48
    C 18 54, 27 54, 37 48
    C 46 43, 54 43, 63 48
    C 73 54, 82 54, 92 48
    C 91 60, 81 66, 64 65
    C 54 64, 46 64, 36 65
    C 19 66, 9 60, 8 48
    Z"
    fill="#FFF0F5" stroke="#4D0A1C" stroke-width="2.8" stroke-linejoin="round" />

  <!-- Upper Pastry Bun (fill only) -->
  <path d="
    M 8 48
    C 5 24, 24 14, 50 14
    C 76 14, 95 24, 92 48
    C 82 54, 73 54, 63 48
    C 54 43, 46 43, 37 48
    C 27 54, 18 54, 8 48
    Z"
    fill="#F02D4C" />

  <!-- Shared Outer Silhouette Stroke (Drawn on top to ensure 100% IDENTICAL border thickness) -->
  <use href="#puff-silhouette" fill="none" stroke="#4D0A1C" stroke-width="3.5" stroke-linejoin="round" />

  <!-- Stem at top -->
  <path d="M 50 8 C 50 3, 56 0, 62 1" fill="none" stroke="#4D0A1C" stroke-width="3.5" stroke-linecap="round" />

  <!-- Cherry on top (Solid flat ruby red, no highlight curve) -->
  <circle cx="50" cy="10" r="7.5" fill="#DC1A36" stroke="#4D0A1C" stroke-width="3" />
</svg>
"""

def create_inactive_svg(stops, is_hover=False):
    grad_stops = "\n".join([f'      <stop offset="{pct}" stop-color="{col}" />' for pct, col in stops])
    stroke_col = "#610E24" if is_hover else "#4D0A1C"
    bottom_3d = "#610E24" if is_hover else "#4D0A1C"
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <!-- Tactile Workspace Gradient -->
    <linearGradient id="body-grad" x1="0" y1="0" x2="0" y2="1">
{grad_stops}
    </linearGradient>
{COMMON_DEFS}
  </defs>

  <!-- BOLD 3D Cel-shaded Bottom Border: shared silhouette offset down by 11px -->
  <use href="#puff-silhouette" y="11" fill="{bottom_3d}" />

  <!-- Main Body Silhouette (Filled with smooth tactile gradient, clean matte, no highlight curve) -->
  <use href="#puff-silhouette" fill="url(#body-grad)" stroke="{stroke_col}" stroke-width="3.5" stroke-linejoin="round" />

  <!-- Stem at top -->
  <path d="M 50 8 C 50 3, 56 0, 62 1" fill="none" stroke="{stroke_col}" stroke-width="3.5" stroke-linecap="round" />

  <!-- Cherry on top (100% round circle filled with SAME gradient, NO red, NO gloss!) -->
  <circle cx="50" cy="10" r="7.5" fill="url(#body-grad)" stroke="{stroke_col}" stroke-width="3" />
</svg>
"""

def main():
    base_dirs = [
        os.path.expanduser("~/custom/config/waybar/icons"),
        os.path.expanduser("~/.config/waybar/icons"),
    ]

    # Inactive tactile stops: #A3183D 0%, #E53262 25%, #FF7299 50%, #EAA2C6 75%, #BE7AA8 100%
    inactive_stops = [
        ("0%", "#A3183D"),
        ("25%", "#E53262"),
        ("50%", "#FF7299"),
        ("75%", "#EAA2C6"),
        ("100%", "#BE7AA8")
    ]

    # Hover tactile stops: #B52048 0%, #F04070 25%, #FF80A6 50%, #F2B2D2 75%, #CA8BB4 100%
    hover_stops = [
        ("0%", "#B52048"),
        ("25%", "#F04070"),
        ("50%", "#FF80A6"),
        ("75%", "#F2B2D2"),
        ("100%", "#CA8BB4")
    ]

    svg_map = {
        "pokepuff_active.svg": SVG_ACTIVE,
        "pokepuff_inactive.svg": create_inactive_svg(inactive_stops, is_hover=False),
        "pokepuff_hover.svg": create_inactive_svg(hover_stops, is_hover=True),
    }

    for bdir in base_dirs:
        os.makedirs(bdir, exist_ok=True)
        for fname, svg_content in svg_map.items():
            svg_path = os.path.join(bdir, fname)
            png_name = fname.replace(".svg", ".png")
            png_path = os.path.join(bdir, png_name)
            
            with open(svg_path, "w") as f:
                f.write(svg_content)
            
            # Also render high-res anti-aliased PNG
            subprocess.run([
                "rsvg-convert",
                "-w", "200", "-h", "200",
                svg_path,
                "-o", png_path
            ], check=True)

    print("Successfully generated clean matte Poké Puff icons in all target directories!")

if __name__ == "__main__":
    main()
