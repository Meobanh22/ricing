#!/usr/bin/env python3
# shelf.py — Clipboard history and file shelf window with previews and drag-and-drop.

import os
import sys
import time
import shutil
import json
import subprocess
import cairo
import socket
import glob
import signal

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango, GdkPixbuf

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

# Unified Tactile Theme tokens (matches widgets & Waybar)
C_LIGHT_BG = C_BG_CREAM
C_RUBY_PRI = C_BG_WAYBAR
C_RUBY_MUT = C_TEXT_MUT

# Paths & Directories
SHELF_DIR = os.path.expanduser("~/.cache/shelf")
if not os.path.exists(SHELF_DIR) and os.path.exists(os.path.expanduser("~/.cache/serena/shelf")):
    SHELF_DIR = os.path.expanduser("~/.cache/serena/shelf")

CLIPHIST_DB = os.path.expanduser("~/.cache/cliphist/db")
PID_FILE = "/tmp/shelf.pid"
MODE_FILE = "/tmp/shelf.mode"

PINNED_FILE = os.path.expanduser("~/.cache/shelf_pinned_clips.json")
if not os.path.exists(PINNED_FILE) and os.path.exists(os.path.expanduser("~/.cache/serena_pinned_clips.json")):
    PINNED_FILE = os.path.expanduser("~/.cache/serena_pinned_clips.json")

PINS_DIR = os.path.expanduser("~/.cache/shelf_pins")
if not os.path.exists(PINS_DIR) and os.path.exists(os.path.expanduser("~/.cache/serena_pins")):
    PINS_DIR = os.path.expanduser("~/.cache/serena_pins")

POSITION_CACHE = "/tmp/shelf_pos.json"
os.makedirs(SHELF_DIR, exist_ok=True)
os.makedirs(PINS_DIR, exist_ok=True)

TARGET_URI_LIST = 80
TARGET_TEXT = 81

DROP_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
    Gtk.TargetEntry.new("text/plain", 0, TARGET_TEXT),
]

DRAG_SOURCE_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
]

# Path to external CSS stylesheet
STYLESHEET_PATH = os.path.join(HYPR_DIR, "styles", "shelf.css")


