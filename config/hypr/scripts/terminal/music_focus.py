"""Desktop dimming with lyrics and spectrum above it, controlled by music."""

import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import zlib

FADE_IN_SECONDS = 0.36
FADE_OUT_SECONDS = 0.28
SPOTLIGHT_DELAY = 0.08
SPOTLIGHT_SECONDS = 0.68


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def send_message(connection, message):
    try:
        data = json.dumps(message, ensure_ascii=False, separators=(',', ':')).encode()
        connection.send(zlib.compress(data, 1))
        return True
    except (OSError, ValueError):
        return False


def receive_messages(connection):
    messages = []
    while True:
        try:
            data = connection.recv(1024 * 1024)
        except OSError:
            break
        if not data:
            break
        try:
            message = json.loads(zlib.decompress(data))
            if isinstance(message, dict):
                messages.append(message)
        except (ValueError, zlib.error):
            continue
    return messages


class MusicFocus:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.process = None
        self.connection = None
        self.ready = False

    @property
    def active(self):
        if self.process is not None and self.process.poll() is not None:
            self.process = None
            if self.connection is not None:
                self.connection.close()
                self.connection = None
            self.ready = False
        return self.process is not None

    def toggle(self):
        if self.active:
            self.close(wait=False)
            return
        if not self.enabled:
            return
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        parent.setblocking(False)
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '--overlay',
                 str(child.fileno()), str(os.getpid())],
                pass_fds=(child.fileno(),), stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=dict(os.environ, GDK_BACKEND='wayland'),
            )
            self.connection = parent
            self.ready = False
        except OSError:
            parent.close()
        finally:
            child.close()

    def update(self, lines, index, track, bars, gain, gradient):
        if self.active and self.connection is not None:
            send_message(self.connection, {'type': 'frame', 'lines': lines, 'index': index,
                                          'track': track, 'bars': bars, 'gain': gain,
                                          'gradient': gradient})

    def read_keys(self):
        if self.connection is None:
            return []
        keys = []
        for message in receive_messages(self.connection):
            if message.get('type') == 'ready':
                self.ready = True
            elif message.get('type') == 'key' and isinstance(message.get('value'), str):
                keys.append(message['value'])
        return keys

    def close(self, wait=True):
        process, connection = self.process, self.connection
        self.process, self.connection, self.ready = None, None, False
        if connection is not None:
            send_message(connection, {'type': 'close'})
            connection.close()
        if process is None:
            return

        def reap():
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        if wait:
            reap()
        else:
            threading.Thread(target=reap, daemon=True).start()


