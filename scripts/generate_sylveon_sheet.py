import os
from PIL import Image, ImageDraw, ImageFont
import colorsys

ASSETS_DIR = r"C:\Users\DManh\Documents\Custom\assets"
OUTPUT_DIR = r"C:\Users\DManh\Documents\Custom\cursors\sylveon_custom"
ART_DIR = r"C:\Users\DManh\.gemini\antigravity\brain\8cd645f9-89dc-4864-bb28-c90e9cd298c2"

def recolor_ribbon_pixel(r, g, b, a):
    if a < 25:
        return (0, 0, 0, 0)
    
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    deg = h * 360.0
    
    # 1. Outline (Dark lines) -> Anime wine-red outline (#77080D / #801A24)
    if v < 0.45 or (s < 0.4 and v < 0.58 and (r < 140 and g < 110 and b < 105)):
        lum = (0.299*r + 0.587*g + 0.114*b) / 255.0
        nr = int(min(255, 115 + lum * 65))
        ng = int(min(255, 15 + lum * 45))
        nb = int(min(255, 25 + lum * 50))
        return (nr, ng, nb, a)
        
    # 2. Pink (Bow wings & tail pink band) -> Soft pastel coral pink (#FA8F9F)
    if (deg >= 330 or deg <= 20) and s > 0.18:
        new_h = 351.0 / 360.0
        new_s = 0.42
        new_v = 0.98
        nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
        return (int(nr*255), int(ng*255), int(nb*255), a)
        
    # 3. Blue / Cyan (Tail stripes) -> Match the sheet's pastel sky-blue (#75BAE4 / #A0DAF6)
    if 180 <= deg <= 245 and s > 0.18:
        if v < 0.82: 
            # Soft pastel sky-blue for the tail tip: #75BAE4
            new_h = 203.0 / 360.0
            new_s = 0.48
            new_v = 0.90
            nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
            return (int(nr*255), int(ng*255), int(nb*255), a)
        else: 
            # Baby cyan band: #A0DAF6
            new_h = 201.0 / 360.0
            new_s = 0.35
            new_v = 0.96
            nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
            return (int(nr*255), int(ng*255), int(nb*255), a)
            
    # 4. White / Shading on White Ribbon -> Soft pearl white & pastel pink shadow
    if s < 0.22:
        if v > 0.92:
            return (255, 248, 252, a)
        else:
            lum = v
            nr = int(min(255, 235 + lum * 18))
            ng = int(min(255, 195 + lum * 45))
            nb = int(min(255, 210 + lum * 38))
            return (nr, ng, nb, a)
            
    return (r, g, b, a)

# 1. Colors & Fonts
C_BG = (253, 246, 250, 255)
C_CARD_BG = (255, 255, 255, 255)
C_BORDER = (244, 185, 206, 255)
C_BORDER_INNER = (252, 230, 238, 255)
C_HEADER_TITLE = (117, 9, 15, 255)      # Wine red (#75090F)
C_HEADER_SUB = (156, 85, 105, 255)
C_PILL_BG = (255, 241, 246, 255)
C_PILL_BORDER = (244, 175, 198, 255)
C_PILL_TEXT = (117, 9, 15, 255)
C_DOT = (244, 145, 175, 255)

font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 36)
font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 17)
font_pill = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)

W, H = 1600, 1080
sheet = Image.new('RGBA', (W, H), C_BG)
draw = ImageDraw.Draw(sheet)

# Outer Card Frame
draw.rounded_rectangle([25, 25, W-25, H-25], radius=24, fill=C_CARD_BG, outline=C_BORDER, width=3)
draw.rounded_rectangle([32, 32, W-32, H-32], radius=18, fill=None, outline=C_BORDER_INNER, width=1)

