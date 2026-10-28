#!/usr/bin/env python3
# control_center.py — Floating quick settings and notifications panel.

import os
import sys
import time
import json
import signal
import subprocess
import threading
import math
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
from palette import PALETTE

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


def token_rgba(name):
    color = Gdk.RGBA()
    color.parse(PALETTE[name])
    return color


def cairo_token(cr, name, opacity=1):
    color = token_rgba(name)
    cr.set_source_rgba(color.red, color.green, color.blue, color.alpha * opacity)


HOLOGRAM_CYAN = Gdk.RGBA()
HOLOGRAM_CYAN.parse("#BDEDF3")
HOLOGRAM_OPACITY = 0.72


def draw_translucent_glass(cr):
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.fill_preserve()
    cr.set_operator(cairo.OPERATOR_OVER)
    cr.set_source_rgba(HOLOGRAM_CYAN.red, HOLOGRAM_CYAN.green, HOLOGRAM_CYAN.blue, HOLOGRAM_OPACITY)
    cr.fill()


class TopCapWidget(Gtk.DrawingArea):
    def __init__(self, height=130):
        super().__init__()
        self.expanded = False
        self.set_size_request(315, height)
        self.connect("draw", self.on_draw)

    def set_expanded(self, expanded):
        if self.expanded != expanded:
            self.expanded = expanded
            self.queue_draw()

    def on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cx = w / 2
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        cr.move_to(0.5, h)
        cr.line_to(0.5, 16)
        cr.arc(16, 16, 15.5, math.pi, 1.5 * math.pi)
        cr.line_to(w - 16, 0.5)
        cr.arc(w - 16, 16, 15.5, 1.5 * math.pi, 2 * math.pi)
        cr.line_to(w - 0.5, h)
        cr.close_path()
        cairo_token(cr, "bg_window")
        cr.fill_preserve()
        cairo_token(cr, "border_window")
        cr.set_line_width(1)
        cr.stroke()

        for radius in (24, 56):
            cr.arc(2, 2, radius, 0, 0.5 * math.pi)
            cairo_token(cr, "accent", 0.25)
            cr.set_line_width(1.5)
            cr.stroke()
            cr.arc(w - 2, 2, radius, 0.5 * math.pi, math.pi)
            cr.stroke()

        cr.arc_negative(cx, h, 78, 0, math.pi)
        cairo_token(cr, "accent")
        cr.fill()
        if not self.expanded:
            cr.rectangle(0, h - 24, w, 24)
            draw_translucent_glass(cr)
        cr.arc(cx, h - 79, 3, 0, 2 * math.pi)
        cairo_token(cr, "bg_window")
        cr.fill()

        if self.expanded:
            cr.arc_negative(cx, h, 59, 0, math.pi)
            draw_translucent_glass(cr)
        else:
            cr.save()
            cr.rectangle(0, 0, w, h - 24)
            cr.clip()
            cr.arc_negative(cx, h, 59, 0, math.pi)
            draw_translucent_glass(cr)
            cr.restore()
        return False


