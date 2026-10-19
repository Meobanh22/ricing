#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA QUICK SHELF & CLIPBOARD MANAGER
# ==============================================================================
# Slide-down top-centered overlay for:
#   1. Clipboard History (Text & Images via cliphist)
#   2. File & Image Drop Shelf (Temporary staging area for drag & drop)
# Follows Serena Anime Minimalist UI/UX Guidelines (AGENTS.md)
# ==============================================================================

import os
import sys
import time
import shutil
import subprocess
import threading
from urllib.parse import unquote, urlparse

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango, GdkPixbuf

# Paths & Directories
SHELF_DIR = os.path.expanduser("~/.cache/serena/shelf")
PID_FILE = "/tmp/serena_shelf.pid"
MODE_FILE = "/tmp/serena_shelf.mode"
os.makedirs(SHELF_DIR, exist_ok=True)

# Drag & Drop Target Types
TARGET_URI_LIST = 80
TARGET_TEXT = 81

DROP_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
    Gtk.TargetEntry.new("text/plain", 0, TARGET_TEXT),
]

DRAG_SOURCE_TARGETS = [
    Gtk.TargetEntry.new("text/uri-list", 0, TARGET_URI_LIST),
]

# CSS Stylesheet adhering to AGENTS.md
CSS = b"""
/* Serena Anime Minimalist Tokens */
* {
    font-family: "JetBrains Mono", "Inter", sans-serif;
    outline: none;
    -GtkWidget-focus-line-width: 0;
}

.shelf-window {
    background-color: rgba(32, 16, 18, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 0 0 16px 16px;
    padding: 14px;
}

/* Header & Tabs */
.header-box {
    margin-bottom: 12px;
}

.tab-switcher {
    background-color: rgba(48, 31, 32, 0.95);
    border-radius: 8px;
    padding: 3px;
}

.tab-btn {
    background-color: transparent;
    color: #E8C2D0;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
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
    background-color: rgba(42, 26, 31, 0.95);
    color: #E8C2D0;
    font-size: 12px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 6px 12px;
    transition: background-color 150ms ease, color 150ms ease;
}

.action-btn:hover {
    background-color: rgba(58, 34, 42, 0.98);
    color: #FFF0F5;
}

.action-btn.accent {
    background-color: #FF2A55;
    color: #FFFFFF;
}

.action-btn.accent:hover {
    background-color: #FF597B;
}

.btn-close {
    background-color: transparent;
    color: #A68595;
    font-size: 14px;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    transition: color 150ms ease;
}

.btn-close:hover {
    color: #FF2A55;
}

/* Search Entry */
.search-entry {
    background-color: rgba(42, 26, 31, 0.95);
    color: #FFF0F5;
    font-size: 12.5px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 7px 12px;
    margin-bottom: 10px;
    caret-color: #FF2A55;
    transition: border-color 150ms ease;
}

.search-entry:focus {
    border: 1px solid #FF2A55;
}

/* Cards & List Items */
.item-card {
    background-color: rgba(42, 26, 31, 0.95);
    border-radius: 10px;
    border: none;
    padding: 10px 12px;
    margin-bottom: 6px;
    transition: background-color 150ms ease;
}

.item-card:hover {
    background-color: rgba(58, 34, 42, 0.98);
}

.item-title {
    color: #FFF0F5;
    font-size: 13px;
    font-weight: 600;
}

.item-subtitle {
    color: #E8C2D0;
    font-size: 11.5px;
}

.item-meta {
    color: #A68595;
    font-size: 11px;
}

.item-icon-box {
    background-color: rgba(48, 31, 32, 0.95);
    border-radius: 8px;
    min-width: 38px;
    min-height: 38px;
}

.item-icon {
    color: #FF2A55;
    font-size: 18px;
}

.item-btn {
    background-color: transparent;
    color: #A68595;
    font-size: 12px;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    transition: color 150ms ease, background-color 150ms ease;
}

.item-btn:hover {
    color: #FFF0F5;
    background-color: rgba(48, 31, 32, 0.95);
}

.item-btn.btn-delete:hover {
    color: #FF2A55;
}

/* Drop Zone for Empty Shelf */
.drop-zone {
    border: 2px dashed rgba(255, 42, 85, 0.4);
    border-radius: 12px;
    background-color: rgba(42, 26, 31, 0.4);
    padding: 36px 20px;
    margin: 10px 0;
}

.drop-zone:hover {
    border-color: #FF2A55;
    background-color: rgba(42, 26, 31, 0.7);
}

.drop-icon {
    color: #FF2A55;
    font-size: 40px;
}

.drop-title {
    color: #FFF0F5;
    font-size: 14px;
    font-weight: 600;
    margin-top: 8px;
}

.drop-subtitle {
    color: #A68595;
    font-size: 12px;
    margin-top: 4px;
}

/* Status Bar & Tips */
.status-bar {
    color: #A68595;
    font-size: 11px;
    margin-top: 8px;
}

/* Scrollbars */
scrollbar {
    background-color: transparent;
}

scrollbar slider {
    background-color: rgba(255, 42, 85, 0.35);
    border-radius: 4px;
    min-width: 5px;
    min-height: 5px;
}

scrollbar slider:hover {
    background-color: #FF2A55;
}
"""


