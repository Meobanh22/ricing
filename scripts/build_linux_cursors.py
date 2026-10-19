#!/usr/bin/env python3
# ==============================================================================
# 🖱️ BUILD COMPLETE HYPRCURSOR + XCURSOR THEME FOR SYLVEON CUSTOM
# ==============================================================================
# Hyprland 0.56 yêu cầu chuẩn native Hyprcursor (.hlc + manifest.hl)
# Đồng thời tạo Xcursor (cursors/ + index.theme) để hỗ trợ toàn bộ GTK/XWayland
# ==============================================================================

import os
import shutil
import subprocess
from PIL import Image, ImageEnhance

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ASSETS_DIR = os.path.join(REPO_DIR, "assets")
OUTPUT_THEME_DIR = os.path.join(REPO_DIR, "cursors", "sylveon-custom")
CURSORS_DIR = os.path.join(OUTPUT_THEME_DIR, "cursors")
TMP_FRAMES_DIR = os.path.join(REPO_DIR, "cursors", ".tmp_frames")
TMP_HC_DIR = os.path.join(REPO_DIR, "cursors", ".tmp_hyprcursor")

os.makedirs(CURSORS_DIR, exist_ok=True)
os.makedirs(TMP_FRAMES_DIR, exist_ok=True)
if os.path.exists(TMP_HC_DIR):
    shutil.rmtree(TMP_HC_DIR)
os.makedirs(os.path.join(TMP_HC_DIR, "hyprcursors"), exist_ok=True)

# 1. Tạo index.theme cho Xcursor
INDEX_THEME = """[Icon Theme]
Name=sylveon-custom
Comment=🌸 Sylveon & Serena Custom Cursor Theme for Linux Wayland & X11
Inherits=core
"""
with open(os.path.join(OUTPUT_THEME_DIR, "index.theme"), "w") as f:
    f.write(INDEX_THEME)

# 2. Tạo manifest.hl cho Hyprcursor
MANIFEST_HL = """name = sylveon-custom
description = 🌸 Sylveon & Serena Custom Cursor Theme for Hyprland
version = 0.2
cursors_directory = hyprcursors
"""
with open(os.path.join(TMP_HC_DIR, "manifest.hl"), "w") as f:
    f.write(MANIFEST_HL)

