#!/usr/bin/env python3
"""
generate_theme.py — Sequential Stage Light Boot Progress Theme.
Generates 45 progressive frames tuned for a graceful ~6.0s theatrical stage warm-up.
Auxiliary spotlights spaced apart in a wide stage arc with proper alpha compositing.
"""

import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = SCRIPT_DIR
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

# Serena Wine Palette
BG_COLOR = (12, 6, 8, 255)         # Deepest stage wine black
FLOOR_LINE_COL = (42, 26, 30, 95)  # Stage floor boundary line
FLOOR_Y = int(H * 0.74)             # Stage floor horizon

# 6 Auxiliary spotlights forming a wide, spaced-out theatrical arc on the stage floor
AUX_LIGHTS = [
    # 1. Far Left
    {"apex": (120, -35),  "target": (400, FLOOR_Y + 28), "top_w": 20, "bot_w": 115, "color": (230, 150, 175), "pool_r": (115, 32)},
    # 2. Mid Left Back
    {"apex": (380, -40),  "target": (620, FLOOR_Y - 6),  "top_w": 22, "bot_w": 120, "color": (235, 170, 190), "pool_r": (120, 34)},
    # 3. Inner Left Back
    {"apex": (680, -45),  "target": (820, FLOOR_Y - 24), "top_w": 24, "bot_w": 125, "color": (240, 190, 205), "pool_r": (125, 36)},
    # 4. Inner Right Back
    {"apex": (1240, -45), "target": (1100, FLOOR_Y - 24), "top_w": 24, "bot_w": 125, "color": (240, 190, 205), "pool_r": (125, 36)},
    # 5. Mid Right Back
    {"apex": (1540, -40), "target": (1300, FLOOR_Y - 6),  "top_w": 22, "bot_w": 120, "color": (235, 170, 190), "pool_r": (120, 34)},
    # 6. Far Right
    {"apex": (1800, -35), "target": (1520, FLOOR_Y + 28), "top_w": 20, "bot_w": 115, "color": (230, 150, 175), "pool_r": (115, 32)},
]

# The Hero Center Spotlight (Final climax light)
MAIN_LIGHT = {
    "apex": (960, -45),
    "target": (960, FLOOR_Y + 44),
    "top_w": 40,
    "bot_w": 330,
    "color": (255, 245, 248),
    "pool_r": (330, 92),
}

# Ambient stage dust particles
random.seed(2026)
NUM_PARTICLES = 50
PARTICLES = []
for _ in range(NUM_PARTICLES):
    px = random.uniform(300, 1620)
    ny = random.uniform(0.1, 0.95)
    size = random.uniform(1.0, 2.4)
    speed_y = random.uniform(-0.1, -0.03)
    base_alpha = random.uniform(0.3, 0.7)
    phase = random.uniform(0, math.pi * 2)
    PARTICLES.append({
        'px': px, 'ny': ny, 'size': size, 'speed_y': speed_y, 'base_alpha': base_alpha, 'phase': phase
    })

