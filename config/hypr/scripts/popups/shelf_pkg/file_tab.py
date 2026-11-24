#!/usr/bin/env python3
# shelf_pkg/file_tab.py — File shelf tab UI, file metadata, drag-and-drop, and clipboard stashing.

import os
import shutil
import subprocess
import time

from gi.repository import Gdk, GLib, Gtk, Pango

from shelf_pkg.constants import (
    C_ACCENT,
    C_RUBY_MUT,
    C_RUBY_PRI,
    C_TEXT_SEC,
    DRAG_SOURCE_TARGETS,
    DROP_TARGETS,
    SHELF_DIR,
)


class ShelfFilesMixin:
    """File shelf cards, drag-and-drop handlers, and clipboard stash actions."""

    def build_shelf_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        self.shelf_stack = Gtk.Stack()
        self.shelf_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.shelf_stack.set_transition_duration(120)

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

        self.content_shelf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
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
            self.shelf_flow.add(self.create_shelf_card(fpath, mtime))

        self.shelf_flow.show_all()
        self.shelf_stack.show_all()

    @staticmethod
    def get_file_info(fpath):
        ext = os.path.splitext(os.path.basename(fpath).lower())[1]
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico"):
            return "󰋩", "Image", "image"
        if ext in (".py", ".sh", ".bash", ".zsh", ".lua", ".js", ".ts", ".html", ".css", ".json", ".c", ".cpp", ".rs", ".go", ".php", ".java"):
            return ("󰌠" if ext == ".py" else "󰈙"), "Code", "code"
        if ext in (".txt", ".md", ".pdf", ".doc", ".docx", ".odt", ".rtf", ".log", ".csv"):
            return ("󰈮" if ext == ".pdf" else "󰈙"), "Document", "doc"
        if ext in (".zip", ".tar", ".gz", ".xz", ".7z", ".rar", ".bz2", ".tgz"):
            return "󰗚", "Archive", "archive"
        if ext in (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus"):
            return "󰎆", "Audio", "audio"
        if ext in (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"):
            return "󰈔", "Video", "video"
        return "󰈢", "File", "other"

    def create_shelf_card(self, fpath, mtime):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("chip-card")
        event_box.set_size_request(190, 160)
        event_box.set_hexpand(True)
        event_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, DRAG_SOURCE_TARGETS, Gdk.DragAction.COPY)
        event_box.connect("drag-data-get", self.on_shelf_drag_data_get, fpath)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath) if os.path.exists(fpath) else 0
        size_str = self.format_file_size(fsize)
        icon, type_label, category = self.get_file_info(fpath)
        is_image = (category == "image")

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
        btn_del.connect("clicked", lambda b: self.remove_shelf_file(fpath))
        btn_del.connect("enter-notify-event", lambda w, e: self.hide_popout())
        right_hdr.pack_end(btn_del, False, False, 2)

        top_row.pack_end(right_hdr, False, False, 0)
        vbox.pack_start(top_row, False, False, 0)

        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_box.set_size_request(-1, 80)
        preview_box.set_valign(Gtk.Align.CENTER)
        preview_box.set_halign(Gtk.Align.FILL)

        if is_image:
            card_pixbuf = self.get_scaled_pixbuf(fpath, 175, 80)
            if card_pixbuf:
                img = Gtk.Image.new_from_pixbuf(card_pixbuf)
                img.set_halign(Gtk.Align.CENTER)
                preview_box.pack_start(img, True, True, 0)
            else:
                lbl_fb = Gtk.Label(label="[Image]")
                lbl_fb.get_style_context().add_class("chip-text")
                preview_box.pack_start(lbl_fb, True, True, 0)
        elif category in ("code", "doc"):
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
                self._pack_center_icon(preview_box, icon)
        else:
            self._pack_center_icon(preview_box, icon)

        vbox.pack_start(preview_box, True, True, 2)

        short_name = fname if len(fname) < 24 else fname[:21] + "..."
        lbl_name = Gtk.Label(label=short_name)
        lbl_name.get_style_context().add_class("chip-text")
        lbl_name.set_halign(Gtk.Align.START)
        lbl_name.set_margin_start(4)
        vbox.pack_start(lbl_name, False, False, 0)

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
        event_box.connect("enter-notify-event", lambda w, e: self.schedule_popout(w, None, is_shelf=True, fpath=fpath))
        event_box.connect("leave-notify-event", lambda w, e: self.cancel_popout(w))
        return event_box

    def _pack_center_icon(self, container, icon):
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        icon_box.set_valign(Gtk.Align.CENTER)
        lbl_big = Gtk.Label()
        lbl_big.set_markup(f"<span font='28' color='{C_ACCENT}'>{icon}</span>")
        icon_box.pack_start(lbl_big, False, False, 0)
        container.pack_start(icon_box, True, True, 0)

    def on_shelf_chip_clicked(self, fpath, event):
        if event.button == 1:
            subprocess.Popen(["xdg-open", fpath])

    def on_shelf_drag_data_get(self, widget, context, data, info, time_val, fpath):
        data.set_uris([GLib.filename_to_uri(fpath)])

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
            filepath = os.path.join(SHELF_DIR, f"snippet_{int(time.time())}.txt")
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
                filepath = os.path.join(SHELF_DIR, f"image_{int(time.time())}.png")
                with open(filepath, "wb") as f:
                    subprocess.run(["wl-paste", "--type", "image/png"], stdout=f)
                self.refresh_shelf()
                self.show_toast("🖼️ Stashed image!")
                return

            if "text/uri-list" in types:
                res2 = subprocess.run(["wl-paste", "--type", "text/uri-list"], stdout=subprocess.PIPE, text=True)
                count = 0
                for uri in res2.stdout.strip().split("\n"):
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
                filepath = os.path.join(SHELF_DIR, f"snippet_{int(time.time())}.txt")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(res.stdout)
                self.refresh_shelf()
                self.show_toast("📝 Stashed text!")
                return
        except Exception:
            pass

        self.show_toast("Clipboard is empty")
