#!/usr/bin/env python3
# shelf_pkg/popout.py — External hover popout preview and fullscreen image lightbox.

import os
import subprocess

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell, Pango

from shelf_pkg.constants import (
    VIVID_RED,
    DARK_RUBY,
    MUTED_PINK,
    WINE_RED,
    CREAM_WHITE,
    WIDTH_SHELF,
    hex_to_rgba,
)
from ui_core import clear_surface, draw_rounded_rect


class ShelfPopoutMixin:
    """Floating hover popout card and image lightbox modal."""

    def on_popout_draw(self, widget, cr):
        clear_surface(cr)
        alloc = widget.get_allocation()
        pad = 1.0
        draw_rounded_rect(cr, pad, pad, float(alloc.width) - pad * 2.0, float(alloc.height) - pad * 2.0, 14.0)
        cr.set_source_rgba(*hex_to_rgba(CREAM_WHITE, 0.98))
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(DARK_RUBY, 1.0))
        cr.set_line_width(2.0)
        cr.stroke()
        return False

    def on_lightbox_draw(self, widget, cr):
        clear_surface(cr)
        alloc = widget.get_allocation()
        pad = 1.0
        draw_rounded_rect(cr, pad, pad, float(alloc.width) - pad * 2.0, float(alloc.height) - pad * 2.0, 16.0)
        cr.set_source_rgba(*hex_to_rgba(CREAM_WHITE, 0.98))
        cr.fill_preserve()
        cr.set_source_rgba(*hex_to_rgba(DARK_RUBY, 1.0))
        cr.set_line_width(2.5)
        cr.stroke()
        return False

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

        visual = self.popout_win.get_screen().get_rgba_visual()
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

    def schedule_popout(self, card_widget, item, is_shelf=False, fpath=None):
        if self.popout_timer:
            GLib.source_remove(self.popout_timer)
            self.popout_timer = None

        def do_show():
            self.show_popout(card_widget, item, is_shelf, fpath)
            self.popout_timer = None
            return False

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
        win_w = WIDTH_SHELF
        main_win_screen_x = getattr(self, 'current_win_x', (mon_w - win_w) // 2)
        main_win_screen_y = getattr(self, 'current_win_y', 44)
        card_x, card_y = coords

        for child in self.popout_box.get_children():
            self.popout_box.remove(child)

        self.current_popout_target = (item, is_shelf, fpath)
        popout_w = 260
        if card_x < win_w / 2:
            pop_screen_x = main_win_screen_x - popout_w - 14
            if pop_screen_x < 10:
                pop_screen_x = main_win_screen_x + win_w + 14
        else:
            pop_screen_x = main_win_screen_x + win_w + 14
            if pop_screen_x + popout_w > mon_w - 10:
                pop_screen_x = main_win_screen_x - popout_w - 14

        pop_screen_y = max(10, min(main_win_screen_y + card_y, mon_h - 260))

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_type = Gtk.Label()
        lbl_type.set_margin_start(8)

        right_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        is_img_target = (item and item.get("is_image")) or (
            is_shelf and fpath and fpath.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"))
        )

        if is_img_target:
            btn_zoom_pop = Gtk.Button()
            btn_zoom_pop.set_relief(Gtk.ReliefStyle.NONE)
            btn_zoom_pop.get_style_context().add_class("action-btn")
            lbl_zp = Gtk.Label()
            lbl_zp.set_markup(f"<span font='9.5' color='{VIVID_RED}'>󰍉 Zoom</span>")
            btn_zoom_pop.add(lbl_zp)
            target_ref = item if not is_shelf else fpath
            btn_zoom_pop.connect("clicked", lambda b: self.open_image_lightbox(target_ref, is_shelf))
            right_actions.pack_start(btn_zoom_pop, False, False, 0)

        lbl_hint = Gtk.Label()
        lbl_hint.set_markup(f"<span font='9.5' color='{VIVID_RED}'>󰆏 Copy</span>" if not is_shelf else f"<span font='9.5' color='{VIVID_RED}'>󰅍 Open</span>")
        lbl_hint.set_margin_end(6)
        right_actions.pack_end(lbl_hint, False, False, 0)
        top_row.pack_end(right_actions, False, False, 0)

        if not is_shelf and item:
            if item["is_image"]:
                lbl_type.set_markup(f"<span font='10.5' color='{VIVID_RED}'>󰋩</span>  <span font='10' color='{CREAM_WHITE}'><b>Image Preview</b></span>")
                top_row.pack_start(lbl_type, False, False, 0)
                vbox.pack_start(top_row, False, False, 0)

                img = Gtk.Image()
                img.set_halign(Gtk.Align.CENTER)
                img.set_size_request(230, 130)
                vbox.pack_start(img, False, False, 2)
                self.load_clip_thumbnail_async(item, 230, 130, img)

                lbl_meta = Gtk.Label()
                lbl_meta.set_markup(f"<span font='9.5' color='{MUTED_PINK}'>PNG Image</span>")
                lbl_meta.set_halign(Gtk.Align.START)
                lbl_meta.set_margin_start(8)
                vbox.pack_start(lbl_meta, False, False, 0)
            else:
                lbl_type.set_markup(f"<span font='10.5' color='{VIVID_RED}'>󰈙</span>  <span font='10' color='{WINE_RED}'><b>Text Preview</b></span>")
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
                display_text = "\n".join(lines[:10]) + f"\n... (+{len(lines) - 10} lines)" if len(lines) > 10 else full_text

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
                lbl_meta.set_markup(f"<span font='9.5' color='{MUTED_PINK}'>{len(lines)} line{'s' if len(lines) > 1 else ''} · {len(full_text)} chars</span>")
                lbl_meta.set_halign(Gtk.Align.START)
                lbl_meta.set_margin_start(8)
                vbox.pack_start(lbl_meta, False, False, 0)

        elif is_shelf and fpath:
            fname = os.path.basename(fpath)
            fsize = os.path.getsize(fpath) if os.path.exists(fpath) else 0
            size_str = self.format_file_size(fsize)
            icon, _, category = self.get_file_info(fpath)
            lbl_type.set_markup(f"<span font='10.5' color='{VIVID_RED}'>{icon}</span>  <span font='10' color='{WINE_RED}'><b>{GLib.markup_escape_text(fname[:22])}</b></span>")
            top_row.pack_start(lbl_type, False, False, 0)
            vbox.pack_start(top_row, False, False, 0)

            if category == "image":
                try:
                    card_pixbuf = self.get_scaled_pixbuf(fpath, 230, 130)
                    if card_pixbuf:
                        img = Gtk.Image.new_from_pixbuf(card_pixbuf)
                        img.set_halign(Gtk.Align.CENTER)
                        vbox.pack_start(img, False, False, 2)
                    lbl_meta = Gtk.Label()
                    lbl_meta.set_markup(f"<span font='9.5' color='{MUTED_PINK}'>{size_str}</span>")
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
                            preview_content = "".join([l for l in [f.readline() for _ in range(10)] if l]).strip()
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
                lbl_meta.set_markup(f"<span font='9.5' color='{MUTED_PINK}'>{size_str} · {GLib.markup_escape_text(fname)}</span>")
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
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(win, edge, False)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.ON_DEMAND)

        visual = win.get_screen().get_rgba_visual()
        if visual:
            win.set_visual(visual)
        win.set_app_paintable(True)
        win.connect("draw", self.on_lightbox_draw)

        pixbuf = None
        raw_bytes = None
        title_str = "Image Preview"

        if not is_shelf:
            try:
                if isinstance(item_or_fpath, dict) and item_or_fpath.get("img_path") and os.path.exists(item_or_fpath["img_path"]):
                    with open(item_or_fpath["img_path"], "rb") as f:
                        raw_bytes = f.read()
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(item_or_fpath["img_path"])
                else:
                    clip_id = item_or_fpath.get("id") if isinstance(item_or_fpath, dict) else None
                    if clip_id and clip_id in self._clip_raw_cache:
                        raw_bytes = self._clip_raw_cache[clip_id]
                    else:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        raw_bytes, _ = p.communicate(input=item_or_fpath["raw"].encode("utf-8"), timeout=1.5)
                        if clip_id and raw_bytes:
                            self._clip_raw_cache[clip_id] = raw_bytes
                    if raw_bytes:
                        loader = GdkPixbuf.PixbufLoader()
                        loader.write(raw_bytes)
                        loader.close()
                        pixbuf = loader.get_pixbuf()
            except Exception:
                pass
        else:
            try:
                with open(item_or_fpath, "rb") as f:
                    raw_bytes = f.read()
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(item_or_fpath)
                title_str = os.path.basename(item_or_fpath)
            except Exception:
                pass

        if not pixbuf:
            self.show_toast("Could not load image")
            return

        orig_w, orig_h = pixbuf.get_width(), pixbuf.get_height()
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame.get_style_context().add_class("lightbox-card")
        frame.set_margin_start(16)
        frame.set_margin_end(16)
        frame.set_margin_top(16)
        frame.set_margin_bottom(16)
        frame.set_size_request(min(720, orig_w + 32), min(540, orig_h + 80))

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_t = Gtk.Label()
        lbl_t.set_markup(f"<span font='11' color='{VIVID_RED}'>󰋩</span>  <span font='11' color='{WINE_RED}'><b>{GLib.markup_escape_text(title_str[:30])}</b></span>  <span font='9.5' color='{MUTED_PINK}'>({orig_w}×{orig_h})</span>")
        hdr.pack_start(lbl_t, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        btn_open = Gtk.Button()
        lbl_o = Gtk.Label()
        lbl_o.set_markup(f"<span font='9.5' color='{WINE_RED}'>󰅍 Open in App</span>")
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
        lbl_c.set_markup(f"<span font='9.5' color='{WINE_RED}'>󰆏 Copy</span>")
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
        lbl_x.set_markup(f"<span font='12' color='{WINE_RED}'>✕</span>")
        btn_cl.add(lbl_x)
        btn_cl.get_style_context().add_class("btn-close")
        btn_cl.connect("clicked", lambda b: win.destroy())
        actions.pack_end(btn_cl, False, False, 0)

        hdr.pack_end(actions, False, False, 0)
        frame.pack_start(hdr, False, False, 0)

        ratio = min(680 / orig_w, 440 / orig_h)
        scaled_pixbuf = pixbuf.scale_simple(max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio)), GdkPixbuf.InterpType.BILINEAR) if ratio < 1.0 else pixbuf

        img_widget = Gtk.Image.new_from_pixbuf(scaled_pixbuf)
        img_widget.set_halign(Gtk.Align.CENTER)
        img_widget.set_valign(Gtk.Align.CENTER)
        frame.pack_start(img_widget, True, True, 4)

        lbl_foot = Gtk.Label()
        lbl_foot.set_markup(f"<span font='9.5' color='{MUTED_PINK}'>Esc to close · Click Open in App to inspect in Loupe</span>")
        frame.pack_end(lbl_foot, False, False, 0)

        win.add(frame)
        win.connect("key-press-event", lambda w, e: win.destroy() if e.keyval == Gdk.KEY_Escape else False)
        win.show_all()
        self.lightbox_win = win
