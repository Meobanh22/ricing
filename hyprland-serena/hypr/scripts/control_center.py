#!/usr/bin/env python3
# Floating quick settings and notifications panel.

import os
import sys
import time
import json
import signal
import subprocess
import threading
import cairo
import gi

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, Pango

PID_FILE = "/tmp/control_center.pid"
CACHE_FILE = os.path.expanduser("~/.cache/notifications.json")
STATUS_CACHE_FILE = "/tmp/status.json"

# Path to external CSS stylesheet
STYLESHEET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "control_center.css")

# Services
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from services.audio import AudioService
from services.brightness import BrightnessService
from services.bluetooth import BluetoothService
from services.power import PowerService

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
    daemon_pid_file = "/tmp/notif_daemon.pid"
    if os.path.exists(daemon_pid_file):
        try:
            with open(daemon_pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return
        except Exception:
            pass

    script = os.path.expanduser("~/.config/hypr/scripts/notif_daemon.py")
    if not os.path.exists(script):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notif_daemon.py")
    try:
        subprocess.Popen(["python3", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class ControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Control Center")
        self.set_name("control-center-window")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(315, -1)
        self.set_size_request(315, -1)

        self.launch_time = time.time()
        self.mouse_entered = False
        self.updating_sliders = False

        # Load cached status for instant flicker-free rendering
        self.status = self.load_status_cache()

        # Non-blocking daemon check
        threading.Thread(target=ensure_notif_daemon, daemon=True).start()

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "control-center")
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
                    dash_w = 315
                    x = geom.x + geom.width - dash_w - 14
                    y = geom.y + 44
                    self.move(x, y)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", self.on_window_draw)

        self.apply_css()
        self.build_ui()

        # Keyboard events
        self.connect("key-press-event", self.on_key_press)

        # Trigger async status refresh immediately after showing
        threading.Thread(target=self.refresh_all_status_async, daemon=True).start()
        GLib.timeout_add(3000, self.trigger_async_refresh)

    def on_window_draw(self, widget, cr):
        # 1. Clear surface to 100% transparent (eliminates sharp rectangle leak)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # 2. Draw perfectly rounded 16px background squircle
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

        # Fill with the shared window background token.
        cr.set_source_rgba(32.0 / 255.0, 16.0 / 255.0, 18.0 / 255.0, 0.98)
        cr.fill_preserve()

        # Draw the shared outer window border.
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        return False

    def load_status_cache(self):
        defaults = {
            "vol": 35,
            "muted": False,
            "bright": 60,
            "bt_on": False,
            "bt_sub": "Off",
            "power_mode": "powersave",
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
        css_file = STYLESHEET_PATH
        if not os.path.exists(css_file):
            css_file = os.path.expanduser("~/.config/hypr/styles/control_center.css")
        if os.path.exists(css_file):
            try:
                css_provider.load_from_path(css_file)
            except Exception as e:
                print(f"Warning: Failed to load CSS from {css_file}: {e}", file=sys.stderr)
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
        self.toggle_audio_mute(widget, event)
        return False

    def on_audio_card_scroll(self, widget, event):
        vol = self.status.get('vol', 50)
        direction = event.direction
        if direction == Gdk.ScrollDirection.UP:
            vol = min(100, vol + 5)
        elif direction == Gdk.ScrollDirection.DOWN:
            vol = max(0, vol - 5)
        elif direction == Gdk.ScrollDirection.SMOOTH:
            _, delta_x, delta_y = event.get_scroll_deltas()
            if delta_y < 0:
                vol = min(100, vol + 5)
            elif delta_y > 0:
                vol = max(0, vol - 5)
            else:
                return False
        else:
            return False
        self.status['vol'] = vol
        self.status['muted'] = False
        self.lbl_vol_val.set_markup(f"<span font='10' color='#E8C2D0'>{vol}%</span>")
        self.update_vol_icon(vol, False)
        threading.Thread(target=lambda v=vol: subprocess.run(['pamixer', '--set-volume', str(v)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()
        return True

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
        # 1. HEADER (Control Center | Quick Settings & Alerts)
        # =====================================================
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        lbl_flower = Gtk.Label()
        lbl_flower.set_markup("<span font='16' color='#FF2A55'>✿</span>")
        lbl_flower.set_valign(Gtk.Align.CENTER)
        header_box.pack_start(lbl_flower, False, False, 0)

        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<span font='14' weight='bold' color='#FFF0F5'>Control Center</span>")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label()
        lbl_sub.set_markup("<span font='10' color='#A68595'>Quick Settings &amp; Alerts</span>")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_sub, False, False, 0)

        header_box.pack_start(title_vbox, True, True, 0)

        card.pack_start(header_box, False, False, 0)

        # =====================================================
        # 2. TOP QUICK ACTION TILES (2x2 Grid)
        # =====================================================
        quick_grid = Gtk.Grid()
        quick_grid.set_column_spacing(8)
        quick_grid.set_row_spacing(8)
        quick_grid.set_column_homogeneous(True)
        quick_grid.set_row_homogeneous(True)

        # --- Card 1: Input Method (Col 0, Row 0) ---
        card_ime = Gtk.EventBox()
        card_ime.get_style_context().add_class("quick-card")
        card_ime.connect("button-press-event", lambda w, e: self.toggle_ime())
        card_ime.connect("enter-notify-event", self.on_card_hover_enter)
        card_ime.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_ime = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_ime.set_halign(Gtk.Align.CENTER)

        lbl_ime_icon = Gtk.Label()
        lbl_ime_icon.get_style_context().add_class("card-icon")
        lbl_ime_icon.set_markup("<span font='18'>󰌌</span>")
        vbox_ime.pack_start(lbl_ime_icon, False, False, 0)

        lbl_ime_title = Gtk.Label()
        lbl_ime_title.get_style_context().add_class("card-title")
        lbl_ime_title.set_markup("<span font='10.5' weight='bold'>Input</span>")
        vbox_ime.pack_start(lbl_ime_title, False, False, 0)

        self.lbl_ime_sub = Gtk.Label()
        self.lbl_ime_sub.set_markup(f"<span font='9.5' color='#E8C2D0'>{self.status['ime_sub']}</span>")
        vbox_ime.pack_start(self.lbl_ime_sub, False, False, 0)

        self.lbl_ime_note = Gtk.Label()
        card_ime.add(vbox_ime)
        quick_grid.attach(card_ime, 0, 0, 1, 1)

        # --- Card 2: Wi-Fi (Col 1, Row 0) ---
        card_wifi = Gtk.EventBox()
        card_wifi.get_style_context().add_class("quick-card")
        card_wifi.connect("button-press-event", lambda w, e: self.launch_app("nm-connection-editor"))
        card_wifi.connect("enter-notify-event", self.on_card_hover_enter)
        card_wifi.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_wifi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_wifi.set_halign(Gtk.Align.CENTER)

        lbl_wifi_icon = Gtk.Label()
        lbl_wifi_icon.get_style_context().add_class("card-icon")
        lbl_wifi_icon.set_markup("<span font='18'>󰖩</span>")
        vbox_wifi.pack_start(lbl_wifi_icon, False, False, 0)

        lbl_wifi_title = Gtk.Label()
        lbl_wifi_title.get_style_context().add_class("card-title")
        lbl_wifi_title.set_markup("<span font='10.5' weight='bold'>Wi-Fi</span>")
        vbox_wifi.pack_start(lbl_wifi_title, False, False, 0)

        self.lbl_wifi_sub = Gtk.Label()
        self.lbl_wifi_sub.set_markup(f"<span font='9.5' color='#E8C2D0'>{self.status['wifi_sub']}</span>")
        vbox_wifi.pack_start(self.lbl_wifi_sub, False, False, 0)

        self.lbl_wifi_ssid = Gtk.Label()
        card_wifi.add(vbox_wifi)
        quick_grid.attach(card_wifi, 1, 0, 1, 1)

        # --- Card 3: Bluetooth (Col 0, Row 1) ---
        card_bt = Gtk.EventBox()
        card_bt.get_style_context().add_class("quick-card")
        card_bt.connect("button-press-event", lambda w, e: self.toggle_bluetooth())
        card_bt.connect("enter-notify-event", self.on_card_hover_enter)
        card_bt.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_bt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_bt.set_halign(Gtk.Align.CENTER)

        self.lbl_bt_icon = Gtk.Label()
        self.lbl_bt_icon.get_style_context().add_class("card-icon")
        vbox_bt.pack_start(self.lbl_bt_icon, False, False, 0)

        lbl_bt_title = Gtk.Label()
        lbl_bt_title.get_style_context().add_class("card-title")
        lbl_bt_title.set_markup("<span font='10.5' weight='bold'>Bluetooth</span>")
        vbox_bt.pack_start(lbl_bt_title, False, False, 0)

        self.lbl_bt_sub = Gtk.Label()
        vbox_bt.pack_start(self.lbl_bt_sub, False, False, 0)

        self.update_bluetooth_ui(self.status.get('bt_on', False), self.status.get('bt_sub', 'Off'))

        card_bt.add(vbox_bt)
        quick_grid.attach(card_bt, 0, 1, 1, 1)

        # --- Card 4: Power Mode (Col 1, Row 1) ---
        card_pwr = Gtk.EventBox()
        card_pwr.get_style_context().add_class("quick-card")
        card_pwr.connect("button-press-event", lambda w, e: self.toggle_power_mode(w, e))
        card_pwr.connect("enter-notify-event", self.on_card_hover_enter)
        card_pwr.connect("leave-notify-event", self.on_card_hover_leave)

        vbox_pwr = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_pwr.set_halign(Gtk.Align.CENTER)

        self.lbl_pwr_icon = Gtk.Label()
        self.lbl_pwr_icon.get_style_context().add_class("card-icon")
        vbox_pwr.pack_start(self.lbl_pwr_icon, False, False, 0)

        lbl_pwr_title = Gtk.Label()
        lbl_pwr_title.get_style_context().add_class("card-title")
        lbl_pwr_title.set_markup("<span font='10.5' weight='bold'>Power Mode</span>")
        vbox_pwr.pack_start(lbl_pwr_title, False, False, 0)

        self.lbl_pwr_sub = Gtk.Label()
        vbox_pwr.pack_start(self.lbl_pwr_sub, False, False, 0)

        self.update_power_ui(self.status.get('power_mode', 'powersave'))

        card_pwr.add(vbox_pwr)
        quick_grid.attach(card_pwr, 1, 1, 1, 1)

        card.pack_start(quick_grid, False, False, 0)

        # =====================================================
        # SLIDERS SECTION (Volume & Brightness)
        # =====================================================
        sliders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # 1. Volume Row
        vol_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vol_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.lbl_vol_icon = Gtk.Label()
        self.lbl_vol_icon.get_style_context().add_class("card-icon")
        self.lbl_vol_icon.set_markup("<span font='13'>󰕾</span>")
        self.lbl_vol_icon.set_margin_start(4)
        vol_header.pack_start(self.lbl_vol_icon, False, False, 0)

        lbl_vol_title = Gtk.Label()
        lbl_vol_title.set_markup("<span font='11' weight='bold' color='#FFF0F5'> Volume</span>")
        vol_header.pack_start(lbl_vol_title, False, False, 0)

        self.lbl_vol_val = Gtk.Label()
        self.lbl_vol_val.set_markup(f"<span font='10' color='#E8C2D0'>{self.status['vol']}%</span>")
        vol_header.pack_end(self.lbl_vol_val, False, False, 4)
        vol_box.pack_start(vol_header, False, False, 0)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_name("vol-scale")
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_value(self.status['vol'])
        self.vol_scale.connect("value-changed", self.on_vol_changed)
        vol_box.pack_start(self.vol_scale, False, False, 0)
        sliders_box.pack_start(vol_box, False, False, 0)

        # 2. Brightness Row
        bright_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bright_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        lbl_bright_icon = Gtk.Label()
        lbl_bright_icon.get_style_context().add_class("card-icon")
        lbl_bright_icon.set_markup("<span font='13'>󰃠</span>")
        lbl_bright_icon.set_margin_start(4)
        bright_header.pack_start(lbl_bright_icon, False, False, 0)

        lbl_bright_title = Gtk.Label()
        lbl_bright_title.set_markup("<span font='11' weight='bold' color='#FFF0F5'> Brightness</span>")
        bright_header.pack_start(lbl_bright_title, False, False, 0)

        self.lbl_bright_val = Gtk.Label()
        self.lbl_bright_val.set_markup(f"<span font='10' color='#E8C2D0'>{self.status.get('bright', 60)}%</span>")
        bright_header.pack_end(self.lbl_bright_val, False, False, 4)
        bright_box.pack_start(bright_header, False, False, 0)

        self.bright_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 1)
        self.bright_scale.set_name("bright-scale")
        self.bright_scale.set_draw_value(False)
        self.bright_scale.set_value(self.status.get('bright', 60))
        self.bright_scale.connect("value-changed", self.on_bright_changed)
        bright_box.pack_start(self.bright_scale, False, False, 0)
        sliders_box.pack_start(bright_box, False, False, 0)

        card.pack_start(sliders_box, False, False, 0)

        # Update initial icons
        self.update_vol_icon(self.status['vol'], self.status['muted'])

        # =====================================================
        # 3. NOTIFICATIONS SECTION (Real Notifications)
        # =====================================================
        notif_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        lbl_notif_title = Gtk.Label()
        lbl_notif_title.set_markup("<span font='13.5' weight='bold' color='#FFF0F5'>Notifications</span>")
        lbl_notif_title.set_halign(Gtk.Align.START)
        notif_header.pack_start(lbl_notif_title, True, True, 0)

        self.btn_clear = Gtk.Button(label="Clear all")
        self.btn_clear.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_clear.get_style_context().add_class("btn-clear-all")
        self.btn_clear.connect("clicked", self.clear_all_notifications)
        self.btn_clear.set_valign(Gtk.Align.CENTER)
        notif_header.pack_end(self.btn_clear, False, False, 0)

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

        self.btn_clear.set_visible(bool(notifs))

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
        lbl_app.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_app.set_max_width_chars(18)
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
            lbl_head.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_head.set_max_width_chars(24)
            vbox_content.pack_start(lbl_head, False, False, 0)

        if detail:
            lbl_detail = Gtk.Label()
            safe_detail = GLib.markup_escape_text(detail[:60] + ("..." if len(detail) > 60 else ""))
            lbl_detail.set_markup(f"<span font='10.5' color='#A68595'>{safe_detail}</span>")
            lbl_detail.set_halign(Gtk.Align.START)
            lbl_detail.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_detail.set_max_width_chars(26)
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
            self.lbl_vol_icon.set_markup("<span font='21.5' color='#8F7481'>󰖁</span>")
        elif vol <= 30:
            self.lbl_vol_icon.set_markup("<span font='21.5'>󰕿</span>")
        elif vol <= 70:
            self.lbl_vol_icon.set_markup("<span font='21.5'>󰖀</span>")
        else:
            self.lbl_vol_icon.set_markup("<span font='21.5'>󰕾</span>")

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
        self.lbl_vol_val.set_markup(f"<span font='10' color='#E8C2D0'>{val}%</span>")
        self.update_vol_icon(val, False)
        self.status['vol'] = val
        self.status['muted'] = False
        threading.Thread(target=lambda v=val: AudioService.set_volume(v), daemon=True).start()

    def on_bright_changed(self, scale):
        if self.updating_sliders:
            return
        val = int(scale.get_value())
        self.lbl_bright_val.set_markup(f"<span font='10' color='#E8C2D0'>{val}%</span>")
        self.status['bright'] = val
        threading.Thread(target=lambda v=val: BrightnessService.set_brightness(v), daemon=True).start()

    POWER_ICONS = {
        "powersave": "",
        "balanced": "",
        "performance": ""
    }

    def update_bluetooth_ui(self, bt_on: bool, sub: str):
        ctx = self.lbl_bt_icon.get_style_context()
        if bt_on:
            ctx.remove_class("card-icon-muted")
            if not ctx.has_class("card-icon"):
                ctx.add_class("card-icon")
            sub_color = "#E8C2D0"
        else:
            ctx.remove_class("card-icon")
            if not ctx.has_class("card-icon-muted"):
                ctx.add_class("card-icon-muted")
            sub_color = "#A68595"
        self.lbl_bt_icon.set_markup("<span font='18'>󰂯</span>")
        self.lbl_bt_sub.set_markup(f"<span font='9.5' color='{sub_color}'>{sub}</span>")

    def toggle_bluetooth(self):
        def do_toggle():
            new_state = BluetoothService.toggle_power()
            self.status['bt_on'] = new_state
            dev_name = BluetoothService.get_connected_device_name() if new_state else ""
            sub = dev_name if dev_name else ("On" if new_state else "Off")
            self.status['bt_sub'] = sub
            GLib.idle_add(lambda: self.update_bluetooth_ui(new_state, sub))
            self.save_status_cache()
        threading.Thread(target=do_toggle, daemon=True).start()

    def update_power_ui(self, mode: str):
        icon = self.POWER_ICONS.get(mode, "")
        name = mode.capitalize()
        self.lbl_pwr_icon.set_markup(f"<span font='18'>{icon}</span>")
        self.lbl_pwr_sub.set_markup(f"<span font='9.5' color='#E8C2D0'>{name}</span>")

    def toggle_power_mode(self, widget=None, event=None):
        def do_toggle():
            cur = self.status.get('power_mode', 'powersave')
            order = ["powersave", "balanced", "performance"]
            try:
                idx = order.index(cur)
                next_p = order[(idx + 1) % len(order)]
            except ValueError:
                next_p = "powersave"
            PowerService.set_power_mode(next_p)
            self.status['power_mode'] = next_p
            GLib.idle_add(lambda: self.update_power_ui(next_p))
            self.save_status_cache()
        threading.Thread(target=do_toggle, daemon=True).start()
        return True

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
            self.lbl_ime_sub.set_markup(f"<span font='9.5' color='#E8C2D0'>{sub}</span>"),
            self.lbl_ime_note.set_markup(f"<span font='9.5' color='#A68595'>{note}</span>")
        ))

    def refresh_all_status_async(self):
        # 1. Volume
        try:
            vol = AudioService.get_volume()
            muted = AudioService.is_muted()
            self.status['vol'] = vol
            self.status['muted'] = muted
            def apply_vol():
                self.updating_sliders = True
                try:
                    self.vol_scale.set_value(vol)
                    self.lbl_vol_val.set_markup(f"<span font='10' color='#E8C2D0'>{vol}%</span>")
                    self.update_vol_icon(vol, muted)
                finally:
                    self.updating_sliders = False
            GLib.idle_add(apply_vol)
        except Exception:
            pass

        # 2. Brightness
        try:
            bright = BrightnessService.get_brightness()
            self.status['bright'] = bright
            def apply_bright():
                self.updating_sliders = True
                try:
                    self.bright_scale.set_value(bright)
                    self.lbl_bright_val.set_markup(f"<span font='10' color='#E8C2D0'>{bright}%</span>")
                finally:
                    self.updating_sliders = False
            GLib.idle_add(apply_bright)
        except Exception:
            pass

        # 3. Bluetooth
        try:
            bt_on = BluetoothService.is_enabled()
            dev_name = BluetoothService.get_connected_device_name() if bt_on else ""
            sub = dev_name if dev_name else ("On" if bt_on else "Off")
            self.status['bt_on'] = bt_on
            self.status['bt_sub'] = sub
            GLib.idle_add(lambda: self.update_bluetooth_ui(bt_on, sub))
        except Exception:
            pass

        # 4. Power Mode
        try:
            pwr = PowerService.get_power_mode()
            self.status['power_mode'] = pwr
            GLib.idle_add(lambda: self.update_power_ui(pwr))
        except Exception:
            pass

        # 5. IME
        self.refresh_ime_async()

        # 6. Wi-Fi
        try:
            out = subprocess.check_output("nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2 | head -n1", shell=True).decode().strip()
            if out:
                sub, ssid = "Connected", out
            else:
                sub, ssid = "Disconnected", "Offline"
            self.status['wifi_sub'] = sub
            self.status['wifi_ssid'] = ssid
            GLib.idle_add(lambda: (
                self.lbl_wifi_sub.set_markup(f"<span font='9.5' color='#E8C2D0'>{sub}</span>"),
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

    app = ControlCenter()

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
