#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA ANDROID-STYLE QUICK SHELF & CLIPBOARD MANAGER
# ==============================================================================
# Android Gboard / Material You inspired dynamic chip grid (FlowBox):
#   - Variable-sized squircle chips fitting seamlessly into columns
#   - Dynamic window sizing adapting naturally to content
#   - No duplicate entries, no annoying numbering/IDs
#   - Zero grey: 100% Serena Warm Obsidian-Wine & Ribbon Red tokens
#   - Drag-and-drop shelf with full thumbnail previews & drag-out
# ==============================================================================

import os
import sys
import time
import shutil
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango, GdkPixbuf

# Paths & Directories
SHELF_DIR = os.path.expanduser("~/.cache/serena/shelf")
CLIPHIST_DB = os.path.expanduser("~/.cache/cliphist/db")
PID_FILE = "/tmp/serena_shelf.pid"
MODE_FILE = "/tmp/serena_shelf.mode"
os.makedirs(SHELF_DIR, exist_ok=True)

TARGET_URI_LIST = 80
TARGET_TEXT = 81

DROP_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
    Gtk.TargetEntry.new("text/plain", 0, TARGET_TEXT),
]

DRAG_SOURCE_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
]

# Pure Serena Anime Minimalist CSS — ZERO GREY!
CSS = b"""
* {
    font-family: "JetBrains Mono", "Inter", sans-serif;
    outline: none;
    -GtkWidget-focus-line-width: 0;
    box-shadow: none;
    text-shadow: none;
    -gtk-icon-shadow: none;
}

window {
    background-color: transparent;
}

/* Main Container: Dynamic width & smooth rounded bottom */
.shelf-window {
    background-color: rgba(32, 16, 18, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top: none;
    border-radius: 0 0 16px 16px;
    padding: 10px 12px;
}

button {
    background-image: none;
    background-color: transparent;
    border: none;
    box-shadow: none;
    padding: 0;
}

/* Header Switcher */
.tab-switcher {
    background-color: rgba(48, 31, 32, 0.95);
    border-radius: 8px;
    padding: 2px;
}

.tab-btn {
    background-image: none;
    background-color: transparent;
    color: #E8C2D0;
    font-size: 11.5px;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    transition: background-color 150ms ease, color 150ms ease;
}

.tab-btn:hover {
    color: #FFF0F5;
}

.tab-btn.active {
    background-color: #FF2A55;
    color: #FFFFFF;
}

.action-btn {
    background-image: none;
    background-color: rgba(42, 26, 31, 0.95);
    color: #E8C2D0;
    font-size: 11px;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    transition: background-color 150ms ease, color 150ms ease;
}

.action-btn:hover {
    background-color: rgba(58, 34, 42, 0.98);
    color: #FFF0F5;
}

.btn-close {
    background-image: none;
    background-color: transparent;
    color: #A68595;
    font-size: 13px;
    font-weight: 700;
    border: none;
    border-radius: 6px;
    padding: 4px 6px;
    transition: color 150ms ease, background-color 150ms ease;
}

.btn-close:hover {
    color: #FF2A55;
    background-color: rgba(42, 26, 31, 0.50);
}

/* Search Entry */
entry,
searchentry {
    background-image: none;
    background-color: rgba(42, 26, 31, 0.95);
    color: #FFF0F5;
    font-size: 11.5px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 5px 10px;
    margin-bottom: 8px;
    caret-color: #FF2A55;
    box-shadow: none;
    transition: border-color 150ms ease;
}

entry:focus,
searchentry:focus {
    border: 1px solid #FF2A55;
}

entry image,
searchentry image {
    color: #A68595;
}

/* Android Gboard Style Flowbox & Chips */
flowbox {
    background-color: transparent;
}

flowboxchild {
    background-color: transparent;
    padding: 0;
    margin: 0;
    outline: none;
    border: none;
}

flowboxchild:selected {
    background-color: transparent;
}

.chip-card {
    background-color: rgba(42, 26, 31, 0.95);
    border-radius: 10px;
    border: none;
    padding: 8px 10px;
    transition: background-color 150ms ease;
}

.chip-card:hover {
    background-color: rgba(58, 34, 42, 0.98);
}

.chip-text {
    color: #FFF0F5;
    font-size: 11px;
    line-height: 1.35;
}

.chip-meta {
    color: #A68595;
    font-size: 9.5px;
    margin-top: 4px;
}

.chip-btn-del {
    color: #A68595;
    font-size: 10px;
    padding: 2px 4px;
    border-radius: 4px;
    transition: color 150ms ease;
}

.chip-btn-del:hover {
    color: #FF2A55;
}

/* Drop Zone */
.drop-zone {
    border: 1.5px dashed rgba(255, 42, 85, 0.4);
    border-radius: 12px;
    background-color: rgba(42, 26, 31, 0.4);
    padding: 24px 16px;
    margin: 6px 0;
}

.drop-zone:hover {
    border-color: #FF2A55;
    background-color: rgba(42, 26, 31, 0.7);
}

.drop-icon {
    color: #FF2A55;
    font-size: 28px;
}

.drop-title {
    color: #FFF0F5;
    font-size: 12px;
    font-weight: 600;
    margin-top: 4px;
}

.drop-subtitle {
    color: #A68595;
    font-size: 10.5px;
    margin-top: 2px;
}

.status-bar {
    color: #A68595;
    font-size: 10px;
    margin-top: 4px;
}

scrollbar {
    background-color: transparent;
}

scrollbar slider {
    background-color: rgba(255, 42, 85, 0.35);
    border-radius: 3px;
    min-width: 4px;
    min-height: 4px;
}

scrollbar slider:hover {
    background-color: #FF2A55;
}
"""


