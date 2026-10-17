#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA & SYLVEON CENTERPIECE DESKTOP DASHBOARD
# ==============================================================================
# - Toggle được: Bấm Super + S hoặc click vào Đồng hồ để Bật/Tắt
# - Bấm phím Escape hoặc nút ✕ góc trên để đóng
# - Tự động thoát nếu đang có 1 bản chạy nền (Toggle switch)
# ==============================================================================

import os
import sys
import time
import calendar
import datetime
import threading
import urllib.request
import json
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

CSS_DATA = b"""
* {
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Segoe UI', sans-serif;
}

window#dashboard-window {
    background: transparent;
}

#main-card {
    background-color: rgba(24, 24, 37, 0.92);
    border: 1.5px solid rgba(229, 57, 53, 0.6);
    border-radius: 24px;
    padding: 20px 26px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.65);
}

.title-serena {
    color: #FF6B8B;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 2px;
}

.btn-close {
    color: #BAC2DE;
    background: transparent;
    border: none;
    font-size: 14px;
    padding: 2px 8px;
    border-radius: 8px;
}

.btn-close:hover {
    background: #E53935;
    color: #FFFFFF;
}

.clock-digits {
    color: #FFFFFF;
    font-size: 48px;
    font-weight: 800;
}

.clock-seconds {
    color: #FFB74D;
    font-size: 22px;
    font-weight: 700;
}

.date-text {
    color: #BAC2DE;
    font-size: 13.5px;
    font-weight: 600;
}

.temp-text {
    color: #FF8A80;
    font-size: 34px;
    font-weight: 800;
}

.weather-desc {
    color: #FFD180;
    font-size: 13px;
    font-weight: 600;
}

.stat-label {
    color: #A6ADC8;
    font-size: 11.5px;
    font-weight: bold;
}

.stat-value {
    color: #F5F5F5;
    font-size: 11.5px;
    font-weight: bold;
}

calendar {
    color: #CDD6F4;
    background-color: transparent;
    border: none;
    font-size: 11px;
}

calendar:selected {
    background-color: #E53935;
    color: #FFFFFF;
    border-radius: 6px;
}

calendar.header {
    color: #FF6B8B;
    font-weight: bold;
}

progressbar progress {
    background-color: #E53935;
    border-radius: 6px;
}

progressbar trough {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    min-height: 8px;
}
"""

PID_FILE = "/tmp/serena_dashboard.pid"