def render_frame_for_progress(progress):
    """
    Renders frame for progress [0.0 to 1.0].
    Evenly paced for 6 auxiliary lights + main center spotlight.
    Each light is composited independently with alpha_composite to prevent overlap clipping.
    """
    img = Image.new("RGBA", (W, H), BG_COLOR)

    # 1. Stage Floor Horizon & Ambient Base
    ambient = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_amb = ImageDraw.Draw(ambient)
    d_amb.line([(0, FLOOR_Y), (W, FLOOR_Y)], fill=FLOOR_LINE_COL, width=1)
    amb_alpha = int(15 + 25 * progress)
    d_amb.rectangle([0, FLOOR_Y, W, H], fill=(24, 12, 16, amb_alpha))
    ambient = ambient.filter(ImageFilter.GaussianBlur(radius=30))
    img = Image.alpha_composite(img, ambient)

    # 6 Aux lights turn on progressively
    aux_intensities = []
    for i in range(6):
        start_p = 0.04 + i * 0.12
        end_p   = start_p + 0.11
        if progress < start_p:
            intensity = 0.0
        elif progress >= end_p:
            intensity = 1.0
        else:
            t = (progress - start_p) / (end_p - start_p)
            intensity = t * t * (3 - 2 * t)
        aux_intensities.append(intensity)

    # Main light turns on from 0.76 to 0.94
    main_start = 0.76
    main_end   = 0.94
    if progress < main_start:
        main_intensity = 0.0
    elif progress >= main_end:
        main_intensity = 1.0
    else:
        mt = (progress - main_start) / (main_end - main_start)
        main_intensity = mt * mt * (3 - 2 * mt)

    # --- 2. Draw Active Volumetric Cones (Composited individually) ---
    cones = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    for i, L in enumerate(AUX_LIGHTS):
        a_int = aux_intensities[i]
        if a_int <= 0.01:
            continue

        ax, ay = L["apex"]
        tx, ty = L["target"]
        tw, bw = L["top_w"], L["bot_w"]
        col = L["color"]

        cone_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d_cone = ImageDraw.Draw(cone_layer)

        poly_halo = [(ax - tw - 12, ay), (ax + tw + 12, ay), (tx + bw + 20, ty), (tx - bw - 20, ty)]
        d_cone.polygon(poly_halo, fill=(255, 42, 85, int(16 * a_int)))

        poly_mid = [(ax - tw, ay), (ax + tw, ay), (tx + bw, ty), (tx - bw, ty)]
        d_cone.polygon(poly_mid, fill=(*col, int(38 * a_int)))

        poly_core = [(ax - tw * 0.35, ay), (ax + tw * 0.35, ay), (tx + bw * 0.35, ty), (tx - bw * 0.35, ty)]
        d_cone.polygon(poly_core, fill=(255, 252, 254, int(60 * a_int)))

        cones = Image.alpha_composite(cones, cone_layer)

    # Render Main Spotlight if active
    if main_intensity > 0.01:
        ax, ay = MAIN_LIGHT["apex"]
        tx, ty = MAIN_LIGHT["target"]
        tw, bw = MAIN_LIGHT["top_w"], MAIN_LIGHT["bot_w"]
        col = MAIN_LIGHT["color"]

        main_cone_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d_cone = ImageDraw.Draw(main_cone_layer)

        poly_halo = [(ax - tw - 16, ay), (ax + tw + 16, ay), (tx + bw + 26, ty), (tx - bw - 26, ty)]
        d_cone.polygon(poly_halo, fill=(255, 42, 85, int(22 * main_intensity)))

        poly_mid = [(ax - tw, ay), (ax + tw, ay), (tx + bw, ty), (tx - bw, ty)]
        d_cone.polygon(poly_mid, fill=(*col, int(48 * main_intensity)))

        poly_core = [(ax - tw * 0.35, ay), (ax + tw * 0.35, ay), (tx + bw * 0.35, ty), (tx - bw * 0.35, ty)]
        d_cone.polygon(poly_core, fill=(255, 255, 255, int(85 * main_intensity)))

        cones = Image.alpha_composite(cones, main_cone_layer)

    cones = cones.filter(ImageFilter.GaussianBlur(radius=32))
    img = Image.alpha_composite(img, cones)

    # --- 3. Draw Floor Oval Pools of Light (Composited individually) ---
    pools = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    for i, L in enumerate(AUX_LIGHTS):
        a_int = aux_intensities[i]
        if a_int <= 0.01:
            continue

        tx, ty = L["target"]
        prx, pry = L["pool_r"]
        col = L["color"]

        pool_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d_pools = ImageDraw.Draw(pool_layer)

        layers = [
            (1.2, int(15 * a_int)),
            (1.0, int(30 * a_int)),
            (0.6, int(55 * a_int)),
            (0.25, int(95 * a_int)),
        ]
        for scale, step_a in layers:
            rx = int(prx * scale)
            ry = int(pry * scale)
            d_pools.ellipse([tx - rx, ty - ry, tx + rx, ty + ry], fill=(*col, step_a))

        pools = Image.alpha_composite(pools, pool_layer)

    if main_intensity > 0.01:
        tx, ty = MAIN_LIGHT["target"]
        prx, pry = MAIN_LIGHT["pool_r"]
        col = MAIN_LIGHT["color"]

        main_pool_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d_pools = ImageDraw.Draw(main_pool_layer)

        layers = [
            (1.25, int(20 * main_intensity)),
            (1.00, int(42 * main_intensity)),
            (0.70, int(72 * main_intensity)),
            (0.40, int(115 * main_intensity)),
            (0.18, int(160 * main_intensity)),
        ]
        for scale, step_a in layers:
            rx = int(prx * scale)
            ry = int(pry * scale)
            d_pools.ellipse([tx - rx, ty - ry, tx + rx, ty + ry], fill=(*col, step_a))

        pools = Image.alpha_composite(pools, main_pool_layer)

    pools = pools.filter(ImageFilter.GaussianBlur(radius=24))
    img = Image.alpha_composite(img, pools)

    # --- 4. Floating Stage Dust Motes ---
    motes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_motes = ImageDraw.Draw(motes)

    apex_y = -35
    for p in PARTICLES:
        curr_ny = (p['ny'] + p['speed_y'] * progress * 3) % 1.0
        py = apex_y + (FLOOR_Y + 40 - apex_y) * curr_ny
        px = p['px'] + math.sin(curr_ny * 6 + p['phase']) * 15

        twinkle = 0.5 + 0.5 * math.sin(progress * 10 * math.pi + p['phase'])
        alpha = int(255 * p['base_alpha'] * twinkle * (0.2 + 0.8 * progress))
        r = p['size']

        d_motes.ellipse([px - r, py - r, px + r, py + r], fill=(255, 245, 250, alpha))

    motes = motes.filter(ImageFilter.GaussianBlur(radius=1.2))
    img = Image.alpha_composite(img, motes)

    return img