# Header with Bow Accents
title_text = "SYLVEON CURSOR SCHEME"
title_bbox = font_title.getbbox(title_text)
tw = title_bbox[2] - title_bbox[0]
draw.text((W // 2, 60), title_text, fill=C_HEADER_TITLE, font=font_title, anchor="mm")

# Draw cute decorative bow sprites on left and right of title
bow_img = Image.open(os.path.join(ASSETS_DIR, "sheet_link.png")).convert('RGBA')
bow_mini = bow_img.resize((36, 36), Image.Resampling.LANCZOS)
sheet.paste(bow_mini, (W // 2 - tw // 2 - 50, 42), bow_mini)
sheet.paste(bow_mini.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 + tw // 2 + 14, 42), bow_mini.transpose(Image.FLIP_LEFT_RIGHT))

draw.text((W // 2, 98), "Dedicated to Serena & Sylveon • Complete 14-Cursor Windows Pack (Pastel Edition)", fill=C_HEADER_SUB, font=font_sub, anchor="mm")

# Header Divider Line with Cute Dots
draw.line([(80, 125), (W - 80, 125)], fill=C_BORDER_INNER, width=2)
draw.circle((W // 2, 125), radius=5, fill=C_BORDER)
draw.circle((W // 2 - 30, 125), radius=3, fill=C_BORDER)
draw.circle((W // 2 + 30, 125), radius=3, fill=C_BORDER)

def draw_pill(x_center, y_center, text):
    bbox = font_pill.getbbox(text)
    pw = (bbox[2] - bbox[0]) + 28
    ph = (bbox[3] - bbox[1]) + 14
    x0 = x_center - pw // 2
    y0 = y_center - ph // 2
    draw.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=ph//2, fill=C_PILL_BG, outline=C_PILL_BORDER, width=2)
    draw.text((x_center, y_center - 1), text, fill=C_PILL_TEXT, font=font_pill, anchor="mm")

def place_sprite(im_or_path, x_center, y_center, max_w, max_h):
    if isinstance(im_or_path, str):
        if not os.path.exists(im_or_path):
            print(f"Missing sprite: {im_or_path}")
            return
        im = Image.open(im_or_path).convert('RGBA')
    else:
        im = im_or_path
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    scale = min(max_w / im.width, max_h / im.height, 1.3)
    nw = int(im.width * scale)
    nh = int(im.height * scale)
    res = im.resize((nw, nh), Image.Resampling.LANCZOS)
    sheet.paste(res, (x_center - nw // 2, y_center - nh // 2), res)

# ==============================================================================
# ROW 1 (5 items): Normal, Help, Working in Background, Precision, Text
# ==============================================================================
row1_items = [
    ("sheet_arrow.png", "Normal Select", 170),
    ("sheet_help.png", "Help Select", 470),
    ("sheet_busy.png", "Working in Background", 780),
    ("sheet_precision.png", "Precision Select", 1100),
    ("sheet_text.png", "Text Select", 1410),
]

for fname, label, xc in row1_items:
    p = os.path.join(ASSETS_DIR, fname)
    max_h = 135 if fname != "sheet_text.png" else 110
    place_sprite(p, xc, 225, 150, max_h)
    draw_pill(xc, 335, label)

draw.line([(80, 380), (W - 80, 380)], fill=(253, 238, 243), width=1)

# ==============================================================================
# ROW 2 (6 items): Link, Unavailable, Vertical, Horizontal, Diagonal 1, Diagonal 2
# ==============================================================================
row2_items = [
    ("sheet_link.png", "Link Select", 155),
    ("sheet_unavailable.png", "Unavailable", 405),
    ("sheet_vertical_resize.png", "Vertical Resize", 650),
    ("sheet_horizontal_resize.png", "Horizontal Resize", 900),
    ("sheet_diagonal_resize1.png", "Diagonal Resize 1", 1155),
    ("sheet_diagonal_resize2.png", "Diagonal Resize 2", 1415),
]

for fname, label, xc in row2_items:
    p = os.path.join(ASSETS_DIR, fname)
    place_sprite(p, xc, 485, 140, 130)
    draw_pill(xc, 595, label)

draw.line([(80, 645), (W - 80, 645)], fill=(253, 238, 243), width=1)

# ==============================================================================
# ROW 3: Move, Alternate Select, and Wait (Animated) with 4 Clean Keyframes!
# ==============================================================================
place_sprite(os.path.join(ASSETS_DIR, "sheet_move.png"), 170, 755, 150, 135)
draw_pill(170, 875, "Move")

place_sprite(os.path.join(ASSETS_DIR, "sheet_alternate.png"), 430, 755, 150, 135)
draw_pill(430, 875, "Alternate Select")

# Wait (Animated) Box Card on the Right (x: 590 .. 1540)
draw.rounded_rectangle([590, 680, W - 60, 925], radius=20, fill=(255, 249, 252), outline=(248, 215, 226), width=2)

# Load clean keyframes directly from original user gif and recolor them individually!
raw_gif = Image.open(os.path.join(ASSETS_DIR, "user_zip", "preview_sylveon_ribbon.gif"))
wait_frames = [0, 6, 12, 18]
x_wait = [710, 950, 1190, 1420]

for idx, f_idx in enumerate(wait_frames):
    raw_gif.seek(f_idx)
    raw_frame = raw_gif.convert('RGBA')
    # Recolor clean individual frame
    recolored_frame = Image.new('RGBA', raw_frame.size)
    for y in range(raw_frame.height):
        for x in range(raw_frame.width):
            recolored_frame.putpixel((x, y), recolor_ribbon_pixel(*raw_frame.getpixel((x, y))))
            
    place_sprite(recolored_frame, x_wait[idx], 770, 150, 140)
    
    # Draw connecting dots '...' between frames
    if idx < len(wait_frames) - 1:
        dot_xc = (x_wait[idx] + x_wait[idx+1]) // 2
        for offset in [-12, 0, 12]:
            draw.circle((dot_xc + offset, 770), radius=3, fill=C_DOT)

draw_pill((590 + W - 60) // 2, 885, "Wait (Animated)")

# Footer Note with bullet points
draw.text((W // 2, 1010), "• 100% Native Win32 Custom Scheme • Pixel-Perfect Hotspots • Zero System Overhead •", fill=C_HEADER_SUB, font=font_sub, anchor="mm")

# Save outputs
out_asset = os.path.join(ASSETS_DIR, "sylveon_concept_sheet_complete.png")
out_cursor = os.path.join(OUTPUT_DIR, "sylveon_concept_sheet_complete.png")
out_art = os.path.join(ART_DIR, "sylveon_concept_sheet_complete.png")

sheet.save(out_asset)
sheet.save(out_cursor)
sheet.save(out_art)

print(f"Master Concept Sheet exported successfully to:\n  - {out_asset}\n  - {out_cursor}\n  - {out_art}")

