import os
import math
import struct
from PIL import Image, ImageDraw, ImageEnhance
import colorsys

OUTPUT_DIR = r"C:\Users\DManh\Documents\Custom\cursors\sylveon_custom"
ASSETS_DIR = r"C:\Users\DManh\Documents\Custom\assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_cur_binary(images_with_hotspots):
    """
    Creates a valid Windows .cur file with multiple resolutions (e.g. 32x32 and 48x48).
    images_with_hotspots: list of tuples (PIL Image RGBA, (hot_x, hot_y))
    """
    n_images = len(images_with_hotspots)
    icondir = struct.pack('<HHH', 0, 2, n_images)
    
    entries = []
    image_datas = []
    current_offset = 6 + n_images * 16
    
    for img, (hot_x, hot_y) in images_with_hotspots:
        w, h = img.size
        biSize = 40
        biWidth = w
        biHeight = h * 2  # XOR mask + AND mask
        biPlanes = 1
        biBitCount = 32
        biCompression = 0
        biSizeImage = w * h * 4
        dib_header = struct.pack('<IIIHHIIIIII', biSize, biWidth, biHeight, biPlanes, biBitCount, biCompression, biSizeImage, 0, 0, 0, 0)
        
        # Pixel data: bottom-to-top, BGRA
        pixels = bytearray()
        for y in reversed(range(h)):
            for x in range(w):
                r, g, b, a = img.getpixel((x, y))
                pixels.extend([b, g, r, a])
                
        # AND mask: 1 bit per pixel, padded to 32-bit (4-byte) boundary per row
        row_bytes = (w + 31) // 32 * 4
        and_mask = bytearray(row_bytes * h)
        for y in reversed(range(h)):
            row_idx = (h - 1 - y) * row_bytes
            for x in range(w):
                if img.getpixel((x, y))[3] == 0:
                    and_mask[row_idx + (x // 8)] |= (1 << (7 - (x % 8)))
                    
        image_data = dib_header + bytes(pixels) + bytes(and_mask)
        entry = struct.pack('<BBBBHHII', 
                            w if w < 256 else 0, 
                            h if h < 256 else 0, 
                            0, 0, 
                            hot_x, hot_y, 
                            len(image_data), 
                            current_offset)
        entries.append(entry)
        image_datas.append(image_data)
        current_offset += len(image_data)
        
    return icondir + b''.join(entries) + b''.join(image_datas)

def create_ani_binary(frames_input, jif_rate=4, hot=(16, 16)):
    """
    Creates a valid Windows RIFF ACON (.ani) file.
    frames_input: list of PIL Image RGBA or list of pre-packed cur_bytes
    jif_rate: frames display time in jiffies (1 jiffy = 1/60 sec, jif_rate=4 -> ~15 FPS)
    """
    icon_chunks = []
    is_bytes = isinstance(frames_input[0], (bytes, bytearray))
    w = 0 if is_bytes else frames_input[0].width
    h = 0 if is_bytes else frames_input[0].height
    
    for item in frames_input:
        cur_bytes = item if is_bytes else create_cur_binary([(item, hot)])
        pad = b'\x00' if len(cur_bytes) % 2 != 0 else b''
        chunk = b'icon' + struct.pack('<I', len(cur_bytes)) + cur_bytes + pad
        icon_chunks.append(chunk)
        
    fram_data = b'fram' + b''.join(icon_chunks)
    list_chunk = b'LIST' + struct.pack('<I', len(fram_data)) + fram_data
    
    n_frames = len(frames_input)
    anih_data = struct.pack('<IIIIIIIII', 36, n_frames, n_frames, w, h, 0 if is_bytes else 32, 1, jif_rate, 1)
    anih_chunk = b'anih' + struct.pack('<I', len(anih_data)) + anih_data
    
    riff_data = b'ACON' + anih_chunk + list_chunk
    riff_chunk = b'RIFF' + struct.pack('<I', len(riff_data)) + riff_data
    return riff_chunk

def make_cursor_from_sprite(sprite_path, out_cur_name, hot_type="ear", preview_prefix=None, target_size_32=None, target_size_48=None):
    """
    Creates 32x32 and 48x48 cursor from sprite image.
    hot_type:
      - 'ear': left ear tip (1, 1) on 32, (2, 2) on 48
      - 'center': center of sprite (16, 16) on 32, (24, 24) on 48
      - 'arrow_center': right-side arrow center
    """
    im = Image.open(sprite_path)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
        
    aspect = im.width / im.height
    max_dim_32 = target_size_32 if target_size_32 is not None else 30
    max_dim_48 = target_size_48 if target_size_48 is not None else 44
    
    # --- 32x32 size ---
    if aspect <= 1.0:
        h32 = max_dim_32
        w32 = max(1, int(h32 * aspect))
    else:
        w32 = max_dim_32
        h32 = max(1, int(w32 / aspect))
        
    res32 = im.resize((w32, h32), Image.Resampling.LANCZOS)
    res32 = ImageEnhance.Sharpness(res32).enhance(1.3)
    c32 = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    
    if hot_type == 'ear':
        c32.paste(res32, (1, 1), res32)
        hot32 = (1, 1)
    elif hot_type == 'center':
        ox = (32 - w32) // 2
        oy = (32 - h32) // 2
        c32.paste(res32, (ox, oy), res32)
        hot32 = (16, 16)
    else: # arrow/other
        c32.paste(res32, (1, 1), res32)
        hot32 = (int(w32 * 0.75), int(h32 * 0.5))
        
    # --- 48x48 size ---
    if aspect <= 1.0:
        h48 = max_dim_48
        w48 = max(1, int(h48 * aspect))
    else:
        w48 = max_dim_48
        h48 = max(1, int(w48 / aspect))
        
    res48 = im.resize((w48, h48), Image.Resampling.LANCZOS)
    res48 = ImageEnhance.Sharpness(res48).enhance(1.3)
    c48 = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    
    if hot_type == 'ear':
        c48.paste(res48, (2, 2), res48)
        hot48 = (2, 2)
    elif hot_type == 'center':
        ox = (48 - w48) // 2
        oy = (48 - h48) // 2
        c48.paste(res48, (ox, oy), res48)
        hot48 = (24, 24)
    else:
        c48.paste(res48, (2, 2), res48)
        hot48 = (int(w48 * 0.75), int(h48 * 0.5))
        
    cur_data = create_cur_binary([(c32, hot32), (c48, hot48)])
    out_path = os.path.join(OUTPUT_DIR, out_cur_name)
    with open(out_path, "wb") as f:
        f.write(cur_data)
        
    if preview_prefix:
        c32.save(os.path.join(OUTPUT_DIR, f"{preview_prefix}32.png"))
        c48.save(os.path.join(OUTPUT_DIR, f"{preview_prefix}48.png"))
        
    print(f"Created {out_cur_name} ({len(cur_data)} bytes, hotspots: {hot32}, {hot48})")

def extract_clean_sheet_sprites():
    sheet_path = r"C:\Users\DManh\.gemini\antigravity\brain\8cd645f9-89dc-4864-bb28-c90e9cd298c2\.user_uploaded\media_1791676770284_cb8fa722.png"
    if not os.path.exists(sheet_path):
        print(f"Warning: sheet file not found at {sheet_path}")
        return
        
    sheet = Image.open(sheet_path).convert('RGBA')
    # Exact bounding boxes strictly avoiding label pills:
    # Row 1 pills: y: 243..275 -> Row 1 sprites safely y: 60..236
    # Row 2 pills: y: 427..465 -> Row 2 sprites safely y: 285..418
    # Row 3 pills: y: 619..655 -> Row 3 sprites safely y: 475..615
    sprites_def = {
        'arrow': (60, 60, 180, 236),
        'help': (270, 60, 410, 236),
        'text': (465, 60, 510, 236),
        'busy': (645, 60, 775, 236),
        'precision': (855, 60, 980, 236),
        'link': (55, 285, 135, 418),
        'unavailable': (220, 285, 330, 418),
        'vertical_resize': (380, 285, 495, 418),
        'horizontal_resize': (545, 285, 665, 418),
        'diagonal_resize1': (705, 285, 825, 418),
        'diagonal_resize2': (880, 285, 985, 418),
        'move': (75, 475, 185, 615),
        'alternate': (235, 475, 355, 615),
    }
    
    for name, (x1, y1, x2, y2) in sprites_def.items():
        crop = sheet.crop((x1, y1, x2, y2))
        alpha = crop.split()[-1]
        mask = alpha.point(lambda p: 255 if p > 30 else 0)
        bbox = mask.getbbox()
        if bbox:
            crop_tight = crop.crop(bbox)
        else:
            crop_tight = crop
        save_path = os.path.join(ASSETS_DIR, f"sheet_{name}.png")
        crop_tight.save(save_path)
        print(f"Extracted clean sprite {name}: size {crop_tight.size} -> {save_path}")

def build_sheet_cursors():
    extract_clean_sheet_sprites()
    print("Building all cursors from user's concept sheet (100% clean, ZERO text/label pills)...")
    # 1. Normal Select (Arrow)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_arrow.png"), "sylveon_arrow.cur", "ear", "sylveon_arrow_preview")
    # 2. Help Select
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_help.png"), "sylveon_help.cur", "ear")
    # 3. Text Select (IBeam) - Scaled down to standard 18px (32) and 26px (48) for comfortable text selection
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_text.png"), "sylveon_text.cur", "center", target_size_32=18, target_size_48=26)
    # 4. Busy Select
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_busy.png"), "sylveon_busy.cur", "ear")
    # 5. Precision Select (Crosshair)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_precision.png"), "sylveon_precision.cur", "center")
    # 6. Link Select (Hand)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_link.png"), "sylveon_link.cur", "ear", "sylveon_link_preview")
    # 7. Unavailable (No)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_unavailable.png"), "sylveon_unavailable.cur", "ear")
    # 8. Vertical Resize (SizeNS)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_vertical_resize.png"), "sylveon_vertical_resize.cur", "center")
    # 9. Horizontal Resize (SizeWE)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_horizontal_resize.png"), "sylveon_horizontal_resize.cur", "center")
    # 10. Diagonal Resize 1 (SizeNWSE)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_diagonal_resize1.png"), "sylveon_diagonal_resize1.cur", "center")
    # 11. Diagonal Resize 2 (SizeNESW)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_diagonal_resize2.png"), "sylveon_diagonal_resize2.cur", "center")
    # 12. Move (SizeAll)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_move.png"), "sylveon_move.cur", "center")
    # 13. Alternate Select (UpArrow)
    make_cursor_from_sprite(os.path.join(ASSETS_DIR, "sheet_alternate.png"), "sylveon_alternate.cur", "ear")

def build_handdrawn_exact_colored_sprite():
    """
    Renders the exact hand-drawn shape (oval ribbon ring with bow on right, 
    upper and lower ribbon loops, and 2 striped forked feeler tails on the left),
    maintaining the user's authentic hand-drawn geometry without forcing it into a circle.
    """
    W, H = 400, 300
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    C_WHITE = (255, 252, 255, 255)
    C_PINK = (246, 148, 172, 255)
    C_BLUE = (48, 72, 138, 255)
    C_CYAN = (110, 195, 235, 255)
    C_OUTLINE = (92, 42, 52, 255)

    # 1. Top Ribbon Body & Stripes
    top_white = [
        (240, 85), (200, 52), (150, 48), (110, 62), (80, 88), (72, 112),
        (88, 114), (94, 92), (120, 72), (160, 64), (200, 68), (238, 96)
    ]
    draw.polygon(top_white, fill=C_WHITE)

    top_pink = [
        (72, 112), (68, 126), (84, 128), (88, 114)
    ]
    draw.polygon(top_pink, fill=C_PINK)

    top_blue = [
        (68, 126), (65, 140), (80, 142), (84, 128)
    ]
    draw.polygon(top_blue, fill=C_BLUE)

    top_cyan = [
        (65, 140), (74, 162), (82, 148), (92, 154), (80, 142)
    ]
    draw.polygon(top_cyan, fill=C_CYAN)

    # 2. Bottom Ribbon Body & Stripes
    bot_white = [
        (265, 120), (278, 155), (262, 195), (225, 222), (180, 226), (145, 215), (125, 202),
        (138, 190), (155, 200), (185, 204), (218, 198), (242, 178), (252, 145), (248, 115)
    ]
    draw.polygon(bot_white, fill=C_WHITE)

    bot_pink = [
        (125, 202), (112, 192), (124, 180), (138, 190)
    ]
    draw.polygon(bot_pink, fill=C_PINK)

    bot_blue = [
        (112, 192), (102, 182), (114, 172), (124, 180)
    ]
    draw.polygon(bot_blue, fill=C_BLUE)

    bot_cyan = [
        (102, 182), (90, 174), (104, 166), (98, 154), (114, 172)
    ]
    draw.polygon(bot_cyan, fill=C_CYAN)

    # 3. Bow on Right
    bow_right = [
        (265, 82), (312, 68), (308, 92), (316, 115), (268, 108)
    ]
    draw.polygon(bow_right, fill=C_PINK)

    bow_left = [
        (248, 85), (228, 72), (230, 108), (250, 105)
    ]
    draw.polygon(bow_left, fill=C_PINK)

    knot = (246, 80, 268, 112)
    draw.rounded_rectangle(knot, radius=6, fill=C_WHITE)

    # 4. Outlines
    draw.line([(240, 85), (200, 52), (150, 48), (110, 62), (80, 88), (72, 112), (68, 126), (65, 140), (74, 162), (82, 148), (92, 154), (80, 142), (84, 128), (88, 114), (94, 92), (120, 72), (160, 64), (200, 68), (238, 96)], fill=C_OUTLINE, width=3)
    draw.line([(265, 120), (278, 155), (262, 195), (225, 222), (180, 226), (145, 215), (125, 202), (112, 192), (102, 182), (90, 174), (104, 166), (98, 154), (114, 172), (124, 180), (138, 190), (155, 200), (185, 204), (218, 198), (242, 178), (252, 145), (248, 115)], fill=C_OUTLINE, width=3)

    draw.polygon(bow_right, outline=C_OUTLINE, width=3)
    draw.polygon(bow_left, outline=C_OUTLINE, width=3)
    draw.rounded_rectangle(knot, radius=6, outline=C_OUTLINE, width=3)

    draw.line([(72, 112), (88, 114)], fill=C_OUTLINE, width=2)
    draw.line([(68, 126), (84, 128)], fill=C_OUTLINE, width=2)
    draw.line([(65, 140), (80, 142)], fill=C_OUTLINE, width=2)

    draw.line([(125, 202), (138, 190)], fill=C_OUTLINE, width=2)
    draw.line([(112, 192), (124, 180)], fill=C_OUTLINE, width=2)
    draw.line([(102, 182), (114, 172)], fill=C_OUTLINE, width=2)

    # Tight crop around the drawn shape
    bbox = im.getbbox()
    cropped = im.crop(bbox)
    
    # Place in square canvas centered at (diag/2, diag/2) for smooth 360 rotation
    max_d = max(cropped.width, cropped.height) + 20
    sq = Image.new('RGBA', (max_d, max_d), (0, 0, 0, 0))
    sq.paste(cropped, ((max_d - cropped.width) // 2, (max_d - cropped.height) // 2), cropped)
    
    master_path = os.path.join(ASSETS_DIR, "sylveon_handdrawn_colored_exact.png")
    sq.save(master_path)
    print(f"Saved handdrawn exact colored sprite: {master_path} (size {sq.size})")
    return sq

def recolor_ribbon_pixel(r, g, b, a):
    if a < 25:
        return (0, 0, 0, 0)
    
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    deg = h * 360.0
    
    # 1. Outline (Dark lines) -> Anime wine-red outline (#75090F)
    if v < 0.45 or (s < 0.4 and v < 0.58 and (r < 140 and g < 110 and b < 105)):
        lum = (0.299*r + 0.587*g + 0.114*b) / 255.0
        nr = int(min(255, 112 + lum * 65))
        ng = int(min(255, 15 + lum * 45))
        nb = int(min(255, 25 + lum * 50))
        return (nr, ng, nb, a)
        
    # 2. Pink (Bow wings & tail pink band) -> Sylveon coral pink (#FA8F9F)
    if (deg >= 330 or deg <= 20) and s > 0.18:
        new_h = 351.0 / 360.0
        new_s = min(1.0, s * 1.25 + 0.08)
        new_v = min(1.0, v * 1.05)
        nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
        return (int(nr*255), int(ng*255), int(nb*255), a)
        
    # 3. Blue / Cyan (Tail stripes) -> Match the sheet's pastel sky-blue (#74BAE3 / #82C1E4)
    if 180 <= deg <= 245 and s > 0.18:
        if v < 0.82:
            # Soft pastel sky-blue for the tail tip: #75BAE4 (RGB 117, 186, 228)
            new_h = 203.0 / 360.0
            new_s = 0.48
            new_v = 0.90
            nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
            return (int(nr*255), int(ng*255), int(nb*255), a)
        else:
            # Baby cyan band: #A0DAF6 (RGB 160, 218, 246)
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

def build_sylveon_wait():
    gif_path = os.path.join(ASSETS_DIR, "user_zip", "preview_sylveon_ribbon.gif")
    if not os.path.exists(gif_path):
        print(f"Warning: {gif_path} not found")
        return
        
    print("Building Sylveon Wait animated cursor with synchronized Sylveon palette...")
    gif = Image.open(gif_path)
    n_frames = gif.n_frames
    
    recolored_256 = []
    cur_frames = []
    
    for i in range(n_frames):
        gif.seek(i)
        im = gif.convert('RGBA')
        out = Image.new('RGBA', im.size)
        for y in range(im.height):
            for x in range(im.width):
                out.putpixel((x, y), recolor_ribbon_pixel(*im.getpixel((x, y))))
        recolored_256.append(out)
        
        f32 = out.resize((32, 32), Image.Resampling.LANCZOS)
        f32 = ImageEnhance.Sharpness(f32).enhance(1.25)
        
        f48 = out.resize((48, 48), Image.Resampling.LANCZOS)
        f48 = ImageEnhance.Sharpness(f48).enhance(1.25)
        
        cur_bytes = create_cur_binary([(f32, (16, 16)), (f48, (24, 24))])
        cur_frames.append(cur_bytes)
        
    # Save preview GIF
    gif_path = os.path.join(OUTPUT_DIR, "sylveon_wait_preview.gif")
    recolored_256[0].save(gif_path, save_all=True, append_images=recolored_256[1:], duration=60, loop=0)
    print(f"Saved preview GIF: {gif_path}")
    
    # Save ANI
    ani_data = create_ani_binary(cur_frames, jif_rate=4)
    out_path = os.path.join(OUTPUT_DIR, "sylveon_wait.ani")
    with open(out_path, "wb") as f:
        f.write(ani_data)
    print(f"Saved {out_path} ({len(ani_data)} bytes, {n_frames} frames)")

if __name__ == "__main__":
    build_sheet_cursors()
    build_sylveon_wait()
    print("ALL SYLVEON SHEET AND HANDDRAWN CURSORS BUILT SUCCESSFULLY!")
