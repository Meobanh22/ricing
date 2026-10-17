#!/usr/bin/env python3
# ==============================================================================
# 🌸 SERENA & SYLVEON FLOATING POP-UP CONTROL CENTER
# ==============================================================================
# - Floating pop-up anchored right beneath Waybar's top-right capsule
# - Hardware accelerated slide-down animation via Hyprland layer-shell rules
# - Live Status Pill (IME, WiFi, Battery)
# - Interactive Audio Volume & Display Brightness sliders
# - Quick Actions: WiFi, Bluetooth, Vietnamese IME Toggle, Power Menu
# - Mini System Resource monitor (CPU & RAM)
# - Toggleable via Super + N, clicking Waybar, Escape key, or clicking outside
# ==============================================================================

import os
import sys
import glob
import subprocess
import threading
import gi

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib

PID_FILE = "/tmp/serena_control_center.pid"

CSS_DATA = b"""
* {
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Segoe UI', sans-serif;
}

window#control-center-window {
    background: transparent;
}

#cc-main-card {
    background-color: rgba(24, 24, 37, 0.95);
    border: 1.5px solid rgba(229, 57, 53, 0.7);
    border-radius: 20px;
    padding: 18px 20px;
    box-shadow: 0 10px 32px rgba(0, 0, 0, 0.7);
    min-width: 330px;
}

/* Header */
.title-serena {
    color: #FF6B8B;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.5px;
}

.btn-close {
    color: #BAC2DE;
    background: transparent;
    border: none;
    font-size: 14px;
    padding: 2px 8px;
    border-radius: 8px;
    transition: all 0.15s ease;
}

.btn-close:hover {
    background: #E53935;
    color: #FFFFFF;
}

/* Live Status Pill */
#status-pill {
    background: rgba(30, 30, 46, 0.88);
    border: 1px solid rgba(229, 57, 53, 0.4);
    border-radius: 12px;
    padding: 7px 12px;
    margin: 4px 0 8px 0;
}

.status-pill-text {
    color: #BAC2DE;
    font-size: 12px;
    font-weight: 700;
}

/* Section Box */
.section-box {
    background: rgba(30, 30, 46, 0.8);
    border: 1px solid rgba(229, 57, 53, 0.3);
    border-radius: 14px;
    padding: 10px 14px;
    margin: 4px 0;
}

.slider-label {
    color: #CDD6F4;
    font-size: 12px;
    font-weight: 700;
}

.slider-val {
    color: #FF8A80;
    font-size: 12px;
    font-weight: 800;
    min-width: 38px;
}

.btn-slider-icon {
    background: transparent;
    border: none;
    color: #FF6B8B;
    font-size: 16px;
    padding: 0 6px 0 0;
}

.btn-slider-icon:hover {
    color: #FF8A80;
}

/* Scales / Sliders */
scale {
    margin: 2px 4px;
    padding: 0;
}

scale trough {
    background-color: rgba(49, 50, 68, 0.85);
    border-radius: 8px;
    min-height: 8px;
}

scale trough highlight {
    background: linear-gradient(90deg, #E53935 0%, #FF6B8B 100%);
    border-radius: 8px;
}

scale slider {
    background-color: #FFFFFF;
    border: 2.5px solid #E53935;
    border-radius: 100%;
    min-width: 14px;
    min-height: 14px;
    margin: -3px;
    box-shadow: 0 0 8px rgba(229, 57, 53, 0.6);
}

scale slider:hover {
    box-shadow: 0 0 12px rgba(255, 107, 139, 0.95);
    background-color: #FFF0F5;
}

/* Quick Action Buttons */
.quick-btn {
    background: rgba(24, 24, 37, 0.9);
    border: 1px solid rgba(229, 57, 53, 0.35);
    border-radius: 12px;
    color: #CDD6F4;
    padding: 10px 0;
    font-size: 17px;
    transition: all 0.2s ease;
}

.quick-btn:hover {
    background: linear-gradient(135deg, #E53935 0%, #FF6B8B 100%);
    border-color: #FF6B8B;
    color: #FFFFFF;
    box-shadow: 0 3px 12px rgba(229, 57, 53, 0.55);
}

.quick-btn-power {
    background: linear-gradient(135deg, #E53935 0%, #FF6B8B 100%);
    border: 1px solid #FF6B8B;
    color: #FFFFFF;
    box-shadow: 0 2px 8px rgba(229, 57, 53, 0.45);
}

.quick-btn-power:hover {
    background: #E53935;
    box-shadow: 0 0 14px rgba(255, 107, 139, 0.95);
}

/* System Stats */
.stat-name {
    color: #A6ADC8;
    font-size: 11px;
    font-weight: 700;
}

.stat-num {
    color: #F5F5F5;
    font-size: 11px;
    font-weight: 800;
}

progressbar progress {
    background: linear-gradient(90deg, #E53935 0%, #FF6B8B 100%);
    border-radius: 6px;
}

progressbar trough {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    min-height: 6px;
}

/* Footer Action */
.btn-footer {
    background: rgba(30, 30, 46, 0.7);
    border: 1px solid rgba(229, 57, 53, 0.35);
    border-radius: 10px;
    color: #BAC2DE;
    padding: 6px 12px;
    font-size: 11.5px;
    font-weight: 700;
    transition: all 0.2s ease;
}

.btn-footer:hover {
    background: #E53935;
    color: #FFFFFF;
    border-color: #E53935;
}
"""

class SerenaControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Serena Control Center")
        self.set_name("control-center-window")
        self.set_wmclass("serena-control-center", "serena-control-center")
        self.set_decorated(False)
        self.set_resizable(False)

        # Flag to prevent focus-out from quitting immediately before the window is rendered
        self.has_focused = False
        self.updating_sliders = False

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "serena-control-center")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 44)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 14)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        else:
            self.set_position(Gtk.WindowPosition.NONE)
            display = Gdk.Display.get_default()
            if display:
                monitor = display.get_primary_monitor() or display.get_monitor(0)
                if monitor:
                    geom = monitor.get_geometry()
                    dash_w = 360
                    x = geom.x + geom.width - dash_w - 14
                    y = geom.y + 44
                    self.move(x, y)

        # RGBA transparent visual
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.apply_css()
        self.build_ui()

        # Keyboard & Focus events
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-in-event", self.on_focus_in)
        self.connect("focus-out-event", self.on_focus_out)

        # Enable dismiss after 400ms to avoid premature dismissal
        GLib.timeout_add(400, self.enable_focus_tracking)

        # Periodic status refresh
        GLib.timeout_add(2000, self.refresh_status_pill)
        GLib.timeout_add(3000, self.refresh_system_stats)

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS_DATA)
        context = Gtk.StyleContext()
        screen = Gdk.Screen.get_default()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_and_quit()
            return True
        return False

    def enable_focus_tracking(self):
        self.has_focused = True
        return False

    def on_focus_in(self, widget, event):
        self.has_focused = True
        return False

    def on_focus_out(self, widget, event):
        if self.has_focused:
            self.close_and_quit()
        return False

    def close_and_quit(self):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    def build_ui(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.set_name("cc-main-card")

        # --- 1. HEADER (Title & Close Button) ---
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_title = Gtk.Label(label="🌸 CONTROL CENTER 🌸")
        lbl_title.get_style_context().add_class("title-serena")
        header_box.pack_start(lbl_title, True, True, 0)

        btn_close = Gtk.Button(label="✕")
        btn_close.get_style_context().add_class("btn-close")
        btn_close.connect("clicked", lambda x: self.close_and_quit())
        header_box.pack_end(btn_close, False, False, 0)
        card.pack_start(header_box, False, False, 0)

        # --- 2. LIVE STATUS PILL ---
        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        pill_box.set_name("status-pill")
        pill_box.set_halign(Gtk.Align.FILL)

        self.lbl_status = Gtk.Label(label="Loading status...")
        self.lbl_status.get_style_context().add_class("status-pill-text")
        self.lbl_status.set_halign(Gtk.Align.CENTER)
        pill_box.pack_start(self.lbl_status, True, True, 0)
        card.pack_start(pill_box, False, False, 0)

        # --- 3. VOLUME SLIDER SECTION ---
        vol_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vol_box.get_style_context().add_class("section-box")

        vol_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_vol_icon = Gtk.Button(label="󰕾")
        self.btn_vol_icon.get_style_context().add_class("btn-slider-icon")
        self.btn_vol_icon.connect("clicked", self.toggle_audio_mute)
        vol_top.pack_start(self.btn_vol_icon, False, False, 0)

        lbl_vol_title = Gtk.Label(label="Audio Volume")
        lbl_vol_title.get_style_context().add_class("slider-label")
        vol_top.pack_start(lbl_vol_title, True, True, 0)

        self.lbl_vol_val = Gtk.Label(label="50%")
        self.lbl_vol_val.get_style_context().add_class("slider-val")
        vol_top.pack_end(self.lbl_vol_val, False, False, 0)
        vol_box.pack_start(vol_top, False, False, 0)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_draw_value(False)
        self.vol_scale.connect("value-changed", self.on_vol_changed)
        vol_box.pack_start(self.vol_scale, False, False, 0)
        card.pack_start(vol_box, False, False, 0)

        # --- 4. BRIGHTNESS SLIDER SECTION ---
        bri_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bri_box.get_style_context().add_class("section-box")

        bri_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_bri_icon = Gtk.Label(label="󰃠")
        lbl_bri_icon.get_style_context().add_class("btn-slider-icon")
        bri_top.pack_start(lbl_bri_icon, False, False, 0)

        lbl_bri_title = Gtk.Label(label="Display Brightness")
        lbl_bri_title.get_style_context().add_class("slider-label")
        bri_top.pack_start(lbl_bri_title, True, True, 0)

        self.lbl_bri_val = Gtk.Label(label="80%")
        self.lbl_bri_val.get_style_context().add_class("slider-val")
        bri_top.pack_end(self.lbl_bri_val, False, False, 0)
        bri_box.pack_start(bri_top, False, False, 0)

        self.bri_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 100, 1)
        self.bri_scale.set_draw_value(False)
        self.bri_scale.connect("value-changed", self.on_bri_changed)
        bri_box.pack_start(self.bri_scale, False, False, 0)
        card.pack_start(bri_box, False, False, 0)

        # --- 5. QUICK ACTIONS GRID (4 BUTTONS IN 1 ROW) ---
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_homogeneous(True)

        btn_wifi = Gtk.Button(label="󰖩")
        btn_wifi.set_tooltip_text("Network / Wi-Fi Settings")
        btn_wifi.get_style_context().add_class("quick-btn")
        btn_wifi.connect("clicked", lambda x: self.launch_app("nm-connection-editor"))
        actions_box.pack_start(btn_wifi, True, True, 0)

        btn_bt = Gtk.Button(label="󰂯")
        btn_bt.set_tooltip_text("Bluetooth Devices")
        btn_bt.get_style_context().add_class("quick-btn")
        btn_bt.connect("clicked", lambda x: self.launch_app("blueman-manager"))
        actions_box.pack_start(btn_bt, True, True, 0)

        btn_ime = Gtk.Button(label="󰌌")
        btn_ime.set_tooltip_text("Toggle Vietnamese Input")
        btn_ime.get_style_context().add_class("quick-btn")
        btn_ime.connect("clicked", self.toggle_ime)
        actions_box.pack_start(btn_ime, True, True, 0)

        btn_power = Gtk.Button(label="")
        btn_power.set_tooltip_text("Power Menu / Logout")
        btn_power.get_style_context().add_class("quick-btn")
        btn_power.get_style_context().add_class("quick-btn-power")
        btn_power.connect("clicked", lambda x: self.launch_app(os.path.expanduser("~/.config/hypr/scripts/Wlogout.sh")))
        actions_box.pack_start(btn_power, True, True, 0)

        card.pack_start(actions_box, False, False, 2)

        # --- 6. MINI SYSTEM STATS (CPU & RAM) ---
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        stats_box.get_style_context().add_class("section-box")

        # CPU meter
        cpu_sub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cpu_lbl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_c_tag = Gtk.Label(label=" CPU")
        lbl_c_tag.get_style_context().add_class("stat-name")
        self.lbl_cpu_val = Gtk.Label(label="0%")
        self.lbl_cpu_val.get_style_context().add_class("stat-num")
        cpu_lbl_box.pack_start(lbl_c_tag, True, True, 0)
        cpu_lbl_box.pack_end(self.lbl_cpu_val, False, False, 0)
        self.cpu_bar = Gtk.ProgressBar()
        cpu_sub.pack_start(cpu_lbl_box, False, False, 0)
        cpu_sub.pack_start(self.cpu_bar, False, False, 0)
        stats_box.pack_start(cpu_sub, True, True, 0)

        # RAM meter
        ram_sub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ram_lbl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_r_tag = Gtk.Label(label="󰍛 RAM")
        lbl_r_tag.get_style_context().add_class("stat-name")
        self.lbl_ram_val = Gtk.Label(label="0%")
        self.lbl_ram_val.get_style_context().add_class("stat-num")
        ram_lbl_box.pack_start(lbl_r_tag, True, True, 0)
        ram_lbl_box.pack_end(self.lbl_ram_val, False, False, 0)
        self.ram_bar = Gtk.ProgressBar()
        ram_sub.pack_start(ram_lbl_box, False, False, 0)
        ram_sub.pack_start(self.ram_bar, False, False, 0)
        stats_box.pack_start(ram_sub, True, True, 0)

        card.pack_start(stats_box, False, False, 0)

        # --- 7. FOOTER BUTTONS (Notifications & DND) ---
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer_box.set_homogeneous(True)

        btn_dnd = Gtk.Button(label="󰂛 Toggle DND")
        btn_dnd.get_style_context().add_class("btn-footer")
        btn_dnd.connect("clicked", self.toggle_dnd)
        footer_box.pack_start(btn_dnd, True, True, 0)

        btn_notif = Gtk.Button(label="󰂚 Notifications")
        btn_notif.get_style_context().add_class("btn-footer")
        btn_notif.connect("clicked", self.open_swaync)
        footer_box.pack_start(btn_notif, True, True, 0)

        card.pack_start(footer_box, False, False, 2)

        self.add(card)

        # Initial values
        self.init_sliders()
        self.refresh_status_pill()
        self.refresh_system_stats()

    # --- ACTIONS & LOGIC ---
    def launch_app(self, cmd):
        subprocess.Popen(cmd, shell=True)
        self.close_and_quit()

    def toggle_ime(self, widget=None):
        script = os.path.expanduser("~/.config/hypr/scripts/toggle_vietnamese.sh")
        subprocess.run(["bash", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        GLib.timeout_add(150, self.refresh_status_pill)

    def toggle_dnd(self, widget=None):
        subprocess.run(["swaync-client", "-d", "-sw"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def open_swaync(self, widget=None):
        subprocess.Popen(["swaync-client", "-t", "-sw"])
        self.close_and_quit()

    def init_sliders(self):
        self.updating_sliders = True
        try:
            # Volume
            vol, muted = self.get_volume_info()
            self.vol_scale.set_value(vol)
            self.lbl_vol_val.set_text(f"{vol}%")
            self.update_vol_icon(vol, muted)

            # Brightness
            bri = self.get_brightness_info()
            self.bri_scale.set_value(bri)
            self.lbl_bri_val.set_text(f"{bri}%")
        finally:
            self.updating_sliders = False

    def get_volume_info(self):
        try:
            vol = int(subprocess.check_output(['pamixer', '--get-volume'], stderr=subprocess.DEVNULL).decode().strip())
            muted = subprocess.check_output(['pamixer', '--get-mute'], stderr=subprocess.DEVNULL).decode().strip() == 'true'
            return vol, muted
        except Exception:
            return 50, False

    def update_vol_icon(self, vol, muted):
        if muted:
            self.btn_vol_icon.set_label("󰖁")
        elif vol <= 30:
            self.btn_vol_icon.set_label("󰕿")
        elif vol <= 70:
            self.btn_vol_icon.set_label("󰖀")
        else:
            self.btn_vol_icon.set_label("󰕾")

    def toggle_audio_mute(self, widget=None):
        subprocess.run(['pamixer', '-t'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vol, muted = self.get_volume_info()
        self.update_vol_icon(vol, muted)

    def on_vol_changed(self, scale):
        if self.updating_sliders:
            return
        val = int(scale.get_value())
        self.lbl_vol_val.set_text(f"{val}%")
        self.update_vol_icon(val, False)
        # Apply volume asynchronously to prevent UI lag
        threading.Thread(target=lambda: subprocess.run(['pamixer', '--set-volume', str(val)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()

    def get_brightness_info(self):
        try:
            paths = glob.glob('/sys/class/backlight/*/brightness')
            if paths:
                p_bri = paths[0]
                p_max = p_bri.replace('brightness', 'max_brightness')
                with open(p_bri, 'r') as f:
                    b = int(f.read().strip())
                with open(p_max, 'r') as f:
                    m = int(f.read().strip())
                return int((b / m) * 100)
        except Exception:
            pass
        return 70

    def on_bri_changed(self, scale):
        if self.updating_sliders:
            return
        val = int(scale.get_value())
        self.lbl_bri_val.set_text(f"{val}%")
        threading.Thread(target=lambda: subprocess.run(['brightnessctl', 'set', f"{val}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()

    def refresh_status_pill(self):
        # 1. IME
        try:
            ime_path = os.path.expanduser("~/.config/hypr/scripts/get_ime.sh")
            ime = subprocess.check_output(['bash', ime_path], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            ime = "ENG"

        # 2. Battery
        bat_txt = "󰚥 AC"
        try:
            bats = glob.glob('/sys/class/power_supply/BAT*')
            if bats:
                with open(os.path.join(bats[0], 'capacity'), 'r') as f:
                    cap = int(f.read().strip())
                with open(os.path.join(bats[0], 'status'), 'r') as f:
                    stat = f.read().strip()
                if stat == "Charging":
                    icon = "󰂄"
                elif cap <= 20:
                    icon = "󰂃"
                else:
                    icon = "󰁹"
                bat_txt = f"{icon} {cap}%"
        except Exception:
            pass

        # 3. WiFi SSID
        wifi_txt = "󰖪 Offline"
        try:
            out = subprocess.check_output("nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2 | head -n1", shell=True).decode().strip()
            if out:
                wifi_txt = f"󰖩 {out}"
        except Exception:
            pass

        self.lbl_status.set_text(f"{ime}   •   {wifi_txt}   •   {bat_txt}")
        return True

    def refresh_system_stats(self):
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
                cpu_pct = 10.0
            self._prev_idle = idle
            self._prev_total = total

            self.lbl_cpu_val.set_text(f"{int(cpu_pct)}%")
            self.cpu_bar.set_fraction(min(1.0, max(0.0, cpu_pct / 100.0)))

            with open('/proc/meminfo', 'r') as f:
                mem = {}
                for line in f:
                    p = line.split(':')
                    if len(p) == 2:
                        mem[p[0].strip()] = int(p[1].strip().split()[0])
            total_ram = mem.get('MemTotal', 1)
            avail_ram = mem.get('MemAvailable', 0)
            ram_pct = ((total_ram - avail_ram) / total_ram) * 100.0

            self.lbl_ram_val.set_text(f"{int(ram_pct)}%")
            self.ram_bar.set_fraction(min(1.0, max(0.0, ram_pct / 100.0)))
        except Exception:
            pass
        return True

def main():
    # Single-instance toggle logic
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)  # SIGTERM
            os.remove(PID_FILE)
            return
        except Exception:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    app = SerenaControlCenter()

    def cleanup(*args):
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        Gtk.main_quit()

    app.connect("destroy", cleanup)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()

