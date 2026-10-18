#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA & FENNEKIN ELEGANT FLOATING CONTROL CENTER
# ==============================================================================
# - Floating pop-up card anchored right beneath Waybar's top-right corner.
# - Compact height (does not stretch full screen height).
# - Quick settings: Vietnamese/English IME toggle, Wi-Fi status, Audio Volume slider.
# - REAL notifications section backed by serena_notif_daemon.py and SwayNC.
# - Full-width bottom "Power Menu" button triggering Wlogout.
# - Ultra-fast instantaneous launch (asynchronous status fetching + caching).
# - Pixel-perfect centered power icon & radiant ruby hover glow on all cards.
# ==============================================================================

import os
import sys
import time
import json
import signal
import subprocess
import threading
import gi

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib

PID_FILE = "/tmp/serena_control_center.pid"
CACHE_FILE = os.path.expanduser("~/.cache/serena_notifications.json")
STATUS_CACHE_FILE = "/tmp/serena_status.json"

CSS_DATA = b"""
* {
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Segoe UI', sans-serif;
}

window#control-center-window {
    background: transparent;
}

/* Reset all button / eventbox styles to eliminate GTK Adwaita white bleed */
button,
button:hover,
button:active,
button:focus,
.quick-card,
.btn-power-card,
eventbox {
    background-image: none;
    box-shadow: none;
    outline: none;
    border: none;
}

/* Main Outer Card - Deep Wine Container with Clean Neutral Border */
#cc-main-card {
    background-color: rgba(22, 8, 15, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.80);
    min-width: 380px;
}

/* Header Flower Box */
.header-flower-box {
    background-color: rgba(45, 16, 30, 0.85);
    border-radius: 10px;
    min-width: 34px;
    min-height: 34px;
    padding: 0;
    margin: 0;
}

/* Close Button */
.btn-close {
    color: #E8C2D0;
    background: transparent;
    border: none;
    font-size: 14px;
    padding: 2px 8px;
    border-radius: 8px;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.btn-close:hover {
    color: #FF2A55;
    background-color: rgba(255, 42, 85, 0.15);
}

/* Quick Action Cards (Top 3 Cards) - Borderless Minimalist */
.quick-card {
    background-color: rgba(40, 14, 26, 0.85);
    border: none;
    border-radius: 16px;
    padding: 12px 6px 10px 6px;
    transition: background-color 0.15s ease;
    box-shadow: none;
}

/* Card Hover Effect: Subtle background shift only, zero borders */
.quick-card.card-hover,
.quick-card:hover {
    background-color: rgba(62, 22, 40, 0.95);
    border: none;
    box-shadow: none;
}

.card-icon {
    color: #FF2A55;
    transition: color 0.15s ease;
}

.card-hover .card-icon,
.quick-card:hover .card-icon {
    color: #FF597B;
    text-shadow: none;
}

.card-title {
    color: #FFF0F5;
    transition: color 0.15s ease;
}

.card-hover .card-title,
.quick-card:hover .card-title {
    color: #FFFFFF;
    text-shadow: none;
}

/* Compact Volume Scale Slider */
scale,
scale.horizontal,
#serena-vol-scale,
scale#serena-vol-scale {
    margin: 4px 6px 2px 6px;
    padding: 0;
    -gtk-outline-radius: 3px;
    outline: none;
}

scale trough,
scale.horizontal trough,
#serena-vol-scale trough,
scale#serena-vol-scale trough {
    background-image: none;
    background-color: rgba(60, 24, 38, 0.85);
    border: none;
    border-radius: 3px;
    min-height: 5px;
    box-shadow: none;
}

scale highlight,
scale.horizontal highlight,
scale trough highlight,
scale.horizontal trough highlight,
#serena-vol-scale highlight,
scale#serena-vol-scale highlight,
scale.horizontal#serena-vol-scale highlight,
#serena-vol-scale trough highlight,
scale#serena-vol-scale trough highlight,
scale.horizontal#serena-vol-scale trough highlight,
#serena-vol-scale highlight:hover,
#serena-vol-scale highlight:focus,
#serena-vol-scale highlight:active {
    background-image: none;
    background-color: #FF2A55;
    border: none;
    border-radius: 3px;
    box-shadow: none;
}

scale slider,
scale.horizontal slider,
#serena-vol-scale slider,
scale#serena-vol-scale slider {
    background-image: none;
    background-color: #FFFFFF;
    border: 2px solid #FF2A55;
    border-radius: 50%;
    min-width: 12px;
    min-height: 12px;
    margin: -3.5px;
    box-shadow: none;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}

scale slider:hover,
scale.horizontal slider:hover,
#serena-vol-scale slider:hover,
scale#serena-vol-scale slider:hover {
    background-color: #FFF0F5;
    border-color: #FF597B;
    box-shadow: none;
}

/* Notification Items - Transparent Minimalist */
.notif-item {
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 8px 10px;
    margin: 2px 0;
    transition: background-color 0.15s ease;
    box-shadow: none;
}

.notif-item:hover {
    background-color: rgba(56, 18, 36, 0.45);
    border: none;
    box-shadow: none;
}

/* Badges */
.notif-badge-box {
    border-radius: 10px;
    min-width: 34px;
    min-height: 34px;
    padding: 0;
    margin: 0;
}

.notif-badge-vscode { background-color: #007ACC; }
.notif-badge-discord { background-color: #5865F2; }
.notif-badge-browser { background-color: #E66000; }
.notif-badge-spotify { background-color: #1DB954; }
.notif-badge-terminal { background-color: #4A148C; }
.notif-badge-system { background-color: #8E24AA; }
.notif-badge-default { background-color: #FF2A55; }

/* Custom Minimalist Scrollbar */
#cc-notif-scroll {
    background: transparent;
    border: none;
}

#cc-notif-scroll scrollbar {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    min-width: 4px;
    -GtkScrollbar-has-backward-stepper: false;
    -GtkScrollbar-has-forward-stepper: false;
}

#cc-notif-scroll scrollbar trough {
    background-color: transparent;
    border: none;
}

#cc-notif-scroll scrollbar slider {
    background-color: rgba(255, 42, 85, 0.40);
    border-radius: 4px;
    min-width: 4px;
    border: none;
    transition: all 0.2s ease;
}

#cc-notif-scroll scrollbar slider:hover {
    background-color: #FF2A55;
    min-width: 6px;
}

/* Clear All Button */
.btn-clear-all {
    color: #E8C2D0;
    background: transparent;
    border: none;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 6px;
    transition: all 0.15s ease;
}

.btn-clear-all:hover {
    color: #FF2A55;
    background-color: rgba(255, 42, 85, 0.18);
}

/* Bottom Power Menu Card - Transparent Minimalist */
.btn-power-card {
    background-color: transparent;
    border: none;
    border-radius: 14px;
    padding: 10px 14px;
    transition: background-color 0.15s ease;
    box-shadow: none;
}

.btn-power-card.card-hover,
.btn-power-card:hover {
    background-color: rgba(56, 18, 36, 0.45);
    border: none;
    box-shadow: none;
}

/* Subtle Power Icon */
.power-icon-circle {
    border: none;
    border-radius: 14px;
    min-width: 28px;
    min-height: 28px;
    padding: 0;
    margin: 0;
    background-color: transparent;
    transition: background-color 0.15s ease;
    box-shadow: none;
}

.power-icon {
    color: #FF2A55;
    transition: color 0.15s ease;
}

.btn-power-card.card-hover .power-icon-circle {
    border: none;
    background-color: transparent;
    box-shadow: none;
}

.btn-power-card.card-hover .power-icon {
    color: #FF597B;
}

.power-label {
    color: #FFF0F5;
    transition: color 0.15s ease;
}

.btn-power-card.card-hover .power-label {
    color: #FFFFFF;
    text-shadow: none;
}

.power-arrow {
    color: #A68595;
    transition: color 0.15s ease;
}

.btn-power-card.card-hover .power-arrow {
    color: #FF2A55;
    text-shadow: none;
}
"""