class SerenaDashboard(Gtk.Window):
    def __init__(self):
        super().__init__(title="Serena Dashboard")
        self.set_name("dashboard-window")
        self.set_wmclass("serena-dashboard", "serena-dashboard")
        self.set_decorated(False)
        self.set_resizable(False)

        # Định vị trí mở rộng ngay dưới đồng hồ Waybar (top-center dropdown)
        self.set_position(Gtk.WindowPosition.NONE)
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_primary_monitor() or display.get_monitor(0)
            if monitor:
                geom = monitor.get_geometry()
                dash_w = 760
                x = geom.x + (geom.width - dash_w) // 2
                y = geom.y + 46
                self.move(x, y)

        # Hỗ trợ nền trong suốt RGBA
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.apply_css()
        self.build_ui()

        # Bấm Escape để tắt
        self.connect("key-press-event", self.on_key_press)

        # Cập nhật thời gian mỗi giây
        GLib.timeout_add(1000, self.update_clock)
        # Cập nhật thông số hệ thống mỗi 3 giây
        GLib.timeout_add(3000, self.update_system_stats)
        # Cập nhật thời tiết
        threading.Thread(target=self.fetch_weather_async, daemon=True).start()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS_DATA)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_name("main-card")

        # --- HEADER NHÃN SERENA & NÚT ĐÓNG ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_brand = Gtk.Label(label="🌸 SERENA & SYLVEON DESKTOP 🌸")
        lbl_brand.get_style_context().add_class("title-serena")
        header_box.pack_start(lbl_brand, True, True, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda x: Gtk.main_quit())
        header_box.pack_end(btn_close, False, False, 0)

        main_box.pack_start(header_box, False, False, 0)

        # --- NỘI DUNG 3 CỘT (LỊCH | ĐỒNG HỒ | THỜI TIẾT) ---
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=26)

        # Cột 1: Lịch
        cal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_cal_title = Gtk.Label(label="📅 CALENDAR")
        lbl_cal_title.get_style_context().add_class("stat-label")
        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING | 
            Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES
        )
        cal_box.pack_start(lbl_cal_title, False, False, 0)
        cal_box.pack_start(self.calendar, True, True, 0)
        content_box.pack_start(cal_box, False, False, 0)

        # Cột 2: Đồng hồ khổng lồ (Trung tâm)
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        center_box.set_valign(Gtk.Align.CENTER)

        clock_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        clock_box.set_halign(Gtk.Align.CENTER)
        self.lbl_clock_hm = Gtk.Label(label="00:00")
        self.lbl_clock_hm.get_style_context().add_class("clock-digits")
        self.lbl_clock_sec = Gtk.Label(label=":00")
        self.lbl_clock_sec.get_style_context().add_class("clock-seconds")
        self.lbl_clock_sec.set_valign(Gtk.Align.END)
        self.lbl_clock_sec.set_margin_bottom(8)
        clock_box.pack_start(self.lbl_clock_hm, False, False, 0)
        clock_box.pack_start(self.lbl_clock_sec, False, False, 0)

        self.lbl_date = Gtk.Label(label="Monday, 01 January 2026")
        self.lbl_date.get_style_context().add_class("date-text")

        self.lbl_slogan = Gtk.Label(label="✨ Bloom like a Ribbon, Shine like a Rose ✨")
        self.lbl_slogan.get_style_context().add_class("stat-label")

        center_box.pack_start(clock_box, False, False, 0)
        center_box.pack_start(self.lbl_date, False, False, 0)
        center_box.pack_start(self.lbl_slogan, False, False, 4)
        content_box.pack_start(center_box, True, True, 10)

        # Cột 3: Thời tiết & Khí hậu
        weather_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        weather_box.set_valign(Gtk.Align.CENTER)
        lbl_wt_title = Gtk.Label(label="🌤️ WEATHER")
        lbl_wt_title.get_style_context().add_class("stat-label")

        self.lbl_temp = Gtk.Label(label="28°C")
        self.lbl_temp.get_style_context().add_class("temp-text")

        self.lbl_weather_desc = Gtk.Label(label="Partly Cloudy / Fair")
        self.lbl_weather_desc.get_style_context().add_class("weather-desc")

        self.lbl_humidity = Gtk.Label(label="💧 Humidity: 65%  |  💨 12 km/h")
        self.lbl_humidity.get_style_context().add_class("stat-label")

        weather_box.pack_start(lbl_wt_title, False, False, 0)
        weather_box.pack_start(self.lbl_temp, False, False, 0)
        weather_box.pack_start(self.lbl_weather_desc, False, False, 0)
        weather_box.pack_start(self.lbl_humidity, False, False, 2)
        content_box.pack_start(weather_box, False, False, 0)

        main_box.pack_start(content_box, True, True, 0)

        # --- THANH TIỆN ÍCH DƯỚI (STATS: CPU | RAM | UPTIME) ---
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(sep, False, False, 2)

        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        stats_box.set_halign(Gtk.Align.CENTER)

        # CPU
        self.cpu_bar = Gtk.ProgressBar()
        self.cpu_bar.set_size_request(70, 6)
        self.lbl_cpu = Gtk.Label(label=" CPU: 0%")
        self.lbl_cpu.get_style_context().add_class("stat-value")
        cpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        cpu_box.pack_start(self.lbl_cpu, False, False, 0)
        cpu_box.pack_start(self.cpu_bar, False, False, 0)
        stats_box.pack_start(cpu_box, False, False, 0)

        # RAM
        self.ram_bar = Gtk.ProgressBar()
        self.ram_bar.set_size_request(70, 6)
        self.lbl_ram = Gtk.Label(label="󰍛 RAM: 0%")
        self.lbl_ram.get_style_context().add_class("stat-value")
        ram_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        ram_box.pack_start(self.lbl_ram, False, False, 0)
        ram_box.pack_start(self.ram_bar, False, False, 0)
        stats_box.pack_start(ram_box, False, False, 0)

        # Uptime
        self.lbl_uptime = Gtk.Label(label="󱑂 Uptime: --")
        self.lbl_uptime.get_style_context().add_class("stat-value")
        self.lbl_uptime.set_valign(Gtk.Align.CENTER)
        stats_box.pack_start(self.lbl_uptime, False, False, 8)

        main_box.pack_start(stats_box, False, False, 0)

        self.add(main_box)
        self.update_clock()
        self.update_system_stats()

    def update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock_hm.set_text(now.strftime("%H:%M"))
        self.lbl_clock_sec.set_text(now.strftime(":%S"))
        self.lbl_date.set_text(now.strftime("%A, %d %B %Y"))
        return True

    def update_system_stats(self):
        try:
            with open('/proc/stat', 'r') as f:
                fields = [float(x) for x in f.readline().strip().split()[1:5]]
            idle = fields[3]
            total = sum(fields)
            if hasattr(self, '_prev_idle'):
                idle_delta = idle - self._prev_idle
                total_delta = total - self._prev_total
                cpu_pct = 100.0 * (1.0 - idle_delta / max(1, total_delta))
            else:
                cpu_pct = 5.0
            self._prev_idle = idle
            self._prev_total = total

            self.lbl_cpu.set_text(f" CPU: {int(cpu_pct)}%")
            self.cpu_bar.set_fraction(min(1.0, max(0.0, cpu_pct / 100.0)))

            with open('/proc/meminfo', 'r') as f:
                mem = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        mem[parts[0].strip()] = int(parts[1].strip().split()[0])
            total_ram = mem.get('MemTotal', 1)
            avail_ram = mem.get('MemAvailable', 0)
            used_pct = ((total_ram - avail_ram) / total_ram) * 100.0
            self.lbl_ram.set_text(f"󰍛 RAM: {int(used_pct)}%")
            self.ram_bar.set_fraction(min(1.0, max(0.0, used_pct / 100.0)))

            with open('/proc/uptime', 'r') as f:
                uptime_sec = float(f.readline().split()[0])
                hours = int(uptime_sec // 3600)
                minutes = int((uptime_sec % 3600) // 60)
                self.lbl_uptime.set_text(f"󱑂 Uptime: {hours}h {minutes}m")
        except Exception:
            pass
        return True

    def fetch_weather_async(self):
        try:
            url = "https://wttr.in/?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                curr = data['current_condition'][0]
                temp_c = curr['temp_C']
                desc = curr['weatherDesc'][0]['value']
                humidity = curr['humidity']
                wind = curr['windspeedKmph']

                def update_labels():
                    self.lbl_temp.set_text(f"{temp_c}°C")
                    self.lbl_weather_desc.set_text(desc)
                    self.lbl_humidity.set_text(f"💧 {humidity}%  |  💨 {wind} km/h")
                    return False
                GLib.idle_add(update_labels)
        except Exception:
            pass

def main():
    # Toggle logic: nếu đang mở thì đóng, nếu chưa thì mở
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 15) # SIGTERM
            os.remove(PID_FILE)
            return
        except Exception:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    app = SerenaDashboard()
    def cleanup_and_quit(*args):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    app.connect("destroy", cleanup_and_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
