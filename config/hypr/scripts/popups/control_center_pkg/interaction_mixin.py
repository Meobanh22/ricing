#!/usr/bin/env python3
# control_center_pkg/interaction_mixin.py — Mouse, touch, keyboard, scroll, and slider interaction handlers.

import json
import math
import os
import shutil
import subprocess
import time

from gi.repository import Gdk

from control_center_pkg.constants import CACHE_FILE, HAS_LAYER_SHELL, SYSTEM_DIR, GtkLayerShell
from services.audio import AudioService
from services.bluetooth import BluetoothService
from services.brightness import BrightnessService
from services.power import PowerService


class ControlCenterInteractionMixin:
    """Pointer, scroll, keyboard, and Pokéball dual-slider interactions."""

    def on_scroll(self, widget, event):
        if self.current_page == "wifi" and not self.wifi_password_prompt_ssid:
            max_page = max(0, (len(self.wifi_networks) - 1) // 5)
            attr = "wifi_page_idx"
        elif self.current_page == "notifications":
            max_page = max(0, (len(self.notifications) - 1) // 5)
            attr = "notif_page_idx"
        else:
            return False

        cur_idx = getattr(self, attr)
        if event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.SMOOTH):
            if event.direction == Gdk.ScrollDirection.SMOOTH and hasattr(event, 'delta_y') and event.delta_y > 0:
                if cur_idx < max_page:
                    setattr(self, attr, cur_idx + 1)
                    self._bake_content()
                self.queue_draw()
            elif cur_idx > 0:
                setattr(self, attr, cur_idx - 1)
                self._bake_content()
                self.queue_draw()
            return True
        if event.direction == Gdk.ScrollDirection.DOWN:
            if cur_idx < max_page:
                setattr(self, attr, cur_idx + 1)
                self._bake_content()
                self.queue_draw()
            return True
        return False

    def on_key_press(self, widget, event):
        if self.current_page == "wifi" and self.wifi_password_prompt_ssid:
            if event.keyval == Gdk.KEY_Escape:
                self.wifi_password_prompt_ssid = None
                self.wifi_password_input = ""
                self.wifi_status_msg = ""
                if HAS_LAYER_SHELL:
                    try:
                        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
                    except Exception:
                        pass
                self.queue_draw()
                return True
            if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                self.submit_wifi_password()
                return True
            if event.keyval == Gdk.KEY_BackSpace:
                self.wifi_password_input = self.wifi_password_input[:-1]
                self.queue_draw()
                return True
            char = Gdk.keyval_to_unicode(event.keyval)
            if char >= 32:
                self.wifi_password_input += chr(char)
                self._bake_content()
                self.queue_draw()
                return True

        if event.keyval == Gdk.KEY_Escape:
            if self.current_page == "wifi":
                self.current_page = "controls"
                self.queue_draw()
                return True
            if self.anim_state == "open":
                self.start_close_animation(quit_after=True)
            else:
                self.close_and_quit()
            return True
        if event.keyval == Gdk.KEY_Tab:
            if self.anim_state == "open":
                self.toggle_page()
            return True
        return False

    def toggle_page(self):
        if self.current_page == "wifi":
            self.current_page = "controls"
        else:
            self.current_page = "notifications" if self.current_page == "controls" else "controls"
            if self.current_page == "notifications":
                self.notifications = self.load_notifications()
                self.notif_page_idx = 0
        self.queue_draw()

    def on_button_press(self, widget, event):
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        x, y = event.x / sx, event.y / sy

        if event.button != 1 or self.anim_state in ("opening", "closing"):
            return event.button == 1

        if self.anim_state == "closed":
            if 180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right:
                return self.drag_manager.handle_press(event, is_inside=True)
            self.close_and_quit()
            return True

        if y < 10.0 or y > self.base_h - 10.0:
            self.start_close_animation(quit_after=True)
            return True

        if self.current_page == "controls":
            dx, dy = x - self.cx, y - self.cy_pokeball
            if 46.0 <= math.sqrt(dx**2 + dy**2) <= 82.0:
                self.dragging_slider = "volume" if dy < 0 else "brightness"
                self.update_slider_from_coords(x, y, self.dragging_slider)
                return True

        return self.drag_manager.handle_press(event, is_inside=True)

    def on_button_release(self, widget, event):
        if event.button == 1:
            if self.dragging_slider:
                slider = self.dragging_slider
                self.dragging_slider = None
                self.last_slider_drag_time = time.time()
                if slider == "volume":
                    AudioService.set_volume(int(self.vol_val * 100.0))
                elif slider == "brightness":
                    BrightnessService.set_brightness(int(self.bri_val * 100.0))
                return True
            return self.drag_manager.handle_release(event, on_click=self.handle_click)
        return False

    def handle_click(self, px, py):
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        x, y = px / sx, py / sy

        if self.anim_state == "closed":
            if 180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right:
                self.start_open_animation()
            else:
                self.close_and_quit()
            return

        if self.anim_state in ("opening", "closing"):
            return

        if y < 10.0 or y > self.base_h - 10.0:
            self.start_close_animation(quit_after=True)
            return

        dist_nav = math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2)
        if dist_nav <= 28.0:
            self.toggle_page()
            return

        if math.sqrt((x - self.cx)**2 + (y - (190.0 - self.top_mark_offset))**2) <= 24.0:
            self.toggle_page()
            return

        y_casing_top_limit = 190.0 - (self.cut_y + self.chassis_thick + self.dark_thick)
        y_casing_bot_limit = 590.0 + (self.cut_y + self.chassis_thick + self.dark_thick)
        if y < y_casing_top_limit and abs(x - self.cx) > 40.0:
            self.start_close_animation()
            return
        if y > y_casing_bot_limit and dist_nav > 30.0:
            self.start_close_animation()
            return

        if self.current_page == "controls":
            self._handle_controls_click(x, y)
        elif self.current_page == "notifications":
            self._handle_notifications_click(x, y)
        elif self.current_page == "wifi":
            self._handle_wifi_click(x, y)

    def _handle_controls_click(self, x, y):
        grid_x = self.x_left + 36.0
        grid_y = 224.0
        col_w = (self.W_shell - 72.0 - 20.0) / 2.0
        row_h = 44.0
        gap_y = 24.0
        c1_x = grid_x + col_w + 20.0
        r1_y = grid_y + row_h + gap_y

        if grid_x <= x <= grid_x + col_w and grid_y <= y <= grid_y + row_h:
            toggle_sh = os.path.join(SYSTEM_DIR, "toggle_vietnamese.sh")
            if not os.path.exists(toggle_sh):
                toggle_sh = os.path.expanduser("~/.config/hypr/scripts/system/toggle_vietnamese.sh")
            if os.path.exists(toggle_sh):
                subprocess.Popen([toggle_sh])
            self.ime_text = "Vietnamese" if self.ime_text == "English" else "English"
            self._bake_content()
            self.queue_draw()
        elif c1_x - 10.0 <= x <= c1_x + col_w + 15.0 and grid_y - 8.0 <= y <= grid_y + row_h + 8.0:
            self.current_page = "wifi"
            self.wifi_password_prompt_ssid = None
            self.wifi_password_input = ""
            self.wifi_status_msg = ""
            self.wifi_page_idx = 0
            self.scan_wifi_networks()
            self._bake_content()
            self.queue_draw()
        elif grid_x <= x <= grid_x + col_w and r1_y <= y <= r1_y + row_h:
            self.bt_enabled = BluetoothService.toggle_power()
            if not self.bt_enabled:
                self.bt_device = ""
            self._bake_content()
            self.queue_draw()
        elif c1_x <= x <= c1_x + col_w and r1_y <= y <= r1_y + row_h:
            order = ["powersave", "balanced", "performance"]
            raw = (self.power_mode or "balanced").lower()
            curr = "powersave" if raw in ("powersave", "power-saver", "power saver") else ("performance" if raw == "performance" else "balanced")
            next_mode = order[(order.index(curr) + 1) % len(order)]
            PowerService.set_power_mode(next_mode)
            self.power_mode = next_mode
            self._bake_content()
            self.queue_draw()
        elif math.sqrt((x - self.cx)**2 + (y - self.cy_pokeball)**2) <= 22.0:
            wlogout_sh = os.path.join(SYSTEM_DIR, "Wlogout.sh")
            if not os.path.exists(wlogout_sh):
                wlogout_sh = os.path.expanduser("~/.config/hypr/scripts/system/Wlogout.sh")
            if os.path.exists(wlogout_sh):
                subprocess.Popen([wlogout_sh])
            elif shutil.which("wlogout"):
                subprocess.Popen(["wlogout"])
            self.close_and_quit()

    def _handle_notifications_click(self, x, y):
        content_x = self.x_left + 36.0
        content_w = self.W_shell - 72.0

        if len(self.notifications) > 0 and 468.0 <= y <= 496.0 and abs(x - self.cx) <= 120.0:
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump([], f)
                except Exception:
                    pass
            self.notifications = []
            self.notif_page_idx = 0
            self.queue_draw()
            return

        if len(self.notifications) > 5 and 498.0 <= y <= 524.0:
            total_pages = max(1, (len(self.notifications) + 4) // 5)
            if content_x <= x <= content_x + 65.0:
                if self.notif_page_idx > 0:
                    self.notif_page_idx -= 1
                    self._bake_content()
                self.queue_draw()
                return
            if content_x + content_w - 65.0 <= x <= content_x + content_w:
                if self.notif_page_idx < total_pages - 1:
                    self.notif_page_idx += 1
                    self._bake_content()
                self.queue_draw()
                return

        start_idx = self.notif_page_idx * 5
        page_notifs = self.notifications[start_idx : start_idx + 5]
        for idx in range(len(page_notifs)):
            item_y = 214.0 + idx * 49.0
            if content_x <= x <= content_x + content_w and item_y <= y <= item_y + 46.0:
                real_idx = start_idx + idx
                if real_idx < len(self.notifications):
                    del self.notifications[real_idx]
                    if os.path.exists(CACHE_FILE):
                        try:
                            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                                json.dump(self.notifications, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                    max_page = max(0, (len(self.notifications) - 1) // 5)
                    self.notif_page_idx = min(self.notif_page_idx, max_page)
                    self._bake_content()
                self.queue_draw()
                return

    def _handle_wifi_click(self, x, y):
        content_x = self.x_left + 36.0
        content_w = self.W_shell - 72.0

        if content_x + content_w - 110.0 <= x <= content_x + content_w - 55.0 and 210.0 <= y <= 236.0:
            self.toggle_wifi_radio()
            return
        if content_x + content_w - 52.0 <= x <= content_x + content_w + 5.0 and 210.0 <= y <= 236.0:
            self.scan_wifi_networks(fast=False)
            return
        if self.wifi_ssid and content_x + content_w - 110.0 <= x <= content_x + content_w + 5.0 and 236.0 <= y <= 258.0:
            self.disconnect_wifi()
            return

        if self.wifi_password_prompt_ssid:
            if content_x <= x <= content_x + 115.0 and 368.0 <= y <= 408.0:
                self.submit_wifi_password()
                return
            if content_x + 125.0 <= x <= content_x + 210.0 and 368.0 <= y <= 408.0:
                self.wifi_password_prompt_ssid = None
                self.wifi_password_input = ""
                self.wifi_status_msg = ""
                if HAS_LAYER_SHELL:
                    try:
                        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
                    except Exception:
                        pass
                self._bake_content()
                self.queue_draw()
                return
            return

        start_idx = self.wifi_page_idx * 5
        page_nets = self.wifi_networks[start_idx : start_idx + 5]
        curr_y = 262.0
        for net in page_nets:
            if content_x - 6.0 <= x <= content_x + content_w + 6.0 and curr_y - 4.0 <= y <= curr_y + 44.0:
                if net.get("in_use"):
                    self.wifi_status_msg = f"Connected to {net.get('ssid')}"
                    self._bake_content()
                    self.queue_draw()
                elif net.get("saved") or not (net.get("security") and net.get("security") != "--"):
                    self.connect_to_network(net["ssid"])
                else:
                    self.wifi_password_prompt_ssid = net["ssid"]
                    self.wifi_password_input = ""
                    self.wifi_status_msg = ""
                    if HAS_LAYER_SHELL:
                        try:
                            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
                        except Exception:
                            pass
                    self.grab_focus()
                    self._bake_content()
                    self.queue_draw()
                return
            curr_y += 48.0

        if len(self.wifi_networks) > 5:
            py_y = 514.0
            total_pages = max(1, (len(self.wifi_networks) + 4) // 5)
            if content_x <= x <= content_x + 70.0 and py_y - 6.0 <= y <= py_y + 24.0:
                if self.wifi_page_idx > 0:
                    self.wifi_page_idx -= 1
                    self._bake_content()
                self.queue_draw()
            elif content_x + content_w - 70.0 <= x <= content_x + content_w and py_y - 6.0 <= y <= py_y + 24.0:
                if self.wifi_page_idx < total_pages - 1:
                    self.wifi_page_idx += 1
                    self._bake_content()
                self.queue_draw()

    def on_leave_notify(self, widget, event):
        if self.hovered_item is not None:
            self.hovered_item = None
            self.queue_draw()
        win = self.get_window()
        if win and not self.is_dragging:
            win.set_cursor(None)
        return False

    def on_motion_notify(self, widget, event):
        sx = self.W_canvas / self.base_w
        sy = self.H_canvas / self.base_h
        x, y = event.x / sx, event.y / sy

        if self.anim_state == "open" and self.dragging_slider:
            self.update_slider_from_coords(x, y, self.dragging_slider)
            return True

        if self.drag_manager.handle_motion(event):
            return True

        win = self.get_window()
        if self.anim_state == "closed":
            if win and not self.is_dragging:
                cursor = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab") if (180.0 <= y <= 600.0 and self.x_left <= x <= self.x_right) else None
                win.set_cursor(cursor)
            return False

        if self.anim_state == "open":
            new_hover = self._resolve_hover_target(x, y)
            if new_hover != self.hovered_item:
                self.hovered_item = new_hover
                self.queue_draw()

            if win and not self.is_dragging:
                if new_hover:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
                elif 46.0 <= math.sqrt((x - self.cx)**2 + (y - self.cy_pokeball)**2) <= 82.0 and self.current_page == "controls":
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
                elif 10.0 <= y <= self.base_h - 10.0:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
                else:
                    win.set_cursor(None)

        return False

    def _resolve_hover_target(self, x, y):
        if self.current_page == "controls":
            grid_x = self.x_left + 36.0
            grid_y = 224.0
            col_w = (self.W_shell - 72.0 - 20.0) / 2.0
            row_h = 44.0
            c1_x = grid_x + col_w + 20.0
            r1_y = grid_y + row_h + 24.0

            if grid_x <= x <= grid_x + col_w and grid_y <= y <= grid_y + row_h:
                return "ime"
            if c1_x - 10.0 <= x <= c1_x + col_w + 15.0 and grid_y - 8.0 <= y <= grid_y + row_h + 8.0:
                return "wifi"
            if grid_x <= x <= grid_x + col_w and r1_y <= y <= r1_y + row_h:
                return "bt"
            if c1_x <= x <= c1_x + col_w and r1_y <= y <= r1_y + row_h:
                return "power"
            if math.sqrt((x - self.cx)**2 + (y - self.cy_pokeball)**2) <= 22.0:
                return "pokeball_pwr"
            if math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2) <= 24.0:
                return "nav"
            return None

        if self.current_page == "wifi":
            content_x = self.x_left + 36.0
            content_w = self.W_shell - 72.0
            if content_x + content_w - 110.0 <= x <= content_x + content_w - 55.0 and 210.0 <= y <= 236.0:
                return "wifi_toggle"
            if content_x + content_w - 52.0 <= x <= content_x + content_w + 5.0 and 210.0 <= y <= 236.0:
                return "wifi_rescan"
            if self.wifi_ssid and content_x + content_w - 110.0 <= x <= content_x + content_w + 5.0 and 236.0 <= y <= 258.0:
                return "wifi_disconnect"
            if self.wifi_password_prompt_ssid:
                if content_x <= x <= content_x + 115.0 and 368.0 <= y <= 408.0:
                    return "wifi_pass_connect"
                if content_x + 125.0 <= x <= content_x + 210.0 and 368.0 <= y <= 408.0:
                    return "wifi_pass_cancel"
                return None

            start_idx = self.wifi_page_idx * 5
            page_nets = self.wifi_networks[start_idx : start_idx + 5]
            curr_y = 262.0
            for idx in range(len(page_nets)):
                if content_x - 6.0 <= x <= content_x + content_w + 6.0 and curr_y - 4.0 <= y <= curr_y + 44.0:
                    return f"wifi_item_{idx}"
                curr_y += 48.0
            if len(self.wifi_networks) > 5:
                py_y = 514.0
                if content_x <= x <= content_x + 70.0 and py_y - 6.0 <= y <= py_y + 24.0:
                    return "wifi_prev"
                if content_x + content_w - 70.0 <= x <= content_x + content_w and py_y - 6.0 <= y <= py_y + 24.0:
                    return "wifi_next"
            if math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2) <= 28.0:
                return "nav"
            return None

        if self.current_page == "notifications":
            grid_x = self.x_left + 36.0
            row_w = self.W_shell - 72.0
            start_idx = self.notif_page_idx * 5
            page_notifs = self.notifications[start_idx : start_idx + 5]
            for idx in range(len(page_notifs)):
                item_y = 214.0 + idx * 49.0
                if grid_x - 6.0 <= x <= grid_x + row_w + 6.0 and item_y - 2.0 <= y <= item_y + 46.0:
                    return f"notif_{idx}"
            if self.notifications:
                if 468.0 <= y <= 496.0 and abs(x - self.cx) <= 120.0:
                    return "clear_all"
                if len(self.notifications) > 5 and 498.0 <= y <= 524.0:
                    if grid_x <= x <= grid_x + 65.0:
                        return "notif_prev"
                    if grid_x + row_w - 65.0 <= x <= grid_x + row_w:
                        return "notif_next"
            if math.sqrt((x - self.cx)**2 + (y - self.socket_well_y)**2) <= 24.0:
                return "nav"
        return None

    def update_slider_from_coords(self, x, y, slider_type):
        dx = x - self.cx
        dy = y - self.cy_pokeball
        now = time.time()
        self.last_slider_drag_time = now
        gap_deg = 16.0

        if slider_type == "volume":
            start_deg, end_deg = -180.0 + gap_deg, -gap_deg
            span_deg = end_deg - start_deg
            if dy > 0:
                val = 1.0 if dx > 0 else 0.0
            else:
                a_deg = math.degrees(math.atan2(dy, dx))
                val = 0.0 if a_deg <= start_deg else (1.0 if a_deg >= end_deg else (a_deg - start_deg) / span_deg)
            self.vol_val = max(0.0, min(1.0, val))
            self.queue_draw()
            if (now - self.last_vol_set_time) >= 0.04:
                self.last_vol_set_time = now
                AudioService.set_volume(int(self.vol_val * 100.0))

        elif slider_type == "brightness":
            start_deg, end_deg = 180.0 - gap_deg, gap_deg
            span_deg = start_deg - end_deg
            if dy < 0:
                val = 1.0 if dx > 0 else 0.0
            else:
                a_deg = math.degrees(math.atan2(dy, dx))
                val = 0.0 if a_deg >= start_deg else (1.0 if a_deg <= end_deg else (start_deg - a_deg) / span_deg)
            self.bri_val = max(0.0, min(1.0, val))
            self.queue_draw()
            if (now - self.last_bri_set_time) >= 0.04:
                self.last_bri_set_time = now
                BrightnessService.set_brightness(int(self.bri_val * 100.0))