class SerenaShelfWindow(Gtk.Window):
    def __init__(self, initial_tab="clip"):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        # 1. Layer Shell Configuration
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "shelf")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        self.set_title("Serena Quick Shelf")
        self.set_default_size(560, 520)
        self.set_resizable(False)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # State Variables
        self.active_tab = initial_tab  # "clip" or "shelf"
        self.clips_cache = []
        self.last_mode_mtime = 0

        # Build UI
        self.build_ui()

        # Connect Window Events
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)

        # Enable Drag-and-Drop Destination for the whole window
        self.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.connect("drag-data-received", self.on_window_drag_data_received)

        # Switch to initial tab
        self.switch_tab(initial_tab)

        # Start background mode monitoring (for switching tabs via hotkeys)
        GLib.timeout_add(150, self.check_mode_change)

    def build_ui(self):
        # Outer Container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class("shelf-window")

        # --- HEADER ---
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_hbox.get_style_context().add_class("header-box")

        # Tab Switcher (Segmented Pills)
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.get_style_context().add_class("tab-switcher")

        self.btn_tab_clip = Gtk.Button(label="📋 Clipboard")
        self.btn_tab_clip.get_style_context().add_class("tab-btn")
        self.btn_tab_clip.connect("clicked", lambda w: self.switch_tab("clip"))
        tab_box.pack_start(self.btn_tab_clip, False, False, 0)

        self.btn_tab_shelf = Gtk.Button(label="📦 File Shelf")
        self.btn_tab_shelf.get_style_context().add_class("tab-btn")
        self.btn_tab_shelf.connect("clicked", lambda w: self.switch_tab("shelf"))
        tab_box.pack_start(self.btn_tab_shelf, False, False, 0)

        header_hbox.pack_start(tab_box, False, False, 0)

        # Right Header Actions
        self.header_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Button: Stash Clipboard (Shown on Shelf Tab)
        self.btn_stash_clip = Gtk.Button(label="📋 Stash Clipboard")
        self.btn_stash_clip.get_style_context().add_class("action-btn")
        self.btn_stash_clip.set_tooltip_text("Save current clipboard image or file to shelf")
        self.btn_stash_clip.connect("clicked", self.on_stash_clipboard_clicked)
        self.header_actions_box.pack_start(self.btn_stash_clip, False, False, 0)

        # Button: Add Files (Shown on Shelf Tab)
        self.btn_add_files = Gtk.Button(label="➕ Add")
        self.btn_add_files.get_style_context().add_class("action-btn")
        self.btn_add_files.set_tooltip_text("Add files to temporary shelf")
        self.btn_add_files.connect("clicked", self.on_add_files_clicked)
        self.header_actions_box.pack_start(self.btn_add_files, False, False, 0)

        # Button: Clear / Wipe
        self.btn_clear_all = Gtk.Button(label="🗑️ Clear")
        self.btn_clear_all.get_style_context().add_class("action-btn")
        self.btn_clear_all.connect("clicked", self.on_clear_clicked)
        self.header_actions_box.pack_start(self.btn_clear_all, False, False, 0)

        # Button: Close
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
        self.stack.set_transition_duration(150)

        # Page 1: Clipboard
        self.clip_page = self.build_clipboard_page()
        self.stack.add_named(self.clip_page, "clip")

        # Page 2: File Shelf
        self.shelf_page = self.build_shelf_page()
        self.stack.add_named(self.shelf_page, "shelf")

        main_box.pack_start(self.stack, True, True, 0)

        # --- FOOTER STATUS BAR ---
        self.lbl_status = Gtk.Label(label="Tip: Drag items out to attach or upload · Press Esc to close")
        self.lbl_status.get_style_context().add_class("status-bar")
        self.lbl_status.set_halign(Gtk.Align.START)
        main_box.pack_end(self.lbl_status, False, False, 0)

        self.add(main_box)

    # =========================================================================
    # TAB 1: CLIPBOARD PAGE
    # =========================================================================
    def build_clipboard_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Search Entry
        self.clip_search = Gtk.SearchEntry()
        self.clip_search.set_placeholder_text("🔍 Type to filter clips...")
        self.clip_search.get_style_context().add_class("search-entry")
        self.clip_search.connect("search-changed", self.on_clip_search_changed)
        vbox.pack_start(self.clip_search, False, False, 0)

        # Scrolled Window for Clips
        self.clip_scroll = Gtk.ScrolledWindow()
        self.clip_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.clip_scroll.set_min_content_height(400)

        self.clip_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.clip_scroll.add(self.clip_list_box)
        vbox.pack_start(self.clip_scroll, True, True, 0)

        return vbox

    def refresh_clipboard(self):
        # Clear existing items
        for child in self.clip_list_box.get_children():
            self.clip_list_box.remove(child)

        # Fetch clip list from cliphist
        query = self.clip_search.get_text().strip().lower()
        clips = []
        try:
            res = subprocess.run(["cliphist", "list"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t", 1)
                    clip_id = parts[0]
                    preview = parts[1] if len(parts) > 1 else ""
                    is_image = "[[ binary data" in preview

                    if query:
                        if query not in preview.lower():
                            continue

                    clips.append({
                        "id": clip_id,
                        "raw": line,
                        "preview": preview,
                        "is_image": is_image
                    })
        except Exception:
            pass

        self.clips_cache = clips

        if not clips:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_margin_top(60)

            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='32' color='#A68595'>📋</span>")
            empty_box.pack_start(lbl_icon, False, False, 0)

            lbl_msg = Gtk.Label()
            lbl_msg.set_markup("<span font='13' color='#A68595'>No clipboard items found</span>")
            empty_box.pack_start(lbl_msg, False, False, 0)

            self.clip_list_box.pack_start(empty_box, True, True, 0)
            self.clip_list_box.show_all()
            return

        # Render first 40 clips for speed
        for item in clips[:40]:
            card = self.create_clip_card(item)
            self.clip_list_box.pack_start(card, False, False, 0)

        self.clip_list_box.show_all()

    def create_clip_card(self, item):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("item-card")

        card_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Icon / Thumbnail
        icon_box = Gtk.Box()
        icon_box.get_style_context().add_class("item-icon-box")
        icon_box.set_size_request(38, 38)
        icon_box.set_valign(Gtk.Align.CENTER)
        icon_box.set_halign(Gtk.Align.CENTER)

        if item["is_image"]:
            # Load thumbnail async or fast decode
            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='14' color='#FF2A55'>󰋩</span>")
            lbl_icon.set_valign(Gtk.Align.CENTER)
            lbl_icon.set_halign(Gtk.Align.CENTER)
            icon_box.pack_start(lbl_icon, True, True, 0)
        else:
            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='14' color='#FF2A55'>󰈙</span>")
            lbl_icon.set_valign(Gtk.Align.CENTER)
            lbl_icon.set_halign(Gtk.Align.CENTER)
            icon_box.pack_start(lbl_icon, True, True, 0)

        card_hbox.pack_start(icon_box, False, False, 0)

        # Text Details
        vbox_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_info.set_valign(Gtk.Align.CENTER)

        if item["is_image"]:
            lbl_title = Gtk.Label(label="Image Clip")
            lbl_title.get_style_context().add_class("item-title")
            lbl_title.set_halign(Gtk.Align.START)
            vbox_info.pack_start(lbl_title, False, False, 0)

            lbl_sub = Gtk.Label(label=item["preview"].replace("[[ binary data", "").replace("]]", "").strip())
            lbl_sub.get_style_context().add_class("item-meta")
            lbl_sub.set_halign(Gtk.Align.START)
            vbox_info.pack_start(lbl_sub, False, False, 0)
        else:
            # Single line preview
            preview_clean = item["preview"].replace("\n", " ").strip()
            if len(preview_clean) > 65:
                preview_clean = preview_clean[:62] + "..."
            lbl_title = Gtk.Label(label=preview_clean)
            lbl_title.get_style_context().add_class("item-title")
            lbl_title.set_halign(Gtk.Align.START)
            lbl_title.set_ellipsize(Pango.EllipsizeMode.END)
            vbox_info.pack_start(lbl_title, False, False, 0)

            lbl_sub = Gtk.Label(label=f"Clip #{item['id']} · {len(item['preview'])} chars")
            lbl_sub.get_style_context().add_class("item-meta")
            lbl_sub.set_halign(Gtk.Align.START)
            vbox_info.pack_start(lbl_sub, False, False, 0)

        card_hbox.pack_start(vbox_info, True, True, 0)

        # Right Action: Delete Button
        btn_del = Gtk.Button(label="✕")
        btn_del.get_style_context().add_class("item-btn")
        btn_del.get_style_context().add_class("btn-delete")
        btn_del.set_tooltip_text("Delete clip")
        btn_del.set_valign(Gtk.Align.CENTER)
        btn_del.connect("clicked", lambda b: self.delete_clip_item(item))
        card_hbox.pack_end(btn_del, False, False, 0)

        # Button: Stash into File Shelf (for images or text)
        btn_stash = Gtk.Button(label="📦 Stash")
        btn_stash.get_style_context().add_class("item-btn")
        btn_stash.set_tooltip_text("Save clip to File Shelf")
        btn_stash.set_valign(Gtk.Align.CENTER)
        btn_stash.connect("clicked", lambda b: self.stash_clip_to_shelf(item))
        card_hbox.pack_end(btn_stash, False, False, 0)

        event_box.add(card_hbox)
        event_box.connect("button-press-event", lambda w, e: self.on_clip_card_clicked(item, e))

        return event_box

    def on_clip_card_clicked(self, item, event):
        if event.button == 1:  # Left Click
            self.copy_clip_to_system(item)
            self.show_toast("✨ Copied to clipboard!")
            # Optional: auto-close or stay
            GLib.timeout_add(400, self.close_window)

    def copy_clip_to_system(self, item):
        try:
            p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out, _ = p.communicate(input=item["raw"].encode("utf-8"))
            if item["is_image"]:
                p2 = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE)
                p2.communicate(input=out)
            else:
                p2 = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                p2.communicate(input=out)
        except Exception as e:
            print("Error copying clip:", e)

    def delete_clip_item(self, item):
        try:
            p = subprocess.Popen(["cliphist", "delete"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p.communicate(input=item["raw"].encode("utf-8"))
            self.refresh_clipboard()
            self.show_toast("🗑️ Clip deleted")
        except Exception as e:
            print("Error deleting clip:", e)

    def stash_clip_to_shelf(self, item):
        try:
            p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            data, _ = p.communicate(input=item["raw"].encode("utf-8"))
            if item["is_image"]:
                filename = f"stash_image_{int(time.time())}.png"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(data)
            else:
                filename = f"stash_snippet_{int(time.time())}.txt"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(data)
            self.show_toast(f"📦 Stashed to File Shelf: {filename}")
            self.update_shelf_badge()
        except Exception as e:
            print("Error stashing clip:", e)

    def on_clip_search_changed(self, entry):
        self.refresh_clipboard()

    # =========================================================================
    # TAB 2: FILE & IMAGE SHELF PAGE
    # =========================================================================
    def build_shelf_page(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Scrolled Window for Shelf Items
        self.shelf_scroll = Gtk.ScrolledWindow()
        self.shelf_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.shelf_scroll.set_min_content_height(430)

        self.shelf_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.shelf_scroll.add(self.shelf_list_box)
        vbox.pack_start(self.shelf_scroll, True, True, 0)

        return vbox

    def refresh_shelf(self):
        for child in self.shelf_list_box.get_children():
            self.shelf_list_box.remove(child)

        # List files in SHELF_DIR
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
            # Drop Zone Box
            drop_box = Gtk.EventBox()
            drop_box.get_style_context().add_class("drop-zone")
            drop_box.drag_dest_set(Gtk.DestDefaults.ALL, DROP_TARGETS, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
            drop_box.connect("drag-data-received", self.on_drop_zone_received)

            v_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            v_content.set_valign(Gtk.Align.CENTER)
            v_content.set_halign(Gtk.Align.CENTER)

            lbl_icon = Gtk.Label()
            lbl_icon.get_style_context().add_class("drop-icon")
            lbl_icon.set_markup("󰉍")
            v_content.pack_start(lbl_icon, False, False, 0)

            lbl_title = Gtk.Label(label="Drag & drop files or images here")
            lbl_title.get_style_context().add_class("drop-title")
            v_content.pack_start(lbl_title, False, False, 0)

            lbl_sub = Gtk.Label(label="Temporary staging shelf · Drag items out to upload anywhere")
            lbl_sub.get_style_context().add_class("drop-subtitle")
            v_content.pack_start(lbl_sub, False, False, 0)

            drop_box.add(v_content)
            self.shelf_list_box.pack_start(drop_box, True, True, 20)
            self.shelf_list_box.show_all()
            return

        # Render Shelf File Cards
        for fpath, mtime in files:
            card = self.create_shelf_card(fpath, mtime)
            self.shelf_list_box.pack_start(card, False, False, 0)

        self.shelf_list_box.show_all()

    def create_shelf_card(self, fpath, mtime):
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("item-card")

        # Enable Drag-and-Drop Source: User can drag card out to another app!
        event_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, DRAG_SOURCE_TARGETS, Gdk.DragAction.COPY)
        event_box.connect("drag-data-get", self.on_shelf_drag_data_get, fpath)

        card_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        size_str = self.format_file_size(fsize)
        is_image = fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"))

        # Icon / Thumbnail
        if is_image:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, 42, 42, True)
                img = Gtk.Image.new_from_pixbuf(pixbuf)
                img.set_size_request(42, 42)
                card_hbox.pack_start(img, False, False, 0)
            except Exception:
                icon_box = Gtk.Box()
                icon_box.get_style_context().add_class("item-icon-box")
                icon_box.set_size_request(38, 38)
                lbl_icon = Gtk.Label()
                lbl_icon.set_markup("<span font='14' color='#FF2A55'>󰋩</span>")
                icon_box.pack_start(lbl_icon, True, True, 0)
                card_hbox.pack_start(icon_box, False, False, 0)
        else:
            icon_box = Gtk.Box()
            icon_box.get_style_context().add_class("item-icon-box")
            icon_box.set_size_request(38, 38)
            lbl_icon = Gtk.Label()
            lbl_icon.set_markup("<span font='14' color='#FF2A55'>󰈙</span>")
            icon_box.pack_start(lbl_icon, True, True, 0)
            card_hbox.pack_start(icon_box, False, False, 0)

        # File Info
        vbox_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_info.set_valign(Gtk.Align.CENTER)

        display_name = fname if len(fname) < 42 else fname[:38] + "..."
        lbl_title = Gtk.Label(label=display_name)
        lbl_title.get_style_context().add_class("item-title")
        lbl_title.set_halign(Gtk.Align.START)
        vbox_info.pack_start(lbl_title, False, False, 0)

        time_str = time.strftime("%H:%M · %d/%m", time.localtime(mtime))
        lbl_sub = Gtk.Label(label=f"{size_str}  ·  {time_str}  ·  Drag out to upload")
        lbl_sub.get_style_context().add_class("item-meta")
        lbl_sub.set_halign(Gtk.Align.START)
        vbox_info.pack_start(lbl_sub, False, False, 0)

        card_hbox.pack_start(vbox_info, True, True, 0)

        # Actions on Card: Open & Copy & Delete
        btn_open = Gtk.Button(label="Open")
        btn_open.get_style_context().add_class("item-btn")
        btn_open.set_tooltip_text("Open file with default app")
        btn_open.set_valign(Gtk.Align.CENTER)
        btn_open.connect("clicked", lambda b: subprocess.Popen(["xdg-open", fpath]))
        card_hbox.pack_end(btn_open, False, False, 0)

        btn_copy = Gtk.Button(label="Copy")
        btn_copy.get_style_context().add_class("item-btn")
        btn_copy.set_tooltip_text("Copy file to clipboard")
        btn_copy.set_valign(Gtk.Align.CENTER)
        btn_copy.connect("clicked", lambda b: self.copy_shelf_file(fpath, is_image))
        card_hbox.pack_end(btn_copy, False, False, 0)

        btn_del = Gtk.Button(label="✕")
        btn_del.get_style_context().add_class("item-btn")
        btn_del.get_style_context().add_class("btn-delete")
        btn_del.set_tooltip_text("Remove from shelf")
        btn_del.set_valign(Gtk.Align.CENTER)
        btn_del.connect("clicked", lambda b: self.remove_shelf_file(fpath))
        card_hbox.pack_end(btn_del, False, False, 0)

        event_box.add(card_hbox)
        return event_box

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
            self.show_toast("✨ File copied to clipboard!")
        except Exception as e:
            print("Error copying file:", e)

    def remove_shelf_file(self, fpath):
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
            self.refresh_shelf()
            self.show_toast("🗑️ File removed from shelf")
        except Exception as e:
            print("Error removing file:", e)

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
                        # Prevent self-copy
                        if os.path.abspath(src_path) != os.path.abspath(dest_path):
                            shutil.copy2(src_path, dest_path)
                            count += 1
                except Exception as e:
                    print("Error importing dropped file:", e)

        if count > 0:
            self.switch_tab("shelf")
            self.refresh_shelf()
            self.show_toast(f"📦 Added {count} file(s) to shelf!")

    def on_stash_clipboard_clicked(self, btn):
        # 1. Try to grab image from clipboard
        try:
            res = subprocess.run(["wl-paste", "--type", "image/png"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and res.stdout:
                filename = f"screenshot_{int(time.time())}.png"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(res.stdout)
                self.refresh_shelf()
                self.show_toast(f"📸 Saved clipboard image: {filename}")
                return
        except Exception:
            pass

        # 2. Try to grab file URI from clipboard
        try:
            res = subprocess.run(["wl-paste", "--type", "text/uri-list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout:
                uris = res.stdout.strip().split("\n")
                count = 0
                for uri in uris:
                    if uri.startswith("file://"):
                        src_path = GLib.filename_from_uri(uri)[0]
                        if os.path.exists(src_path):
                            dest_path = os.path.join(SHELF_DIR, os.path.basename(src_path))
                            shutil.copy2(src_path, dest_path)
                            count += 1
                if count > 0:
                    self.refresh_shelf()
                    self.show_toast(f"📦 Stashed {count} file(s) from clipboard!")
                    return
        except Exception:
            pass

        # 3. Try to grab text from clipboard
        try:
            res = subprocess.run(["wl-paste"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                filename = f"snippet_{int(time.time())}.txt"
                filepath = os.path.join(SHELF_DIR, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(res.stdout)
                self.refresh_shelf()
                self.show_toast(f"📝 Stashed text snippet: {filename}")
                return
        except Exception:
            pass

        self.show_toast("Clipboard is empty or unrecognized format")

    def on_add_files_clicked(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="Select Files to Stash",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)

        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
            count = 0
            for fpath in filenames:
                if os.path.isfile(fpath):
                    dest = os.path.join(SHELF_DIR, os.path.basename(fpath))
                    if os.path.abspath(fpath) != os.path.abspath(dest):
                        shutil.copy2(fpath, dest)
                        count += 1
            if count > 0:
                self.refresh_shelf()
                self.show_toast(f"📦 Added {count} file(s) to shelf!")
        dialog.destroy()

    def on_clear_clicked(self, btn):
        if self.active_tab == "clip":
            subprocess.run(["cliphist", "wipe"], stderr=subprocess.DEVNULL)
            self.refresh_clipboard()
            self.show_toast("🗑️ Clipboard history cleared")
        else:
            try:
                for fname in os.listdir(SHELF_DIR):
                    fpath = os.path.join(SHELF_DIR, fname)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                self.refresh_shelf()
                self.show_toast("🗑️ Shelf cleared")
            except Exception as e:
                print("Error clearing shelf:", e)

    # =========================================================================
    # TAB SWITCHING & UTILITIES
    # =========================================================================
    def switch_tab(self, tab_name):
        self.active_tab = tab_name

        if tab_name == "clip":
            self.btn_tab_clip.get_style_context().add_class("active")
            self.btn_tab_shelf.get_style_context().remove_class("active")
            self.btn_stash_clip.hide()
            self.btn_add_files.hide()
            self.btn_clear_all.set_label("🗑️ Wipe All")
            self.stack.set_visible_child_name("clip")
            self.refresh_clipboard()
            self.clip_search.grab_focus()
        else:
            self.btn_tab_shelf.get_style_context().add_class("active")
            self.btn_tab_clip.get_style_context().remove_class("active")
            self.btn_stash_clip.show()
            self.btn_add_files.show()
            self.btn_clear_all.set_label("🗑️ Clear Shelf")
            self.stack.set_visible_child_name("shelf")
            self.refresh_shelf()

    def update_shelf_badge(self, count=None):
        if count is None:
            try:
                count = len([f for f in os.listdir(SHELF_DIR) if os.path.isfile(os.path.join(SHELF_DIR, f))])
            except Exception:
                count = 0
        if count > 0:
            self.btn_tab_shelf.set_label(f"📦 File Shelf ({count})")
        else:
            self.btn_tab_shelf.set_label("📦 File Shelf")

    def show_toast(self, message):
        self.lbl_status.set_text(message)
        GLib.timeout_add(3000, lambda: self.lbl_status.set_text("Tip: Drag items out to attach or upload · Press Esc to close"))

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
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def main():
    # Write PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    mode = "clip"
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if "shelf" in arg or "stash" in arg or "drop" in arg:
            mode = "shelf"

    with open(MODE_FILE, "w") as f:
        f.write(mode)

    win = SerenaShelfWindow(initial_tab=mode)
    win.show_all()
    if mode == "clip":
        win.btn_stash_clip.hide()
        win.btn_add_files.hide()
    Gtk.main()


if __name__ == "__main__":
    main()
