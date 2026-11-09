#!/usr/bin/env python3
# draggable_popup.py — Reusable draggable popup window manager for Hyprland & GtkLayerShell.

import os
import sys
import json
import glob
import math
import socket
import gi

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk


def get_cursor_pos():
    """
    Queries Hyprland's IPC socket for the global hardware cursor coordinates.
    Works reliably on Wayland where GDK event.x_root/y_root are intentionally suppressed.
    """
    try:
        xdg = os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
        sig = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        sock_path = f"{xdg}/hypr/{sig}/.socket.sock" if sig else ""
        if not sock_path or not os.path.exists(sock_path):
            socks = glob.glob(f"{xdg}/hypr/*/.socket.sock")
            sock_path = socks[0] if socks else None
        if sock_path:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(0.05)
            s.connect(sock_path)
            s.sendall(b"cursorpos")
            res = s.recv(256).decode('utf-8', errors='ignore').strip()
            s.close()
            parts = res.split(',')
            return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        pass
    return None


def get_monitor_geometry(display=None):
    """
    Returns the primary or first active monitor width and height in pixels.
    """
    try:
        d = display or Gdk.Display.get_default()
        monitor = d.get_primary_monitor() or d.get_monitor(0)
        geom = monitor.get_geometry()
        return geom.width, geom.height
    except Exception:
        return 1600, 900