class SerenaAndroidShelf(Gtk.Window):
    def __init__(self, initial_tab="clip"):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        # 1. Layer Shell Setup (Anchor Top, Centered)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "shelf")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        # Dynamic comfortable width (360px: perfect for 2 columns of Android chips)
        self.set_title("Serena Shelf")
        self.set_default_size(360, -1)
        self.set_resizable(False)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.active_tab = initial_tab
        self.last_mode_mtime = 0
        self.last_clip_mtime = 0

        # Ensure daemon is running
        self.ensure_cliphist_daemon()

        # Build UI
        self.build_ui()

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

    def ensure_cliphist_daemon(self):
        try:
            res = subprocess.run(["pgrep", "-f", "cliphist store"], stdout=subprocess.DEVNULL)
            if res.returncode != 0:
                subprocess.Popen(["wl-paste", "--type", "text", "--watch", "cliphist", "store"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.Popen(["wl-paste", "--type", "image", "--watch", "cliphist", "store"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class("shelf-window")

        # --- HEADER ---
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.get_style_context().add_class("tab-switcher")

        self.btn_tab_clip = Gtk.Button(label="📋 Clipboard")
        self.btn_tab_clip.get_style_context().add_class("tab-btn")
        self.btn_tab_clip.connect("clicked", lambda w: self.switch_tab("clip"))
        tab_box.pack_start(self.btn_tab_clip, False, False, 0)

        self.btn_tab_shelf = Gtk.Button(label="📦 Shelf")
        self.btn_tab_shelf.get_style_context().add_class("tab-btn")
        self.btn_tab_shelf.connect("clicked", lambda w: self.switch_tab("shelf"))
        tab_box.pack_start(self.btn_tab_shelf, False, False, 0)

        header_hbox.pack_start(tab_box, False, False, 0)

        # Right actions
        self.header_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self.btn_stash_clip = Gtk.Button(label="📋 Stash")
        self.btn_stash_clip.get_style_context().add_class("action-btn")
        self.btn_stash_clip.set_tooltip_text("Save current clipboard into shelf")
        self.btn_stash_clip.connect("clicked", self.on_stash_clipboard_clicked)
        self.header_actions_box.pack_start(self.btn_stash_clip, False, False, 0)

        self.btn_clear_all = Gtk.Button(label="🗑️")
        self.btn_clear_all.get_style_context().add_class("action-btn")
        self.btn_clear_all.set_tooltip_text("Clear all")
        self.btn_clear_all.connect("clicked", self.on_clear_clicked)
        self.header_actions_box.pack_start(self.btn_clear_all, False, False, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.set_tooltip_text("Close (Esc)")
        btn_close.connect("clicked", lambda w: self.close_window())
        self.header_actions_box.pack_end(btn_close, False, False, 0)

        header_hbox.pack_end(self.header_actions_box, False, False, 0)
        main_box.pack_start(header_hbox, False, False, 0)

        # --- BODY (STACK) ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)

        self.clip_page = self.build_clipboard_page()
        self.stack.add_named(self.clip_page, "clip")

        self.shelf_page = self.build_shelf_page()
        self.stack.add_named(self.shelf_page, "shelf")

        main_box.pack_start(self.stack, True, True, 4)

        # --- FOOTER ---
        self.lbl_status = Gtk.Label(label="Tip: Drag items out to upload · Esc to close")
        self.lbl_status.get_style_context().add_class("status-bar")
        self.lbl_status.set_halign(Gtk.Align.START)
        main_box.pack_end(self.lbl_status, False, False, 0)

        self.add(main_box)

    # =========================================================================
    # TAB 1: CLIPBOARD (ANDROID GBOARD CHIP GRID)
    # =========================================================================
    def build_clipboard_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.clip_search = Gtk.SearchEntry()
        self.clip_search.set_placeholder_text("🔍 Search clips...")
        self.clip_search.get_style_context().add_class("search-entry")
        self.clip_search.connect("search-changed", lambda e: self.refresh_clipboard())
        vbox.pack_start(self.clip_search, False, False, 0)

        # Dynamic Natural Height ScrolledWindow (Expands with items up to 380px)
        self.clip_scroll = Gtk.ScrolledWindow()
        self.clip_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.clip_scroll.set_propagate_natural_height(True)
        self.clip_scroll.set_min_content_height(80)
        self.clip_scroll.set_max_content_height(380)

        # Android-Style FlowBox (2 columns of dynamic cards)
        self.clip_flow = Gtk.FlowBox()
        self.clip_flow.set_valign(Gtk.Align.START)
        self.clip_flow.set_max_children_per_line(2)
        self.clip_flow.set_min_children_per_line(1)
        self.clip_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.clip_flow.set_row_spacing(6)
        self.clip_flow.set_column_spacing(6)
        self.clip_flow.set_homogeneous(False)

        self.clip_scroll.add(self.clip_flow)
        vbox.pack_start(self.clip_scroll, True, True, 0)

        return vbox

    def refresh_clipboard(self):
        for child in self.clip_flow.get_children():
            self.clip_flow.remove(child)

        query = self.clip_search.get_text().strip().lower()
        clips = []
        seen_previews = set()

        try:
            res = subprocess.run(["cliphist", "list"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t", 1)
                    clip_id = parts[0]
                    preview = parts[1] if len(parts) > 1 else ""

                    # Deduplicate exact same text/preview
                    norm_preview = preview.strip()
                    if norm_preview in seen_previews:
                        continue
                    seen_previews.add(norm_preview)

                    is_image = "[[ binary data" in preview

                    if query and query not in preview.lower():
                        continue

                    clips.append({
                        "id": clip_id,
                        "raw": line,
                        "preview": preview,
                        "is_image": is_image
                    })
        except Exception:
            pass

        if not clips:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_halign(Gtk.Align.CENTER)
            empty_box.set_margin_top(30)
            empty_box.set_margin_bottom(30)

            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='22' color='#A68595'>📋</span>")
            empty_box.pack_start(lbl_icon, False, False, 0)

            lbl_msg = Gtk.Label()
            lbl_msg.set_markup("<span font='11' color='#A68595'>No clipboard items found</span>")
            empty_box.pack_start(lbl_msg, False, False, 0)

            self.clip_flow.add(empty_box)
            self.clip_flow.show_all()
            return

        # Render first 24 items in Android-style FlowBox
        for item in clips[:24]:
            chip = self.create_android_clip_chip(item)
            self.clip_flow.add(chip)

        self.clip_flow.show_all()

    def create_android_clip_chip(self, item):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("chip-card")
        event_box.set_size_request(162, -1)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        # Top row: Type indicator + Quick Delete button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        lbl_icon = Gtk.Label()
        lbl_icon.set_markup("<span font='10' color='#FF2A55'>󰋩 Image</span>" if item["is_image"] else "<span font='10' color='#A68595'>󰈙 Text</span>")
        top_row.pack_start(lbl_icon, False, False, 0)

        btn_del = Gtk.Button(label="✕")
        btn_del.get_style_context().add_class("chip-btn-del")
        btn_del.set_tooltip_text("Delete")
        btn_del.connect("clicked", lambda b: self.delete_clip(item))
        top_row.pack_end(btn_del, False, False, 0)

        vbox.pack_start(top_row, False, False, 0)

        # Content: Image thumbnail or Text snippet
        if item["is_image"]:
            # Image chip
            try:
                p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                img_data, _ = p.communicate(input=item["raw"].encode("utf-8"))
                loader = GdkPixbuf.PixbufLoader()
                loader.write(img_data)
                loader.close()
                pixbuf = loader.get_pixbuf()
                # Scale nicely into chip (max 150x80)
                scaled = pixbuf.scale_simple(145, 75, GdkPixbuf.InterpType.BILINEAR)
                img = Gtk.Image.new_from_pixbuf(scaled)
                vbox.pack_start(img, False, False, 2)
            except Exception:
                lbl_fallback = Gtk.Label(label="[Image Preview]")
                lbl_fallback.get_style_context().add_class("chip-text")
                vbox.pack_start(lbl_fallback, False, False, 0)
        else:
            # Text chip with wrap
            clean_txt = item["preview"].strip()
            lbl_txt = Gtk.Label()
            lbl_txt.get_style_context().add_class("chip-text")
            lbl_txt.set_text(clean_txt)
            lbl_txt.set_line_wrap(True)
            lbl_txt.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            lbl_txt.set_max_width_chars(18)
            lbl_txt.set_lines(4)
            lbl_txt.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_txt.set_halign(Gtk.Align.START)
            vbox.pack_start(lbl_txt, False, False, 2)

        event_box.add(vbox)
        event_box.connect("button-press-event", lambda w, e: self.on_clip_chip_clicked(item, e))
        return event_box

    def on_clip_chip_clicked(self, item, event):
        if event.button == 1:
            try:
                p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                out, _ = p.communicate(input=item["raw"].encode("utf-8"))
                if item["is_image"]:
                    p2 = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                    p2.communicate(input=out)
                else:
                    p2 = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                    p2.communicate(input=out)
                self.show_toast("✨ Copied!")
                GLib.timeout_add(250, self.close_window)
            except Exception as e:
                print("Error copying clip:", e)

    def delete_clip(self, item):
        try:
            p = subprocess.Popen(["cliphist", "delete"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p.communicate(input=item["raw"].encode("utf-8"))
            self.refresh_clipboard()
        except Exception:
            pass

    # =========================================================================
    # TAB 2: FILE SHELF (ANDROID GRID CHIPS)
    # =========================================================================
    def build_shelf_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.shelf_scroll = Gtk.ScrolledWindow()
        self.shelf_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.shelf_scroll.set_propagate_natural_height(True)
        self.shelf_scroll.set_min_content_height(80)
        self.shelf_scroll.set_max_content_height(380)

        self.shelf_flow = Gtk.FlowBox()
        self.shelf_flow.set_valign(Gtk.Align.START)
        self.shelf_flow.set_max_children_per_line(2)
        self.shelf_flow.set_min_children_per_line(1)
        self.shelf_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.shelf_flow.set_row_spacing(6)
        self.shelf_flow.set_column_spacing(6)
        self.shelf_flow.set_homogeneous(False)

        self.shelf_scroll.add(self.shelf_flow)
        vbox.pack_start(self.shelf_scroll, True, True, 0)

        return vbox

    def refresh_shelf(self):
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
            drop_box = Gtk.EventBox()
            drop_box.get_style_context().add_class("drop-zone")
            drop_box.set_size_request(335, -1)
            drop_box.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
            drop_box.connect("drag-data-received", self.on_drop_zone_received)

            v_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            v_content.set_valign(Gtk.Align.CENTER)
            v_content.set_halign(Gtk.Align.CENTER)

            lbl_icon = Gtk.Label()
            lbl_icon.get_style_context().add_class("drop-icon")
            lbl_icon.set_markup("󰉍")
            v_content.pack_start(lbl_icon, False, False, 0)

            lbl_title = Gtk.Label(label="Drop files or images here")
            lbl_title.get_style_context().add_class("drop-title")
            v_content.pack_start(lbl_title, False, False, 0)

            lbl_sub = Gtk.Label(label="Drag items out to upload anywhere")
            lbl_sub.get_style_context().add_class("drop-subtitle")
            v_content.pack_start(lbl_sub, False, False, 0)

            drop_box.add(v_content)
            self.shelf_flow.add(drop_box)
            self.shelf_flow.show_all()
            return

        for fpath, mtime in files:
            chip = self.create_android_shelf_chip(fpath, mtime)
            self.shelf_flow.add(chip)

        self.shelf_flow.show_all()

    def create_android_shelf_chip(self, fpath, mtime):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("chip-card")
        event_box.set_size_request(162, -1)

        # Drag-out source
        event_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, DRAG_SOURCE_TARGETS, Gdk.DragAction.COPY)
        event_box.connect("drag-data-get", self.on_shelf_drag_data_get, fpath)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        size_str = self.format_file_size(fsize)
        is_image = fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"))

        # Top row: Icon / Format + Delete button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lbl_type = Gtk.Label()
        lbl_type.set_markup("<span font='9.5' color='#FF2A55'>󰋩 Image</span>" if is_image else "<span font='9.5' color='#A68595'>󰈙 File</span>")
        top_row.pack_start(lbl_type, False, False, 0)

        btn_del = Gtk.Button(label="✕")
        btn_del.get_style_context().add_class("chip-btn-del")
        btn_del.set_tooltip_text("Remove")
        btn_del.connect("clicked", lambda b: self.remove_shelf_file(fpath))
        top_row.pack_end(btn_del, False, False, 0)
        vbox.pack_start(top_row, False, False, 0)

        # Preview thumbnail
        if is_image:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, 145, 75, True)
                img = Gtk.Image.new_from_pixbuf(pixbuf)
                vbox.pack_start(img, False, False, 2)
            except Exception:
                pass

        # Filename
        short_name = fname if len(fname) < 22 else fname[:19] + "..."
        lbl_name = Gtk.Label(label=short_name)
        lbl_name.get_style_context().add_class("chip-text")
        lbl_name.set_halign(Gtk.Align.START)
        vbox.pack_start(lbl_name, False, False, 0)

        # Bottom info row
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lbl_size = Gtk.Label(label=size_str)
        lbl_size.get_style_context().add_class("chip-meta")
        bottom_row.pack_start(lbl_size, False, False, 0)

        btn_copy = Gtk.Button(label="Copy")
        btn_copy.get_style_context().add_class("chip-btn-del")
        btn_copy.connect("clicked", lambda b: self.copy_shelf_file(fpath, is_image))
        bottom_row.pack_end(btn_copy, False, False, 0)
        vbox.pack_start(bottom_row, False, False, 0)

        event_box.add(vbox)
        event_box.connect("button-press-event", lambda w, e: self.on_shelf_chip_clicked(fpath, e))
        return event_box

    def on_shelf_chip_clicked(self, fpath, event):
        if event.button == 1:
            # Single click open
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
                uri = GLib.filename_to_uri(fpath)
                p = subprocess.Popen(["wl-copy", "--type", "text/uri-list"], stdin=subprocess.PIPE)
                p.communicate(input=uri.encode("utf-8"))
            self.show_toast("✨ Copied!")
        except Exception as e:
            print("Error copying file:", e)

    def remove_shelf_file(self, fpath):
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
            self.refresh_shelf()
        except Exception:
            pass

    def on_window_drag_data_received(self, widget, context, x, y, data, info, time_val):
        self.handle_drag_data(data)
        context.finish(True, False, time_val)

    def on_drop_zone_received(self, widget, context, x, y, data, info, time_val):
        self.handle_drag_data(data)
        context.finish(True, False, time_val)

    def handle_drag_data(self, data):
        uris = data.get_uris()
        count = 0
        if uris:
            for uri in uris:
                try:
                    src_path = GLib.filename_from_uri(uri)[0]
                    if os.path.exists(src_path):
                        dest_path = os.path.join(SHELF_DIR, os.path.basename(src_path))
                        if os.path.abspath(src_path) != os.path.abspath(dest_path):
                            shutil.copy2(src_path, dest_path)
                            count += 1
                except Exception:
                    pass

        if count > 0:
            self.switch_tab("shelf")
            self.refresh_shelf()
            self.show_toast(f"📦 Stashed {count} item(s)!")

    def on_stash_clipboard_clicked(self, btn):
        try:
            res = subprocess.run(["wl-paste", "--type", "image/png"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and res.stdout:
                filename = f"image_{int(time.time())}.png"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(res.stdout)
                self.refresh_shelf()
                self.show_toast(f"📸 Saved image!")
                return
        except Exception:
            pass

        try:
            res = subprocess.run(["wl-paste", "--type", "text/uri-list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout:
                uris = res.stdout.strip().split("\n")
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
        if self.active_tab == "clip":
            subprocess.run(["cliphist", "wipe"], stderr=subprocess.DEVNULL)
            self.refresh_clipboard()
            self.show_toast("🗑️ Cleared")
        else:
            try:
                for fname in os.listdir(SHELF_DIR):
                    fpath = os.path.join(SHELF_DIR, fname)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                self.refresh_shelf()
                self.show_toast("🗑️ Shelf cleared")
            except Exception:
                pass

    def switch_tab(self, tab_name):
        self.active_tab = tab_name
        if tab_name == "clip":
            self.btn_tab_clip.get_style_context().add_class("active")
            self.btn_tab_shelf.get_style_context().remove_class("active")
            self.btn_stash_clip.hide()
            self.stack.set_visible_child_name("clip")
            self.refresh_clipboard()
            self.clip_search.grab_focus()
        else:
            self.btn_tab_shelf.get_style_context().add_class("active")
            self.btn_tab_clip.get_style_context().remove_class("active")
            self.btn_stash_clip.show()
            self.stack.set_visible_child_name("shelf")
            self.refresh_shelf()

    def update_shelf_badge(self, count=None):
        if count is None:
            try:
                count = len([f for f in os.listdir(SHELF_DIR) if os.path.isfile(os.path.join(SHELF_DIR, f))])
            except Exception:
                count = 0
        self.btn_tab_shelf.set_label(f"📦 Shelf ({count})" if count > 0 else "📦 Shelf")

    def show_toast(self, message):
        self.lbl_status.set_text(message)
        GLib.timeout_add(2200, lambda: self.lbl_status.set_text("Tip: Drag items out to upload · Esc to close"))

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
            self.close_window()
            return True
        return False

    def close_window(self):
        self.destroy()

    def on_destroy(self, widget):
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
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    mode = "clip"
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if "shelf" in arg or "stash" in arg or "drop" in arg:
            mode = "shelf"

    with open(MODE_FILE, "w") as f:
        f.write(mode)

    win = SerenaAndroidShelf(initial_tab=mode)
    win.show_all()
    if mode == "clip":
        win.btn_stash_clip.hide()
    Gtk.main()


if __name__ == "__main__":
    main()
