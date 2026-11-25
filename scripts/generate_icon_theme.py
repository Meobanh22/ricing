#!/usr/bin/env python3
# generate_icon_theme.py — Generate Serena Wine red folder & audio icon theme from tokens.json.

import json
import os
import re
import shutil
import subprocess

ADWAITA_PLACES = "/usr/share/icons/Adwaita/scalable"
THEME_NAME = "serena-wine"

DEFAULT_GRADIENT_STOPS = [
    ("0%", "#A3183D"),
    ("25%", "#E53262"),
    ("50%", "#FF7299"),
    ("75%", "#EAA2C6"),
    ("100%", "#BE7AA8"),
]


def parse_stops(gradient_str: str):
    matches = re.findall(r"(#[0-9A-Fa-f]{6})\s+(\d+(?:\.\d+)?)%", gradient_str or "")
    if not matches:
        return DEFAULT_GRADIENT_STOPS
    return [(f"{pct}%", col.upper()) for col, pct in matches]


def load_theme_tokens():
    """Load palette colors and gradient stops from config/theme/tokens.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    candidates = [
        os.path.join(root_dir, "config", "theme", "tokens.json"),
        os.path.expanduser("~/.config/hypr/theme/tokens.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return root_dir, data.get("colors", {}), parse_stops(data.get("gradient"))
    return root_dir, {}, DEFAULT_GRADIENT_STOPS


def build_index_theme():
    return """[Icon Theme]
Name=Serena Wine
Comment=Serena Wine red folder and media icons inheriting Adwaita
Inherits=Adwaita,AdwaitaLegacy,hicolor
Example=folder

Directories=16x16/places,16x16/mimetypes,16x16/actions,scalable/places,scalable/mimetypes,scalable/actions

[16x16/places]
Context=Places
Size=16
Type=Fixed

[16x16/mimetypes]
Context=MimeTypes
Size=16
Type=Fixed

[16x16/actions]
Context=Actions
Size=16
Type=Fixed

[scalable/places]
Context=Places
Size=128
MinSize=24
MaxSize=512
Type=Scalable

[scalable/mimetypes]
Context=MimeTypes
Size=128
MinSize=24
MaxSize=512
Type=Scalable

[scalable/actions]
Context=Actions
Size=128
MinSize=24
MaxSize=512
Type=Scalable
"""


def build_music_note_svg(colors: dict) -> str:
    """Build a clean anime minimalist double eighth-note SVG from tokens.json."""
    dark_ruby = colors.get("dark_ruby", "#4D0A1C")
    wine_red = colors.get("wine_red", "#851733")
    vivid_red = colors.get("vivid_red", "#DC1A36")
    light_red = colors.get("light_red", "#F02D4C")
    vivid_pink = colors.get("vivid_pink", "#FF5C8A")
    soft_pink = colors.get("soft_pink", "#E8C2D0")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="note-grad" x1="20%" y1="10%" x2="85%" y2="95%">
      <stop offset="0%" stop-color="{vivid_pink}"/>
      <stop offset="45%" stop-color="{light_red}"/>
      <stop offset="100%" stop-color="{vivid_red}"/>
    </linearGradient>
    <path id="music-note-shape" d="
      M 46 27
      Q 46 21, 52 19.5
      L 100 9
      Q 108 7.5, 108 16
      L 108 85
      C 108 96.5, 97 106, 84 106
      C 72.5 106, 64 99, 64 89.5
      C 64 79.5, 73.5 71, 86 71
      C 90.8 71, 95 72.3, 98 74.5
      L 98 34
      L 56 43
      L 56 97
      C 56 108.5, 45 118, 32 118
      C 20.5 118, 12 111, 12 101.5
      C 12 91.5, 21.5 83, 34 83
      C 38.8 83, 43 84.3, 46 86.5
      Z"/>
  </defs>

  <!-- 3D cel-shaded depth shadow -->
  <use href="#music-note-shape" y="5" fill="{dark_ruby}"/>
  <use href="#music-note-shape" y="2.5" fill="{wine_red}"/>

  <!-- Main music note body -->
  <use href="#music-note-shape" fill="url(#note-grad)" stroke="{dark_ruby}" stroke-width="3" stroke-linejoin="round"/>

  <!-- Subtle top beam & notehead cel highlights -->
  <path d="M 51 24.5 L 101 14" stroke="{soft_pink}" stroke-width="2.8" stroke-linecap="round" opacity="0.6"/>
  <ellipse cx="29" cy="95" rx="5.5" ry="2.6" transform="rotate(-22 29 95)" fill="{soft_pink}" opacity="0.45"/>
  <ellipse cx="81" cy="83" rx="5.5" ry="2.6" transform="rotate(-22 81 83)" fill="{soft_pink}" opacity="0.45"/>
</svg>
"""