def make_cursor(sprite_path, base_name, aliases, hot_type="ear"):
    im = Image.open(sprite_path)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)

    aspect = im.width / im.height
    sizes = [(24, 22), (32, 30), (48, 44)]
    xcursor_lines = []
    
    # Thư mục cho shape này trong hyprcursor
    shape_hc_dir = os.path.join(TMP_HC_DIR, "hyprcursors", base_name)
    os.makedirs(shape_hc_dir, exist_ok=True)
    
    hc_meta_lines = [
        "resize_algorithm = bilinear"
    ]

    for canvas_size, max_dim in sizes:
        if aspect <= 1.0:
            h = max_dim
            w = max(1, int(h * aspect))
        else:
            w = max_dim
            h = max(1, int(w / aspect))

        res = im.resize((w, h), Image.Resampling.LANCZOS)
        res = ImageEnhance.Sharpness(res).enhance(1.25)
        canvas = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))

        if hot_type == 'ear':
            canvas.paste(res, (1, 1), res)
            hot = (1, 1)
            rel_hot = (round(1.0 / canvas_size, 3), round(1.0 / canvas_size, 3))
        elif hot_type == 'center':
            ox = (canvas_size - w) // 2
            oy = (canvas_size - h) // 2
            canvas.paste(res, (ox, oy), res)
            hot = (canvas_size // 2, canvas_size // 2)
            rel_hot = (0.5, 0.5)
        else:
            canvas.paste(res, (1, 1), res)
            hot = (int(w * 0.75), int(h * 0.5))
            rel_hot = (round((w * 0.75) / canvas_size, 3), round((h * 0.5) / canvas_size, 3))

        png_name = f"{base_name}_{canvas_size}.png"
        png_path = os.path.join(TMP_FRAMES_DIR, png_name)
        canvas.save(png_path)
        
        # Copy vào shape_hc_dir cho hyprcursor
        canvas.save(os.path.join(shape_hc_dir, png_name))

        xcursor_lines.append(f"{canvas_size} {hot[0]} {hot[1]} {png_path}")
        hc_meta_lines.append(f"define_size = {canvas_size}, {png_name}")

    # Ghi cấu hình Xcursor
    cfg_path = os.path.join(TMP_FRAMES_DIR, f"{base_name}.cursor")
    with open(cfg_path, "w") as f:
        f.write("\n".join(xcursor_lines) + "\n")
    out_file = os.path.join(CURSORS_DIR, base_name)
    subprocess.run(["xcursorgen", cfg_path, out_file], check=True)

    # Symlink cho Xcursor
    for alias in aliases:
        alias_path = os.path.join(CURSORS_DIR, alias)
        if os.path.exists(alias_path) or os.path.islink(alias_path):
            os.remove(alias_path)
        os.symlink(base_name, alias_path)

    # Ghi meta.hl cho Hyprcursor
    hc_meta_lines.insert(1, f"hotspot_x = {rel_hot[0]}")
    hc_meta_lines.insert(2, f"hotspot_y = {rel_hot[1]}")
    for alias in aliases:
        hc_meta_lines.append(f"define_override = {alias}")

    with open(os.path.join(shape_hc_dir, "meta.hl"), "w") as f:
        f.write("\n".join(hc_meta_lines) + "\n")

def build_all():
    print("🌸 Đang biên dịch bộ con trỏ chuột Sylveon Custom (Chuẩn Hyprcursor + Xcursor)...")

    shapes = [
        ("sheet_arrow.png", "left_ptr", ["default", "arrow", "top_left_arrow"], "ear"),
        ("sheet_link.png", "pointer", ["hand1", "hand2", "pointing_hand", "link"], "ear"),
        ("sheet_text.png", "xterm", ["text", "ibeam"], "center"),
        ("sheet_busy.png", "left_ptr_watch", ["progress", "half-busy"], "ear"),
        ("sheet_help.png", "help", ["whats_this", "question_arrow"], "ear"),
        ("sheet_precision.png", "crosshair", ["cross", "tcross"], "center"),
        ("sheet_unavailable.png", "not-allowed", ["crossed_circle", "forbidden", "circle"], "ear"),
        ("sheet_move.png", "move", ["all-scroll", "fleur", "size_all"], "center"),
        ("sheet_vertical_resize.png", "v_double_arrow", ["ns-resize", "size_ver", "n-resize", "s-resize"], "center"),
        ("sheet_horizontal_resize.png", "h_double_arrow", ["ew-resize", "size_hor", "e-resize", "w-resize"], "center"),
        ("sheet_diagonal_resize1.png", "fd_double_arrow", ["nwse-resize", "size_fdiag"], "center"),
        ("sheet_diagonal_resize2.png", "bk_double_arrow", ["nesw-resize", "size_bdiag"], "center"),
    ]

    for asset_file, base_name, aliases, hot_type in shapes:
        asset_path = os.path.join(ASSETS_DIR, asset_file)
        if os.path.exists(asset_path):
            make_cursor(asset_path, base_name, aliases, hot_type)

    # Biên dịch Hyprcursor theme bằng hyprcursor-util
    hc_compile_out = os.path.join(REPO_DIR, "cursors", ".tmp_hc_out")
    if os.path.exists(hc_compile_out):
        shutil.rmtree(hc_compile_out)
    os.makedirs(hc_compile_out, exist_ok=True)

    print("  Đang đóng gói định dạng Hyprcursor (.hlc)...")
    res = subprocess.run(["hyprcursor-util", "--create", TMP_HC_DIR, "--output", hc_compile_out], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        theme_compiled = os.path.join(hc_compile_out, "theme_sylveon-custom")
        if os.path.exists(theme_compiled):
            # Copy manifest.hl và hyprcursors vào OUTPUT_THEME_DIR
            manifest_src = os.path.join(theme_compiled, "manifest.hl")
            hyprcursors_src = os.path.join(theme_compiled, "hyprcursors")
            if os.path.exists(manifest_src):
                shutil.copy(manifest_src, OUTPUT_THEME_DIR)
            if os.path.exists(hyprcursors_src):
                dest_hc = os.path.join(OUTPUT_THEME_DIR, "hyprcursors")
                if os.path.exists(dest_hc):
                    shutil.rmtree(dest_hc)
                shutil.copytree(hyprcursors_src, dest_hc)
            print("  ✔ Đã biên dịch xong thành phần Hyprcursor (.hlc)!")
    # Dọn dẹp thư mục tạm
    for tmp_d in [TMP_FRAMES_DIR, TMP_HC_DIR, hc_compile_out]:
        if os.path.exists(tmp_d):
            shutil.rmtree(tmp_d)

    print(f"✔ HOÀN TẤT! Bộ cursor Sylveon đa nền tảng (Hyprcursor + Xcursor) sẵn sàng tại:\n  {OUTPUT_THEME_DIR}")

if __name__ == "__main__":
    build_all()