class BottomCapWidget(Gtk.DrawingArea):
    def __init__(self, height=130):
        super().__init__()
        self.expanded = False
        self.set_size_request(315, height)
        self.connect("draw", self.on_draw)

    def set_expanded(self, expanded):
        if self.expanded != expanded:
            self.expanded = expanded
            self.queue_draw()

    def on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cx = w / 2
        cr.set_antialias(cairo.ANTIALIAS_BEST)

        cr.move_to(0.5, 0)
        cr.line_to(w - 0.5, 0)
        cr.line_to(w - 0.5, h - 16)
        cr.arc(w - 16, h - 16, 15.5, 0, 0.5 * math.pi)
        cr.line_to(16, h - 0.5)
        cr.arc(16, h - 16, 15.5, 0.5 * math.pi, math.pi)
        cr.close_path()
        cairo_token(cr, "bg_window")
        cr.fill_preserve()
        cairo_token(cr, "border_window")
        cr.set_line_width(1)
        cr.stroke()

        cr.arc_negative(cx, 0, 78, math.pi, 0)
        cairo_token(cr, "accent")
        cr.fill()
        if not self.expanded:
            cr.rectangle(0, 0, w, 24)
            draw_translucent_glass(cr)
        if self.expanded:
            cr.arc_negative(cx, 0, 59, math.pi, 0)
            draw_translucent_glass(cr)
        else:
            cr.save()
            cr.rectangle(0, 24, w, h - 24)
            cr.clip()
            cr.arc_negative(cx, 0, 59, math.pi, 0)
            draw_translucent_glass(cr)
            cr.restore()

        cr.arc(cx, 79, 3, 0, 2 * math.pi)
        cairo_token(cr, "bg_window")
        cr.fill()

        for radius in (24, 56):
            cr.arc(2, h - 2, radius, 1.5 * math.pi, 2 * math.pi)
            cairo_token(cr, "accent", 0.25)
            cr.set_line_width(1.5)
            cr.stroke()
            cr.arc(w - 2, h - 2, radius, math.pi, 1.5 * math.pi)
            cr.stroke()

        return False


class HologramBridgeWidget(Gtk.DrawingArea):
    def __init__(self, top):
        super().__init__()
        self.top = top
        self.set_size_request(315, 2)
        self.connect("draw", self.on_draw)

    def on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cr.rectangle(0, 0, w, h)
        draw_translucent_glass(cr)
        return False


