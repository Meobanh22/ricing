#!/usr/bin/env python3
# shelf_pkg/storage.py — Thumbnail decoding, pinned clip persistence, and size formatting.

import json
import os
import shutil
import subprocess
import time

from gi.repository import GdkPixbuf, GLib

from shelf_pkg.constants import PINNED_FILE, PINS_DIR


class ShelfStorageMixin:
    """Async image thumbnail caching, pinned clipboard storage, and cliphist daemon setup."""

    def get_scaled_pixbuf(self, fpath: str, max_w: int, max_h: int):
        if not fpath or not os.path.exists(fpath):
            return None
        try:
            mtime = os.path.getmtime(fpath)
            key = (fpath, mtime, max_w, max_h)
            if key in self._thumb_cache:
                return self._thumb_cache[key]
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(fpath, max_w, max_h, True)
            if len(self._thumb_cache) > 120:
                self._thumb_cache.clear()
            self._thumb_cache[key] = pixbuf
            return pixbuf
        except Exception:
            return None

    def load_clip_thumbnail_async(self, item, max_w: int, max_h: int, img_widget):
        if not item:
            return

        if item.get("img_path") and os.path.exists(item["img_path"]):
            card_pixbuf = self.get_scaled_pixbuf(item["img_path"], max_w, max_h)
            if card_pixbuf:
                img_widget.set_from_pixbuf(card_pixbuf)
                return

        clip_id = item.get("id")
        cache_key = (clip_id, max_w, max_h)

        if clip_id and cache_key in self._clip_thumb_cache:
            pb = self._clip_thumb_cache[cache_key]
            if pb:
                img_widget.set_from_pixbuf(pb)
                return

        raw_bytes = self._clip_raw_cache.get(clip_id) if clip_id else None
        if raw_bytes:
            try:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(raw_bytes)
                loader.close()
                pixbuf = loader.get_pixbuf()
                if pixbuf:
                    orig_w, orig_h = pixbuf.get_width(), pixbuf.get_height()
                    ratio = min(max_w / orig_w, max_h / orig_h)
                    scaled = pixbuf.scale_simple(max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio)), GdkPixbuf.InterpType.BILINEAR)
                    if clip_id:
                        self._clip_thumb_cache[cache_key] = scaled
                    img_widget.set_from_pixbuf(scaled)
                    return
            except Exception:
                pass

        raw_line = item.get("raw", "")
        if not raw_line:
            return

        img_widget._target_clip_id = clip_id

        def _bg_decode():
            try:
                p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                out_bytes, _ = p.communicate(input=raw_line.encode("utf-8"), timeout=1.5)
                if not out_bytes:
                    return None, None
                loader = GdkPixbuf.PixbufLoader()
                loader.write(out_bytes)
                loader.close()
                pixbuf = loader.get_pixbuf()
                scaled = None
                if pixbuf:
                    orig_w, orig_h = pixbuf.get_width(), pixbuf.get_height()
                    ratio = min(max_w / orig_w, max_h / orig_h)
                    scaled = pixbuf.scale_simple(max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio)), GdkPixbuf.InterpType.BILINEAR)
                return out_bytes, scaled
            except Exception:
                return None, None

        def _on_done(future):
            try:
                out_bytes, scaled = future.result()
                if out_bytes and clip_id:
                    self._clip_raw_cache[clip_id] = out_bytes
                    if len(self._clip_raw_cache) > 40:
                        for k in list(self._clip_raw_cache.keys())[:15]:
                            del self._clip_raw_cache[k]
                if scaled and clip_id:
                    self._clip_thumb_cache[cache_key] = scaled
                    if len(self._clip_thumb_cache) > 80:
                        for k in list(self._clip_thumb_cache.keys())[:30]:
                            del self._clip_thumb_cache[k]

                def _apply_ui():
                    try:
                        if not img_widget.in_destruction() and getattr(img_widget, '_target_clip_id', None) == clip_id:
                            if scaled:
                                img_widget.set_from_pixbuf(scaled)
                    except Exception:
                        pass
                    return False

                GLib.idle_add(_apply_ui)
            except Exception:
                pass

        try:
            future = self._thread_pool.submit(_bg_decode)
            future.add_done_callback(_on_done)
        except Exception:
            pass

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

    def _clip_matches(self, item, candidate) -> bool:
        if item.get("is_image") and candidate.get("is_image"):
            return candidate.get("id") == item.get("id") or bool(candidate.get("raw") and candidate.get("raw") == item.get("raw"))
        if not item.get("is_image") and not candidate.get("is_image"):
            t1 = (item.get("full_text") or item.get("preview", "")).strip()
            t2 = (candidate.get("full_text") or candidate.get("preview", "")).strip()
            return bool(t1 and t1 == t2)
        return False

    def is_item_pinned(self, item, pins=None):
        if item.get("is_pinned"):
            return True
        if pins is None:
            pins = self.load_pinned_clips()
        return any(self._clip_matches(item, p) for p in pins)

    def toggle_pin_clip(self, item):
        self.hide_popout()
        pins = self.load_pinned_clips()
        found_idx = next((idx for idx, p in enumerate(pins) if self._clip_matches(item, p)), -1)

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
                "raw": item.get("raw", ""),
            }
            if item.get("is_image"):
                pin_img_path = os.path.join(PINS_DIR, f"{pin_id}.png")
                try:
                    if item.get("img_path") and os.path.exists(item["img_path"]):
                        shutil.copy2(item["img_path"], pin_img_path)
                    else:
                        clip_id = item.get("id")
                        if clip_id and clip_id in self._clip_raw_cache:
                            img_data = self._clip_raw_cache[clip_id]
                        else:
                            p = subprocess.Popen(["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                            img_data, _ = p.communicate(input=item["raw"].encode("utf-8"), timeout=1.5)
                            if clip_id and img_data:
                                self._clip_raw_cache[clip_id] = img_data
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

    @staticmethod
    def format_file_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes}B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f}KB"
        return f"{size_bytes / (1024 * 1024):.1f}MB"
