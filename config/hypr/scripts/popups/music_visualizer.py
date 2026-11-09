#!/usr/bin/env python3
# music_visualizer.py — Music visualizer and MPRIS controls.

import os
import sys
import time
import signal
import subprocess
import threading
import html
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, GdkPixbuf

# Ensure script dir and system dir are in sys.path before loading palette
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = os.path.dirname(SCRIPT_DIR)
SYSTEM_DIR = os.path.join(SCRIPTS_ROOT, "system")
HYPR_DIR = os.path.dirname(SCRIPTS_ROOT)

for p in (SCRIPT_DIR, SCRIPTS_ROOT, SYSTEM_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from draggable_popup import DraggablePopup, get_cursor_pos, get_monitor_geometry

# Color tokens & Cairo RGBA
try:
    from palette import (
        PALETTE, hex_to_rgba,
        C_BG_WIN, C_BG_CARD, C_BG_CARD_HOVER, C_BG_SUBTLE,
        C_ACCENT, C_ACCENT_HOVER, C_TEXT_PRI, C_TEXT_SEC, C_TEXT_MUT, C_TEXT_INV,
        C_STATUS_WARN, C_STATUS_CRIT, C_STATUS_SUCC, C_RIBBON,
        C_BG_WAYBAR, C_BORDER_3D, C_BG_CREAM,
        BG_WINDOW_RGBA, BG_CARD_RGBA, ACCENT_RGBA, ACCENT_HOVER_RGBA,
        BORDER_WINDOW_RGBA, BORDER_CARD_RGBA
    )
except ImportError:
    C_BG_WIN = "#201011"
    C_BG_CARD = "#2A1A1E"
    C_BG_CARD_HOVER = "#3A222A"
    C_BG_SUBTLE = "#301F20"
    C_ACCENT = "#DC1A36"
    C_ACCENT_HOVER = "#F02D4C"
    C_TEXT_PRI = "#FFF0F5"
    C_TEXT_SEC = "#E8C2D0"
    C_TEXT_MUT = "#A68595"
    C_TEXT_INV = "#FFFFFF"
    C_STATUS_WARN = "#FFB86C"
    C_STATUS_CRIT = "#DC1A36"
    C_STATUS_SUCC = "#8FBC8F"
    C_RIBBON = "#50A6FF"
    C_BG_WAYBAR = "#851733"
    C_BORDER_3D = "#4D0A1C"
    C_BG_CREAM = "rgba(255, 240, 245, 0.96)"
    BG_WINDOW_RGBA = (32.0/255.0, 16.0/255.0, 18.0/255.0, 0.98)
    BG_CARD_RGBA = (42.0/255.0, 26.0/255.0, 31.0/255.0, 0.95)
    ACCENT_RGBA = (220.0/255.0, 26.0/255.0, 54.0/255.0, 1.0)
    ACCENT_HOVER_RGBA = (240.0/255.0, 45.0/255.0, 76.0/255.0, 1.0)
    BORDER_WINDOW_RGBA = (1.0, 1.0, 1.0, 0.12)
    BORDER_CARD_RGBA = (1.0, 1.0, 1.0, 0.12)

PID_FILE = "/tmp/music_visualizer.pid"
CAVA_CONF = "/tmp/cava.conf"

# Path to external CSS stylesheet
STYLESHEET_PATH = os.path.join(HYPR_DIR, "styles", "music_visualizer.css")

class MusicVisualizer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Music Visualizer")
        self.set_name("music-visualizer-window")
        self.set_wmclass("music-visualizer", "music-visualizer")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(315, -1)
        self.set_size_request(315, -1)

        # 1. Draggable Layer-Shell Setup via shared DraggablePopup manager
        def music_bounds(x, y, mon_w, mon_h):
            return max(10, min(mon_w - 325, x)), max(10, min(mon_h - 100, y))

        self.drag_manager = DraggablePopup(
            self,
            name="music_visualizer",
            default_pos=(14, 44),
            bounds_fn=music_bounds
        )
        self.drag_manager.init_layer_shell(
            namespace="music-visualizer",
            layer=GtkLayerShell.Layer.TOP if HAS_LAYER_SHELL else None,
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND if HAS_LAYER_SHELL else None
        )

        # 2. Transparent Visual & Cairo Squircle Background
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", self.on_window_draw)

        # 3. State & Cava Data
        self.num_bars = 20
        self.bars = [2.0] * self.num_bars
        self.target_bars = [0.0] * self.num_bars
        self.running = True
        self.cava_proc = None

        self.apply_css()
        self.build_ui()

        # Keyboard shortcuts
        self.connect("key-press-event", self.on_key_press)

        # Launch CAVA in background thread
        self.start_cava()

        # Animation timer (~40 FPS)
        GLib.timeout_add(25, self.update_animation)

        # Track metadata timer (1 sec)
        GLib.timeout_add(1000, self.update_media_info)
        self.update_media_info()

    # === DRAGGABLE POPUP BRIDGES ===
    @property
    def current_win_x(self):
        return self.drag_manager.current_x

    @current_win_x.setter
    def current_win_x(self, val):
        self.drag_manager.current_x = val

    @property
    def current_win_y(self):
        return self.drag_manager.current_y

    @current_win_y.setter
    def current_win_y(self, val):
        self.drag_manager.current_y = val

    @property
    def is_dragging(self):
        return self.drag_manager.is_dragging

    def get_cursor_pos(self):
        return get_cursor_pos()

    def get_monitor_geometry(self):
        return get_monitor_geometry()

    def save_window_pos(self):
        self.drag_manager.save_position()

    def reset_window_pos(self):
        self.drag_manager.reset_to_default()

    def on_window_draw(self, widget, cr):
        # Clear surface completely so GTK CSS renders 3D tactile borders
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def close_and_quit(self):
        self.running = False
        if self.cava_proc:
            try:
                self.cava_proc.terminate()
            except Exception:
                pass
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_and_quit()
            return True
        return False

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_file = STYLESHEET_PATH
        if not os.path.exists(css_file):
            css_file = os.path.expanduser("~/.config/hypr/styles/music_visualizer.css")
        if os.path.exists(css_file):
            try:
                css_provider.load_from_path(css_file)
            except Exception as e:
                print(f"Warning: Failed to load CSS from {css_file}: {e}", file=sys.stderr)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 10)

    def generate_default_art_pixbuf(self, size=56):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surface)

        # Clean floating musical note (no background frame/box)
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("JetBrains Mono Nerd Font 34"))
        layout.set_text("", -1)
        ink, log = layout.get_pixel_extents()
        cx = (size - log.width) / 2.0 - log.x
        cy = (size - log.height) / 2.0 - log.y - 1.0

        # 3D shadow extrusion (#4D0A1C)
        cr.move_to(cx, cy + 2.5)
        cr.set_source_rgb(0x4D / 255.0, 0x0A / 255.0, 0x1C / 255.0)
        PangoCairo.show_layout(cr, layout)

        # Crisp subtle light contour
        cr.move_to(cx, cy + 1.0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.65)
        PangoCairo.show_layout(cr, layout)

        # Main musical note: Ruby Wine (#851733, Waybar right corner color)
        cr.move_to(cx, cy)
        cr.set_source_rgb(0x85 / 255.0, 0x17 / 255.0, 0x33 / 255.0)
        PangoCairo.show_layout(cr, layout)

        return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)

    def set_default_art(self):
        if not hasattr(self, "_default_art_pixbuf") or not self._default_art_pixbuf:
            self._default_art_pixbuf = self.generate_default_art_pixbuf()
        self.art_img.set_from_pixbuf(self._default_art_pixbuf)

    def load_art_async(self, art_url):
        if not art_url:
            GLib.idle_add(self.set_default_art)
            return

        path = art_url
        if path.startswith("file://"):
            path = path[7:]
        if os.path.exists(path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 56, 56, True)
                GLib.idle_add(lambda: self.art_img.set_from_pixbuf(pixbuf))
                return
            except Exception:
                pass
        GLib.idle_add(self.set_default_art)

    @staticmethod
    def format_time(seconds: float) -> str:
        s = int(max(0, seconds))
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_name("main-card")

        # === HEADER (Brand Title & Drag Handle) ===
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        lbl_header = Gtk.Label()
        lbl_header.set_markup(f"<span font='11.5' color='{C_ACCENT}'>󰎆</span>   <span color='{C_BG_WAYBAR}' font='10.5' weight='800' letter_spacing='1024'>NOW PLAYING</span>")
        header_box.pack_start(lbl_header, False, False, 0)

        # Drag grip zone with tactile pill (like shelf.py)
        drag_handle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        drag_handle_box.set_hexpand(True)
        drag_handle_box.get_style_context().add_class("drag-grip-zone")
        pill = Gtk.Box()
        pill.get_style_context().add_class("drag-handle-pill")
        drag_handle_box.pack_start(pill, True, True, 0)
        drag_handle_box.set_tooltip_text("Drag header to move · Double-click to reset")
        header_box.pack_start(drag_handle_box, True, True, 6)

        # Close button on header
        btn_close = Gtk.Button()
        lbl_close = Gtk.Label(label="󰅖")
        lbl_close.get_style_context().add_class("btn-close-icon")
        btn_close.add(lbl_close)
        btn_close.get_style_context().add_class("btn-header-close")
        btn_close.connect("clicked", lambda b: self.close_and_quit())
        btn_close.set_tooltip_text("Close Visualizer (Esc)")
        header_box.pack_end(btn_close, False, False, 0)

        # Wrap header in EventBox for smooth window dragging
        self.header_event_box = Gtk.EventBox()
        self.header_event_box.set_visible_window(False)
        self.drag_manager.attach_header(self.header_event_box)
        self.header_event_box.add(header_box)

        main_box.pack_start(self.header_event_box, False, False, 0)

        # === PLAYER CARD (Album Art + Track Info + Progress) ===
        player_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        player_card.get_style_context().add_class("player-card")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Album Art
        self.art_img = Gtk.Image()
        self.art_box = Gtk.Box()
        self.art_box.get_style_context().add_class("album-art-box")
        self.art_box.set_size_request(56, 56)
        self.art_box.set_valign(Gtk.Align.CENTER)
        self.art_box.pack_start(self.art_img, True, True, 0)
        self.set_default_art()
        top_row.pack_start(self.art_box, False, False, 0)

        # Title, Artist, Status Badge
        info_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_vbox.set_valign(Gtk.Align.CENTER)

        self.lbl_title = Gtk.Label(label="No media playing")
        self.lbl_title.get_style_context().add_class("track-title")
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)

        self.lbl_artist = Gtk.Label(label="")
        self.lbl_artist.get_style_context().add_class("track-artist")
        self.lbl_artist.set_halign(Gtk.Align.START)
        self.lbl_artist.set_ellipsize(Pango.EllipsizeMode.END)

        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.get_style_context().add_class("status-badge")
        self.lbl_status.set_halign(Gtk.Align.START)
        self.lbl_status.set_no_show_all(True)
        self.lbl_status.hide()

        info_vbox.pack_start(self.lbl_title, False, False, 0)
        info_vbox.pack_start(self.lbl_artist, False, False, 0)
        info_vbox.pack_start(self.lbl_status, False, False, 2)
        top_row.pack_start(info_vbox, True, True, 0)

        player_card.pack_start(top_row, False, False, 0)

        # Progress bar & Timestamps
        progress_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        progress_vbox.pack_start(self.progress_bar, False, False, 0)

        time_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.lbl_time_cur = Gtk.Label(label="00:00")
        self.lbl_time_cur.get_style_context().add_class("time-label")
        self.lbl_time_cur.set_halign(Gtk.Align.START)

        self.lbl_time_total = Gtk.Label(label="00:00")
        self.lbl_time_total.get_style_context().add_class("time-label")
        self.lbl_time_total.set_halign(Gtk.Align.END)

        time_hbox.pack_start(self.lbl_time_cur, True, True, 0)
        time_hbox.pack_end(self.lbl_time_total, False, False, 0)
        progress_vbox.pack_start(time_hbox, False, False, 0)

        player_card.pack_start(progress_vbox, False, False, 0)
        main_box.pack_start(player_card, False, False, 0)

        # === CONTROLS ROW (Previous, Play/Pause, Next) ===
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        ctrl_box.set_halign(Gtk.Align.CENTER)
        ctrl_box.set_margin_top(2)
        ctrl_box.set_margin_bottom(2)

        btn_prev = Gtk.Button(label="󰒮")
        btn_prev.get_style_context().add_class("btn-ctrl-nav")
        btn_prev.connect("clicked", self.on_prev_clicked)

        self.btn_play = Gtk.Button(label="󰐊")
        self.btn_play.get_style_context().add_class("btn-ctrl-play")
        self.btn_play.connect("clicked", self.on_play_clicked)

        btn_next = Gtk.Button(label="󰒭")
        btn_next.get_style_context().add_class("btn-ctrl-nav")
        btn_next.connect("clicked", self.on_next_clicked)

        ctrl_box.pack_start(btn_prev, False, False, 0)
        ctrl_box.pack_start(self.btn_play, False, False, 0)
        ctrl_box.pack_start(btn_next, False, False, 0)
        main_box.pack_start(ctrl_box, False, False, 0)

        # === AUDIO VISUALIZER DRAWING AREA ===
        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(-1, 64)
        self.darea.connect("draw", self.on_visualizer_draw)
        main_box.pack_start(self.darea, True, True, 2)

        self.add(main_box)

    # === CAVA AUDIO VISUALIZER DRAWING & ANIMATION ===
    def on_visualizer_draw(self, widget, cr):
        alloc = widget.get_allocation()
        w = float(alloc.width)
        h = float(alloc.height)

        num = self.num_bars
        gap = 4.0
        total_gaps = gap * (num - 1)
        bar_w = max(4.0, (w - total_gaps) / num)
        total_content_w = num * bar_w + total_gaps
        start_x = (w - total_content_w) / 2.0

        r = 2.5
        for i in range(num):
            val = self.bars[i]
            bar_h = max(5.0, (val / 100.0) * (h - 8.0))
            x = start_x + i * (bar_w + gap)
            y = h - 4.0 - bar_h

            # Draw flat baseline bar with subtle rounded top
            cr.new_sub_path()
            cr.arc(x + bar_w - r, y + r, r, -1.57079632679, 0)
            cr.line_to(x + bar_w, h - 4.0)
            cr.line_to(x, h - 4.0)
            cr.arc(x + r, y + r, r, 3.14159265359, 4.71238898038)
            cr.close_path()

            # Use a flat accent fill without shadows.
            cr.set_source_rgba(*ACCENT_RGBA)
            cr.fill()

        return False

    def update_animation(self):
        if not self.running:
            return False

        # Smooth interpolation with quick attack & gentle decay
        for i in range(self.num_bars):
            target = self.target_bars[i]
            curr = self.bars[i]
            if target > curr:
                self.bars[i] += (target - curr) * 0.65
            else:
                self.bars[i] += (target - curr) * 0.18

            if self.bars[i] < 2.0:
                self.bars[i] = 2.0

        self.darea.queue_draw()
        return True

    def start_cava(self):
        conf_content = f"""
[general]
bars = {self.num_bars}
framerate = 35

[input]
method = pulse

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
"""
        try:
            with open(CAVA_CONF, "w") as f:
                f.write(conf_content)
        except Exception:
            pass

        def worker():
            while self.running:
                try:
                    self.cava_proc = subprocess.Popen(
                        ["cava", "-p", CAVA_CONF],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        bufsize=1
                    )
                    while self.running and self.cava_proc.poll() is None:
                        line = self.cava_proc.stdout.readline()
                        if not line:
                            break
                        parts = line.strip().split(";")
                        vals = []
                        for p in parts:
                            if p.isdigit():
                                vals.append(min(100.0, float(p)))
                        if len(vals) >= self.num_bars:
                            self.target_bars = vals[:self.num_bars]
                except Exception:
                    time.sleep(1)
                finally:
                    if self.cava_proc:
                        try:
                            self.cava_proc.terminate()
                        except Exception:
                            pass

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # === PLAYERCTL MPRIS CONTROLS & INFO ===
    def on_play_clicked(self, widget):
        subprocess.run(["playerctl", "play-pause"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        GLib.timeout_add(150, self.update_media_info)

    def on_prev_clicked(self, widget):
        subprocess.run(["playerctl", "previous"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        GLib.timeout_add(150, self.update_media_info)

    def on_next_clicked(self, widget):
        subprocess.run(["playerctl", "next"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        GLib.timeout_add(150, self.update_media_info)

    def update_media_info(self):
        try:
            res_status = subprocess.run(["playerctl", "status"], capture_output=True, text=True, timeout=0.3)
            status = res_status.stdout.strip()
        except Exception:
            status = ""

        if status in ["Playing", "Paused"]:
            try:
                res_meta = subprocess.run(
                    ["playerctl", "metadata", "--format", "{{title}}|||{{artist}}|||{{mpris:artUrl}}|||{{position}}|||{{mpris:length}}"],
                    capture_output=True,
                    text=True,
                    timeout=0.3
                )
                parts = res_meta.stdout.strip().split("|||")
                raw_t = parts[0] if len(parts) > 0 and parts[0] else "Playing Media"
                raw_a = parts[1] if len(parts) > 1 and parts[1] else ""
                title = html.unescape(raw_t)
                artist = html.unescape(raw_a)
                art_url = parts[2] if len(parts) > 2 else ""
                pos_us = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                len_us = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
            except Exception:
                title = "Playing Media"
                artist = ""
                art_url = ""
                pos_us = 0
                len_us = 0

            self.lbl_title.set_markup(f"<span color='{C_TEXT_INV}'><b>{GLib.markup_escape_text(title)}</b></span>")
            self.lbl_artist.set_markup(f"<span color='{C_TEXT_PRI}'>{GLib.markup_escape_text(artist)}</span>")

            # Progress calculation
            pos_sec = pos_us / 1e6
            len_sec = len_us / 1e6
            if len_sec > 0:
                fraction = max(0.0, min(1.0, pos_sec / len_sec))
                self.progress_bar.set_fraction(fraction)
                self.lbl_time_cur.set_markup(f"<span color='{C_BORDER_3D}'><b>{self.format_time(pos_sec)}</b></span>")
                self.lbl_time_total.set_markup(f"<span color='{C_BORDER_3D}'><b>{self.format_time(len_sec)}</b></span>")
            else:
                self.progress_bar.set_fraction(0.0)
                self.lbl_time_cur.set_markup(f"<span color='{C_BORDER_3D}'><b>00:00</b></span>")
                self.lbl_time_total.set_markup(f"<span color='{C_BORDER_3D}'><b>00:00</b></span>")

            # Check and update album art
            if getattr(self, "current_art_url", None) != art_url:
                self.current_art_url = art_url
                threading.Thread(target=lambda: self.load_art_async(art_url), daemon=True).start()

            if status == "Playing":
                self.btn_play.set_label("󰏤")
                self.lbl_status.set_text("● Playing")
                self.lbl_status.get_style_context().remove_class("paused")
                self.lbl_status.get_style_context().add_class("playing")
                self.lbl_status.show()
            else:
                self.btn_play.set_label("󰐊")
                self.lbl_status.set_text("󰐎 Paused")
                self.lbl_status.get_style_context().remove_class("playing")
                self.lbl_status.get_style_context().add_class("paused")
                self.lbl_status.show()
        else:
            self.lbl_title.set_markup(f"<span color='{C_TEXT_INV}'><b>No media playing</b></span>")
            self.lbl_artist.set_text("")
            self.lbl_time_cur.set_markup(f"<span color='{C_BORDER_3D}'><b>00:00</b></span>")
            self.lbl_time_total.set_markup(f"<span color='{C_BORDER_3D}'><b>00:00</b></span>")
            self.btn_play.set_label("󰐊")
            self.lbl_status.set_text("")
            self.lbl_status.hide()
            self.lbl_status.get_style_context().remove_class("playing")
            self.lbl_status.get_style_context().remove_class("paused")
            self.progress_bar.set_fraction(0.0)
            self.lbl_time_cur.set_text("00:00")
            self.lbl_time_total.set_text("00:00")
            self.set_default_art()
            self.target_bars = [0.0] * self.num_bars

        return True

def main():
    def sig_handler(signum, frame):
        GLib.idle_add(Gtk.main_quit)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    my_pid = os.getpid()
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(my_pid))
    except Exception:
        pass

    app = MusicVisualizer()

    def cleanup(*args):
        app.running = False
        if app.cava_proc:
            try:
                app.cava_proc.terminate()
            except Exception:
                pass
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    app.connect("destroy", cleanup)
    app.show_all()
    try:
        Gtk.main()
    finally:
        cleanup()

if __name__ == "__main__":
    main()
