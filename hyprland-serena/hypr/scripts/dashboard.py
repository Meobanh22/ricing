#!/usr/bin/env python3
# Profile dashboard with clock, calendar, weather, and system uptime.

import os
import sys
import time
import datetime
import threading
import urllib.request
import json
import signal
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

# Path to external CSS stylesheet
STYLESHEET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles", "dashboard.css")

PID_FILE = "/tmp/dashboard.pid"

class Dashboard(Gtk.Window):
    def __init__(self):
        super().__init__(title="Dashboard")
        self.set_name("dashboard-window")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(700, -1)
        self.set_size_request(700, -1)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "dashboard")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 44)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        else:
            self.set_wmclass("dashboard", "dashboard")
            self.set_position(Gtk.WindowPosition.NONE)
            display = Gdk.Display.get_default()
            if display:
                monitor = display.get_primary_monitor() or display.get_monitor(0)
                if monitor:
                    geom = monitor.get_geometry()
                    dash_w = 720
                    x = geom.x + (geom.width - dash_w) // 2
                    y = geom.y + 44
                    self.move(x, y)

        # Nền trong suốt RGBA & Cairo squircle drawing (loại bỏ hoàn toàn góc nhọn)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", self.on_window_draw)

        self.apply_css()
        self.build_ui()

        # Bấm Escape để tắt
        self.connect("key-press-event", self.on_key_press)

        # Cập nhật thời gian & Uptime mỗi giây
        GLib.timeout_add(1000, self.update_clock)
        
        # Cập nhật thời tiết bất đồng bộ
        threading.Thread(target=self.fetch_weather_async, daemon=True).start()

    def on_window_draw(self, widget, cr):
        # 1. Xóa trong suốt 100% surface (triệt tiêu góc chữ nhật rò rỉ)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # 2. Vẽ hình squircle chuẩn 16px
        alloc = widget.get_allocation()
        pad = 0.5
        w = float(alloc.width) - pad * 2.0
        h = float(alloc.height) - pad * 2.0
        x = pad
        y = pad
        r = 16.0

        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.57079632679, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.57079632679)
        cr.arc(x + r, y + h - r, r, 1.57079632679, 3.14159265359)
        cr.arc(x + r, y + r, r, 3.14159265359, 4.71238898038)
        cr.close_path()

        # Nền ấm Obsidian-Wine (--bg-window: rgba(32, 16, 18, 0.98))
        cr.set_source_rgba(32.0 / 255.0, 16.0 / 255.0, 18.0 / 255.0, 0.98)
        cr.fill_preserve()

        # Draw the shared outer window border.
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        return False

    def close_and_quit(self):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_and_quit()
            return True
        return False

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_file = STYLESHEET_PATH
        if not os.path.exists(css_file):
            css_file = os.path.expanduser("~/.config/hypr/styles/dashboard.css")
        if os.path.exists(css_file):
            try:
                css_provider.load_from_path(css_file)
            except Exception as e:
                print(f"Warning: Failed to load CSS from {css_file}: {e}", file=sys.stderr)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def load_avatar(self, size=86):
        paths = [
            os.path.expanduser("~/.config/hypr/serena_lock_avatar.png"),
            "/home/meobanh/custom/ricing/hyprland-serena/hypr/serena_lock_avatar.png",
            "/home/meobanh/custom/ricing/assets/serena_lock_avatar.png",
        ]
        avatar_path = None
        for p in paths:
            if os.path.exists(p):
                avatar_path = p
                break

        if not avatar_path:
            lbl = Gtk.Label()
            lbl.set_markup("<span font='42' color='#FF2A55'>✿</span>")
            return lbl

        try:
            import cairo
            src = GdkPixbuf.Pixbuf.new_from_file_at_scale(avatar_path, size, size, True)
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            cr = cairo.Context(surface)
            cr.set_antialias(cairo.ANTIALIAS_BEST)

            # Khung tròn bo viền
            cr.arc(size / 2.0, size / 2.0, size / 2.0 - 2.0, 0, 2 * 3.1415926535)
            cr.clip()

            w = src.get_width()
            h = src.get_height()
            Gdk.cairo_set_source_pixbuf(cr, src, (size - w) / 2.0, (size - h) / 2.0)
            cr.paint()

            # Viền đỏ ruy-băng mảnh sang trọng
            cr.reset_clip()
            cr.arc(size / 2.0, size / 2.0, size / 2.0 - 2.0, 0, 2 * 3.1415926535)
            cr.set_source_rgba(1.0, 0.165, 0.333, 0.95) # #FF2A55
            cr.set_line_width(2.0)
            cr.stroke()

            pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)
            return Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(avatar_path, size, size, True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                lbl = Gtk.Label()
                lbl.set_markup("<span font='42' color='#FF2A55'>✿</span>")
                return lbl

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        main_box.set_name("main-card")

        # =====================================================================
        # 1. PROFILE HERO CARD (LEFT)
        # =====================================================================
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        profile_box.get_style_context().add_class("profile-card")
        profile_box.set_size_request(225, -1)
        profile_box.set_valign(Gtk.Align.FILL)

        # Avatar container (centered)
        avatar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        avatar_box.set_halign(Gtk.Align.CENTER)
        avatar_img = self.load_avatar(86)
        avatar_box.pack_start(avatar_img, False, False, 0)
        profile_box.pack_start(avatar_box, False, False, 2)

        # Tên & Username
        user_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        user_info_box.set_halign(Gtk.Align.CENTER)

        lbl_name = Gtk.Label(label="Serena")
        lbl_name.get_style_context().add_class("profile-name")
        user_info_box.pack_start(lbl_name, False, False, 0)

        username = os.getenv("USER") or "meobanh"
        lbl_username = Gtk.Label(label=f"@{username} · Kalos")
        lbl_username.get_style_context().add_class("profile-user")
        user_info_box.pack_start(lbl_username, False, False, 0)

        # Status badge (Online / Active)
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_halign(Gtk.Align.CENTER)
        lbl_status = Gtk.Label()
        lbl_status.set_markup("<span foreground='#8FBC8F'>●</span> Active")
        lbl_status.get_style_context().add_class("profile-status")
        status_box.pack_start(lbl_status, False, False, 0)
        user_info_box.pack_start(status_box, False, False, 4)

        profile_box.pack_start(user_info_box, False, False, 0)

        # Slogan / Bio
        lbl_bio = Gtk.Label()
        lbl_bio.set_line_wrap(True)
        lbl_bio.set_justify(Gtk.Justification.CENTER)
        lbl_bio.set_markup("<span font='9.5' color='#FFF0F5'><i>\"Bloom like a Ribbon,\nShine like a Rose\"</i></span>")
        profile_box.pack_start(lbl_bio, False, False, 2)

        # Đường phân cách nhẹ trong Profile
        sep_profile = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        profile_box.pack_start(sep_profile, False, False, 4)

        # Thông tin hệ thống & Thời gian hoạt động (Uptime)
        info_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        info_list_box.set_halign(Gtk.Align.START)
        info_list_box.set_margin_start(8)
        info_list_box.set_margin_end(8)

        # Uptime
        row_uptime = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_up_ic = Gtk.Label(label="󱑂")
        lbl_up_ic.get_style_context().add_class("info-icon")
        self.lbl_uptime = Gtk.Label(label="Uptime: --")
        self.lbl_uptime.get_style_context().add_class("info-item")
        row_uptime.pack_start(lbl_up_ic, False, False, 0)
        row_uptime.pack_start(self.lbl_uptime, False, False, 0)
        info_list_box.pack_start(row_uptime, False, False, 0)

        # Desktop Environment / Window Manager
        row_os = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_os_ic = Gtk.Label(label="󰌌")
        lbl_os_ic.get_style_context().add_class("info-icon")
        lbl_os = Gtk.Label(label="Hyprland Wayland")
        lbl_os.get_style_context().add_class("info-item")
        row_os.pack_start(lbl_os_ic, False, False, 0)
        row_os.pack_start(lbl_os, False, False, 0)
        info_list_box.pack_start(row_os, False, False, 0)

        profile_box.pack_start(info_list_box, False, False, 2)
        main_box.pack_start(profile_box, False, False, 0)

        # =====================================================================
        # 2. DASHBOARD TILES (RIGHT: CLOCK | CALENDAR | WEATHER)
        # =====================================================================
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Top Header (Title + Close Button)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_brand = Gtk.Label()
        lbl_brand.set_markup("<span font='12' color='#FF2A55'>✿</span>   <span color='#FFF0F5' font='11' weight='bold' letter_spacing='1024'>PROFILE DASHBOARD</span>")
        header_box.pack_start(lbl_brand, True, True, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda x: self.close_and_quit())
        header_box.pack_end(btn_close, False, False, 0)
        right_box.pack_start(header_box, False, False, 0)

        # Big Center Clock & Date Card
        clock_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        clock_card.get_style_context().add_class("card-tile")
        clock_card.set_halign(Gtk.Align.FILL)

        clock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        clock_row.set_halign(Gtk.Align.CENTER)
        self.lbl_clock_hm = Gtk.Label(label="00:00")
        self.lbl_clock_hm.get_style_context().add_class("clock-digits")
        self.lbl_clock_sec = Gtk.Label(label=":00")
        self.lbl_clock_sec.get_style_context().add_class("clock-seconds")
        self.lbl_clock_sec.set_valign(Gtk.Align.END)
        self.lbl_clock_sec.set_margin_bottom(6)
        clock_row.pack_start(self.lbl_clock_hm, False, False, 0)
        clock_row.pack_start(self.lbl_clock_sec, False, False, 0)

        self.lbl_date = Gtk.Label(label="Monday, 01 January 2026")
        self.lbl_date.get_style_context().add_class("date-text")
        self.lbl_date.set_halign(Gtk.Align.CENTER)

        clock_card.pack_start(clock_row, False, False, 0)
        clock_card.pack_start(self.lbl_date, False, False, 2)
        right_box.pack_start(clock_card, False, False, 0)

        # Bottom Grid (Calendar + Weather)
        bottom_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Calendar Card
        cal_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cal_card.get_style_context().add_class("card-tile")
        lbl_cal_title = Gtk.Label()
        lbl_cal_title.set_markup("<span font='11.5' color='#FF2A55'>󰸗</span>   <span color='#FFF0F5' weight='bold'>CALENDAR</span>")
        lbl_cal_title.set_halign(Gtk.Align.START)

        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING | 
            Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES
        )
        cal_card.pack_start(lbl_cal_title, False, False, 0)
        cal_card.pack_start(self.calendar, True, True, 0)
        bottom_grid.pack_start(cal_card, True, True, 0)

        # Weather Card
        weather_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        weather_card.get_style_context().add_class("card-tile")
        weather_card.set_valign(Gtk.Align.FILL)

        self.lbl_wt_title = Gtk.Label()
        self.lbl_wt_title.set_markup("<span font='11.5' color='#FF2A55'>󰖙</span>   <span color='#FFF0F5' weight='bold'>WEATHER</span>")
        self.lbl_wt_title.set_halign(Gtk.Align.START)
        weather_card.pack_start(self.lbl_wt_title, False, False, 0)

        self.lbl_temp = Gtk.Label(label="--°C")
        self.lbl_temp.get_style_context().add_class("temp-text")
        self.lbl_temp.set_halign(Gtk.Align.START)
        weather_card.pack_start(self.lbl_temp, False, False, 2)

        self.lbl_weather_desc = Gtk.Label(label="Loading weather...")
        self.lbl_weather_desc.get_style_context().add_class("weather-desc")
        self.lbl_weather_desc.set_halign(Gtk.Align.START)
        weather_card.pack_start(self.lbl_weather_desc, False, False, 0)

        self.lbl_humidity = Gtk.Label()
        self.lbl_humidity.get_style_context().add_class("weather-sub")
        self.lbl_humidity.set_markup("<span font='10.5' color='#FF2A55'>󰖌</span> <span color='#FFF0F5'>--%</span>    <span color='#FFF0F5'>·</span>    <span font='10.5' color='#FF2A55'>󰖝</span> <span color='#FFF0F5'>-- km/h</span>")
        self.lbl_humidity.set_halign(Gtk.Align.START)
        weather_card.pack_start(self.lbl_humidity, False, False, 2)

        bottom_grid.pack_start(weather_card, True, True, 0)
        right_box.pack_start(bottom_grid, True, True, 0)

        main_box.pack_start(right_box, True, True, 0)

        self.add(main_box)
        self.update_clock()

    def update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock_hm.set_text(now.strftime("%H:%M"))
        self.lbl_clock_sec.set_text(now.strftime(":%S"))
        self.lbl_date.set_text(now.strftime("%A, %d %B %Y"))

        # Cập nhật Uptime trong profile card
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_sec = float(f.readline().split()[0])
                hours = int(uptime_sec // 3600)
                minutes = int((uptime_sec % 3600) // 60)
                self.lbl_uptime.set_text(f"Uptime: {hours}h {minutes}m")
        except Exception:
            pass

        return True

    def fetch_weather_async(self):
        def get_weather_icon(desc, hour):
            low = desc.lower()
            is_day = 6 <= hour < 18
            if "thunder" in low or "lightning" in low:
                return "󰖓"
            elif "snow" in low or "ice" in low or "sleet" in low or "blizzard" in low:
                return "󰖘"
            elif "rain" in low or "drizzle" in low or "shower" in low:
                return "󰖗"
            elif "fog" in low or "mist" in low or "haze" in low:
                return "󰖑"
            elif "partly cloudy" in low or "few clouds" in low:
                return "󰖕" if is_day else "󰼱"
            elif "cloud" in low or "overcast" in low:
                return "󰖐"
            elif "clear" in low or "sunny" in low:
                return "󰖙" if is_day else "󰖔"
            else:
                return "󰖕" if is_day else "󰖔"

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
                    current_hour = datetime.datetime.now().hour
                    icon = get_weather_icon(desc, current_hour)
                    self.lbl_wt_title.set_markup(f"<span font='11.5' color='#FF2A55'>{icon}</span>   <span color='#FFF0F5' weight='bold'>WEATHER</span>")
                    self.lbl_temp.set_text(f"{temp_c}°C")
                    self.lbl_weather_desc.set_text(desc)
                    self.lbl_humidity.set_markup(f"<span font='10.5' color='#FF2A55'>󰖌</span> <span color='#FFF0F5'>{humidity}%</span>    <span color='#FFF0F5'>·</span>    <span font='10.5' color='#FF2A55'>󰖝</span> <span color='#FFF0F5'>{wind} km/h</span>")
                    return False
                GLib.idle_add(update_labels)
        except Exception:
            pass

def main():
    def sig_handler(signum, frame):
        GLib.idle_add(Gtk.main_quit)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    my_pid = os.getpid()
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(my_pid))
    except Exception:
        pass

    app = Dashboard()

    def cleanup(*args):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    app.connect("destroy", cleanup)
    app.show_all()
    try:
        Gtk.main()
    finally:
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

if __name__ == "__main__":
    main()
