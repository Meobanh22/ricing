"""Pixel-rendered spectrum with continuous token gradients for Kitty."""

import io
import os
import sys
import zlib
import tempfile
import time
from pathlib import Path
from collections import OrderedDict

import cairo

from music_lyrics import Image, image_command, pixel_size

MAX_CANVAS_WIDTH = 720
MAX_CANVAS_HEIGHT = 160


class SpectrumCanvas:
    def __init__(self, stops):
        self.stops = tuple((position, tuple(int(color[index:index + 2], 16) / 255
                                          for index in (1, 3, 5)))
                           for position, color in stops)
        self.image_id = ((os.getpid() & 0xFFFFFF) << 4) | 5
        self.shown = False
        self.last_scene = None
        # Stream transport with fast in-memory zlib avoids ~104 MiB/s temp file churn to /tmp
        self.file_transport = bool(os.environ.get('KITTY_FILE_TRANSPORT', '0') == '1')
        self.buffers = None
        self.pending = []
        self.bar_cache = OrderedDict()
        self.bar_cache_bytes = 0
        self.bar_cache_limit = 24 * 1024 * 1024

    def draw(self, heights, cols, width, height, rgba_bytes=False):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = cairo.Context(surface)
        self.paint(context, heights, cols, width, height, rgba_bytes)
        return surface

    def paint(self, context, heights, cols, width, height, rgba_bytes=False):
        if rgba_bytes:
            # Filled bars need no partial-alpha edge pixels. Swapping R/B at
            # draw time makes Cairo's native BGRA buffer directly usable as RGBA.
            context.set_antialias(cairo.ANTIALIAS_NONE)
        cell_width = width / max(1, cols)
        count = len(heights)
        bar_width = min(2, cols)
        gap = 1 if count > 1 else 0
        spare = cols - (count * bar_width + gap * (count - 1))
        left = spare // 2
        for index, bar_height in enumerate(heights):
            if bar_height <= 0:
                continue
            top = height - bar_height
            gradient = cairo.LinearGradient(0, top, 0, height)
            for position, rgb in self.stops:
                gradient.add_color_stop_rgb(position, *(rgb[::-1] if rgba_bytes else rgb))
            context.set_source(gradient)
            context.rectangle((left + index * (bar_width + gap)) * cell_width,
                              top, bar_width * cell_width, bar_height)
            context.fill()

    def render_png(self, heights, cols, width, height):
        surface = self.draw(heights, cols, width, height)
        output = io.BytesIO()
        if Image is not None and sys.byteorder == 'little':
            surface.flush()
            image = Image.frombuffer('RGBA', (width, height), surface.get_data(), 'raw',
                                     'BGRa', surface.get_stride(), 1)
            image.save(output, format='PNG', compress_level=1)
        else:
            surface.write_to_png(output)
        return output.getvalue()

    def paint_cached(self, context, heights, cols, width, height, scale=1):
        """Blit opaque gradient tiles at device pixels instead of shading each frame."""
        count = len(heights)
        if not count:
            return
        bar_width = min(2, cols)
        gap = 1 if count > 1 else 0
        left = (cols - (count * bar_width + gap * (count - 1))) // 2
        cell_width = width / max(1, cols)
        pixels_wide = max(1, round(bar_width * cell_width * scale))
        for index, level in enumerate(heights):
            pixels_high = min(round(height * scale), max(0, round(level * scale)))
            if not pixels_high:
                continue
            key = (pixels_wide, pixels_high, scale)
            tile = self.bar_cache.pop(key, None)
            if tile is None:
                tile = cairo.ImageSurface(cairo.FORMAT_RGB24, pixels_wide, pixels_high)
                painter = cairo.Context(tile)
                gradient = cairo.LinearGradient(0, 0, 0, pixels_high)
                for position, rgb in self.stops:
                    gradient.add_color_stop_rgb(position, *rgb)
                painter.set_source(gradient)
                painter.paint()
                tile.set_device_scale(scale, scale)
                self.bar_cache_bytes += tile.get_stride() * tile.get_height()
            self.bar_cache[key] = tile
            while self.bar_cache_bytes > self.bar_cache_limit and len(self.bar_cache) > 1:
                _, old = self.bar_cache.popitem(last=False)
                self.bar_cache_bytes -= old.get_stride() * old.get_height()
            x = round((left + index * (bar_width + gap)) * cell_width * scale) / scale
            y = height - pixels_high / scale
            context.set_source_surface(tile, x, y)
            context.rectangle(x, y, pixels_wide / scale, pixels_high / scale)
            context.fill()

    def render(self, bars, cols, rows, top, gain=1.0, cell_dimensions=None):
        canvas_rows = rows - top
        if cols <= 0 or canvas_rows <= 0 or not bars:
            return self.clear()
        cell_width, cell_height = cell_dimensions or pixel_size(cols, rows)
        width = min(MAX_CANVAS_WIDTH, max(1, round(cols * cell_width)))
        # Kitty scales this continuous gradient to the requested rows. Bounding
        # the source height keeps large windows within the animation budget.
        height = min(MAX_CANVAS_HEIGHT, max(1, round(canvas_rows * cell_height)))
        heights = tuple(min(height, max(0, round(value / 100 * gain * height)))
                        for value in bars)
        # Stable frames reuse the current image. Heights are rounded to pixels,
        # preserving motion finer than a terminal cell without caching past frames.
        scene = (heights, cols, canvas_rows, top, width, height)
        if scene == self.last_scene:
            return ''
        self.pending = [(path, created) for path, created in self.pending if path.exists()]
        if self.file_transport and len(self.pending) >= 3:
            if time.monotonic() - self.pending[0][1] < 0.25:
                return ''
            # A remote or restricted terminal may not support local files.
            self.file_transport = False
            for path, _ in self.pending:
                path.unlink(missing_ok=True)
            self.pending.clear()
        if sys.byteorder == 'little':
            surface = self.draw(heights, cols, width, height, rgba_bytes=True)
            surface.flush()
            pixels = surface.get_data()
            graphic = None
            if self.file_transport:
                try:
                    if self.buffers is None:
                        self.buffers = tempfile.TemporaryDirectory(prefix='tty-graphics-protocol-music-')
                    fd, name = tempfile.mkstemp(dir=self.buffers.name, suffix='.rgba')
                    with os.fdopen(fd, 'wb') as output:
                        output.write(pixels)
                    path = Path(name)
                    self.pending.append((path, time.monotonic()))
                    graphic = image_command(b'', self.image_id, cols, canvas_rows,
                                            pixel_dimensions=(width, height), temporary_path=path)
                except OSError:
                    self.file_transport = False
            if graphic is None:
                graphic = image_command(zlib.compress(pixels, 1), self.image_id, cols, canvas_rows,
                                        pixel_dimensions=(width, height))
        else:
            graphic = image_command(self.render_png(heights, cols, width, height),
                                    self.image_id, cols, canvas_rows)
        command = f'\x1b[{top + 1};1H' + graphic
        self.last_scene = scene
        self.shown = True
        return command

    def clear(self):
        command = f'\x1b_Ga=d,d=I,i={self.image_id},q=2\x1b\\' if self.shown else ''
        self.shown = False
        self.last_scene = None
        for path, _ in self.pending:
            path.unlink(missing_ok=True)
        self.pending.clear()
        if self.buffers is not None:
            self.buffers.cleanup()
            self.buffers = None
        return command