def recolor_svg(svg_text: str, color_map: dict, gradient_stops=None) -> str:
    if gradient_stops:
        stops_xml = "".join(f'<stop offset="{offset}" stop-color="{col}"/>' for offset, col in gradient_stops)
        grad_def = f'<linearGradient id="serena-sunset" x1="0%" y1="0%" x2="0%" y2="100%">{stops_xml}</linearGradient>'
        svg_text = svg_text.replace("<linearGradient ", grad_def + "<linearGradient ", 1)
        svg_text = svg_text.replace('fill="#a4caee"', 'fill="url(#serena-sunset)"')
        svg_text = svg_text.replace('fill="#A4CAEE"', 'fill="url(#serena-sunset)"')
    for src_hex, dst_hex in color_map.items():
        svg_text = svg_text.replace(src_hex, dst_hex).replace(src_hex.upper(), dst_hex)
    return svg_text


def render_category(src_dir, dst_svg_dir, dst_png_dir, targets, color_map, aliases, rsvg, gradient_stops=None):
    os.makedirs(dst_svg_dir, exist_ok=True)
    os.makedirs(dst_png_dir, exist_ok=True)
    generated = {}

    for filename in targets:
        src_path = os.path.join(src_dir, filename)
        if not os.path.isfile(src_path):
            continue
        with open(src_path, "r", encoding="utf-8") as f:
            recolored = recolor_svg(f.read(), color_map, gradient_stops=gradient_stops)
        dst_svg = os.path.join(dst_svg_dir, filename)
        with open(dst_svg, "w", encoding="utf-8") as f:
            f.write(recolored)
        generated[filename] = dst_svg

    for alias_name, base_name in aliases.items():
        if base_name in generated:
            alias_path = os.path.join(dst_svg_dir, alias_name)
            shutil.copy2(generated[base_name], alias_path)
            generated[alias_name] = alias_path

    if rsvg:
        for filename, svg_path in generated.items():
            png_path = os.path.join(dst_png_dir, filename[:-4] + ".png")
            subprocess.run([rsvg, "-w", "16", "-h", "16", svg_path, "-o", png_path], check=True)

    return len(generated)