class ControlCenter(Gtk.Window):
    def __init__(self, initial_page="controls"):
        super().__init__(title="Control Center")
        self.set_name("control-center-window")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(315, -1)
        self.set_size_request(315, -1)

        self.current_page = initial_page
        self.is_open = False
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

        # Keyboard event (Escape closes)
        self.connect("key-press-event", self.on_key_press)
        # NOTE: Auto-dismiss on focus-out removed per user requirement!

        # Signal Handling for Sequential Super+N cycling
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)

        # Trigger async status refresh immediately after showing
        threading.Thread(target=self.refresh_all_status_async, daemon=True).start()
        GLib.timeout_add(3000, self.trigger_async_refresh)

    def on_sigusr1(self, *args):
        # Sequential Super+N:
        if not self.is_open:
            self.open_pokedex("controls")
        elif self.current_page == "controls":
            self.switch_to_page("notifications")
        else:
            self.close_pokedex()
        return GLib.SOURCE_CONTINUE

    def switch_to_page(self, page_name):
        self.current_page = page_name
        self.stack.set_visible_child_name(page_name)
        if page_name == "notifications":
            self.refresh_notifications()

    def open_pokedex(self, target_page=None):
        if target_page:
            self.switch_to_page(target_page)
        self.is_open = True
        self.top_cap.set_expanded(True)
        self.bottom_cap.set_expanded(True)
        self.revealer.set_reveal_child(True)

    def close_pokedex(self):
        if not self.is_open:
            return
        self.is_open = False
        self.top_cap.set_expanded(False)
        self.bottom_cap.set_expanded(False)
        self.revealer.set_reveal_child(False)
        # Collapse and then exit
        GLib.timeout_add(220, self.close_and_quit)

    def on_casing_clicked(self, widget, event):
        if self.is_open:
            self.close_pokedex()
        else:
            self.open_pokedex()
        return True

    def on_window_draw(self, widget, cr):
        # Clear surface to 100% transparent: eliminates outer gray border box!
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
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
        self.css_provider = css_provider
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

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_pokedex()
            return True
        return False

    def close_and_quit(self):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def build_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_vbox.set_name("cc-main-card")

        # =====================================================
        # 1. TOP CASING
        # =====================================================
        top_eventbox = Gtk.EventBox()
        top_eventbox.connect("button-press-event", self.on_casing_clicked)
        top_eventbox.connect("enter-notify-event", self.on_card_hover_enter)
        top_eventbox.connect("leave-notify-event", self.on_card_hover_leave)

        self.top_cap = TopCapWidget(height=130)
        top_eventbox.add(self.top_cap)
        main_vbox.pack_start(top_eventbox, False, False, 0)

        # =====================================================
        # 2. REVEALER: HOLOGRAPHIC VIEWPORT (Between Caps)
        # =====================================================
        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        animations_enabled = Gtk.Settings.get_default().get_property("gtk-enable-animations")
        self.revealer.set_transition_duration(200 if animations_enabled else 0)

        hologram_eventbox = Gtk.EventBox()
        hologram_eventbox.get_style_context().add_class("pokedex-body")
        # Consumes click inside hologram so it DOES NOT close the Pokédex
        hologram_eventbox.connect("button-press-event", lambda w, e: False)

        hologram_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hologram_frame.pack_start(HologramBridgeWidget(top=True), False, False, 0)

        hologram_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hologram_container.get_style_context().add_class("pokedex-hologram")

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150 if animations_enabled else 0)

        # ---------------- PAGE 1: CONTROLS ----------------
        page_controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Original Header: ✿ Control Center | Quick Settings & Alerts
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_bottom(2)
        header_box.get_style_context().add_class("dex-header")

        lbl_flower = Gtk.Label()
        lbl_flower.get_style_context().add_class("dex-header-mark")
        lbl_flower.set_markup("<span font='16'>◆</span>")
        lbl_flower.set_valign(Gtk.Align.CENTER)
        header_box.pack_start(lbl_flower, False, False, 0)

        title_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_title = Gtk.Label()
        lbl_title.get_style_context().add_class("dex-title")
        lbl_title.set_text("Control Center")
        lbl_title.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label()
        lbl_sub.get_style_context().add_class("dex-subtitle")
        lbl_sub.set_text("Quick Settings & Alerts")
        lbl_sub.set_halign(Gtk.Align.START)
        title_vbox.pack_start(lbl_sub, False, False, 0)

        header_box.pack_start(title_vbox, True, True, 0)
        page_controls.pack_start(header_box, False, False, 0)

        # 2x2 Quick Action Tiles
        quick_grid = Gtk.Grid()
        quick_grid.set_column_spacing(8)
        quick_grid.set_row_spacing(8)
        quick_grid.set_column_homogeneous(True)
        quick_grid.set_row_homogeneous(True)

        # Tile 1: Input
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
        self.lbl_ime_sub.set_max_width_chars(16)
        self.lbl_ime_sub.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_ime_sub.set_markup(f"<span font='9.5' color='#3A222A'>{self.status['ime_sub']}</span>")
        vbox_ime.pack_start(self.lbl_ime_sub, False, False, 0)

        self.lbl_ime_note = Gtk.Label()
        card_ime.add(vbox_ime)
        quick_grid.attach(card_ime, 0, 0, 1, 1)

        # Tile 2: Wi-Fi
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
        self.lbl_wifi_sub.set_max_width_chars(16)
        self.lbl_wifi_sub.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_wifi_sub.set_markup(f"<span font='9.5' color='#3A222A'>{self.status['wifi_sub']}</span>")
        vbox_wifi.pack_start(self.lbl_wifi_sub, False, False, 0)

        self.lbl_wifi_ssid = Gtk.Label()
        card_wifi.add(vbox_wifi)
        quick_grid.attach(card_wifi, 1, 0, 1, 1)

        # Tile 3: Bluetooth
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
        self.lbl_bt_sub.set_max_width_chars(16)
        self.lbl_bt_sub.set_ellipsize(Pango.EllipsizeMode.END)
        vbox_bt.pack_start(self.lbl_bt_sub, False, False, 0)

        self.update_bluetooth_ui(self.status.get('bt_on', False), self.status.get('bt_sub', 'Off'))

        card_bt.add(vbox_bt)
        quick_grid.attach(card_bt, 0, 1, 1, 1)

        # Tile 4: Power Mode
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
        self.lbl_pwr_sub.set_max_width_chars(16)
        self.lbl_pwr_sub.set_ellipsize(Pango.EllipsizeMode.END)
        vbox_pwr.pack_start(self.lbl_pwr_sub, False, False, 0)

        self.update_power_ui(self.status.get('power_mode', 'powersave'))

        card_pwr.add(vbox_pwr)
        quick_grid.attach(card_pwr, 1, 1, 1, 1)

        page_controls.pack_start(quick_grid, False, False, 0)

        # Sliders (Volume & Brightness)
        sliders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sliders_box.get_style_context().add_class("dex-slider-pane")

        # Volume Row
        vol_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vol_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.lbl_vol_icon = Gtk.Label()
        self.lbl_vol_icon.get_style_context().add_class("card-icon")
        self.lbl_vol_icon.set_markup("<span font='13'>󰕾</span>")
        self.lbl_vol_icon.set_margin_start(4)
        vol_header.pack_start(self.lbl_vol_icon, False, False, 0)

        lbl_vol_title = Gtk.Label()
        lbl_vol_title.set_markup("<span font='11' weight='bold' color='#201011'> Volume</span>")
        vol_header.pack_start(lbl_vol_title, False, False, 0)

        self.lbl_vol_val = Gtk.Label()
        self.lbl_vol_val.set_markup(f"<span font='10' color='#3A222A'>{self.status['vol']}%</span>")
        vol_header.pack_end(self.lbl_vol_val, False, False, 4)
        vol_box.pack_start(vol_header, False, False, 0)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_name("vol-scale")
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_value(self.status['vol'])
        self.vol_scale.connect("value-changed", self.on_vol_changed)
        vol_box.pack_start(self.vol_scale, False, False, 0)
        sliders_box.pack_start(vol_box, False, False, 0)

        # Brightness Row
        bright_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bright_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        lbl_bright_icon = Gtk.Label()
        lbl_bright_icon.get_style_context().add_class("card-icon")
        lbl_bright_icon.set_markup("<span font='13'>󰃠</span>")
        lbl_bright_icon.set_margin_start(4)
        bright_header.pack_start(lbl_bright_icon, False, False, 0)

        lbl_bright_title = Gtk.Label()
        lbl_bright_title.set_markup("<span font='11' weight='bold' color='#201011'> Brightness</span>")
        bright_header.pack_start(lbl_bright_title, False, False, 0)

        self.lbl_bright_val = Gtk.Label()
        self.lbl_bright_val.set_markup(f"<span font='10' color='#3A222A'>{self.status.get('bright', 60)}%</span>")
        bright_header.pack_end(self.lbl_bright_val, False, False, 4)
        bright_box.pack_start(bright_header, False, False, 0)

        self.bright_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 1)
        self.bright_scale.set_name("bright-scale")
        self.bright_scale.set_draw_value(False)
        self.bright_scale.set_value(self.status.get('bright', 60))
        self.bright_scale.connect("value-changed", self.on_bright_changed)
        bright_box.pack_start(self.bright_scale, False, False, 0)
        sliders_box.pack_start(bright_box, False, False, 0)

        page_controls.pack_start(sliders_box, False, False, 0)
        self.update_vol_icon(self.status['vol'], self.status['muted'])

        # Bottom Power Menu Card
        card_power = Gtk.EventBox()
        card_power.get_style_context().add_class("btn-power-card")
        card_power.connect("button-press-event", lambda w, e: self.launch_app(os.path.expanduser("~/.config/hypr/scripts/Wlogout.sh")))
        card_power.connect("enter-notify-event", self.on_card_hover_enter)
        card_power.connect("leave-notify-event", self.on_card_hover_leave)

        power_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        power_circle = Gtk.Box()
        power_circle.get_style_context().add_class("power-icon-circle")
        power_circle.set_valign(Gtk.Align.CENTER)
        power_circle.set_halign(Gtk.Align.CENTER)
        power_circle.set_size_request(26, 26)

        lbl_power_icon = Gtk.Label()
        lbl_power_icon.get_style_context().add_class("power-icon")
        lbl_power_icon.set_markup("<span font='12'></span>")
        power_circle.pack_start(lbl_power_icon, True, True, 0)
        power_hbox.pack_start(power_circle, False, False, 0)

        lbl_power_label = Gtk.Label()
        lbl_power_label.get_style_context().add_class("power-label")
        lbl_power_label.set_markup("<span font='11.5' weight='bold'>Power Menu</span>")
        lbl_power_label.set_halign(Gtk.Align.START)
        power_hbox.pack_start(lbl_power_label, True, True, 0)

        lbl_arrow = Gtk.Label()
        lbl_arrow.get_style_context().add_class("power-arrow")
        lbl_arrow.set_markup("<span font='12'>&gt;</span>")
        power_hbox.pack_end(lbl_arrow, False, False, 6)

        card_power.add(power_hbox)
        page_controls.pack_start(card_power, False, False, 0)

        self.stack.add_named(page_controls, "controls")

        # ---------------- PAGE 2: NOTIFICATIONS ----------------
        page_notifs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        notif_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_notif_title = Gtk.Label()
        lbl_notif_title.get_style_context().add_class("dex-title")
        lbl_notif_title.set_text("Notifications")
        lbl_notif_title.set_halign(Gtk.Align.START)
        notif_header.pack_start(lbl_notif_title, True, True, 0)

        self.btn_clear = Gtk.Button(label="Clear all")
        self.btn_clear.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_clear.get_style_context().add_class("btn-clear-all")
        self.btn_clear.get_style_context().add_provider(
            self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        self.btn_clear.connect("clicked", self.clear_all_notifications)
        self.btn_clear.set_valign(Gtk.Align.CENTER)
        notif_header.pack_end(self.btn_clear, False, False, 0)

        page_notifs.pack_start(notif_header, False, False, 0)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_name("cc-notif-scroll")
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_propagate_natural_height(True)
        self.scrolled_window.set_max_content_height(280)
        self.scrolled_window.set_min_content_height(240)

        self.notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.scrolled_window.add(self.notif_box)
        self.scrolled_window.get_style_context().add_provider(
            self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        self.scrolled_window.get_child().get_style_context().add_provider(
            self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        page_notifs.pack_start(self.scrolled_window, True, True, 0)

        self.stack.add_named(page_notifs, "notifications")

        hologram_container.pack_start(self.stack, True, True, 0)
        hologram_frame.pack_start(hologram_container, True, True, 0)
        hologram_frame.pack_start(HologramBridgeWidget(top=False), False, False, 0)
        hologram_eventbox.add(hologram_frame)
        self.revealer.add(hologram_eventbox)

        main_vbox.pack_start(self.revealer, True, True, 0)

        # =====================================================
        # 3. BOTTOM CASING
        # =====================================================
        bottom_eventbox = Gtk.EventBox()
        bottom_eventbox.connect("button-press-event", self.on_casing_clicked)
        bottom_eventbox.connect("enter-notify-event", self.on_card_hover_enter)
        bottom_eventbox.connect("leave-notify-event", self.on_card_hover_leave)

        self.bottom_cap = BottomCapWidget(height=130)
        bottom_eventbox.add(self.bottom_cap)
        main_vbox.pack_start(bottom_eventbox, False, False, 0)

        self.add(main_vbox)

        # Load initial notifications
        self.refresh_notifications()

        # Set initial page view
        self.switch_to_page(self.current_page)

        # Start closed with the central hologram
        if "--open" in sys.argv or "--notifications" in sys.argv:
            self.open_pokedex()
        else:
            self.revealer.set_reveal_child(False)
            self.is_open = False

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
            empty_box.set_margin_top(40)
            empty_box.set_margin_bottom(40)
            
            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='24' color='#3A222A'>󰂚</span>")
            empty_box.pack_start(lbl_icon, False, False, 0)

            lbl_empty = Gtk.Label()
            lbl_empty.set_markup("<span font='11' weight='bold' color='#3A222A'>No new notifications</span>")
            empty_box.pack_start(lbl_empty, False, False, 0)

            lbl_sub = Gtk.Label()
            lbl_sub.set_markup("<span font='9.5' color='#3A222A'>You're all caught up!</span>")
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
        item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        item_box.get_style_context().add_class("notif-item")

        badge_box = Gtk.Box()
        badge_box.get_style_context().add_class("notif-badge-box")
        badge_box.get_style_context().add_class(badge_class)
        badge_box.set_size_request(32, 32)
        badge_box.set_valign(Gtk.Align.CENTER)
        badge_box.set_halign(Gtk.Align.CENTER)

        badge_icon = Gtk.Label()
        badge_icon.set_markup(f"<span font='13' color='#FF2A55'>{icon_char}</span>")
        badge_icon.set_valign(Gtk.Align.CENTER)
        badge_icon.set_halign(Gtk.Align.CENTER)
        badge_icon.set_xalign(0.5)
        badge_icon.set_yalign(0.5)
        badge_icon.set_margin_end(2)
        badge_box.pack_start(badge_icon, True, True, 0)

        item_box.pack_start(badge_box, False, False, 0)

        vbox_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_app = Gtk.Label()
        safe_app = GLib.markup_escape_text(app_title)
        lbl_app.set_markup(f"<span font='11.5' weight='bold' color='#201011'>{safe_app}</span>")
        lbl_app.set_halign(Gtk.Align.START)
        lbl_app.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_app.set_max_width_chars(18)
        row1.pack_start(lbl_app, True, True, 0)

        lbl_time = Gtk.Label()
        safe_time = GLib.markup_escape_text(time_ago)
        lbl_time.set_markup(f"<span font='9.5' color='#3A222A'>{safe_time}</span>")
        row1.pack_end(lbl_time, False, False, 0)
        vbox_content.pack_start(row1, False, False, 0)

        if headline:
            lbl_head = Gtk.Label()
            safe_head = GLib.markup_escape_text(headline[:45] + ("..." if len(headline) > 45 else ""))
            lbl_head.set_markup(f"<span font='11' color='#201011'>{safe_head}</span>")
            lbl_head.set_halign(Gtk.Align.START)
            lbl_head.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_head.set_max_width_chars(24)
            vbox_content.pack_start(lbl_head, False, False, 0)

        if detail:
            lbl_detail = Gtk.Label()
            safe_detail = GLib.markup_escape_text(detail[:60] + ("..." if len(detail) > 60 else ""))
            lbl_detail.set_markup(f"<span font='10' color='#3A222A'>{safe_detail}</span>")
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
            self.lbl_vol_icon.set_markup("<span font='21.5' color='#3A222A'>󰖁</span>")
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
        self.lbl_vol_val.set_markup(f"<span font='10' color='#3A222A'>{val}%</span>")
        self.update_vol_icon(val, False)
        self.status['vol'] = val
        self.status['muted'] = False
        threading.Thread(target=lambda v=val: AudioService.set_volume(v), daemon=True).start()

    def on_bright_changed(self, scale):
        if self.updating_sliders:
            return
        val = int(scale.get_value())
        self.lbl_bright_val.set_markup(f"<span font='10' color='#3A222A'>{val}%</span>")
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
            sub_color = "#3A222A"
        else:
            ctx.remove_class("card-icon")
            if not ctx.has_class("card-icon-muted"):
                ctx.add_class("card-icon-muted")
            sub_color = "#3A222A"
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
        self.lbl_pwr_sub.set_markup(f"<span font='9.5' color='#3A222A'>{name}</span>")

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
            self.lbl_ime_sub.set_markup(f"<span font='9.5' color='#3A222A'>{sub}</span>"),
            self.lbl_ime_note.set_markup(f"<span font='9.5' color='#3A222A'>{note}</span>")
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
                    self.lbl_vol_val.set_markup(f"<span font='10' color='#3A222A'>{vol}%</span>")
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
                    self.lbl_bright_val.set_markup(f"<span font='10' color='#3A222A'>{bright}%</span>")
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
                self.lbl_wifi_sub.set_markup(f"<span font='9.5' color='#3A222A'>{sub}</span>"),
                self.lbl_wifi_ssid.set_markup(f"<span font='9.5' color='#3A222A'>{ssid}</span>")
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

    initial_page = "notifications" if "--notifications" in sys.argv else "controls"
    app = ControlCenter(initial_page=initial_page)

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
