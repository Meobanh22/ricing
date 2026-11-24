#!/usr/bin/env python3
# shelf_pkg/clipboard_tab.py — Clipboard history tab UI, search, copy, and deletion.

import os
import subprocess

from gi.repository import GLib, Gtk, Pango

from shelf_pkg.constants import CLIPHIST_DB, C_ACCENT, C_RUBY_MUT, C_RUBY_PRI


class ShelfClipboardMixin:
    """Clipboard history UI and cliphist interactions."""

    def build_clipboard_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        self.clip_search = Gtk.SearchEntry()
        self.clip_search.set_placeholder_text("Search clips...")
        self.clip_search.get_style_context().add_class("search-entry")
        self.clip_search.set_margin_bottom(8)
        self.clip_search.connect("search-changed", self.on_search_changed)
        vbox.pack_start(self.clip_search, False, False, 0)

        self.clip_stack = Gtk.Stack()
        self.clip_stack.set_transition_type(Gtk.StackTransitionType.NONE)

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

        self.clip_scroll = Gtk.ScrolledWindow()
        self.clip_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.clip_scroll.set_propagate_natural_height(True)
        self.clip_scroll.set_min_content_height(100)
        self.clip_scroll.set_max_content_height(400)
        self.clip_scroll.get_vadjustment().connect("value-changed", lambda a: self.hide_popout())

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

    def on_search_changed(self, entry):
        if self.search_debounce_timer is not None:
            try:
                GLib.source_remove(self.search_debounce_timer)
            except Exception:
                pass
            self.search_debounce_timer = None
        self.search_debounce_timer = GLib.timeout_add(150, self._apply_search_filter)

    def _apply_search_filter(self):
        self.search_debounce_timer = None
        self.refresh_clipboard()
        return False

    def _get_raw_clips(self):
        current_mtime = 0
        if os.path.exists(CLIPHIST_DB):
            try:
                current_mtime = os.path.getmtime(CLIPHIST_DB)
            except Exception:
                current_mtime = 0

        if self._raw_clips_cache is not None and current_mtime == self._raw_clips_mtime and current_mtime > 0:
            return self._raw_clips_cache

        clips = []
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
                    clips.append({
                        "id": clip_id,
                        "raw": line,
                        "preview": preview,
                        "is_image": is_image,
                        "is_pinned": False,
                    })
        except Exception:
            pass

        self._raw_clips_cache = clips
        self._raw_clips_mtime = current_mtime
        return clips

    def refresh_clipboard(self):
        self.hide_popout()
        for child in self.clip_flow.get_children():
            self.clip_flow.remove(child)

        query = self.clip_search.get_text().strip().lower()
        seen_text_previews = set()

        pins = self.load_pinned_clips()
        filtered_pins = []
        for p in pins:
            p_item = dict(p)
            p_item["is_pinned"] = True
            if not p_item.get("is_image"):
                seen_text_previews.add((p_item.get("full_text") or p_item.get("preview") or "").strip())
            if query:
                p_txt = (p_item.get("full_text") or p_item.get("preview") or "").lower()
                if query not in p_txt:
                    continue
            filtered_pins.append(p_item)

        clips = []
        for item in self._get_raw_clips():
            preview = item["preview"]
            if not item["is_image"]:
                norm_preview = preview.strip()
                if norm_preview in seen_text_previews:
                    continue
                seen_text_previews.add(norm_preview)

            if query and query not in preview.lower():
                continue
            if self.is_item_pinned(item, pins):
                continue
            clips.append(item)

        all_clips = filtered_pins + clips
        if not all_clips:
            self.clip_stack.set_visible_child_name("empty")
            self.clip_stack.show_all()
            return

        self.clip_stack.set_visible_child_name("content")
        for item in all_clips[:24]:
            self.clip_flow.add(self.create_clip_card(item))
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
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        lbl_icon = Gtk.Label()
        lbl_icon.set_margin_start(8)
        if item["is_image"]:
            lbl_icon.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰋩</span>  <span font='10' color='{C_RUBY_MUT}'>Image</span>")
        else:
            lbl_icon.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰈙</span>  <span font='10' color='{C_RUBY_MUT}'>Text</span>")
        top_row.pack_start(lbl_icon, False, False, 0)

        right_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        btn_pin = Gtk.Button()
        btn_pin.set_relief(Gtk.ReliefStyle.NONE)
        btn_pin.get_style_context().add_class("flat")
        btn_pin.get_style_context().add_class("chip-btn-pin")
        lbl_p = Gtk.Label()
        if item.get("is_pinned"):
            btn_pin.get_style_context().add_class("pinned")
            lbl_p.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰤲</span>")
        else:
            lbl_p.set_markup(f"<span font='10.5' color='{C_ACCENT}'>󰤱</span>")
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
            btn_zoom.connect("clicked", lambda b: self.open_image_lightbox(item, is_shelf=False))
            btn_zoom.connect("enter-notify-event", lambda w, e: self.hide_popout())
            right_hdr.pack_start(btn_zoom, False, False, 0)

        btn_del = Gtk.Button()
        btn_del.set_relief(Gtk.ReliefStyle.NONE)
        btn_del.get_style_context().add_class("flat")
        btn_del.get_style_context().add_class("chip-btn-del")
        lbl_x = Gtk.Label()
        lbl_x.set_markup(f"<span font='9.5' color='{C_RUBY_PRI}'>✕</span>")
        btn_del.add(lbl_x)
        btn_del.connect("clicked", lambda b: self.delete_clip(item))
        btn_del.connect("enter-notify-event", lambda w, e: self.hide_popout())
        right_hdr.pack_end(btn_del, False, False, 2)

        top_row.pack_end(right_hdr, False, False, 0)
        vbox.pack_start(top_row, False, False, 0)

        if item["is_image"]:
            img = Gtk.Image()
            img.set_halign(Gtk.Align.CENTER)
            img.set_size_request(175, 80)
            vbox.pack_start(img, False, False, 2)
            self.load_clip_thumbnail_async(item, 175, 90, img)
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
        event_box.connect("enter-notify-event", lambda w, e: self.schedule_popout(w, item, is_shelf=False))
        event_box.connect("leave-notify-event", lambda w, e: self.cancel_popout(w))
        return event_box

    def on_clip_chip_clicked(self, item, event):
        if event.button != 1:
            return
        try:
            if item.get("is_image"):
                if item.get("img_path") and os.path.exists(item["img_path"]):
                    with open(item["img_path"], "rb") as f:
                        img_bytes = f.read()
                    p2 = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                    p2.communicate(input=img_bytes)
                else:
                    clip_id = item.get("id")
                    if clip_id and clip_id in self._clip_raw_cache:
                        out = self._clip_raw_cache[clip_id]
                    else:
                        p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        out, _ = p.communicate(input=item["raw"].encode("utf-8", errors="replace"))
                        if clip_id and out:
                            self._clip_raw_cache[clip_id] = out
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
                    if not self._clip_matches(item, p):
                        new_pins.append(p)
                    elif p.get("img_path") and os.path.exists(p["img_path"]):
                        try:
                            os.remove(p["img_path"])
                        except Exception:
                            pass
                self.save_pinned_clips(new_pins)
            if item.get("raw"):
                p = subprocess.Popen(["cliphist", "delete"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                p.communicate(input=item["raw"].encode("utf-8"))
            clip_id = item.get("id")
            if clip_id:
                self._clip_raw_cache.pop(clip_id, None)
                for k in list(self._clip_thumb_cache.keys()):
                    if k[0] == clip_id:
                        del self._clip_thumb_cache[k]
            self._raw_clips_cache = None
            self.refresh_clipboard()
        except Exception:
            pass

    def check_cliphist_update(self):
        if os.path.exists(CLIPHIST_DB):
            try:
                mtime = os.path.getmtime(CLIPHIST_DB)
                if mtime > self.last_clip_mtime:
                    self.last_clip_mtime = mtime
                    self._raw_clips_cache = None
                    self._clip_thumb_cache.clear()
                    self._clip_raw_cache.clear()
                    if self.get_visible() and self.active_tab == "clip":
                        self.refresh_clipboard()
            except Exception:
                pass
        return True