def format_relative_time(timestamp):
    if not timestamp:
        return "just now"
    now = time.time()
    diff = max(0, int(now - timestamp))
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = diff // 60
        return f"{mins}m ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours}h ago"
    else:
        days = diff // 86400
        return f"{days}d ago"

def get_badge_info(app_name):
    low = (app_name or "").lower()
    if "code" in low:
        return "notif-badge-vscode", "󰨞"
    elif "discord" in low:
        return "notif-badge-discord", "󰙯"
    elif "spotify" in low:
        return "notif-badge-spotify", "󰓇"
    elif "firefox" in low or "chrome" in low or "edge" in low or "browser" in low:
        return "notif-badge-browser", "󰈹"
    elif "terminal" in low or "kitty" in low or "alacritty" in low:
        return "notif-badge-terminal", "󰞷"
    elif "system" in low or "update" in low or "ubuntu" in low:
        return "notif-badge-system", "󰒓"
    else:
        return "notif-badge-default", "󰂚"

def ensure_notif_daemon():
    daemon_pid_file = "/tmp/serena_notif_daemon.pid"
    if os.path.exists(daemon_pid_file):
        try:
            with open(daemon_pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return
        except Exception:
            pass

    script = os.path.expanduser("~/.config/hypr/scripts/serena_notif_daemon.py")
    if not os.path.exists(script):
        script = "/home/meobanh/custom/ricing/hyprland-serena/hypr/scripts/serena_notif_daemon.py"
    try:
        subprocess.Popen(["python3", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class SerenaControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Serena Control Center")
        self.set_name("control-center-window")
        self.set_decorated(False)
        self.set_resizable(False)

        self.launch_time = time.time()
        self.mouse_entered = False
        self.updating_sliders = False

        # Load cached status for instant flicker-free rendering
        self.status = self.load_status_cache()

        # Non-blocking daemon check
        threading.Thread(target=ensure_notif_daemon, daemon=True).start()

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "serena-control-center")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 44)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 14)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        else:
            self.set_position(Gtk.WindowPosition.NONE)
            display = Gdk.Display.get_default()
            if display:
                monitor = display.get_primary_monitor() or display.get_monitor(0)
                if monitor:
                    geom = monitor.get_geometry()
                    dash_w = 390
                    x = geom.x + geom.width - dash_w - 14
                    y = geom.y + 44
                    self.move(x, y)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.apply_css()
        self.build_ui()

        # Keyboard events
        self.connect("key-press-event", self.on_key_press)

        # Trigger async status refresh immediately after showing
        threading.Thread(target=self.refresh_all_status_async, daemon=True).start()
        GLib.timeout_add(3000, self.trigger_async_refresh)

    def load_status_cache(self):
        defaults = {
            "vol": 35,
            "muted": False,
            "ime_sub": "Vietnamese",
            "ime_note": "Telex - VIE",
            "wifi_sub": "Connected",
            "wifi_ssid": "Tang2"
        }
        if os.path.exists(STATUS_CACHE_FILE):
            try:
                with open(STATUS_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception:
                pass
        return defaults

    def save_status_cache(self):
        try:
            with open(STATUS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.status, f)
        except Exception:
            pass

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS_DATA)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # Hover Handlers with explicit CSS class switching for 100% reliable GTK EventBox hover
    def on_card_hover_enter(self, widget, event):
        widget.get_style_context().add_class("card-hover")
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
        return False

    def on_card_hover_leave(self, widget, event):
        widget.get_style_context().remove_class("card-hover")
        window = widget.get_window()
        if window:
            window.set_cursor(None)
        return False

    def on_audio_hover_enter(self, widget, event):
        self.card_audio.get_style_context().add_class("card-hover")
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
        return False

    def on_audio_hover_leave(self, widget, event):
        self.card_audio.get_style_context().remove_class("card-hover")
        window = widget.get_window()
        if window:
            window.set_cursor(None)
        return False

    def on_audio_card_clicked(self, widget, event):
        # If clicked above the slider, toggle mute
        scale_alloc = self.vol_scale.get_allocation()
        if event.y < scale_alloc.y:
            self.toggle_audio_mute(widget, event)
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_and_quit()
            return True
        return False

    def on_enter_notify(self, widget, event):
        self.mouse_entered = True
        return False

    def on_focus_out(self, widget, event):
        if time.time() - getattr(self, "launch_time", 0) < 0.8:
            return False
        if getattr(self, "mouse_entered", False):
            self.close_and_quit()
        return False

    def close_and_quit(self):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def build_ui(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        card.set_name("cc-main-card")

        # =====================================================
        # 1. HEADER (🌸 Control Center | Quick settings & notifications)
        # =====================================================
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        flower_box = Gtk.Box()
        flower_box.get_style_context().add_class("header-flower-box")
        flower_box.set_size_request(34, 34)
        flower_box.set_valign(Gtk.Align.CENTER)
        flower_box.set_halign(Gtk.Align.CENTER)

        lbl_flower = Gtk.Label()
        lbl_flower.set_markup("<span font='16' color='#FF2A55'>🌸</span>")
        lbl_flower.set_valign(Gtk.Align.CENTER)
        lbl_flower.set_halign(Gtk.Align.CENTER)
        lbl_flower.set_xalign(0.5)
        lbl_flower.set_yalign(0.5)
        flower_box.pack_start(lbl_flower, True, True, 0)
        header_box.pack_start(flower_box, False, False, 0)

        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span font='15' weight='bold' color='#FFF0F5'>Control Center</span>")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label()
        lbl_sub.set_markup("<span font='10.5' color='#A68595'>Quick settings &amp; notifications</span>")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_sub, False, False, 0)

        header_box.pack_start(title_vbox, True, True, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda x: self.close_and_quit())
        header_box.pack_end(btn_close, False, False, 0)

        card.pack_start(header_box, False, False, 0)

        # =====================================================
        # 2. TOP 3 QUICK ACTION CARDS (Input Method | Wi-Fi | Volume)
        # =====================================================
        quick_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        quick_grid.set_homogeneous(True)

        # --- Card 1: Input Method ---
        card_ime = Gtk.EventBox()
        card_ime.get_style_context().add_class("quick-card")
        card_ime.connect("button-press-event", lambda w, e: self.toggle_ime())
        card_ime.connect("enter-notify-event", self.on_card_hover_enter)
        card_ime.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_ime = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_ime.set_halign(Gtk.Align.CENTER)

        lbl_ime_icon = Gtk.Label()
        lbl_ime_icon.get_style_context().add_class("card-icon")
        lbl_ime_icon.set_markup("<span font='20'>󰌌</span>")
        vbox_ime.pack_start(lbl_ime_icon, False, False, 0)

        lbl_ime_title = Gtk.Label()
        lbl_ime_title.get_style_context().add_class("card-title")
        lbl_ime_title.set_markup("<span font='10.2' weight='bold'>Input Method</span>")
        vbox_ime.pack_start(lbl_ime_title, False, False, 2)

        self.lbl_ime_sub = Gtk.Label()
        self.lbl_ime_sub.set_markup(f"<span font='10.5' color='#E8C2D0'>{self.status['ime_sub']}</span>")
        vbox_ime.pack_start(self.lbl_ime_sub, False, False, 0)

        self.lbl_ime_note = Gtk.Label()
        self.lbl_ime_note.set_markup(f"<span font='9.5' color='#A68595'>{self.status['ime_note']}</span>")
        vbox_ime.pack_start(self.lbl_ime_note, False, False, 0)

        card_ime.add(vbox_ime)
        quick_grid.pack_start(card_ime, True, True, 0)

        # --- Card 2: Wi-Fi ---
        card_wifi = Gtk.EventBox()
        card_wifi.get_style_context().add_class("quick-card")
        card_wifi.connect("button-press-event", lambda w, e: self.launch_app("nm-connection-editor"))
        card_wifi.connect("enter-notify-event", self.on_card_hover_enter)
        card_wifi.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_wifi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_wifi.set_halign(Gtk.Align.CENTER)

        lbl_wifi_icon = Gtk.Label()
        lbl_wifi_icon.get_style_context().add_class("card-icon")
        lbl_wifi_icon.set_markup("<span font='20'>󰖩</span>")
        vbox_wifi.pack_start(lbl_wifi_icon, False, False, 0)

        lbl_wifi_title = Gtk.Label()
        lbl_wifi_title.get_style_context().add_class("card-title")
        lbl_wifi_title.set_markup("<span font='11.5' weight='bold'>Wi-Fi</span>")
        vbox_wifi.pack_start(lbl_wifi_title, False, False, 2)

        self.lbl_wifi_sub = Gtk.Label()
        self.lbl_wifi_sub.set_markup(f"<span font='10.5' color='#E8C2D0'>{self.status['wifi_sub']}</span>")
        vbox_wifi.pack_start(self.lbl_wifi_sub, False, False, 0)

        self.lbl_wifi_ssid = Gtk.Label()
        self.lbl_wifi_ssid.set_markup(f"<span font='9.5' color='#A68595'>{self.status['wifi_ssid']}</span>")
        vbox_wifi.pack_start(self.lbl_wifi_ssid, False, False, 0)

        card_wifi.add(vbox_wifi)
        quick_grid.pack_start(card_wifi, True, True, 0)

        # --- Card 3: Volume ---
        self.card_audio = Gtk.EventBox()
        self.card_audio.get_style_context().add_class("quick-card")
        self.card_audio.connect("button-press-event", self.on_audio_card_clicked)
        self.card_audio.connect("enter-notify-event", self.on_card_hover_enter)
        self.card_audio.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_audio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_audio.set_halign(Gtk.Align.CENTER)

        self.lbl_vol_icon = Gtk.Label()
        self.lbl_vol_icon.get_style_context().add_class("card-icon")
        self.lbl_vol_icon.set_markup("<span font='20'>󰕾</span>")
        vbox_audio.pack_start(self.lbl_vol_icon, False, False, 0)

        lbl_audio_title = Gtk.Label()
        lbl_audio_title.get_style_context().add_class("card-title")
        lbl_audio_title.set_markup("<span font='11.5' weight='bold'>Volume</span>")
        vbox_audio.pack_start(lbl_audio_title, False, False, 2)

        self.lbl_vol_val = Gtk.Label()
        self.lbl_vol_val.set_markup(f"<span font='10.5' color='#E8C2D0'>{self.status['vol']}%</span>")
        vbox_audio.pack_start(self.lbl_vol_val, False, False, 0)

        # Mini Volume Scale
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_name("serena-vol-scale")
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_value(self.status['vol'])
        self.vol_scale.connect("value-changed", self.on_vol_changed)
        vbox_audio.pack_start(self.vol_scale, False, False, 0)

        self.card_audio.add(vbox_audio)
        quick_grid.pack_start(self.card_audio, True, True, 0)
        card.pack_start(quick_grid, False, False, 0)

        # Update initial icon
        self.update_vol_icon(self.status['vol'], self.status['muted'])

        # =====================================================
        # 3. NOTIFICATIONS SECTION (Real Notifications)
        # =====================================================
        notif_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        lbl_notif_title = Gtk.Label()
        lbl_notif_title.set_markup("<span font='13.5' weight='bold' color='#FFF0F5'>Notifications</span>")
        lbl_notif_title.set_halign(Gtk.Align.START)
        notif_header.pack_start(lbl_notif_title, True, True, 0)

        btn_clear = Gtk.Button(label="Clear all")
        btn_clear.get_style_context().add_class("btn-clear-all")
        btn_clear.connect("clicked", self.clear_all_notifications)
        notif_header.pack_end(btn_clear, False, False, 0)

        self.lbl_notif_count = Gtk.Label()
        self.lbl_notif_count.set_markup("<span font='11' color='#A68595'>0 new</span>")
        self.lbl_notif_count.set_margin_end(12)
        notif_header.pack_end(self.lbl_notif_count, False, False, 0)

        card.pack_start(notif_header, False, False, 0)

        # Scrollable Notifications Window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_name("cc-notif-scroll")
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_propagate_natural_height(True)
        self.scrolled_window.set_max_content_height(280)

        # Dynamic Notification Stack
        self.notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.scrolled_window.add(self.notif_box)

        card.pack_start(self.scrolled_window, True, True, 0)

        # Load real notifications immediately from JSON
        self.refresh_notifications()

        # =====================================================
        # 4. BOTTOM POWER MENU CARD (Pixel-Perfect Alignment & Hover)
        # =====================================================
        card_power = Gtk.EventBox()
        card_power.get_style_context().add_class("btn-power-card")
        card_power.connect("button-press-event", lambda w, e: self.launch_app(os.path.expanduser("~/.config/hypr/scripts/Wlogout.sh")))
        card_power.connect("enter-notify-event", self.on_card_hover_enter)
        card_power.connect("leave-notify-event", self.on_card_hover_leave)

        power_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Perfectly centered circular container for power icon
        power_circle = Gtk.Box()
        power_circle.get_style_context().add_class("power-icon-circle")
        power_circle.set_valign(Gtk.Align.CENTER)
        power_circle.set_halign(Gtk.Align.CENTER)
        power_circle.set_size_request(28, 28)

        lbl_power_icon = Gtk.Label()
        lbl_power_icon.get_style_context().add_class("power-icon")
        lbl_power_icon.set_markup("<span font='12.5'></span>")
        lbl_power_icon.set_valign(Gtk.Align.CENTER)
        lbl_power_icon.set_halign(Gtk.Align.CENTER)
        lbl_power_icon.set_xalign(0.5)
        lbl_power_icon.set_yalign(0.5)
        # Optical centering: shift 2px to the left to counteract Nerd Font glyph right-bearing
        lbl_power_icon.set_margin_end(2)
        power_circle.pack_start(lbl_power_icon, True, True, 0)

        power_hbox.pack_start(power_circle, False, False, 0)

        lbl_power_label = Gtk.Label()
        lbl_power_label.get_style_context().add_class("power-label")
        lbl_power_label.set_markup("<span font='13' weight='bold'>Power Menu</span>")
        lbl_power_label.set_halign(Gtk.Align.START)
        lbl_power_label.set_valign(Gtk.Align.CENTER)
        power_hbox.pack_start(lbl_power_label, True, True, 0)

        lbl_arrow = Gtk.Label()
        lbl_arrow.get_style_context().add_class("power-arrow")
        lbl_arrow.set_markup("<span font='13' weight='bold'>&gt;</span>")
        lbl_arrow.set_valign(Gtk.Align.CENTER)
        lbl_arrow.set_margin_end(16)
        power_hbox.pack_end(lbl_arrow, False, False, 0)

        card_power.add(power_hbox)
        card.pack_start(card_power, False, False, 0)

        self.add(card)

    def refresh_notifications(self):
        for child in self.notif_box.get_children():
            self.notif_box.remove(child)

        notifs = []
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    notifs = json.load(f)
            except Exception:
                notifs = []

        count_display = len(notifs)
        self.lbl_notif_count.set_markup(f"<span font='11' color='#A88D9B'>{count_display} new</span>" if count_display > 0 else "<span font='11' color='#A88D9B'>0 new</span>")

        if not notifs:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            empty_box.set_margin_top(10)
            empty_box.set_margin_bottom(10)
            
            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='22' color='#6E485A'>󰂚</span>")
            empty_box.pack_start(lbl_icon, False, False, 0)

            lbl_empty = Gtk.Label()
            lbl_empty.set_markup("<span font='11' weight='bold' color='#E8C2D0'>No new notifications</span>")
            empty_box.pack_start(lbl_empty, False, False, 0)

            lbl_sub = Gtk.Label()
            lbl_sub.set_markup("<span font='9.5' color='#A68595'>You're all caught up!</span>")
            empty_box.pack_start(lbl_sub, False, False, 0)

            self.notif_box.pack_start(empty_box, True, True, 0)
        else:
            for item in notifs[:25]:
                badge_class, icon_char = get_badge_info(item.get("app_name", ""))
                app_title = item.get("app_name", "System")
                time_ago = format_relative_time(item.get("timestamp"))
                headline = item.get("summary", "")
                detail = item.get("body", "")

                card_item = self.create_notification_item(
                    badge_class=badge_class,
                    icon_char=icon_char,
                    app_title=app_title,
                    time_ago=time_ago,
                    headline=headline,
                    detail=detail
                )
                self.notif_box.pack_start(card_item, False, False, 0)

        self.notif_box.show_all()

    def create_notification_item(self, badge_class, icon_char, app_title, time_ago, headline, detail):
        item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        item_box.get_style_context().add_class("notif-item")

        # Perfectly centered square badge box
        badge_box = Gtk.Box()
        badge_box.get_style_context().add_class("notif-badge-box")
        badge_box.get_style_context().add_class(badge_class)
        badge_box.set_size_request(34, 34)
        badge_box.set_valign(Gtk.Align.CENTER)
        badge_box.set_halign(Gtk.Align.CENTER)

        badge_icon = Gtk.Label()
        badge_icon.set_markup(f"<span font='14' color='#FFFFFF'>{icon_char}</span>")
        badge_icon.set_valign(Gtk.Align.CENTER)
        badge_icon.set_halign(Gtk.Align.CENTER)
        badge_icon.set_xalign(0.5)
        badge_icon.set_yalign(0.5)
        # Shift 2px left for optical centering to counteract Nerd Font glyph right-offset
        badge_icon.set_margin_end(2)
        badge_box.pack_start(badge_icon, True, True, 0)

        item_box.pack_start(badge_box, False, False, 0)

        vbox_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_app = Gtk.Label()
        safe_app = GLib.markup_escape_text(app_title)
        lbl_app.set_markup(f"<span font='12' weight='bold' color='#FFF0F5'>{safe_app}</span>")
        lbl_app.set_halign(Gtk.Align.START)
        row1.pack_start(lbl_app, True, True, 0)

        lbl_time = Gtk.Label()
        safe_time = GLib.markup_escape_text(time_ago)
        lbl_time.set_markup(f"<span font='10' color='#A68595'>{safe_time}</span>")
        row1.pack_end(lbl_time, False, False, 0)
        vbox_content.pack_start(row1, False, False, 0)

        if headline:
            lbl_head = Gtk.Label()
            safe_head = GLib.markup_escape_text(headline[:45] + ("..." if len(headline) > 45 else ""))
            lbl_head.set_markup(f"<span font='11.5' color='#FFF0F5'>{safe_head}</span>")
            lbl_head.set_halign(Gtk.Align.START)
            vbox_content.pack_start(lbl_head, False, False, 0)

        if detail:
            lbl_detail = Gtk.Label()
            safe_detail = GLib.markup_escape_text(detail[:60] + ("..." if len(detail) > 60 else ""))
            lbl_detail.set_markup(f"<span font='10.5' color='#A68595'>{safe_detail}</span>")
            lbl_detail.set_halign(Gtk.Align.START)
            vbox_content.pack_start(lbl_detail, False, False, 0)

        item_box.pack_start(vbox_content, True, True, 0)
        return item_box

    def clear_all_notifications(self, widget=None):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass

        threading.Thread(target=lambda: subprocess.run(["swaync-client", "-C"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()
        self.refresh_notifications()

    def launch_app(self, cmd):
        subprocess.Popen(cmd, shell=True)
        self.close_and_quit()

    def toggle_ime(self, widget=None):
        script = os.path.expanduser("~/.config/hypr/scripts/toggle_vietnamese.sh")
        subprocess.run(["bash", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        GLib.timeout_add(100, lambda: threading.Thread(target=self.refresh_ime_async, daemon=True).start())

    def update_vol_icon(self, vol, muted):
        if muted:
            self.lbl_vol_icon.set_markup("<span font='20' color='#8F7481'>󰖁</span>")
        elif vol <= 30:
            self.lbl_vol_icon.set_markup("<span font='20'>󰕿</span>")
        elif vol <= 70:
            self.lbl_vol_icon.set_markup("<span font='20'>󰖀</span>")
        else:
            self.lbl_vol_icon.set_markup("<span font='20'>󰕾</span>")

    def toggle_audio_mute(self, widget=None, event=None):
        def do_toggle():
            subprocess.run(['pamixer', '-t'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                muted = subprocess.check_output(['pamixer', '--get-mute'], stderr=subprocess.DEVNULL).decode().strip() == 'true'
                vol = int(subprocess.check_output(['pamixer', '--get-volume'], stderr=subprocess.DEVNULL).decode().strip())
                GLib.idle_add(lambda: self.update_vol_icon(vol, muted))
            except Exception:
                pass
        threading.Thread(target=do_toggle, daemon=True).start()
        return True

    def on_vol_changed(self, scale):
        if self.updating_sliders:
            return
        val = int(scale.get_value())
        self.lbl_vol_val.set_markup(f"<span font='10.5' color='#E8C2D0'>{val}%</span>")
        self.update_vol_icon(val, False)
        self.status['vol'] = val
        self.status['muted'] = False
        threading.Thread(target=lambda: subprocess.run(['pamixer', '--set-volume', str(val)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()

    # Asynchronous Background Refresh (Zero GUI blocking)
    def trigger_async_refresh(self):
        threading.Thread(target=self.refresh_all_status_async, daemon=True).start()
        return True

    def refresh_ime_async(self):
        try:
            ime_path = os.path.expanduser("~/.config/hypr/scripts/get_ime.sh")
            ime_output = subprocess.check_output(['bash', ime_path], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            ime_output = "ENG"

        is_vie = "VIE" in ime_output
        sub = "Vietnamese" if is_vie else "English"
        note = "Telex - VIE" if is_vie else "US - ENG"

        self.status['ime_sub'] = sub
        self.status['ime_note'] = note

        GLib.idle_add(lambda: (
            self.lbl_ime_sub.set_markup(f"<span font='10.5' color='#E8C2D0'>{sub}</span>"),
            self.lbl_ime_note.set_markup(f"<span font='9.5' color='#A68595'>{note}</span>")
        ))

    def refresh_all_status_async(self):
        # 1. Volume
        try:
            vol = int(subprocess.check_output(['pamixer', '--get-volume'], stderr=subprocess.DEVNULL).decode().strip())
            muted = subprocess.check_output(['pamixer', '--get-mute'], stderr=subprocess.DEVNULL).decode().strip() == 'true'
            self.status['vol'] = vol
            self.status['muted'] = muted
            def apply_vol():
                self.updating_sliders = True
                try:
                    self.vol_scale.set_value(vol)
                    self.lbl_vol_val.set_markup(f"<span font='10.5' color='#E8C2D0'>{vol}%</span>")
                    self.update_vol_icon(vol, muted)
                finally:
                    self.updating_sliders = False
            GLib.idle_add(apply_vol)
        except Exception:
            pass

        # 2. IME
        self.refresh_ime_async()

        # 3. Wi-Fi
        try:
            out = subprocess.check_output("nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2 | head -n1", shell=True).decode().strip()
            if out:
                sub, ssid = "Connected", out
            else:
                sub, ssid = "Disconnected", "Offline"
            self.status['wifi_sub'] = sub
            self.status['wifi_ssid'] = ssid
            GLib.idle_add(lambda: (
                self.lbl_wifi_sub.set_markup(f"<span font='10.5' color='#E8C2D0'>{sub}</span>"),
                self.lbl_wifi_ssid.set_markup(f"<span font='9.5' color='#A68595'>{ssid}</span>")
            ))
        except Exception:
            pass

        # Save latest status cache for next opening
        self.save_status_cache()

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

    app = SerenaControlCenter()

    def cleanup(*args):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    app.connect("destroy", cleanup)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