def run_overlay(fd, parent_pid):
    import cairo
    import gi

    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'system'))
    from palette import PALETTE, SUNSET_STOPS
    from music_layout import visualizer_regions
    from music_lyrics import LyricsCanvas
    from music_spectrum import SpectrumCanvas
    from music_spotlight import StageSpotlight

    if not Gtk.init_check([])[0] or not GtkLayerShell.is_supported():
        return 1
    connection = socket.socket(fileno=fd)
    connection.setblocking(False)
    display = Gdk.Display.get_default()
    target = display.get_primary_monitor() or display.get_monitor(0)
    try:
        window = json.loads(subprocess.check_output(['hyprctl', '-j', 'activewindow'],
                                                    text=True, timeout=1))
        x, y = window['at']
        width, height = window['size']
        target = display.get_monitor_at_point(int(x + width / 2), int(y + height / 2)) or target
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        pass

    class Overlay:
        def __init__(self):
            self.frame = {}
            self.windows = []
            self.lyrics = LyricsCanvas(PALETTE)
            self.spectrum = SpectrumCanvas(SUNSET_STOPS)
            self.spotlight = StageSpotlight(PALETTE)
            self.backgrounds = {}
            self.lyric_scene = None
            self.lyric_surface = None
            self.drawn_lyric_state = None
            self.lyric_animating = False
            self.gradient = SUNSET_STOPS
            self.opened_at = None
            self.closing_at = None
            self.ready_sent = False
            self.animating = True
            self.background = tuple(int(PALETTE['dark_wine'][i:i + 2], 16) / 255
                                    for i in (1, 3, 5))
            geometry = target.get_geometry()
            self.spotlight.warm(geometry.width, geometry.height)
            for index in range(display.get_n_monitors()):
                monitor = display.get_monitor(index)
                self.add_window(monitor, monitor == target)
            display.connect('monitor-added', lambda _, monitor: self.add_window(monitor, False))
            display.connect('monitor-removed', self.remove_monitor)
            GLib.io_add_watch(connection.fileno(), GLib.IO_IN, self.receive)
            GLib.timeout_add(500, self.check_parent)
            GLib.timeout_add(16, self.animate)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self.quit)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.quit)

        def add_window(self, monitor, content):
            window = Gtk.Window(title='Music Focus')
            window.set_decorated(False)
            window.set_app_paintable(True)
            visual = window.get_screen().get_rgba_visual()
            if visual is not None:
                window.set_visual(visual)
            GtkLayerShell.init_for_window(window)
            GtkLayerShell.set_namespace(window, 'music-focus')
            GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_monitor(window, monitor)
            GtkLayerShell.set_exclusive_zone(window, -1)
            GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.EXCLUSIVE
                                           if content else GtkLayerShell.KeyboardMode.NONE)
            for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                         GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
                GtkLayerShell.set_anchor(window, edge, True)
            window.connect('draw', self.draw, content)
            window.connect('key-press-event', self.key)
            self.windows.append((window, monitor, content))
            window.show_all()

        def remove_monitor(self, _, monitor):
            removed_content = any(content for _, item, content in self.windows if item == monitor)
            for window, item, _ in self.windows:
                if item == monitor:
                    window.destroy()
            self.windows = [item for item in self.windows if item[1] != monitor]
            if removed_content and self.windows:
                window, monitor, _ = self.windows[0]
                self.windows[0] = (window, monitor, True)
                # Reconnect to draw the foreground on the remaining monitor.
                window.disconnect_by_func(self.draw)
                window.connect('draw', self.draw, True)
                GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.EXCLUSIVE)

        def receive(self, *_):
            for message in receive_messages(connection):
                if message.get('type') == 'close':
                    if self.closing_at is None:
                        self.closing_at = time.monotonic()
                        if not self.animating:
                            self.animating = True
                            GLib.timeout_add(16, self.animate)
                elif message.get('type') == 'frame':
                    self.frame = message
                    gradient = message.get('gradient', self.gradient)
                    if gradient != self.gradient:
                        self.gradient = gradient
                        self.spectrum = SpectrumCanvas(gradient)
            if not self.animating:
                self.redraw()
            return True

        def redraw(self):
            now = time.monotonic()
            intro_done = self.opened_at is not None and now - self.opened_at >= SPOTLIGHT_DELAY + SPOTLIGHT_SECONDS
            full = self.closing_at is not None or not intro_done
            state = (self.frame.get('track', ''), self.frame.get('index', 0),
                     tuple(tuple(line) for line in self.frame.get('lines', [])))
            for window, _, content in self.windows:
                if full:
                    window.queue_draw()
                elif content:
                    width, height = window.get_allocated_width(), window.get_allocated_height()
                    rows = max(12, int(height / 24))
                    top, count, wave = visualizer_regions(rows)
                    wave_top = int(wave * height / rows)
                    window.queue_draw_area(0, wave_top, width, height - wave_top)
                    if state != self.drawn_lyric_state or self.lyric_animating:
                        window.queue_draw_area(0, int(top * height / rows), width,
                                               math.ceil(count * height / rows) + 2)

        def animate(self):
            now = time.monotonic()
            if self.closing_at is not None and now - self.closing_at >= FADE_OUT_SECONDS:
                self.animating = False
                return self.quit()
            self.redraw()
            intro_done = self.opened_at is not None and now - self.opened_at >= SPOTLIGHT_DELAY + SPOTLIGHT_SECONDS
            keep_running = self.closing_at is not None or not intro_done
            self.animating = keep_running
            return keep_running

        def check_parent(self):
            if os.getppid() != parent_pid:
                return self.quit()
            return True

        def quit(self):
            Gtk.main_quit()
            return False

        def key(self, _, event):
            special = {Gdk.KEY_Escape: 'd', Gdk.KEY_Left: '\x1b[D', Gdk.KEY_Right: '\x1b[C',
                       Gdk.KEY_Tab: '\t', Gdk.KEY_ISO_Left_Tab: '\t'}
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                value = '\x03' if event.keyval in (Gdk.KEY_c, Gdk.KEY_C) else ''
            elif event.state & (Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.SUPER_MASK):
                value = ''
            else:
                value = special.get(event.keyval)
            if value is None:
                codepoint = Gdk.keyval_to_unicode(event.keyval)
                value = chr(codepoint) if codepoint else ''
            if value:
                send_message(connection, {'type': 'key', 'value': value})
            return True

        def draw(self, window, context, content):
            width, height = window.get_allocated_width(), window.get_allocated_height()
            if not self.frame and self.closing_at is None:
                context.set_operator(cairo.OPERATOR_SOURCE)
                context.set_source_rgba(0, 0, 0, 0)
                context.paint()
                return True
            now = time.monotonic()
            if self.opened_at is None:
                self.opened_at = now
            alpha = smoothstep((now - self.opened_at) / FADE_IN_SECONDS)
            if self.closing_at is not None:
                alpha *= 1.0 - smoothstep((now - self.closing_at) / FADE_OUT_SECONDS)
            if not self.ready_sent and self.frame:
                self.ready_sent = True
                GLib.idle_add(lambda: send_message(connection, {'type': 'ready'}) and False)
            if now - self.opened_at >= SPOTLIGHT_DELAY + SPOTLIGHT_SECONDS and self.closing_at is None:
                scale = window.get_scale_factor()
                key = (width, height, content, scale)
                if key not in self.backgrounds:
                    if len(self.backgrounds) >= 4:
                        self.backgrounds.clear()
                    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * scale, height * scale)
                    surface.set_device_scale(scale, scale)
                    background = cairo.Context(surface)
                    background.set_source_rgba(*self.background, 0.85)
                    background.paint()
                    if content:
                        self.spotlight.paint(background, width, height)
                    self.backgrounds[key] = surface
                context.set_operator(cairo.OPERATOR_SOURCE)
                context.set_source_surface(self.backgrounds[key], 0, 0)
                context.paint()
                context.set_operator(cairo.OPERATOR_OVER)
                if content:
                    self.draw_content(context, width, height, now, scale)
                return True
            context.set_operator(cairo.OPERATOR_SOURCE)
            context.set_source_rgba(*self.background, 0.85 * alpha)
            context.paint()
            context.set_operator(cairo.OPERATOR_OVER)
            if content and alpha > 0:
                light = smoothstep((now - self.opened_at - SPOTLIGHT_DELAY) / SPOTLIGHT_SECONDS)
                self.spotlight.paint(context, width, height, alpha * light)
                self.draw_content(context, width, height, now, window.get_scale_factor(), alpha)
            return True

        def draw_content(self, context, width, height, now, scale, content_alpha=1.0):
            rows = max(12, int(height / 24))
            cell_height = height / rows
            lyric_top, lyric_rows, spectrum_top = visualizer_regions(rows)
            canvas_height = lyric_rows * cell_height
            lines = self.frame.get('lines', [])
            index = self.frame.get('index', 0)
            self.drawn_lyric_state = (self.frame.get('track', ''), index,
                                      tuple(tuple(line) for line in lines))
            if lines:
                scroll = self.lyrics.set_target(index, self.frame.get('track', ''), now)
                lyric_width = min(1200, width)
                scene = (self.drawn_lyric_state, round(scroll, 5), lyric_width,
                         round(canvas_height), cell_height, scale)
                if scene != self.lyric_scene:
                    self.lyric_surface = self.lyrics.draw_surface(lines, scroll, lyric_width,
                                                                  round(canvas_height), cell_height, scale)
                    self.lyric_scene = scene
                self.lyric_animating = abs(scroll - index) > 0.000001
                context.set_source_surface(self.lyric_surface, (width - lyric_width) / 2,
                                           lyric_top * cell_height)
                if content_alpha < 0.999:
                    context.paint_with_alpha(content_alpha)
                else:
                    context.paint()
            else:
                self.lyric_scene = self.lyric_surface = None
                self.lyric_animating = False
            bars = self.frame.get('bars', [])
            if bars:
                wave_top = round(spectrum_top * cell_height)
                wave_height = max(1, height - wave_top)
                gain = self.frame.get('gain', 1.0)
                heights = [min(wave_height, max(0, round(value / 100 * gain * wave_height))) for value in bars]
                context.save()
                if content_alpha < 0.999:
                    context.rectangle(0, wave_top, width, wave_height)
                    context.clip()
                    context.push_group()
                    context.translate(0, wave_top)
                    self.spectrum.paint_cached(context, heights, len(bars) * 3 - 1, width, wave_height, scale)
                    context.pop_group_to_source()
                    context.paint_with_alpha(content_alpha)
                else:
                    context.translate(0, wave_top)
                    self.spectrum.paint_cached(context, heights, len(bars) * 3 - 1, width, wave_height, scale)
                context.restore()

    overlay = Overlay()
    try:
        Gtk.main()
    finally:
        for window, _, _ in overlay.windows:
            window.destroy()
        connection.close()
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--overlay':
        raise SystemExit(run_overlay(int(sys.argv[2]), int(sys.argv[3])))
