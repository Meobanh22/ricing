#!/usr/bin/env python3
# shelf.py — Clipboard history and file shelf window entrypoint.

import concurrent.futures
import os
import signal
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from shelf_pkg.constants import (  # noqa: E402
    VIVID_RED,
    WINE_RED,
    PURE_WHITE,
    DROP_TARGETS,
    MODE_FILE,
    PID_FILE,
    SHELF_DIR,
    STYLESHEET_PATH,
    WIDTH_SHELF,
)
from gi.repository import Gdk, GLib, GLibUnix, Gtk, GtkLayerShell  # noqa: E402
from shelf_pkg.clipboard_tab import ShelfClipboardMixin  # noqa: E402
from shelf_pkg.file_tab import ShelfFilesMixin  # noqa: E402
from shelf_pkg.popout import ShelfPopoutMixin  # noqa: E402
from shelf_pkg.storage import ShelfStorageMixin  # noqa: E402
from ui_core import DraggablePopup, clear_surface, get_cursor_pos, get_monitor_geometry  # noqa: E402


class ShelfWindow(
    Gtk.Window,
    ShelfStorageMixin,
    ShelfClipboardMixin,
    ShelfFilesMixin,
    ShelfPopoutMixin,
):
    def __init__(self, initial_tab="clip"):
        super().__init__(type=Gtk.WindowType.TOPLEVEL, title="Shelf")
        self.set_name("shelf-window")
        self.set_wmclass("shelf", "shelf")

        def shelf_bounds(x, y, mon_w, mon_h):
            return max(10, min(mon_w - 475, x)), max(10, min(mon_h - 100, y))

        self.drag_manager = DraggablePopup(
            self,
            name="shelf",
            default_pos=lambda mw, mh: (int((mw - WIDTH_SHELF) / 2), 44),
            bounds_fn=shelf_bounds,
            on_drag_start=self.hide_popout,
        )
        self.drag_manager.init_layer_shell(
            namespace="shelf",
            layer=GtkLayerShell.Layer.TOP,
            keyboard_mode=GtkLayerShell.KeyboardMode.ON_DEMAND,
        )

        self.set_title("Shelf")
        self.set_name("shelf-window-root")
        self.set_default_size(480, -1)
        self.set_resizable(False)

        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect("draw", self.on_window_draw)

        css_provider = Gtk.CssProvider()
        css_file = STYLESHEET_PATH if os.path.exists(STYLESHEET_PATH) else os.path.expanduser("~/.config/hypr/styles/shelf.css")
        if os.path.exists(css_file):
            try:
                css_provider.load_from_path(css_file)
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_USER + 10,
                )
            except Exception as e:
                print(f"Warning: CSS error: {e}", file=sys.stderr)

        self.active_tab = initial_tab
        self.last_mode_mtime = 0
        self.last_clip_mtime = 0
        self.popout_timer = None
        self.current_popout_target = None
        self.lightbox_win = None
        self._thumb_cache = {}
        self._raw_clips_cache = None
        self._raw_clips_mtime = 0
        self.search_debounce_timer = None
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="shelf_worker")
        self._clip_thumb_cache = {}
        self._clip_raw_cache = {}

        self.ensure_cliphist_daemon()
        self.build_ui()
        self.build_external_popout_window()

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)
        self.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.connect("drag-data-received", self.on_window_drag_data_received)

        self.switch_tab(initial_tab)
        GLib.timeout_add(150, self.check_mode_change)
        GLib.timeout_add(300, self.check_cliphist_update)
        GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_sigusr1)

    def on_window_draw(self, widget, cr):
        clear_surface(cr)
        return False

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

    def get_monitor_geometry(self):
        return get_monitor_geometry()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_size_request(480, -1)
        main_box.get_style_context().add_class("shelf-window")

        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header_hbox.set_margin_start(16)
        header_hbox.set_margin_end(16)
        header_hbox.set_margin_top(16)
        header_hbox.set_margin_bottom(10)

        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.get_style_context().add_class("tab-switcher")

        self.btn_tab_clip = Gtk.Button()
        self.lbl_tab_clip = Gtk.Label()
        self.lbl_tab_clip.set_markup(f"<span font='12' color='{PURE_WHITE}'>󰅌</span>   <span color='{PURE_WHITE}'><b>Clipboard</b></span>")
        self.btn_tab_clip.add(self.lbl_tab_clip)
        self.btn_tab_clip.get_style_context().add_class("tab-btn")
        self.btn_tab_clip.connect("clicked", lambda w: self.switch_tab("clip"))
        tab_box.pack_start(self.btn_tab_clip, False, False, 0)

        self.btn_tab_shelf = Gtk.Button()
        self.lbl_tab_shelf = Gtk.Label()
        self.lbl_tab_shelf.set_markup(f"<span font='12' color='{VIVID_RED}'>󰏖</span>   <span color='{WINE_RED}'>Shelf</span>")
        self.btn_tab_shelf.add(self.lbl_tab_shelf)
        self.btn_tab_shelf.get_style_context().add_class("tab-btn")
        self.btn_tab_shelf.connect("clicked", lambda w: self.switch_tab("shelf"))
        tab_box.pack_start(self.btn_tab_shelf, False, False, 0)

        header_hbox.pack_start(tab_box, False, False, 0)

        self.drag_handle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.drag_handle_box.set_hexpand(True)
        self.drag_handle_box.get_style_context().add_class("drag-grip-zone")
        pill = Gtk.Box()
        pill.get_style_context().add_class("drag-handle-pill")
        pill.set_valign(Gtk.Align.CENTER)
        pill.set_halign(Gtk.Align.CENTER)
        pill.set_size_request(38, 4)
        self.drag_handle_box.pack_start(pill, True, True, 0)
        header_hbox.pack_start(self.drag_handle_box, True, True, 4)

        self.header_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self.btn_stash_clip = Gtk.Button()
        self.lbl_stash = Gtk.Label()
        self.lbl_stash.set_markup(f"<span font='11' color='{VIVID_RED}'>󰅍</span>  <span color='{WINE_RED}'>Stash</span>")
        self.btn_stash_clip.add(self.lbl_stash)
        self.btn_stash_clip.get_style_context().add_class("action-btn")
        self.btn_stash_clip.connect("clicked", self.on_stash_clipboard_clicked)
        self.header_actions_box.pack_start(self.btn_stash_clip, False, False, 0)

        self.btn_clear_all = Gtk.Button()
        self.lbl_clear = Gtk.Label()
        self.lbl_clear.set_markup(f"<span font='12' color='{VIVID_RED}'>󰆴</span>")
        self.btn_clear_all.add(self.lbl_clear)
        self.btn_clear_all.get_style_context().add_class("action-btn")
        self.btn_clear_all.connect("clicked", self.on_clear_clicked)
        self.header_actions_box.pack_start(self.btn_clear_all, False, False, 0)

        btn_close = Gtk.Button()
        lbl_close = Gtk.Label()
        lbl_close.set_markup(f"<span font='12' color='{WINE_RED}'>✕</span>")
        btn_close.add(lbl_close)
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda w: self.close_window())
        self.header_actions_box.pack_end(btn_close, False, False, 0)

        header_hbox.pack_end(self.header_actions_box, False, False, 0)

        self.header_event_box = Gtk.EventBox()
        self.header_event_box.set_visible_window(False)
        self.drag_manager.attach_header(self.header_event_box)
        self.header_event_box.add(header_hbox)
        main_box.pack_start(self.header_event_box, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)

        self.clip_page = self.build_clipboard_page()
        self.stack.add_named(self.clip_page, "clip")
        self.shelf_page = self.build_shelf_page()
        self.stack.add_named(self.shelf_page, "shelf")
        main_box.pack_start(self.stack, True, True, 4)

        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.get_style_context().add_class("status-bar")
        self.lbl_status.set_halign(Gtk.Align.START)
        self.lbl_status.set_margin_start(16)
        self.lbl_status.set_margin_bottom(12)
        main_box.pack_end(self.lbl_status, False, False, 0)
        self.add(main_box)

    def on_clear_clicked(self, btn):
        self.hide_popout()
        if self.active_tab == "clip":
            subprocess.run(["cliphist", "wipe"], stderr=subprocess.DEVNULL)
            self._raw_clips_cache = None
            self._clip_thumb_cache.clear()
            self._clip_raw_cache.clear()
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
            self.lbl_tab_clip.set_markup(f"<span font='12' color='{PURE_WHITE}'>󰅌</span>   <span color='{PURE_WHITE}'><b>Clipboard</b></span>")
            self.update_shelf_badge()
            self.btn_stash_clip.hide()
            self.stack.set_visible_child_name("clip")
            self.refresh_clipboard()
            self.clip_search.grab_focus()
        else:
            self.btn_tab_shelf.get_style_context().add_class("active")
            self.btn_tab_clip.get_style_context().remove_class("active")
            self.lbl_tab_clip.set_markup(f"<span font='12' color='{VIVID_RED}'>󰅌</span>   <span color='{WINE_RED}'>Clipboard</span>")
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
        suffix = f" ({count})" if count > 0 else ""
        if self.active_tab == "shelf":
            txt = f"<span font='12' color='{PURE_WHITE}'>󰏖</span>   <span color='{PURE_WHITE}'><b>Shelf{suffix}</b></span>"
        else:
            txt = f"<span font='12' color='{VIVID_RED}'>󰏖</span>   <span color='{WINE_RED}'>Shelf{suffix}</span>"
        self.lbl_tab_shelf.set_markup(txt)

    def show_toast(self, message):
        self.lbl_status.set_text(message)
        GLib.timeout_add(2000, lambda: self.lbl_status.set_text(""))

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

    def on_sigusr1(self, *args):
        target_mode = "clip"
        if os.path.exists(MODE_FILE):
            try:
                with open(MODE_FILE, "r") as f:
                    target_mode = f.read().strip()
            except Exception:
                target_mode = "clip"

        if self.get_visible():
            if target_mode == self.active_tab:
                self.close_window()
            else:
                self.switch_tab(target_mode)
        else:
            self.show_window(target_mode)
        return True

    def show_window(self, mode=None):
        target = mode or self.active_tab
        self.switch_tab(target)
        if target == "clip":
            self.refresh_clipboard()
        else:
            self.refresh_shelf()
        self.show_all()
        self.present()
        if target == "clip":
            GLib.idle_add(self.clip_search.grab_focus)

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
        self.clip_search.set_text("")
        self.hide()

    def quit_permanently(self):
        self.hide_popout()
        if self.lightbox_win:
            self.lightbox_win.destroy()
            self.lightbox_win = None
        self.destroy()

    def on_destroy(self, widget):
        if hasattr(self, '_thread_pool') and self._thread_pool:
            try:
                self._thread_pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        if self.search_debounce_timer is not None:
            try:
                GLib.source_remove(self.search_debounce_timer)
            except Exception:
                pass
            self.search_debounce_timer = None
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


def main():
    daemon_mode = False
    mode = "clip"
    for arg in sys.argv[1:]:
        a = arg.lower()
        if "--daemon" in a or a == "-d" or "--hidden" in a:
            daemon_mode = True
        elif "shelf" in a or "stash" in a or "drop" in a:
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

        signal.signal(signal.SIGTERM, lambda *_: GLib.idle_add(win.quit_permanently))
        signal.signal(signal.SIGINT, lambda *_: GLib.idle_add(win.quit_permanently))

        if daemon_mode:
            win.show_all()
            win.hide()
        else:
            win.show_all()
            win.switch_tab(mode)
            if mode == "clip":
                GLib.idle_add(win.clip_search.grab_focus)

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
