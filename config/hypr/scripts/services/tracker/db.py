#!/usr/bin/env python3
# tracker/db.py — SQLite persistence layer for Hyprland app & web usage tracking.

import os
import sqlite3
import time

from tracker.browser import FirefoxTabResolver
from tracker.utils import (
    DB_PATH,
    clean_window_title,
    get_domain,
    get_uptime_seconds,
    is_browser_app,
)


class TrackerDB:
    """SQLite database manager for application and browser tab usage."""

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=10.0)
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self._init_tables()

    def _init_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS app_usage (
                    boot_id TEXT,
                    date TEXT,
                    app_class TEXT,
                    total_seconds REAL DEFAULT 0,
                    PRIMARY KEY (boot_id, date, app_class)
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS app_titles (
                    boot_id TEXT,
                    date TEXT,
                    app_class TEXT,
                    title TEXT,
                    total_seconds REAL DEFAULT 0,
                    url TEXT DEFAULT '',
                    PRIMARY KEY (boot_id, date, app_class, title)
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS boot_meta (
                    boot_id TEXT PRIMARY KEY,
                    boot_time REAL,
                    first_seen REAL,
                    last_seen REAL
                );
            """)
            try:
                self.conn.execute("ALTER TABLE app_titles ADD COLUMN url TEXT DEFAULT '';")
            except Exception:
                pass

    def record_usage(self, boot_id: str, date_str: str, app_class: str, title: str, seconds: float, url: str = ""):
        if seconds <= 0:
            return
        now = time.time()
        title_trimmed = (title or "")[:200].strip()

        with self.conn:
            self.conn.execute("""
                INSERT INTO app_usage (boot_id, date, app_class, total_seconds)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(boot_id, date, app_class)
                DO UPDATE SET total_seconds = total_seconds + excluded.total_seconds;
            """, (boot_id, date_str, app_class, seconds))

            if title_trimmed:
                self.conn.execute("""
                    INSERT INTO app_titles (boot_id, date, app_class, title, total_seconds, url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(boot_id, date, app_class, title)
                    DO UPDATE SET
                        total_seconds = total_seconds + excluded.total_seconds,
                        url = CASE WHEN excluded.url != '' THEN excluded.url ELSE app_titles.url END;
                """, (boot_id, date_str, app_class, title_trimmed, seconds, url))

            self.conn.execute("""
                INSERT INTO boot_meta (boot_id, boot_time, first_seen, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(boot_id)
                DO UPDATE SET last_seen = excluded.last_seen;
            """, (boot_id, now - get_uptime_seconds(), now, now))

    def get_session_stats(self, boot_id: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT app_class, SUM(total_seconds) as total
            FROM app_usage
            WHERE boot_id = ?
            GROUP BY app_class
            ORDER BY total DESC;
        """, (boot_id,))
        return cursor.fetchall()

    def get_today_stats(self, date_str: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT app_class, SUM(total_seconds) as total
            FROM app_usage
            WHERE date = ?
            GROUP BY app_class
            ORDER BY total DESC;
        """, (date_str,))
        return cursor.fetchall()

    def get_top_web_titles(self, boot_id: str = None, date_str: str = None, limit: int = 8):
        cursor = self.conn.cursor()
        query = """
            SELECT app_class, title, SUM(total_seconds) as total, MAX(url) as saved_url
            FROM app_titles
            WHERE (app_class LIKE '%firefox%' OR app_class LIKE '%chrome%' OR app_class LIKE '%brave%' OR app_class LIKE '%chromium%' OR app_class LIKE '%zen%')
        """
        params = []
        if boot_id:
            query += " AND boot_id = ?"
            params.append(boot_id)
        elif date_str:
            query += " AND date = ?"
            params.append(date_str)

        query += " GROUP BY title ORDER BY total DESC LIMIT 60;"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        live_tabs = FirefoxTabResolver.get_open_tabs()

        results = []
        seen = set()
        for app_cls, title, duration, saved_url in rows:
            clean = clean_window_title(title, app_cls)
            low = clean.lower()
            if not clean or low in ("mozilla firefox", "firefox", "google chrome", "brave", "new tab", "tab mới"):
                continue
            if clean in seen:
                continue
            seen.add(clean)

            resolved_url = saved_url or ""
            if not resolved_url:
                resolved_url = live_tabs.get(clean) or live_tabs.get(title) or ""
            if not resolved_url:
                resolved_url = FirefoxTabResolver.guess_url_from_title(clean)

            domain = get_domain(resolved_url)
            results.append((app_cls, clean, duration, resolved_url, domain))
            if len(results) >= limit:
                break
        return results

    def get_app_details(self, app_class: str, boot_id: str = None, date_str: str = None):
        cursor = self.conn.cursor()
        query = """
            SELECT title, SUM(total_seconds) as total, MAX(url) as saved_url
            FROM app_titles
            WHERE (app_class = ? OR app_class LIKE ?)
        """
        params = [app_class, f"%{app_class}%"]
        if boot_id:
            query += " AND boot_id = ?"
            params.append(boot_id)
        elif date_str:
            query += " AND date = ?"
            params.append(date_str)

        query += " GROUP BY title ORDER BY total DESC LIMIT 40;"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        live_tabs = FirefoxTabResolver.get_open_tabs() if is_browser_app(app_class) else {}
        results = []
        for title, duration, saved_url in rows:
            clean = clean_window_title(title, app_class)
            resolved_url = saved_url or live_tabs.get(clean) or live_tabs.get(title) or FirefoxTabResolver.guess_url_from_title(clean)
            results.append((title, duration, resolved_url))
        return results

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