class DraggablePopup:
    """
    Manages draggable behavior, position persistence, and boundary constraints
    for popup windows on Hyprland using GtkLayerShell.
    """
    def __init__(
        self,
        window,
        name="popup",
        default_pos=None,
        bounds_fn=None,
        on_drag_start=None,
        on_drag_end=None,
        drag_threshold=5.0
    ):
        self.window = window
        self.name = name
        self.cache_file = f"/tmp/{name}_pos.json"
        self.default_pos = default_pos
        self.bounds_fn = bounds_fn
        self.on_drag_start = on_drag_start
        self.on_drag_end = on_drag_end
        self.drag_threshold = drag_threshold

        # Drag state
        self.drag_armed = False
        self.is_dragging = False
        self.drag_start_cursor = None
        self.drag_start_win = (0, 0)
        self.press_pos = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Determine initial position
        self.current_x, self.current_y = self._resolve_initial_pos()

    def _resolve_initial_pos(self):
        mon_w, mon_h = get_monitor_geometry()
        def_x, def_y = 50, 50
        if callable(self.default_pos):
            def_x, def_y = self.default_pos(mon_w, mon_h)
        elif isinstance(self.default_pos, (tuple, list)) and len(self.default_pos) == 2:
            def_x, def_y = self.default_pos

        # Check saved cache
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    saved = json.load(f)
                    x = saved.get("x", def_x)
                    y = saved.get("y", def_y)
                    return self.clamp_bounds(x, y)
            except Exception:
                pass

        return self.clamp_bounds(def_x, def_y)

    def clamp_bounds(self, x, y):
        mon_w, mon_h = get_monitor_geometry()
        if self.bounds_fn:
            return self.bounds_fn(x, y, mon_w, mon_h)
        # Default boundary clamping: keep at least part on screen
        clamped_x = max(10, min(mon_w - 100, x))
        clamped_y = max(10, min(mon_h - 100, y))
        return clamped_x, clamped_y

    def init_layer_shell(
        self,
        namespace=None,
        layer=None,
        keyboard_mode=None
    ):
        """Initializes GtkLayerShell with Top-Left draggable anchor and margins."""
        if not HAS_LAYER_SHELL:
            return
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, namespace or self.name)
        GtkLayerShell.set_layer(self.window, layer or GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, False)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, int(self.current_y))
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.LEFT, int(self.current_x))
        if keyboard_mode is not None:
            GtkLayerShell.set_keyboard_mode(self.window, keyboard_mode)

    def set_position(self, x, y, save=False, clamp=True):
        if clamp:
            cx, cy = self.clamp_bounds(x, y)
        else:
            cx, cy = x, y
        self.current_x = cx
        self.current_y = cy
        if HAS_LAYER_SHELL and GtkLayerShell.is_layer_window(self.window):
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.LEFT, int(cx))
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, int(cy))
        if save:
            self.save_position()

    def save_position(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump({"x": int(self.current_x), "y": int(self.current_y)}, f)
        except Exception:
            pass

    def reset_to_default(self):
        mon_w, mon_h = get_monitor_geometry()
        def_x, def_y = 50, 50
        if callable(self.default_pos):
            def_x, def_y = self.default_pos(mon_w, mon_h)
        elif isinstance(self.default_pos, (tuple, list)) and len(self.default_pos) == 2:
            def_x, def_y = self.default_pos
        self.set_position(def_x, def_y, save=True)

    # --- Mode 1: Threshold-based drag for custom drawn surfaces (Settings, etc.) ---
    def handle_press(self, event, is_inside=True):
        """
        Call in on_button_press.
        Handles double-click to reset, or arms dragging if clicked inside draggable body.
        Returns True if handled.
        """
        if event.button != 1:
            return False

        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.reset_to_default()
            self.drag_armed = False
            self.is_dragging = False
            return True

        if not is_inside:
            self.drag_armed = False
            self.is_dragging = False
            return False

        cur = get_cursor_pos()
        self.drag_armed = True
        self.is_dragging = False
        self.drag_start_cursor = cur if cur else (int(event.x_root), int(event.y_root))
        self.drag_start_win = (self.current_x, self.current_y)
        self.press_pos = (event.x, event.y)
        return True

    def handle_motion(self, event):
        """
        Call in on_motion_notify.
        If drag is active or threshold reached, updates window position.
        Returns True if dragging was performed.
        """
        if not self.drag_armed:
            return False

        cur = get_cursor_pos()
        if not cur or not self.drag_start_cursor:
            return False

        dx = cur[0] - self.drag_start_cursor[0]
        dy = cur[1] - self.drag_start_cursor[1]

        if not self.is_dragging and math.hypot(dx, dy) >= self.drag_threshold:
            self.is_dragging = True
            win = self.window.get_window()
            if win:
                win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grabbing"))
            if self.on_drag_start:
                self.on_drag_start()

        if self.is_dragging:
            new_x = self.drag_start_win[0] + dx
            new_y = self.drag_start_win[1] + dy
            self.set_position(new_x, new_y, save=False)
            return True

        return False

    def handle_release(self, event, on_click=None):
        """
        Call in on_button_release.
        If dragging was active, finishes drag and saves position.
        If stationary click (< threshold), invokes on_click(press_x, press_y).
        Returns True if handled.
        """
        if event.button != 1:
            return False

        if self.is_dragging:
            self.is_dragging = False
            self.drag_armed = False
            self.save_position()
            win = self.window.get_window()
            if win:
                win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
            if self.on_drag_end:
                self.on_drag_end()
            return True

        if self.drag_armed:
            self.drag_armed = False
            px, py = self.press_pos if self.press_pos else (event.x, event.y)
            if on_click:
                on_click(px, py)
            return True

        return False

    # --- Mode 2: Header / Handle-based drag for GTK container widgets (Shelf, etc.) ---
    def attach_header(self, header_widget):
        """
        Attaches drag events to a specific header or grab-bar widget.
        Automatically manages grab/grabbing cursors and dragging.
        """
        header_widget.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        header_widget.connect("enter-notify-event", self._on_header_enter)
        header_widget.connect("leave-notify-event", self._on_header_leave)
        header_widget.connect("button-press-event", self._on_header_press)
        header_widget.connect("button-release-event", self._on_header_release)
        header_widget.connect("motion-notify-event", self._on_header_motion)

    def _on_header_enter(self, widget, event):
        win = widget.get_window()
        if win and not self.is_dragging:
            win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
        return False

    def _on_header_leave(self, widget, event):
        if not self.is_dragging:
            win = widget.get_window()
            if win:
                win.set_cursor(None)
        return False

    def _on_header_press(self, widget, event):
        if event.button == 1:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.reset_to_default()
                self.is_dragging = False
                return True

            cur = get_cursor_pos()
            if cur:
                self.is_dragging = True
                self.drag_offset_x = cur[0] - self.current_x
                self.drag_offset_y = cur[1] - self.current_y
                if self.on_drag_start:
                    self.on_drag_start()
                win = widget.get_window()
                if win:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grabbing"))
                return True
        return False

    def _on_header_release(self, widget, event):
        if event.button == 1 and self.is_dragging:
            self.is_dragging = False
            self.save_position()
            win = widget.get_window()
            if win:
                win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
            if self.on_drag_end:
                self.on_drag_end()
            return True
        return False

    def _on_header_motion(self, widget, event):
        if self.is_dragging:
            cur = get_cursor_pos()
            if cur:
                new_x = cur[0] - self.drag_offset_x
                new_y = cur[1] - self.drag_offset_y
                self.set_position(new_x, new_y, save=False)
                return True
        return False
