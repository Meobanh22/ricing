#!/usr/bin/env python3
# tracker/browser.py — Firefox mozlz4 session tab & URL resolver.

import glob
import json
import os
import struct

from tracker.utils import clean_window_title


class FirefoxTabResolver:
    """Extracts URLs and tab titles from Firefox's sessionstore without any extension or CPU overhead."""

    @staticmethod
    def decompress_mozlz4(raw_bytes: bytes) -> bytes:
        """Decompress Mozilla mozlz4 headered raw LZ4 payload in pure Python."""
        if len(raw_bytes) < 12 or raw_bytes[:8] != b"mozLz40\0":
            return b""
        uncompressed_size = struct.unpack("<I", raw_bytes[8:12])[0]
        compressed = raw_bytes[12:]
        dest = bytearray(uncompressed_size)
        src_pos, dest_pos = 0, 0
        c_len = len(compressed)

        try:
            while src_pos < c_len and dest_pos < uncompressed_size:
                token = compressed[src_pos]
                src_pos += 1
                lit_len = token >> 4
                if lit_len == 15:
                    while src_pos < c_len:
                        extra = compressed[src_pos]
                        src_pos += 1
                        lit_len += extra
                        if extra != 255:
                            break
                dest[dest_pos : dest_pos + lit_len] = compressed[src_pos : src_pos + lit_len]
                dest_pos += lit_len
                src_pos += lit_len
                if dest_pos >= uncompressed_size:
                    break
                offset = compressed[src_pos] | (compressed[src_pos + 1] << 8)
                src_pos += 2
                match_len = (token & 0x0F) + 4
                if match_len == 19:
                    while src_pos < c_len:
                        extra = compressed[src_pos]
                        src_pos += 1
                        match_len += extra
                        if extra != 255:
                            break
                for _ in range(match_len):
                    dest[dest_pos] = dest[dest_pos - offset]
                    dest_pos += 1
            return bytes(dest)
        except Exception:
            return bytes(dest[:dest_pos])

    @classmethod
    def get_open_tabs(cls) -> dict:
        """Scan Firefox profile sessionstore files and return {title: url} map."""
        results = {}
        patterns = [
            os.path.expanduser("~/.config/mozilla/firefox/*default*/sessionstore-backups/recovery.jsonlz4"),
            os.path.expanduser("~/.mozilla/firefox/*default*/sessionstore-backups/recovery.jsonlz4"),
            os.path.expanduser("~/.config/mozilla/firefox/*default*/sessionstore-backups/recovery.baklz4"),
            os.path.expanduser("~/.mozilla/firefox/*default*/sessionstore-backups/recovery.baklz4"),
        ]
        files = []
        for p in patterns:
            files.extend(glob.glob(p))

        for fpath in files:
            try:
                with open(fpath, "rb") as f:
                    raw = f.read()
                dec = cls.decompress_mozlz4(raw)
                if not dec:
                    continue
                data = json.loads(dec.decode("utf-8", errors="ignore"))
                for w in data.get("windows", []):
                    for tab in w.get("tabs", []):
                        idx = tab.get("index", 1) - 1
                        entries = tab.get("entries", [])
                        if 0 <= idx < len(entries):
                            cur = entries[idx]
                            title = cur.get("title", "").strip()
                            url = cur.get("url", "").strip()
                            if title and url:
                                results[title] = url
                                clean_t = clean_window_title(title, "firefox")
                                if clean_t:
                                    results[clean_t] = url
            except Exception:
                pass
        return results

    @staticmethod
    def guess_url_from_title(title: str) -> str:
        """Heuristic fallback for common sites if tab was closed."""
        t = title.lower()
        mapping = (
            ("gemini", "https://gemini.google.com"),
            ("chatgpt", "https://chatgpt.com"),
            ("youtube", "https://youtube.com"),
            ("github", "https://github.com"),
            ("reddit", "https://reddit.com"),
            ("google search", "https://google.com"),
            ("facebook", "https://facebook.com"),
            ("add-ons for firefox", "https://addons.mozilla.org"),
            ("addons", "https://addons.mozilla.org"),
            ("about:processes", "about:processes"),
            ("process manager", "about:processes"),
            ("about:addons", "about:addons"),
            ("add-ons manager", "about:addons"),
        )
        for key, url in mapping:
            if key in t:
                return url
        return ""
