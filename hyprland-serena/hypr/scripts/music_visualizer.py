#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA MINIMALIST MUSIC VISUALIZER (STATIC LAYER-SHELL)
# ==============================================================================
# - Fixed Anchor: TOP | LEFT (Symmetric with Control Center at TOP | RIGHT)
# - Real-time CAVA Audio Visualizer with smooth Cairo capsule bars
# - Lightweight MPRIS Player Controls & Track Info (playerctl)
# - Clean, borderless inner layout adhering strictly to AGENTS.md
# ==============================================================================

import os
import sys
import time
import signal
import subprocess
import threading
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, Pango

PID_FILE = "/tmp/music_visualizer.pid"
CAVA_CONF = "/tmp/serena_cava.conf"

CSS_DATA = b"""
* {
    font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', 'Inter', sans-serif;
}

window#music-visualizer-window {
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
}

#main-card {
    background-color: transparent;
    border: none;
    padding: 14px;
    min-width: 287px;
}

.title-header {
    color: #FF2A55;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 1px;
}

.btn-close {
    color: #A68595;
    background: transparent;
    border: none;
    font-size: 13px;
    padding: 2px 7px;
    border-radius: 8px;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.btn-close:hover {
    background: rgba(42, 26, 31, 0.50);
    color: #FF2A55;
}

.track-title {
    color: #FFF0F5;
    font-size: 13px;
    font-weight: 700;
}

.track-artist {
    color: #E8C2D0;
    font-size: 11px;
    font-weight: 500;
}

button {
    background-image: none;
    box-shadow: none;
    outline: none;
}

.btn-ctrl {
    color: #E8C2D0;
    background-color: rgba(42, 26, 31, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    font-size: 13px;
    padding: 4px 12px;
    transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.btn-ctrl:hover {
    background-color: #3A222A;
    border-color: rgba(255, 42, 85, 0.65);
    color: #FF2A55;
}

.btn-ctrl-accent {
    color: #FF2A55;
    background-color: rgba(42, 26, 31, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    font-size: 15px;
    padding: 4px 16px;
    transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.btn-ctrl-accent:hover {
    background-color: #3A222A;
    border-color: rgba(255, 42, 85, 0.65);
    color: #FF597B;
}

.status-badge {
    background-color: rgba(42, 26, 31, 0.95);
    color: #E8C2D0;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.status-badge.playing {
    color: #7FA873;
}

.status-badge.paused {
    color: #A68595;
}
"""