def main():
    root_dir, colors, gradient_stops = load_theme_tokens()
    places_src = os.path.join(ADWAITA_PLACES, "places")
    mimes_src = os.path.join(ADWAITA_PLACES, "mimetypes")
    if not os.path.isdir(places_src):
        print(f"Skipping icon theme generation: {places_src} not found")
        return

    folder_solid_map = {
        "#a4caee": colors.get("wine_red", "#851733"),
        "#438de6": colors.get("dark_ruby", "#4D0A1C"),
        "#62a0ea": "#610E24",
        "#afd4ff": colors.get("vivid_pink", "#FF5C8A"),
        "#c0d5ea": colors.get("vivid_red", "#DC1A36"),
    }

    folder_gradient_map = {
        "#438de6": colors.get("dark_ruby", "#4D0A1C"),
        "#62a0ea": colors.get("wine_red", "#851733"),
        "#afd4ff": colors.get("vivid_pink", "#FF5C8A"),
        "#c0d5ea": colors.get("soft_pink", "#E8C2D0"),
    }

    repo_theme_dir = os.path.join(root_dir, "assets", "icon-themes", THEME_NAME)
    os.makedirs(repo_theme_dir, exist_ok=True)
    with open(os.path.join(repo_theme_dir, "index.theme"), "w", encoding="utf-8") as f:
        f.write(build_index_theme())

    rsvg = shutil.which("rsvg-convert")

    gradient_place_targets = {
        "folder-documents.svg",
        "folder-download.svg",
        "folder-music.svg",
        "folder-pictures.svg",
        "folder-projects.svg",
        "folder-publicshare.svg",
        "folder-templates.svg",
        "folder-videos.svg",
        "user-bookmarks.svg",
        "user-desktop.svg",
        "user-home.svg",
    }
    all_place_targets = [
        name
        for name in sorted(os.listdir(places_src))
        if name.endswith(".svg") and (name.startswith("folder") or name in {"user-bookmarks.svg", "user-desktop.svg", "user-home.svg"})
    ]
    solid_place_targets = [name for name in all_place_targets if name not in gradient_place_targets]

    total = render_category(
        places_src,
        os.path.join(repo_theme_dir, "scalable", "places"),
        os.path.join(repo_theme_dir, "16x16", "places"),
        solid_place_targets,
        folder_solid_map,
        {"folder-open.svg": "folder-drag-accept.svg"},
        rsvg,
    )
    total += render_category(
        places_src,
        os.path.join(repo_theme_dir, "scalable", "places"),
        os.path.join(repo_theme_dir, "16x16", "places"),
        sorted(gradient_place_targets),
        folder_gradient_map,
        {"folder-bookmarks.svg": "user-bookmarks.svg"},
        rsvg,
        gradient_stops=gradient_stops,
    )

    user_home_svg = os.path.join(repo_theme_dir, "scalable", "places", "user-home.svg")
    if os.path.isfile(user_home_svg):
        actions_svg_dir = os.path.join(repo_theme_dir, "scalable", "actions")
        actions_png_dir = os.path.join(repo_theme_dir, "16x16", "actions")
        os.makedirs(actions_svg_dir, exist_ok=True)
        os.makedirs(actions_png_dir, exist_ok=True)
        go_home_svg = os.path.join(actions_svg_dir, "go-home.svg")
        shutil.copy2(user_home_svg, go_home_svg)
        if rsvg:
            subprocess.run(
                [rsvg, "-w", "16", "-h", "16", go_home_svg, "-o", os.path.join(actions_png_dir, "go-home.png")],
                check=True,
            )
        total += 1

    if os.path.isdir(mimes_src):
        mimes_svg_dir = os.path.join(repo_theme_dir, "scalable", "mimetypes")
        mimes_png_dir = os.path.join(repo_theme_dir, "16x16", "mimetypes")
        total += render_category(
            mimes_src,
            mimes_svg_dir,
            mimes_png_dir,
            ["inode-directory.svg"],
            folder_solid_map,
            {},
            rsvg,
        )
        audio_svg_path = os.path.join(mimes_svg_dir, "audio-x-generic.svg")
        with open(audio_svg_path, "w", encoding="utf-8") as f:
            f.write(build_music_note_svg(colors))
        if rsvg:
            subprocess.run(
                [rsvg, "-w", "16", "-h", "16", audio_svg_path, "-o", os.path.join(mimes_png_dir, "audio-x-generic.png")],
                check=True,
            )
        total += 1

    cache_tool = shutil.which("gtk-update-icon-cache")
    if cache_tool:
        subprocess.run([cache_tool, "-f", "-t", repo_theme_dir], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for dest_root in [os.path.expanduser("~/.local/share/icons"), os.path.expanduser("~/.icons")]:
        dest_theme = os.path.join(dest_root, THEME_NAME)
        os.makedirs(dest_root, exist_ok=True)
        shutil.copytree(repo_theme_dir, dest_theme, dirs_exist_ok=True)
        if cache_tool:
            subprocess.run([cache_tool, "-f", "-t", dest_theme], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"✔ Generated {THEME_NAME} icon theme ({total} icons)")


if __name__ == "__main__":
    main()
