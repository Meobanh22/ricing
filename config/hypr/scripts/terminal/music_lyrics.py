#!/usr/bin/env python3
# music_lyrics.py — Smooth, outlined lyrics on a transparent Kitty canvas.

import base64
import fcntl
import io
import math
import os
import struct
import sys
import termios
import time
import unicodedata
from functools import lru_cache

from music_layout import visualizer_regions

import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo
try:
    from PIL import Image
except ImportError:
    Image = None

TRANSITION_SECONDS = 0.32


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def pixel_size(cols, rows):
    try:
        data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, bytes(8))
        _, _, width, height = struct.unpack('HHHH', data)
        if width and height:
            return width / cols, height / rows
    except (OSError, ValueError, io.UnsupportedOperation):
        pass
    return 9.0, 20.0


def image_command(data, image_id, cols, rows, pixel_dimensions=None, temporary_path=None):
    if temporary_path is not None:
        data = os.fsencode(temporary_path)
    encoded = base64.b64encode(data).decode('ascii')
    image_format = 'f=100,'
    if pixel_dimensions is not None:
        width, height = pixel_dimensions
        transport = 't=t,' if temporary_path is not None else 'o=z,'
        image_format = f'f=32,{transport}s={width},v={height},'
    chunks = []
    for offset in range(0, len(encoded), 4096):
        chunk = encoded[offset:offset + 4096]
        more = int(offset + 4096 < len(encoded))
        header = f'a=T,{image_format}i={image_id},p=1,c={cols},r={rows},C=1,z=1,q=2,' if offset == 0 else ''
        chunks.append(f'\x1b_G{header}m={more};{chunk}\x1b\\')
    return ''.join(chunks)


class LyricsCanvas:
    def __init__(self, palette):
        self.palette = palette
        self.image_id = ((os.getpid() & 0xFFFFFF) << 4) | 3
        self.shown = False
        self.track_key = None
        self.target = None
        self.origin = 0.0
        self.started_at = 0.0
        self.last_scene = None
        self.layout_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8))
        options = cairo.FontOptions()
        options.set_antialias(cairo.ANTIALIAS_GRAY)
        options.set_hint_style(cairo.HINT_STYLE_NONE)
        options.set_hint_metrics(cairo.HINT_METRICS_OFF)
        self.layout_context.set_font_options(options)

    def scroll_at(self, now):
        if self.target is None:
            return 0.0
        progress = smoothstep((now - self.started_at) / TRANSITION_SECONDS)
        return self.origin + (self.target - self.origin) * progress

    def set_target(self, index, track_key, now):
        if self.target is None or track_key != self.track_key or abs(index - self.target) > 1:
            self.origin = float(index)
            self.target = index
            self.started_at = now - TRANSITION_SECONDS
            self.track_key = track_key
        elif index != self.target:
            self.origin = self.scroll_at(now)
            self.target = index
            self.started_at = now
        return self.scroll_at(now)

    @lru_cache(maxsize=64)
    def layout(self, text, width, font_pixels):
        layout = PangoCairo.create_layout(self.layout_context)
        font = Pango.FontDescription()
        font.set_family('JetBrainsMono Nerd Font')
        font.set_weight(Pango.Weight.BOLD)
        font.set_absolute_size(font_pixels * Pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(text, -1)
        layout.set_width(width * Pango.SCALE)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        return layout

    def color(self, context, left, right, amount, alpha):
        colors = []
        for color in (self.palette[left], self.palette[right]):
            colors.append(tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)))
        context.set_source_rgba(*(a + (b - a) * amount for a, b in zip(*colors)), alpha)

    def draw_line(self, context, text, focus, center_y, width, height, font_pixels):
        if not text:
            return
        layout = self.layout(text, width - 32, font_pixels)
        _, text_height = layout.get_pixel_size()
        # Keep line breaks fixed while the preview grows into the active line.
        scale = 0.56 + 0.44 * focus
        scale = min(scale, height * 0.45 / max(1, text_height))
        actual_height = text_height * scale
        y = center_y - actual_height / 2
        if y + actual_height < 0 or y > height:
            return
        alpha = (0.78 + 0.22 * focus) * max(0.0, min(1.0, (height / 2 - abs(center_y - height / 2)) / max(1, actual_height / 2)))
        context.save()
        context.translate((width - (width - 32) * scale) / 2, y)
        context.scale(scale, scale)
        # A narrow wine outline keeps the letters readable over bright wallpaper.
        PangoCairo.layout_path(context, layout)
        self.color(context, 'bg_window', 'bg_window', 0, alpha)
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.set_line_width(3.0 / scale)
        context.stroke_preserve()
        self.color(context, 'text_secondary', 'text_inverse', focus, alpha)
        context.fill()
        context.restore()

    def draw_surface(self, lines, scroll, width, height, cell_height, pixel_scale=1):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * pixel_scale, height * pixel_scale)
        surface.set_device_scale(pixel_scale, pixel_scale)
        context = cairo.Context(surface)
        font_pixels = max(18, round(cell_height * 1.55))
        spacing = height * 0.36
        for candidate in range(max(0, math.floor(scroll) - 1), min(len(lines), math.ceil(scroll) + 3)):
            distance = candidate - scroll
            focus = max(0.0, 1 - abs(distance))
            text = ''.join(char for char in unicodedata.normalize('NFC', lines[candidate][1])
                           if unicodedata.category(char) not in ('Cc', 'Cs'))
            self.draw_line(context, text, focus, height / 2 + distance * spacing,
                           width, height, font_pixels)
        return surface

    def render_png(self, lines, scroll, width, height, cell_height):
        surface = self.draw_surface(lines, scroll, width, height, cell_height)
        output = io.BytesIO()
        if Image is not None and sys.byteorder == 'little':
            # Cairo's default PNG compression can consume a whole frame budget.
            surface.flush()
            image = Image.frombuffer('RGBA', (width, height), surface.get_data(), 'raw',
                                     'BGRa', surface.get_stride(), 1)
            image.save(output, format='PNG', compress_level=1)
        else:
            surface.write_to_png(output)
        return output.getvalue()

    def render(self, lines, index, cols, rows, track_key, now=None, cell_dimensions=None):
        now = time.monotonic() if now is None else now
        cell_width, cell_height = cell_dimensions or pixel_size(cols, rows)
        top, canvas_rows, spectrum_top = visualizer_regions(rows)
        placement_cols = min(cols, max(1, int(1200 / cell_width)))
        left = max(0, (cols - placement_cols) // 2)
        width, height = max(1, round(placement_cols * cell_width)), max(1, round(canvas_rows * cell_height))
        scroll = self.set_target(index, track_key, now)
        scene = (track_key, tuple(lines), index, round(scroll, 5), cols, rows, placement_cols, width, height, top, left)
        command = ''
        if scene != self.last_scene:
            png = self.render_png(lines, scroll, width, height, cell_height)
            command = f'\x1b[{top + 1};{left + 1}H' + image_command(png, self.image_id, placement_cols, canvas_rows)
            self.last_scene = scene
            self.shown = True
        return spectrum_top, command

    def clear(self):
        command = f'\x1b_Ga=d,d=I,i={self.image_id},q=2\x1b\\' if self.shown else ''
        self.shown = False
        self.last_scene = None
        self.target = None
        return command