class MusicVisualizer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Music Visualizer")
        self.set_name("music-visualizer-window")
        self.set_decorated(False)
        self.set_resizable(False)

        # 1. GtkLayerShell setup (Static Layer-Shell: TOP | LEFT)
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "music-visualizer")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 44)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 14)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        else:
            self.set_wmclass("music-visualizer", "music-visualizer")
            self.set_position(Gtk.WindowPosition.NONE)
            self.move(14, 44)

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

    def on_window_draw(self, widget, cr):
        # Clear surface completely to prevent square artifacts
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw 16px Squircle Frame
        alloc = widget.get_allocation()
        pad = 0.5
        w = float(alloc.width) - pad * 2.0
        h = float(alloc.height) - pad * 2.0
        x = pad
        y = pad
        r = 16.0

        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.57079632679, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.57079632679)
        cr.arc(x + r, y + h - r, r, 1.57079632679, 3.14159265359)
        cr.arc(x + r, y + r, r, 3.14159265359, 4.71238898038)
        cr.close_path()

        # Background: --bg-window (rgba(32, 16, 18, 0.98))
        cr.set_source_rgba(32.0 / 255.0, 16.0 / 255.0, 18.0 / 255.0, 0.98)
        cr.fill_preserve()

        # Border: --border-window (rgba(255, 255, 255, 0.12))
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

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
        css_provider.load_from_data(CSS_DATA)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_name("main-card")

        # -------------------------------------------------------------
        # 1. Header (Brand Title + Close Button)
        # -------------------------------------------------------------
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        lbl_header = Gtk.Label()
        lbl_header.set_markup("<span font='11.5' color='#FF2A55'>󰎆</span>   <span color='#FFF0F5' font='10.5' weight='bold' letter_spacing='1024'>NOW PLAYING</span>")
        header_box.pack_start(lbl_header, False, False, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda x: self.close_and_quit())
        header_box.pack_end(btn_close, False, False, 0)

        main_box.pack_start(header_box, False, False, 0)

        # -------------------------------------------------------------
        # 2. Track Title & Artist (Directly on window, no surrounding box)
        # -------------------------------------------------------------
        info_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_vbox.set_margin_top(2)

        self.lbl_title = Gtk.Label(label="No media playing")
        self.lbl_title.get_style_context().add_class("track-title")
        self.lbl_title.set_halign(Gtk.Align.START)
        self.lbl_title.set_ellipsize(Pango.EllipsizeMode.END)

        meta_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.lbl_artist = Gtk.Label(label="")
        self.lbl_artist.get_style_context().add_class("track-artist")
        self.lbl_artist.set_halign(Gtk.Align.START)
        self.lbl_artist.set_ellipsize(Pango.EllipsizeMode.END)
        meta_hbox.pack_start(self.lbl_artist, True, True, 0)

        self.lbl_status = Gtk.Label(label="Idle")
        self.lbl_status.get_style_context().add_class("status-badge")
        meta_hbox.pack_end(self.lbl_status, False, False, 0)

        info_vbox.pack_start(self.lbl_title, False, False, 0)
        info_vbox.pack_start(meta_hbox, False, False, 0)
        main_box.pack_start(info_vbox, False, False, 0)

        # -------------------------------------------------------------
        # 3. Controls Row (Previous, Play/Pause, Next)
        # -------------------------------------------------------------
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_box.set_halign(Gtk.Align.CENTER)
        ctrl_box.set_margin_top(4)
        ctrl_box.set_margin_bottom(4)

        btn_prev = Gtk.Button(label="󰒮")
        btn_prev.get_style_context().add_class("btn-ctrl")
        btn_prev.connect("clicked", self.on_prev_clicked)

        self.btn_play = Gtk.Button(label="󰐊")
        self.btn_play.get_style_context().add_class("btn-ctrl-accent")
        self.btn_play.connect("clicked", self.on_play_clicked)

        btn_next = Gtk.Button(label="󰒭")
        btn_next.get_style_context().add_class("btn-ctrl")
        btn_next.connect("clicked", self.on_next_clicked)

        ctrl_box.pack_start(btn_prev, False, False, 0)
        ctrl_box.pack_start(self.btn_play, False, False, 0)
        ctrl_box.pack_start(btn_next, False, False, 0)
        main_box.pack_start(ctrl_box, False, False, 0)

        # -------------------------------------------------------------
        # 4. Real-time CAVA Audio Visualizer (Directly on window surface)
        # -------------------------------------------------------------
        self.darea = Gtk.DrawingArea()
        self.darea.set_size_request(-1, 72)
        self.darea.connect("draw", self.on_visualizer_draw)
        main_box.pack_start(self.darea, True, True, 2)

        self.add(main_box)

    # -----------------------------------------------------------------
    # CAVA Audio Visualizer Drawing & Animation
    # -----------------------------------------------------------------
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

            # Pure Flat Serena Accent (#FF2A55) — Zero gradients, zero drop shadow
            cr.set_source_rgba(255.0 / 255.0, 42.0 / 255.0, 85.0 / 255.0, 1.0)
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

    # -----------------------------------------------------------------
    # Playerctl MPRIS Controls & Info
    # -----------------------------------------------------------------
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
                    ["playerctl", "metadata", "--format", "{{title}}|||{{artist}}"],
                    capture_output=True,
                    text=True,
                    timeout=0.3
                )
                parts = res_meta.stdout.strip().split("|||")
                title = parts[0] if len(parts) > 0 and parts[0] else "Unknown Title"
                artist = parts[1] if len(parts) > 1 and parts[1] else ""
            except Exception:
                title = "Playing Media"
                artist = ""

            self.lbl_title.set_text(title)
            self.lbl_artist.set_text(artist)

            if status == "Playing":
                self.btn_play.set_label("󰏤")
                self.lbl_status.set_text("● Playing")
                self.lbl_status.get_style_context().remove_class("paused")
                self.lbl_status.get_style_context().add_class("playing")
            else:
                self.btn_play.set_label("󰐊")
                self.lbl_status.set_text("󰐎 Paused")
                self.lbl_status.get_style_context().remove_class("playing")
                self.lbl_status.get_style_context().add_class("paused")
        else:
            self.lbl_title.set_text("No media playing")
            self.lbl_artist.set_text("")
            self.btn_play.set_label("󰐊")
            self.lbl_status.set_text("Idle")
            self.lbl_status.get_style_context().remove_class("playing")
            self.lbl_status.get_style_context().remove_class("paused")
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