def main():
    print("Generating 45 Paced Stage Light Progress Frames...")

    # Static background
    bg_static = Image.new("RGBA", (W, H), BG_COLOR)
    bg_static.save(os.path.join(OUTPUT_DIR, "background.png"))
    print("  ✔ Generated background.png")

    # Clean existing frame files
    for old_f in os.listdir(FRAMES_DIR):
        if old_f.endswith(".png"):
            try:
                os.remove(os.path.join(FRAMES_DIR, old_f))
            except OSError:
                pass

    NUM_FRAMES = 45
    gif_frames = []

    print(f"  🎨 Rendering {NUM_FRAMES} progress frames (paced for ~6.0s boot)...")
    for f in range(NUM_FRAMES):
        p = f / float(NUM_FRAMES - 1)
        frame = render_frame_for_progress(p)

        frame.save(os.path.join(FRAMES_DIR, f"frame-{f}.png"), "PNG")

        preview_frame = frame.resize((960, 540), Image.Resampling.LANCZOS)
        gif_frames.append(preview_frame.convert("RGB"))

    # Save animated GIF preview (with hold on final frame)
    final_preview = gif_frames + [gif_frames[-1]] * 24

    gif_path = os.path.join(OUTPUT_DIR, "preview.gif")
    final_preview[0].save(
        gif_path,
        save_all=True,
        append_images=final_preview[1:],
        duration=70, # ~14 fps (paced for ~6.5s)
        loop=0
    )
    print(f"  ✔ Generated animated preview: {gif_path}")
    print("\n🎉 45-frame optimized stage light theme generated successfully!")

if __name__ == "__main__":
    main()