class ShelfWindow(Gtk.Window):
    def __init__(self, initial_tab="clip"):
        super().__init__(type=Gtk.WindowType.TOPLEVEL, title="Shelf")
        self.set_name("shelf-window")
        self.set_wmclass("shelf", "shelf")

        # 1. Main Layer Shell Setup via shared DraggablePopup manager
        def shelf_bounds(x, y, mon_w, mon_h):
            return max(10, min(mon_w - 475, x)), max(10, min(mon_h - 100, y))

        self.drag_manager = DraggablePopup(
            self,
            name="shelf",
            default_pos=lambda mw, mh: (int((mw - 464) / 2), 44),
            bounds_fn=shelf_bounds,
            on_drag_start=self.hide_popout
        )
        self.drag_manager.init_layer_shell(
            namespace="shelf",
            layer=GtkLayerShell.Layer.TOP,
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND
        )

        # Dynamic comfortable width (480px: spacious 2-column cards & drop frame)
        self.set_title("Shelf")
        self.set_name("shelf-window-root")
        self.set_default_size(480, -1)
        self.set_resizable(False)

        # Set transparent RGBA visual and app_paintable to eliminate sharp corner leakage
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect("draw", self.on_window_draw)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_file = STYLESHEET_PATH
        if not os.path.exists(css_file):
            css_file = os.path.expanduser("~/.config/hypr/styles/shelf.css")
        if os.path.exists(css_file):
            try:
                css_provider.load_from_path(css_file)
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_USER + 10
                )
            except Exception as e:
                print(f"Warning: CSS error: {e}", file=sys.stderr)

        self.active_tab = initial_tab
        self.last_mode_mtime = 0
        self.last_clip_mtime = 0
        self.popout_timer = None
        self.current_popout_target = None
        self.lightbox_win = None

        # Ensure daemon is running
        self.ensure_cliphist_daemon()

        # Build UI
        self.build_ui()

        # Build External Floating Popout Window (Can extend OUTSIDE clipboard window)
        self.build_external_popout_window()

        # Events
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)

        # Drag-and-drop target for whole window
        self.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.connect("drag-data-received", self.on_window_drag_data_received)

        # Switch to initial tab
        self.switch_tab(initial_tab)

        # Timers: hotkey mode check & cliphist db watcher
        GLib.timeout_add(150, self.check_mode_change)
        GLib.timeout_add(300, self.check_cliphist_update)

    def on_window_draw(self, widget, cr):
        # Clear surface to transparent for CSS border rendering
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def on_popout_draw(self, widget, cr):
        # 1. Clear surface to transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # 2. Draw rounded squircle for external floating popout card
        alloc = widget.get_allocation()
        pad = 1.0
        w = float(alloc.width) - pad * 2.0
        h = float(alloc.height) - pad * 2.0
        x = pad
        y = pad
        r = 14.0

        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.57079632679, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.57079632679)
        cr.arc(x + r, y + h - r, r, 1.57079632679, 3.14159265359)
        cr.arc(x + r, y + r, r, 3.14159265359, 4.71238898038)
        cr.close_path()

        # Light cream card background
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 0.98))
        cr.fill_preserve()

        # 3D wine border
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 1.0))
        cr.set_line_width(2.0)
        cr.stroke()

        return False

    def on_lightbox_draw(self, widget, cr):
        # 1. Clear surface to transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # 2. Draw rounded squircle for lightbox modal
        alloc = widget.get_allocation()
        pad = 1.0
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

        # Light cream background
        cr.set_source_rgba(*hex_to_rgba(C_TEXT_PRI, 0.98))
        cr.fill_preserve()

        # 3D wine border
        cr.set_source_rgba(*hex_to_rgba(C_BORDER_3D, 1.0))
        cr.set_line_width(2.5)
        cr.stroke()

        return False

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

    def save_window_pos(self):
        self.drag_manager.save_position()

    def reset_window_pos(self):
        self.drag_manager.reset_to_default()

    # === PINNED CLIP PERSISTENCE ===
    def load_pinned_clips(self):
        if os.path.exists(PINNED_FILE):
            try:
                with open(PINNED_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_pinned_clips(self, pins):
        try:
            with open(PINNED_FILE, "w", encoding="utf-8") as f:
                json.dump(pins, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error saving pinned clips:", e)

    def is_item_pinned(self, item, pins=None):
        if pins is None:
            pins = self.load_pinned_clips()
        if item.get("is_pinned"):
            return True
        for p in pins:
            if item.get("is_image") and p.get("is_image"):
                if p.get("id") == item.get("id") or (p.get("raw") and p.get("raw") == item.get("raw")):
                    return True
            elif not item.get("is_image") and not p.get("is_image"):
                t1 = (item.get("full_text") or item.get("preview", "")).strip()
                t2 = (p.get("full_text") or p.get("preview", "")).strip()
                if t1 and t1 == t2:
                    return True
        return False

    def toggle_pin_clip(self, item):
        self.hide_popout()
        pins = self.load_pinned_clips()
        found_idx = -1
        for idx, p in enumerate(pins):
            if item.get("is_image") and p.get("is_image"):
                if p.get("id") == item.get("id") or (p.get("raw") and p.get("raw") == item.get("raw")):
                    found_idx = idx
                    break
            elif not item.get("is_image") and not p.get("is_image"):
                t1 = (item.get("full_text") or item.get("preview", "")).strip()
                t2 = (p.get("full_text") or p.get("preview", "")).strip()
                if t1 and t1 == t2:
                    found_idx = idx
                    break

        if found_idx >= 0:
            removed = pins.pop(found_idx)
            if removed.get("img_path") and os.path.exists(removed["img_path"]):
                try:
                    os.remove(removed["img_path"])
                except Exception:
                    pass
            self.save_pinned_clips(pins)
            self.show_toast("📌 Unpinned")
        else:
            pin_id = f"pin_{int(time.time() * 1000)}"
            new_pin = {
                "id": pin_id,
                "is_image": item.get("is_image", False),
                "preview": item.get("preview", ""),
                "is_pinned": True,
                "pinned_at": time.time(),
                "raw": item.get("raw", "")
            }
            if item.get("is_image"):
                pin_img_path = os.path.join(PINS_DIR, f"{pin_id}.png")
                try:
                    if item.get("img_path") and os.path.exists(item["img_path"]):
                        shutil.copy2(item["img_path"], pin_img_path)
                    else:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        img_data, _ = p.communicate(input=item["raw"].encode("utf-8"), timeout=1.5)
                        with open(pin_img_path, "wb") as f:
                            f.write(img_data)
                    new_pin["img_path"] = pin_img_path
                except Exception:
                    pass
            else:
                new_pin["full_text"] = item.get("full_text") or item.get("preview", "")

            pins.insert(0, new_pin)
            self.save_pinned_clips(pins)
            self.show_toast("📌 Pinned to top!")

        self.refresh_clipboard()

    def ensure_cliphist_daemon(self):
        try:
            res = subprocess.run(["pgrep", "-f", "cliphist store"], stdout=subprocess.DEVNULL)
            if res.returncode != 0:
                subprocess.Popen(["wl-paste", "--type", "text", "--watch", "cliphist", "store"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.Popen(["wl-paste", "--type", "image", "--watch", "cliphist", "store"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def get_monitor_geometry(self):
        return get_monitor_geometry()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_size_request(480, -1)
        main_box.get_style_context().add_class("shelf-window")

        # --- HEADER ---
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header_hbox.set_margin_start(16)
        header_hbox.set_margin_end(16)
        header_hbox.set_margin_top(16)
        header_hbox.set_margin_bottom(10)

        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.get_style_context().add_class("tab-switcher")

        # Tab: Clipboard
        self.btn_tab_clip = Gtk.Button()
        self.lbl_tab_clip = Gtk.Label()
        self.lbl_tab_clip.set_markup(f"<span font='12' color='#FFFFFF'>󰅌</span>   <span color='#FFFFFF'><b>Clipboard</b></span>")
        self.btn_tab_clip.add(self.lbl_tab_clip)
        self.btn_tab_clip.get_style_context().add_class("tab-btn")
        self.btn_tab_clip.connect("clicked", lambda w: self.switch_tab("clip"))
        tab_box.pack_start(self.btn_tab_clip, False, False, 0)

        # Tab: Shelf
        self.btn_tab_shelf = Gtk.Button()
        self.lbl_tab_shelf = Gtk.Label()
        self.lbl_tab_shelf.set_markup(f"<span font='12' color='{C_ACCENT}'>󰏖</span>   <span color='{C_RUBY_PRI}'>Shelf</span>")
        self.btn_tab_shelf.add(self.lbl_tab_shelf)
        self.btn_tab_shelf.get_style_context().add_class("tab-btn")
        self.btn_tab_shelf.connect("clicked", lambda w: self.switch_tab("shelf"))
        tab_box.pack_start(self.btn_tab_shelf, False, False, 0)

        header_hbox.pack_start(tab_box, False, False, 0)

        # Drag Handle Grip Zone (Draggable Window Feature)
        self.drag_handle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.drag_handle_box.set_hexpand(True)
        self.drag_handle_box.get_style_context().add_class("drag-grip-zone")
        pill = Gtk.Box()
        pill.get_style_context().add_class("drag-handle-pill")
        pill.set_valign(Gtk.Align.CENTER)
        pill.set_halign(Gtk.Align.CENTER)
        pill.set_size_request(38, 4)
        self.drag_handle_box.pack_start(pill, True, True, 0)
        self.drag_handle_box.set_tooltip_text("Drag header to move · Double-click to center")
        header_hbox.pack_start(self.drag_handle_box, True, True, 4)

        # Right actions
        self.header_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Stash Button
        self.btn_stash_clip = Gtk.Button()
        self.lbl_stash = Gtk.Label()
        self.lbl_stash.set_markup(f"<span font='11' color='{C_ACCENT}'>󰅍</span>  <span color='{C_RUBY_PRI}'>Stash</span>")
        self.btn_stash_clip.add(self.lbl_stash)
        self.btn_stash_clip.get_style_context().add_class("action-btn")
        self.btn_stash_clip.set_tooltip_text("Save current clipboard content into shelf")
        self.btn_stash_clip.connect("clicked", self.on_stash_clipboard_clicked)
        self.header_actions_box.pack_start(self.btn_stash_clip, False, False, 0)

        # Clear All Button
        self.btn_clear_all = Gtk.Button()
        self.lbl_clear = Gtk.Label()
        self.lbl_clear.set_markup(f"<span font='12' color='{C_ACCENT}'>󰆴</span>")
        self.btn_clear_all.add(self.lbl_clear)
        self.btn_clear_all.get_style_context().add_class("action-btn")
        self.btn_clear_all.set_tooltip_text("Clear all items")
        self.btn_clear_all.connect("clicked", self.on_clear_clicked)
        self.header_actions_box.pack_start(self.btn_clear_all, False, False, 0)

        # Close Button
        btn_close = Gtk.Button()
        lbl_close = Gtk.Label()
        lbl_close.set_markup(f"<span font='12' color='{C_RUBY_PRI}'>✕</span>")
        btn_close.add(lbl_close)
        btn_close.get_style_context().add_class("btn-close")
        btn_close.set_tooltip_text("Close (Esc)")
        btn_close.connect("clicked", lambda w: self.close_window())
        self.header_actions_box.pack_end(btn_close, False, False, 0)

        header_hbox.pack_end(self.header_actions_box, False, False, 0)

        # Wrap header in EventBox for smooth window dragging
        self.header_event_box = Gtk.EventBox()
        self.header_event_box.set_visible_window(False)
        self.drag_manager.attach_header(self.header_event_box)
        self.header_event_box.add(header_hbox)
        main_box.pack_start(self.header_event_box, False, False, 0)

        # --- BODY (STACK) ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)

        self.clip_page = self.build_clipboard_page()
        self.stack.add_named(self.clip_page, "clip")

        self.shelf_page = self.build_shelf_page()
        self.stack.add_named(self.shelf_page, "shelf")

        main_box.pack_start(self.stack, True, True, 4)

        # --- FOOTER (Status Toast only, no tip text) ---
        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.get_style_context().add_class("status-bar")
        self.lbl_status.set_halign(Gtk.Align.START)
        self.lbl_status.set_margin_start(16)
        self.lbl_status.set_margin_bottom(12)
        main_box.pack_end(self.lbl_status, False, False, 0)

        self.add(main_box)

    # === EXTERNAL FLOATING POPOUT WINDOW ===
    def build_external_popout_window(self):
        self.popout_win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.popout_win.set_name("shelf-popout-root")
        GtkLayerShell.init_for_window(self.popout_win)
        GtkLayerShell.set_namespace(self.popout_win, "shelf-popout")
        GtkLayerShell.set_layer(self.popout_win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self.popout_win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self.popout_win, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self.popout_win, GtkLayerShell.Edge.RIGHT, False)
        GtkLayerShell.set_anchor(self.popout_win, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_keyboard_mode(self.popout_win, GtkLayerShell.KeyboardMode.NONE)

        screen = self.popout_win.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.popout_win.set_visual(visual)
        self.popout_win.set_app_paintable(True)
        self.popout_win.connect("draw", self.on_popout_draw)

        self.popout_event_box = Gtk.EventBox()
        self.popout_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.popout_box.get_style_context().add_class("popout-card")
        self.popout_box.set_margin_start(12)
        self.popout_box.set_margin_end(12)
        self.popout_box.set_margin_top(12)
        self.popout_box.set_margin_bottom(12)
        self.popout_event_box.add(self.popout_box)
        self.popout_event_box.connect("enter-notify-event", lambda w, e: self.cancel_popout(w))
        self.popout_event_box.connect("leave-notify-event", self.on_popout_leave)
        self.popout_event_box.connect("button-press-event", self.on_popout_clicked)

        self.popout_win.add(self.popout_event_box)

    # === CLIPBOARD TAB ===
    def build_clipboard_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        self.clip_search = Gtk.SearchEntry()
        self.clip_search.set_placeholder_text("Search clips...")
        self.clip_search.get_style_context().add_class("search-entry")
        self.clip_search.set_margin_bottom(8)
        self.clip_search.connect("search-changed", lambda e: self.refresh_clipboard())
        vbox.pack_start(self.clip_search, False, False, 0)

        # Stack for switching between Empty State and Content State
        self.clip_stack = Gtk.Stack()
        self.clip_stack.set_transition_type(Gtk.StackTransitionType.NONE)

        # 1. Empty State View (Perfect center across entire window width)
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_halign(Gtk.Align.CENTER)
        empty_box.set_hexpand(True)
        empty_box.set_vexpand(True)
        empty_box.set_margin_top(48)
        empty_box.set_margin_bottom(48)

        lbl_icon = Gtk.Label()
        lbl_icon.set_markup(f"<span font='28' color='{C_ACCENT}'>󰅌</span>")
        empty_box.pack_start(lbl_icon, False, False, 0)

        lbl_msg = Gtk.Label()
        lbl_msg.set_markup(f"<span font='11' color='{C_RUBY_MUT}'>No clipboard items found</span>")
        empty_box.pack_start(lbl_msg, False, False, 0)

        self.clip_stack.add_named(empty_box, "empty")

        # 2. Content State View: ScrolledWindow with 2-column FlowBox
        self.clip_scroll = Gtk.ScrolledWindow()
        self.clip_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.clip_scroll.set_propagate_natural_height(True)
        self.clip_scroll.set_min_content_height(100)
        self.clip_scroll.set_max_content_height(400)
        self.clip_scroll.get_vadjustment().connect("value-changed", lambda a: self.hide_popout())

        # Two-column clipboard card grid.
        self.clip_flow = Gtk.FlowBox()
        self.clip_flow.set_valign(Gtk.Align.START)
        self.clip_flow.set_max_children_per_line(2)
        self.clip_flow.set_min_children_per_line(1)
        self.clip_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.clip_flow.set_row_spacing(10)
        self.clip_flow.set_column_spacing(10)
        self.clip_flow.set_homogeneous(True)
        self.clip_flow.set_margin_end(8)
        self.clip_flow.set_margin_start(0)

        self.clip_scroll.add(self.clip_flow)
        self.clip_stack.add_named(self.clip_scroll, "content")

        vbox.pack_start(self.clip_stack, True, True, 0)

        return vbox

    def refresh_clipboard(self):
        self.hide_popout()
        for child in self.clip_flow.get_children():
            self.clip_flow.remove(child)

        query = self.clip_search.get_text().strip().lower()
        clips = []
        seen_text_previews = set()

        # 1. Load pinned clips at top of list
        pins = self.load_pinned_clips()
        filtered_pins = []
        for p in pins:
            p_item = dict(p)
            p_item["is_pinned"] = True
            if not p_item.get("is_image"):
                txt = (p_item.get("full_text") or p_item.get("preview") or "").strip()
                seen_text_previews.add(txt)
            if query:
                p_txt = (p_item.get("full_text") or p_item.get("preview") or "").lower()
                if query not in p_txt:
                    continue
            filtered_pins.append(p_item)

        try:
            res = subprocess.run(["cliphist", "list"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and res.stdout:
                stdout_text = res.stdout.decode("utf-8", errors="replace")
                for line in stdout_text.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t", 1)
                    clip_id = parts[0]
                    preview = parts[1] if len(parts) > 1 else ""

                    is_image = "binary data" in preview.lower() or "[[ binary data" in preview.lower()

                    # Deduplicate exact text entries only
                    if not is_image:
                        norm_preview = preview.strip()
                        if norm_preview in seen_text_previews:
                            continue
                        seen_text_previews.add(norm_preview)

                    if query and query not in preview.lower():
                        continue

                    # Skip if already displayed in pinned section
                    if self.is_item_pinned({"id": clip_id, "is_image": is_image, "raw": line, "preview": preview}, pins):
                        continue

                    clips.append({
                        "id": clip_id,
                        "raw": line,
                        "preview": preview,
                        "is_image": is_image,
                        "is_pinned": False
                    })
        except Exception:
            pass

        all_clips = filtered_pins + clips

        if not all_clips:
            self.clip_stack.set_visible_child_name("empty")
            self.clip_stack.show_all()
            return

        self.clip_stack.set_visible_child_name("content")
        for item in all_clips[:24]:
            chip = self.create_clip_card(item)
            self.clip_flow.add(chip)

        self.clip_flow.show_all()
        self.clip_stack.show_all()

    def create_clip_card(self, item):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("chip-card")
        if item.get("is_pinned"):
            event_box.get_style_context().add_class("pinned")
        event_box.set_size_request(190, -1)
        event_box.set_hexpand(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # Top row: Type indicator (Inset with 8px margin) + Right actions (Pin + Zoom + Delete)
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        lbl_icon = Gtk.Label()
        lbl_icon.set_margin_start(8)
        if item["is_image"]:
            lbl_icon.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰋩</span>  <span font='10' color='{C_RUBY_MUT}'>Image</span>")
        else:
            lbl_icon.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰈙</span>  <span font='10' color='{C_RUBY_MUT}'>Text</span>")
        top_row.pack_start(lbl_icon, False, False, 0)

        # Right actions in header: Pin + Zoom (if image) + Delete
        right_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Pin button.
        btn_pin = Gtk.Button()
        btn_pin.set_relief(Gtk.ReliefStyle.NONE)
        btn_pin.get_style_context().add_class("flat")
        btn_pin.get_style_context().add_class("chip-btn-pin")
        lbl_p = Gtk.Label()
        if item.get("is_pinned"):
            btn_pin.get_style_context().add_class("pinned")
            lbl_p.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰤲</span>")
            btn_pin.set_tooltip_text("Unpin clip")
        else:
            lbl_p.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰤱</span>")
            btn_pin.set_tooltip_text("Pin clip to top")
        btn_pin.add(lbl_p)
        btn_pin.connect("clicked", lambda b: self.toggle_pin_clip(item))
        btn_pin.connect("enter-notify-event", lambda w, e: self.hide_popout())
        right_hdr.pack_start(btn_pin, False, False, 0)

        if item["is_image"]:
            btn_zoom = Gtk.Button()
            btn_zoom.set_relief(Gtk.ReliefStyle.NONE)
            btn_zoom.get_style_context().add_class("flat")
            btn_zoom.get_style_context().add_class("chip-btn-del")
            lbl_z = Gtk.Label()
            lbl_z.set_markup(f"<span font='9.5' color='{C_ACCENT}'>󰍉</span>")
            btn_zoom.add(lbl_z)
            btn_zoom.set_tooltip_text("Zoom image full-size")
            btn_zoom.connect("clicked", lambda b: self.open_image_lightbox(item, is_shelf=False))
            btn_zoom.connect("enter-notify-event", lambda w, e: self.hide_popout())
            right_hdr.pack_start(btn_zoom, False, False, 0)

        # Compact delete button.
        btn_del = Gtk.Button()
        btn_del.set_relief(Gtk.ReliefStyle.NONE)
        btn_del.get_style_context().add_class("flat")
        btn_del.get_style_context().add_class("chip-btn-del")
        lbl_x = Gtk.Label()
        lbl_x.set_markup(f"<span font='9.5' color='{C_RUBY_PRI}'>✕</span>")
        btn_del.add(lbl_x)
        btn_del.set_tooltip_text("Delete")
        btn_del.connect("clicked", lambda b: self.delete_clip(item))
        btn_del.connect("enter-notify-event", lambda w, e: self.hide_popout())
        right_hdr.pack_end(btn_del, False, False, 2)

        top_row.pack_end(right_hdr, False, False, 0)
        vbox.pack_start(top_row, False, False, 0)

        # Content: Image thumbnail or Text snippet
        if item["is_image"]:
            try:
                if item.get("img_path") and os.path.exists(item["img_path"]):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(item["img_path"])
                else:
                    p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    img_data, _ = p.communicate(input=item["raw"].encode("utf-8"), timeout=1.0)
                    loader = GdkPixbuf.PixbufLoader()
                    loader.write(img_data)
                    loader.close()
                    pixbuf = loader.get_pixbuf()

                orig_w = pixbuf.get_width()
                orig_h = pixbuf.get_height()
                ratio = min(175 / orig_w, 90 / orig_h)
                scaled_w = max(1, int(orig_w * ratio))
                scaled_h = max(1, int(orig_h * ratio))
                card_pixbuf = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.BILINEAR)
                img = Gtk.Image.new_from_pixbuf(card_pixbuf)
                img.set_halign(Gtk.Align.CENTER)
                vbox.pack_start(img, False, False, 2)
            except Exception:
                lbl_fallback = Gtk.Label(label="[Image Preview]")
                lbl_fallback.get_style_context().add_class("chip-text")
                vbox.pack_start(lbl_fallback, False, False, 0)
        else:
            clean_txt = (item.get("full_text") or item.get("preview") or "").strip()
            lbl_txt = Gtk.Label()
            lbl_txt.get_style_context().add_class("chip-text")
            lbl_txt.set_text(clean_txt)
            lbl_txt.set_line_wrap(True)
            lbl_txt.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            lbl_txt.set_max_width_chars(22)
            lbl_txt.set_lines(4)
            lbl_txt.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_txt.set_halign(Gtk.Align.START)
            lbl_txt.set_margin_start(4)
            vbox.pack_start(lbl_txt, False, False, 2)

        event_box.add(vbox)
        event_box.connect("button-press-event", lambda w, e: self.on_clip_chip_clicked(item, e))

        # External hover popout trigger (elevate and preview outside window)
        event_box.connect("enter-notify-event", lambda w, e: self.schedule_popout(w, item, is_shelf=False))
        event_box.connect("leave-notify-event", lambda w, e: self.cancel_popout(w))

        return event_box

    # === FILE SHELF TAB ===
    def build_shelf_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        self.shelf_stack = Gtk.Stack()
        self.shelf_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.shelf_stack.set_transition_duration(120)

        # 1. Empty State View: Full-width comfortable drop zone
        self.empty_shelf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.drop_box_empty = Gtk.EventBox()
        self.drop_box_empty.get_style_context().add_class("drop-zone")
        self.drop_box_empty.set_hexpand(True)
        self.drop_box_empty.set_vexpand(True)
        self.drop_box_empty.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.drop_box_empty.connect("drag-data-received", self.on_drop_zone_received)

        v_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        v_content.set_valign(Gtk.Align.CENTER)
        v_content.set_halign(Gtk.Align.CENTER)

        lbl_icon = Gtk.Label()
        lbl_icon.get_style_context().add_class("drop-icon")
        lbl_icon.set_markup("󰉍")
        v_content.pack_start(lbl_icon, False, False, 0)

        lbl_title = Gtk.Label(label="Drop files or images here")
        lbl_title.get_style_context().add_class("drop-title")
        v_content.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label="Drag items out to upload · Or click Stash to save clipboard")
        lbl_sub.get_style_context().add_class("drop-subtitle")
        v_content.pack_start(lbl_sub, False, False, 0)

        self.drop_box_empty.add(v_content)
        self.empty_shelf_box.pack_start(self.drop_box_empty, True, True, 0)
        self.shelf_stack.add_named(self.empty_shelf_box, "empty")

        # 2. Content State View: Compact drop banner + ScrolledWindow FlowBox
        self.content_shelf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Full-width compact drop banner at top
        self.drop_banner = Gtk.EventBox()
        self.drop_banner.get_style_context().add_class("drop-banner")
        self.drop_banner.set_hexpand(True)
        self.drop_banner.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.drop_banner.connect("drag-data-received", self.on_drop_zone_received)

        banner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        banner_box.set_halign(Gtk.Align.CENTER)
        lbl_b_icon = Gtk.Label()
        lbl_b_icon.set_markup(f"<span font='11.5' color='{C_ACCENT}'>󰉍</span>  <span font='10.5' color='{C_TEXT_SEC}'>Drop files/images here to add</span>")
        banner_box.pack_start(lbl_b_icon, False, False, 0)
        self.drop_banner.add(banner_box)
        self.content_shelf_box.pack_start(self.drop_banner, False, False, 0)

        self.shelf_scroll = Gtk.ScrolledWindow()
        self.shelf_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.shelf_scroll.set_propagate_natural_height(True)
        self.shelf_scroll.set_min_content_height(100)
        self.shelf_scroll.set_max_content_height(400)
        self.shelf_scroll.get_vadjustment().connect("value-changed", lambda a: self.hide_popout())

        self.shelf_flow = Gtk.FlowBox()
        self.shelf_flow.set_valign(Gtk.Align.START)
        self.shelf_flow.set_max_children_per_line(2)
        self.shelf_flow.set_min_children_per_line(1)
        self.shelf_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.shelf_flow.set_row_spacing(10)
        self.shelf_flow.set_column_spacing(10)
        self.shelf_flow.set_homogeneous(True)
        self.shelf_flow.set_margin_end(8)
        self.shelf_flow.set_margin_start(0)

        self.shelf_scroll.add(self.shelf_flow)
        self.content_shelf_box.pack_start(self.shelf_scroll, True, True, 0)
        self.shelf_stack.add_named(self.content_shelf_box, "content")

        vbox.pack_start(self.shelf_stack, True, True, 0)
        return vbox

    def refresh_shelf(self):
        self.hide_popout()
        for child in self.shelf_flow.get_children():
            self.shelf_flow.remove(child)

        files = []
        try:
            for fname in os.listdir(SHELF_DIR):
                fpath = os.path.join(SHELF_DIR, fname)
                if os.path.isfile(fpath):
                    files.append((fpath, os.path.getmtime(fpath)))
            files.sort(key=lambda x: x[1], reverse=True)
        except Exception:
            pass

        self.update_shelf_badge(len(files))

        if not files:
            self.shelf_stack.set_visible_child_name("empty")
            self.shelf_stack.show_all()
            return

        self.shelf_stack.set_visible_child_name("content")
        for fpath, mtime in files:
            chip = self.create_shelf_card(fpath, mtime)
            self.shelf_flow.add(chip)

        self.shelf_flow.show_all()
        self.shelf_stack.show_all()

    @staticmethod
    def get_file_info(fpath):
        fname = os.path.basename(fpath).lower()
        ext = os.path.splitext(fname)[1]
        
        # Images
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico"]:
            return "󰋩", "Image", "image"
        # Code & Scripts
        elif ext in [".py", ".sh", ".bash", ".zsh", ".lua", ".js", ".ts", ".html", ".css", ".json", ".c", ".cpp", ".rs", ".go", ".php", ".java"]:
            return "󰌠" if ext == ".py" else "󰈙", "Code", "code"
        # Documents & Text
        elif ext in [".txt", ".md", ".pdf", ".doc", ".docx", ".odt", ".rtf", ".log", ".csv"]:
            return "󰈮" if ext == ".pdf" else "󰈙", "Document", "doc"
        # Archives & Compressed
        elif ext in [".zip", ".tar", ".gz", ".xz", ".7z", ".rar", ".bz2", ".tgz"]:
            return "󰗚", "Archive", "archive"
        # Audio
        elif ext in [".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus"]:
            return "󰎆", "Audio", "audio"
        # Video
        elif ext in [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"]:
            return "󰈔", "Video", "video"
        else:
            return "󰈢", "File", "other"

    def create_shelf_card(self, fpath, mtime):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("chip-card")
        event_box.set_size_request(190, 160)
        event_box.set_hexpand(True)

        # Drag-out source
        event_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, DRAG_SOURCE_TARGETS, Gdk.DragAction.COPY)
        event_box.connect("drag-data-get", self.on_shelf_drag_data_get, fpath)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath) if os.path.exists(fpath) else 0
        size_str = self.format_file_size(fsize)
        icon, type_label, category = self.get_file_info(fpath)
        is_image = (category == "image")

        # Top row: Icon / Format (Inset with 8px margin) + Delete button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lbl_type = Gtk.Label()
        lbl_type.set_margin_start(8)
        lbl_type.set_markup(f"<span font='9.5' color='{C_ACCENT}'>{icon}</span>  <span font='9.5' color='{C_RUBY_MUT}'>{type_label}</span>")
        top_row.pack_start(lbl_type, False, False, 0)

        right_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        if is_image:
            btn_zoom = Gtk.Button()
            btn_zoom.set_relief(Gtk.ReliefStyle.NONE)
            btn_zoom.get_style_context().add_class("flat")
            btn_zoom.get_style_context().add_class("chip-btn-del")
            lbl_z = Gtk.Label()
            lbl_z.set_markup(f"<span font='9.5' color='{C_ACCENT}'>󰍉</span>")
            btn_zoom.add(lbl_z)
            btn_zoom.set_tooltip_text("Zoom image full-size")
            btn_zoom.connect("clicked", lambda b: self.open_image_lightbox(fpath, is_shelf=True))
            btn_zoom.connect("enter-notify-event", lambda w, e: self.hide_popout())
            right_hdr.pack_start(btn_zoom, False, False, 0)

        btn_del = Gtk.Button()
        btn_del.set_relief(Gtk.ReliefStyle.NONE)
        btn_del.get_style_context().add_class("flat")
        btn_del.get_style_context().add_class("chip-btn-del")
        lbl_x = Gtk.Label()
        lbl_x.set_markup(f"<span font='9.5' color='{C_RUBY_PRI}'>✕</span>")
        btn_del.add(lbl_x)
        btn_del.set_tooltip_text("Remove")
        btn_del.connect("clicked", lambda b: self.remove_shelf_file(fpath))
        btn_del.connect("enter-notify-event", lambda w, e: self.hide_popout())
        right_hdr.pack_end(btn_del, False, False, 2)

        top_row.pack_end(right_hdr, False, False, 0)
        vbox.pack_start(top_row, False, False, 0)

        # Fixed height preview box (80px) to guarantee identical layout regardless of content
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_box.set_size_request(-1, 80)
        preview_box.set_valign(Gtk.Align.CENTER)
        preview_box.set_halign(Gtk.Align.FILL)

        if is_image:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(fpath)
                orig_w = pixbuf.get_width()
                orig_h = pixbuf.get_height()
                ratio = min(175 / orig_w, 80 / orig_h)
                scaled_w = max(1, int(orig_w * ratio))
                scaled_h = max(1, int(orig_h * ratio))
                card_pixbuf = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.BILINEAR)
                img = Gtk.Image.new_from_pixbuf(card_pixbuf)
                img.set_halign(Gtk.Align.CENTER)
                preview_box.pack_start(img, True, True, 0)
            except Exception:
                lbl_fb = Gtk.Label(label="[Image]")
                lbl_fb.get_style_context().add_class("chip-text")
                preview_box.pack_start(lbl_fb, True, True, 0)
        elif category in ["code", "doc"]:
            preview_text = ""
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    lines = [f.readline().strip() for _ in range(3)]
                    preview_text = "\n".join([l for l in lines if l][:2])
            except Exception:
                pass

            if preview_text:
                lbl_snippet = Gtk.Label()
                lbl_snippet.get_style_context().add_class("chip-text")
                lbl_snippet.set_text(preview_text)
                lbl_snippet.set_line_wrap(True)
                lbl_snippet.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl_snippet.set_max_width_chars(22)
                lbl_snippet.set_ellipsize(Pango.EllipsizeMode.END)
                lbl_snippet.set_halign(Gtk.Align.START)
                lbl_snippet.set_margin_start(4)
                lbl_snippet.set_margin_end(4)
                preview_box.pack_start(lbl_snippet, True, True, 0)
            else:
                icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                icon_box.set_valign(Gtk.Align.CENTER)
                lbl_big = Gtk.Label()
                lbl_big.set_markup(f"<span font='28' color='{C_ACCENT}'>{icon}</span>")
                icon_box.pack_start(lbl_big, False, False, 0)
                preview_box.pack_start(icon_box, True, True, 0)
        else:
            icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            icon_box.set_valign(Gtk.Align.CENTER)
            lbl_big = Gtk.Label()
            lbl_big.set_markup(f"<span font='28' color='{C_ACCENT}'>{icon}</span>")
            icon_box.pack_start(lbl_big, False, False, 0)
            preview_box.pack_start(icon_box, True, True, 0)

        vbox.pack_start(preview_box, True, True, 2)

        # Filename
        short_name = fname if len(fname) < 24 else fname[:21] + "..."
        lbl_name = Gtk.Label(label=short_name)
        lbl_name.get_style_context().add_class("chip-text")
        lbl_name.set_halign(Gtk.Align.START)
        lbl_name.set_margin_start(4)
        vbox.pack_start(lbl_name, False, False, 0)

        # Bottom info row (ALWAYS pinned to bottom of the card)
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bottom_row.set_valign(Gtk.Align.END)
        lbl_size = Gtk.Label(label=size_str)
        lbl_size.get_style_context().add_class("chip-meta")
        lbl_size.set_margin_start(4)
        bottom_row.pack_start(lbl_size, False, False, 0)

        btn_copy = Gtk.Button()
        lbl_cp = Gtk.Label()
        lbl_cp.set_markup(f"<span font='9.5' color='{C_RUBY_PRI}'>Copy</span>")
        btn_copy.add(lbl_cp)
        btn_copy.get_style_context().add_class("chip-btn-action")
        btn_copy.connect("clicked", lambda b: self.copy_shelf_file(fpath, is_image))
        bottom_row.pack_end(btn_copy, False, False, 0)
        vbox.pack_end(bottom_row, False, False, 0)

        event_box.add(vbox)
        event_box.connect("button-press-event", lambda w, e: self.on_shelf_chip_clicked(fpath, e))

        # External hover popout trigger
        event_box.connect("enter-notify-event", lambda w, e: self.schedule_popout(w, None, is_shelf=True, fpath=fpath))
        event_box.connect("leave-notify-event", lambda w, e: self.cancel_popout(w))

        return event_box

    # === EXTERNAL FLOATING POPOUT ENGINE ===
    def schedule_popout(self, card_widget, item, is_shelf=False, fpath=None):
        if self.popout_timer:
            GLib.source_remove(self.popout_timer)
            self.popout_timer = None

        def do_show():
            self.show_popout(card_widget, item, is_shelf, fpath)
            self.popout_timer = None
            return False

        # 150ms debounce for smooth, deliberate elevation
        self.popout_timer = GLib.timeout_add(150, do_show)

    def cancel_popout(self, card_widget):
        if self.popout_timer:
            GLib.source_remove(self.popout_timer)
            self.popout_timer = None

    def show_popout(self, card_widget, item, is_shelf=False, fpath=None):
        if not card_widget.get_realized():
            return

        coords = card_widget.translate_coordinates(self, 0, 0)
        if not coords:
            return

        mon_w, mon_h = self.get_monitor_geometry()
        win_w = 464
        main_win_screen_x = getattr(self, 'current_win_x', (mon_w - win_w) // 2)
        main_win_screen_y = getattr(self, 'current_win_y', 44)

        card_x, card_y = coords

        # Clear existing popout content
        for child in self.popout_box.get_children():
            self.popout_box.remove(child)

        self.current_popout_target = (item, is_shelf, fpath)

        # Keep the preview clear of the cursor and card actions.
        popout_w = 260
        if card_x < win_w / 2:
            # Left column: Float to the LEFT side of the main window
            pop_screen_x = main_win_screen_x - popout_w - 14
            if pop_screen_x < 10:
                pop_screen_x = main_win_screen_x + win_w + 14
        else:
            # Right column: Float to the RIGHT side of the main window
            pop_screen_x = main_win_screen_x + win_w + 14
            if pop_screen_x + popout_w > mon_w - 10:
                pop_screen_x = main_win_screen_x - popout_w - 14

        pop_screen_y = max(10, min(main_win_screen_y + card_y, mon_h - 260))

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Header Row
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_type = Gtk.Label()
        lbl_type.set_margin_start(8)

        right_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        is_img_target = (item and item.get("is_image")) or (is_shelf and fpath and fpath.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")))

        if is_img_target:
            btn_zoom_pop = Gtk.Button()
            btn_zoom_pop.set_relief(Gtk.ReliefStyle.NONE)
            btn_zoom_pop.get_style_context().add_class("action-btn")
            lbl_zp = Gtk.Label()
            lbl_zp.set_markup(f"<span font='9.5' color='{C_ACCENT}'>󰍉 Zoom</span>")
            btn_zoom_pop.add(lbl_zp)
            target_ref = item if not is_shelf else fpath
            btn_zoom_pop.connect("clicked", lambda b: self.open_image_lightbox(target_ref, is_shelf))
            right_actions.pack_start(btn_zoom_pop, False, False, 0)

        lbl_hint = Gtk.Label()
        lbl_hint.set_markup(f"<span font='9.5' color='{C_ACCENT}'>󰆏 Copy</span>" if not is_shelf else f"<span font='9.5' color='{C_ACCENT}'>󰅍 Open</span>")
        lbl_hint.set_margin_end(6)
        right_actions.pack_end(lbl_hint, False, False, 0)
        top_row.pack_end(right_actions, False, False, 0)

        if not is_shelf and item:
            if item["is_image"]:
                lbl_type.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰋩</span>  <span font='10' color='{C_TEXT_PRI}'><b>Image Preview</b></span>")
                top_row.pack_start(lbl_type, False, False, 0)
                vbox.pack_start(top_row, False, False, 0)

                # Decode high-res image
                try:
                    if item.get("img_path") and os.path.exists(item["img_path"]):
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(item["img_path"])
                    else:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        img_data, _ = p.communicate(input=item["raw"].encode("utf-8"), timeout=1.0)
                        loader = GdkPixbuf.PixbufLoader()
                        loader.write(img_data)
                        loader.close()
                        pixbuf = loader.get_pixbuf()

                    orig_w = pixbuf.get_width()
                    orig_h = pixbuf.get_height()
                    ratio = min(230 / orig_w, 130 / orig_h)
                    scaled_w = max(1, int(orig_w * ratio))
                    scaled_h = max(1, int(orig_h * ratio))
                    card_pixbuf = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.BILINEAR)
                    img = Gtk.Image.new_from_pixbuf(card_pixbuf)
                    img.set_halign(Gtk.Align.CENTER)
                    vbox.pack_start(img, False, False, 2)

                    lbl_meta = Gtk.Label()
                    lbl_meta.set_markup(f"<span font='9.5' color='{C_RUBY_MUT}'>{orig_w}×{orig_h} · PNG Image</span>")
                    lbl_meta.set_halign(Gtk.Align.START)
                    lbl_meta.set_margin_start(8)
                    vbox.pack_start(lbl_meta, False, False, 0)
                except Exception:
                    lbl_err = Gtk.Label(label="[Image Preview]")
                    vbox.pack_start(lbl_err, False, False, 0)
            else:
                lbl_type.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰈙</span>  <span font='10' color='{C_RUBY_PRI}'><b>Text Preview</b></span>")
                top_row.pack_start(lbl_type, False, False, 0)
                vbox.pack_start(top_row, False, False, 0)

                if "full_text" not in item:
                    try:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        out, _ = p.communicate(input=item["raw"].encode("utf-8"), timeout=1.0)
                        item["full_text"] = out.decode("utf-8", errors="replace")
                    except Exception:
                        item["full_text"] = item["preview"]

                full_text = item["full_text"].strip()
                lines = full_text.split("\n")
                line_count = len(lines)
                char_count = len(full_text)

                display_text = "\n".join(lines[:10]) + f"\n... (+{line_count - 10} lines)" if len(lines) > 10 else full_text

                lbl_text = Gtk.Label()
                lbl_text.set_text(display_text)
                lbl_text.set_line_wrap(True)
                lbl_text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl_text.set_max_width_chars(30)
                lbl_text.set_halign(Gtk.Align.START)
                lbl_text.set_margin_start(8)
                lbl_text.get_style_context().add_class("popout-text")
                vbox.pack_start(lbl_text, False, False, 2)

                lbl_meta = Gtk.Label()
                lbl_meta.set_markup(f"<span font='9.5' color='{C_RUBY_MUT}'>{line_count} line{'s' if line_count > 1 else ''} · {char_count} chars</span>")
                lbl_meta.set_halign(Gtk.Align.START)
                lbl_meta.set_margin_start(8)
                vbox.pack_start(lbl_meta, False, False, 0)

        elif is_shelf and fpath:
            fname = os.path.basename(fpath)
            fsize = os.path.getsize(fpath) if os.path.exists(fpath) else 0
            size_str = self.format_file_size(fsize)
            icon, type_label, category = self.get_file_info(fpath)
            is_image = (category == "image")
            lbl_type.set_markup(f"<span font='10.5' color='{C_ACCENT}'>{icon}</span>  <span font='10' color='{C_RUBY_PRI}'><b>{GLib.markup_escape_text(fname[:22])}</b></span>")
            top_row.pack_start(lbl_type, False, False, 0)
            vbox.pack_start(top_row, False, False, 0)

            if is_image:
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(fpath)
                    orig_w = pixbuf.get_width()
                    orig_h = pixbuf.get_height()
                    ratio = min(230 / orig_w, 130 / orig_h)
                    scaled_w = max(1, int(orig_w * ratio))
                    scaled_h = max(1, int(orig_h * ratio))
                    card_pixbuf = pixbuf.scale_simple(scaled_w, scaled_h, GdkPixbuf.InterpType.BILINEAR)
                    img = Gtk.Image.new_from_pixbuf(card_pixbuf)
                    img.set_halign(Gtk.Align.CENTER)
                    vbox.pack_start(img, False, False, 2)

                    lbl_meta = Gtk.Label()
                    lbl_meta.set_markup(f"<span font='9.5' color='{C_RUBY_MUT}'>{orig_w}×{orig_h} · {size_str}</span>")
                    lbl_meta.set_halign(Gtk.Align.START)
                    lbl_meta.set_margin_start(8)
                    vbox.pack_start(lbl_meta, False, False, 0)
                except Exception:
                    pass
            else:
                is_text = fname.lower().endswith((".txt", ".py", ".sh", ".json", ".md", ".css", ".conf", ".lua", ".xml", ".yaml", ".yml", ".ini", ".c", ".cpp", ".h", ".rs", ".js", ".ts", ".html"))
                preview_content = None
                if is_text and fsize < 100 * 1024:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            lines = [f.readline() for _ in range(10)]
                            preview_content = "".join([l for l in lines if l]).strip()
                    except Exception:
                        pass

                if preview_content:
                    lbl_text = Gtk.Label()
                    lbl_text.set_text(preview_content[:600])
                    lbl_text.set_line_wrap(True)
                    lbl_text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                    lbl_text.set_max_width_chars(30)
                    lbl_text.set_halign(Gtk.Align.START)
                    lbl_text.set_margin_start(8)
                    lbl_text.get_style_context().add_class("popout-text")
                    vbox.pack_start(lbl_text, False, False, 2)

                lbl_meta = Gtk.Label()
                lbl_meta.set_markup(f"<span font='9.5' color='{C_RUBY_MUT}'>{size_str} · {GLib.markup_escape_text(fname)}</span>")
                lbl_meta.set_halign(Gtk.Align.START)
                lbl_meta.set_margin_start(8)
                vbox.pack_start(lbl_meta, False, False, 0)

        self.popout_box.add(vbox)
        self.popout_event_box.set_size_request(popout_w, -1)

        GtkLayerShell.set_margin(self.popout_win, GtkLayerShell.Edge.LEFT, int(pop_screen_x))
        GtkLayerShell.set_margin(self.popout_win, GtkLayerShell.Edge.TOP, int(pop_screen_y))

        self.popout_win.show_all()

    def hide_popout(self):
        if self.popout_timer:
            GLib.source_remove(self.popout_timer)
            self.popout_timer = None
        if hasattr(self, 'popout_win') and self.popout_win:
            self.popout_win.hide()
        self.current_popout_target = None

    def on_popout_leave(self, widget, event):
        if event.detail != Gdk.NotifyType.INFERIOR:
            self.hide_popout()

    def on_popout_clicked(self, widget, event):
        if event.button == 1 and self.current_popout_target:
            item, is_shelf, fpath = self.current_popout_target
            if not is_shelf and item:
                self.on_clip_chip_clicked(item, event)
            elif is_shelf and fpath:
                self.on_shelf_chip_clicked(fpath, event)
            self.hide_popout()
            return True
        return False

    # === IMAGE LIGHTBOX ===
    def open_image_lightbox(self, item_or_fpath, is_shelf=False):
        self.hide_popout()

        if self.lightbox_win is not None:
            self.lightbox_win.destroy()
            self.lightbox_win = None

        win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        win.set_name("shelf-lightbox-root")
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, "shelf-lightbox")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.RIGHT, False)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.ON_DEMAND)

        screen = win.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            win.set_visual(visual)
        win.set_app_paintable(True)
        win.connect("draw", self.on_lightbox_draw)

        pixbuf = None
        orig_w, orig_h = 0, 0
        raw_bytes = None
        title_str = "Image Preview"

        if not is_shelf:
            try:
                if isinstance(item_or_fpath, dict) and item_or_fpath.get("img_path") and os.path.exists(item_or_fpath["img_path"]):
                    raw_bytes = open(item_or_fpath["img_path"], "rb").read()
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(item_or_fpath["img_path"])
                else:
                    p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    raw_bytes, _ = p.communicate(input=item_or_fpath["raw"].encode("utf-8"), timeout=1.5)
                    loader = GdkPixbuf.PixbufLoader()
                    loader.write(raw_bytes)
                    loader.close()
                    pixbuf = loader.get_pixbuf()
            except Exception:
                pass
        else:
            try:
                raw_bytes = open(item_or_fpath, "rb").read()
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(item_or_fpath)
                title_str = os.path.basename(item_or_fpath)
            except Exception:
                pass

        if not pixbuf:
            self.show_toast("Could not load image")
            return

        orig_w = pixbuf.get_width()
        orig_h = pixbuf.get_height()

        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame.get_style_context().add_class("lightbox-card")
        frame.set_margin_start(16)
        frame.set_margin_end(16)
        frame.set_margin_top(16)
        frame.set_margin_bottom(16)
        frame.set_size_request(min(720, orig_w + 32), min(540, orig_h + 80))

        # Header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_t = Gtk.Label()
        lbl_t.set_markup(f"<span font='11' color='{C_ACCENT}'>󰋩</span>  <span font='11' color='{C_RUBY_PRI}'><b>{GLib.markup_escape_text(title_str[:30])}</b></span>  <span font='9.5' color='{C_RUBY_MUT}'>({orig_w}×{orig_h})</span>")
        hdr.pack_start(lbl_t, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        btn_open = Gtk.Button()
        lbl_o = Gtk.Label()
        lbl_o.set_markup(f"<span font='9.5' color='{C_RUBY_PRI}'>󰅍 Open in App</span>")
        btn_open.add(lbl_o)
        btn_open.get_style_context().add_class("action-btn")
        def do_open(b):
            tmp_path = "/tmp/zoom_preview.png"
            if raw_bytes:
                with open(tmp_path, "wb") as f:
                    f.write(raw_bytes)
                subprocess.Popen(["xdg-open", tmp_path])
            win.destroy()
        btn_open.connect("clicked", do_open)
        actions.pack_start(btn_open, False, False, 0)

        btn_copy = Gtk.Button()
        lbl_c = Gtk.Label()
        lbl_c.set_markup(f"<span font='9.5' color='{C_RUBY_PRI}'>󰆏 Copy</span>")
        btn_copy.add(lbl_c)
        btn_copy.get_style_context().add_class("action-btn")
        def do_copy(b):
            if raw_bytes:
                p = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                p.communicate(input=raw_bytes)
                self.show_toast("✨ Copied full image!")
            win.destroy()
        btn_copy.connect("clicked", do_copy)
        actions.pack_start(btn_copy, False, False, 0)

        btn_cl = Gtk.Button()
        lbl_x = Gtk.Label()
        lbl_x.set_markup(f"<span font='12' color='{C_RUBY_PRI}'>✕</span>")
        btn_cl.add(lbl_x)
        btn_cl.get_style_context().add_class("btn-close")
        btn_cl.connect("clicked", lambda b: win.destroy())
        actions.pack_end(btn_cl, False, False, 0)

        hdr.pack_end(actions, False, False, 0)
        frame.pack_start(hdr, False, False, 0)

        # Scale image to max 680x440
        ratio = min(680 / orig_w, 440 / orig_h)
        if ratio < 1.0:
            sw = max(1, int(orig_w * ratio))
            sh = max(1, int(orig_h * ratio))
            scaled_pixbuf = pixbuf.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
        else:
            scaled_pixbuf = pixbuf

        img_widget = Gtk.Image.new_from_pixbuf(scaled_pixbuf)
        img_widget.set_halign(Gtk.Align.CENTER)
        img_widget.set_valign(Gtk.Align.CENTER)
        frame.pack_start(img_widget, True, True, 4)

        lbl_foot = Gtk.Label()
        lbl_foot.set_markup(f"<span font='9.5' color='{C_RUBY_MUT}'>Esc to close · Click Open in App to inspect in Loupe</span>")
        frame.pack_end(lbl_foot, False, False, 0)

        win.add(frame)
        win.connect("key-press-event", lambda w, e: win.destroy() if e.keyval == Gdk.KEY_Escape else False)
        win.show_all()
        self.lightbox_win = win

    def on_clip_chip_clicked(self, item, event):
        if event.button == 1:
            try:
                if item.get("is_image"):
                    if item.get("img_path") and os.path.exists(item["img_path"]):
                        with open(item["img_path"], "rb") as f:
                            img_bytes = f.read()
                        p2 = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                        p2.communicate(input=img_bytes)
                    else:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        out, _ = p.communicate(input=item["raw"].encode("utf-8", errors="replace"))
                        p2 = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                        p2.communicate(input=out)
                else:
                    clip_text = item.get("full_text") or item.get("preview", "")
                    if item.get("is_pinned") and clip_text:
                        p2 = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                        p2.communicate(input=clip_text.encode("utf-8", errors="replace"))
                    else:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        out, _ = p.communicate(input=item["raw"].encode("utf-8", errors="replace"))
                        p2 = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                        p2.communicate(input=out)
                self.show_toast("✨ Copied!")
                GLib.timeout_add(250, self.close_window)
            except Exception as e:
                print("Error copying clip:", e)

    def delete_clip(self, item):
        self.hide_popout()
        try:
            if item.get("is_pinned"):
                pins = self.load_pinned_clips()
                new_pins = []
                for p in pins:
                    is_match = False
                    if item.get("id") and p.get("id") == item.get("id"):
                        is_match = True
                    elif item.get("is_image") and p.get("is_image") and item.get("raw") and p.get("raw") == item.get("raw"):
                        is_match = True
                    elif not item.get("is_image") and not p.get("is_image"):
                        t1 = (item.get("full_text") or item.get("preview", "")).strip()
                        t2 = (p.get("full_text") or p.get("preview", "")).strip()
                        if t1 and t1 == t2:
                            is_match = True
                    if not is_match:
                        new_pins.append(p)
                    else:
                        if p.get("img_path") and os.path.exists(p["img_path"]):
                            try:
                                os.remove(p["img_path"])
                            except Exception:
                                pass
                self.save_pinned_clips(new_pins)
            if item.get("raw"):
                p = subprocess.Popen(["cliphist", "delete"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                p.communicate(input=item["raw"].encode("utf-8"))
            self.refresh_clipboard()
        except Exception:
            pass

    def on_shelf_chip_clicked(self, fpath, event):
        if event.button == 1:
            subprocess.Popen(["xdg-open", fpath])

    def on_shelf_drag_data_get(self, widget, context, data, info, time_val, fpath):
        uri = GLib.filename_to_uri(fpath)
        data.set_uris([uri])

    def copy_shelf_file(self, fpath, is_image):
        try:
            if is_image:
                p = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                with open(fpath, "rb") as f:
                    p.communicate(input=f.read())
            else:
                is_text = False
                text_content = ""
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        text_content = f.read(1024 * 512)
                        is_text = True
                except Exception:
                    is_text = False

                if is_text:
                    p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                    p.communicate(input=text_content.encode("utf-8"))
                else:
                    uri = GLib.filename_to_uri(fpath)
                    p = subprocess.Popen(["wl-copy", "--type", "text/uri-list"], stdin=subprocess.PIPE)
                    p.communicate(input=uri.encode("utf-8"))
            self.show_toast("✨ Copied!")
        except Exception as e:
            print("Error copying file:", e)

    def remove_shelf_file(self, fpath):
        self.hide_popout()
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
            self.refresh_shelf()
        except Exception:
            pass

    # === DRAG & DROP HANDLERS ===
    def on_drop_zone_received(self, widget, context, x, y, data, info, time_val):
        self.process_incoming_drop(data, info)
        context.finish(True, False, time_val)

    def on_window_drag_data_received(self, widget, context, x, y, data, info, time_val):
        self.process_incoming_drop(data, info)
        context.finish(True, False, time_val)

    def process_incoming_drop(self, data, info):
        uris = data.get_uris()
        if uris:
            count = 0
            for uri in uris:
                try:
                    src = GLib.filename_from_uri(uri)[0]
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(SHELF_DIR, os.path.basename(src)))
                        count += 1
                except Exception:
                    pass
            if count > 0:
                self.switch_tab("shelf")
                self.refresh_shelf()
                self.show_toast(f"📦 Stashed {count} file(s)!")
                return

        text = data.get_text()
        if text and text.strip():
            filename = f"snippet_{int(time.time())}.txt"
            filepath = os.path.join(SHELF_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            self.switch_tab("shelf")
            self.refresh_shelf()
            self.show_toast("📝 Stashed snippet!")

    def on_stash_clipboard_clicked(self, btn):
        try:
            res = subprocess.run(["wl-paste", "--list-types"], stdout=subprocess.PIPE, text=True)
            types = res.stdout if res.returncode == 0 else ""

            if "image/png" in types:
                filename = f"image_{int(time.time())}.png"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "wb") as f:
                    subprocess.run(["wl-paste", "--type", "image/png"], stdout=f)
                self.refresh_shelf()
                self.show_toast("🖼️ Stashed image!")
                return

            if "text/uri-list" in types:
                res2 = subprocess.run(["wl-paste", "--type", "text/uri-list"], stdout=subprocess.PIPE, text=True)
                uris = res2.stdout.strip().split("\n")
                count = 0
                for uri in uris:
                    if uri.startswith("file://"):
                        src = GLib.filename_from_uri(uri)[0]
                        if os.path.exists(src):
                            shutil.copy2(src, os.path.join(SHELF_DIR, os.path.basename(src)))
                            count += 1
                if count > 0:
                    self.refresh_shelf()
                    self.show_toast(f"📦 Stashed {count} file(s)!")
                    return
        except Exception:
            pass

        try:
            res = subprocess.run(["wl-paste"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                filename = f"snippet_{int(time.time())}.txt"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(res.stdout)
                self.refresh_shelf()
                self.show_toast("📝 Stashed text!")
                return
        except Exception:
            pass

        self.show_toast("Clipboard is empty")

    def on_clear_clicked(self, btn):
        self.hide_popout()
        if self.active_tab == "clip":
            subprocess.run(["cliphist", "wipe"], stderr=subprocess.DEVNULL)
            self.refresh_clipboard()
        else:
            try:
                for fname in os.listdir(SHELF_DIR):
                    fpath = os.path.join(SHELF_DIR, fname)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                self.refresh_shelf()
            except Exception:
                pass

    def switch_tab(self, tab_name):
        self.active_tab = tab_name
        self.hide_popout()
        if tab_name == "clip":
            self.btn_tab_clip.get_style_context().add_class("active")
            self.btn_tab_shelf.get_style_context().remove_class("active")
            self.lbl_tab_clip.set_markup(f"<span font='12' color='#FFFFFF'>󰅌</span>   <span color='#FFFFFF'><b>Clipboard</b></span>")
            self.update_shelf_badge()
            self.btn_stash_clip.hide()
            self.stack.set_visible_child_name("clip")
            self.refresh_clipboard()
            self.clip_search.grab_focus()
        else:
            self.btn_tab_shelf.get_style_context().add_class("active")
            self.btn_tab_clip.get_style_context().remove_class("active")
            self.lbl_tab_clip.set_markup(f"<span font='12' color='{C_ACCENT}'>󰅌</span>   <span color='{C_RUBY_PRI}'>Clipboard</span>")
            self.update_shelf_badge()
            self.btn_stash_clip.show()
            self.stack.set_visible_child_name("shelf")
            self.refresh_shelf()

    def update_shelf_badge(self, count=None):
        if count is None:
            try:
                count = len([f for f in os.listdir(SHELF_DIR) if os.path.isfile(os.path.join(SHELF_DIR, f))])
            except Exception:
                count = 0
        if self.active_tab == "shelf":
            txt = f"<span font='12' color='#FFFFFF'>󰏖</span>   <span color='#FFFFFF'><b>Shelf ({count})</b></span>" if count > 0 else f"<span font='12' color='#FFFFFF'>󰏖</span>   <span color='#FFFFFF'><b>Shelf</b></span>"
        else:
            txt = f"<span font='12' color='{C_ACCENT}'>󰏖</span>   <span color='{C_RUBY_PRI}'>Shelf ({count})</span>" if count > 0 else f"<span font='12' color='{C_ACCENT}'>󰏖</span>   <span color='{C_RUBY_PRI}'>Shelf</span>"
        self.lbl_tab_shelf.set_markup(txt)

    def show_toast(self, message):
        self.lbl_status.set_text(message)
        GLib.timeout_add(2000, lambda: self.lbl_status.set_text(""))

    def check_cliphist_update(self):
        if os.path.exists(CLIPHIST_DB):
            try:
                mtime = os.path.getmtime(CLIPHIST_DB)
                if mtime > self.last_clip_mtime:
                    self.last_clip_mtime = mtime
                    if self.active_tab == "clip":
                        self.refresh_clipboard()
            except Exception:
                pass
        return True

    def check_mode_change(self):
        if os.path.exists(MODE_FILE):
            try:
                mtime = os.path.getmtime(MODE_FILE)
                if mtime > self.last_mode_mtime:
                    self.last_mode_mtime = mtime
                    with open(MODE_FILE, "r") as f:
                        mode = f.read().strip()
                    if mode in ("clip", "shelf") and mode != self.active_tab:
                        self.switch_tab(mode)
            except Exception:
                pass
        return True

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.lightbox_win:
                self.lightbox_win.destroy()
                self.lightbox_win = None
                return True
            self.close_window()
            return True
        return False

    def close_window(self):
        self.hide_popout()
        if self.lightbox_win:
            self.lightbox_win.destroy()
            self.lightbox_win = None
        self.destroy()

    def on_destroy(self, widget):
        self.hide_popout()
        if hasattr(self, 'popout_win') and self.popout_win:
            try:
                self.popout_win.destroy()
            except Exception:
                pass
        if self.lightbox_win:
            try:
                self.lightbox_win.destroy()
            except Exception:
                pass
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    @staticmethod
    def format_file_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f}MB"


def main():
    def sig_handler(signum, frame):
        GLib.idle_add(Gtk.main_quit)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    mode = "clip"
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if "shelf" in arg or "stash" in arg or "drop" in arg:
            mode = "shelf"

    try:
        with open(MODE_FILE, "w") as f:
            f.write(mode)
    except Exception:
        pass

    try:
        win = ShelfWindow(initial_tab=mode)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        win.show_all()
        win.switch_tab(mode)
        Gtk.main()
    except Exception as e:
        print(f"Error starting shelf: {e}", file=sys.stderr)
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
