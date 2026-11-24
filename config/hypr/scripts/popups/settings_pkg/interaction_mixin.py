#!/usr/bin/env python3
# settings_pkg/interaction_mixin.py — Pointer, scroll, and keyboard handlers for Settings.

import math

from gi.repository import Gdk

from services.audio import AudioService
from services.brightness import BrightnessService
from settings_pkg.constants import OPEN_W


class SettingsInteractionMixin:
    """Mouse, scroll, and keyboard interaction handlers for Settings clamshell."""

    def on_button_press(self, widget, event):
        x, y = event.x, event.y
        cx = OPEN_W / 2.0
        panel_w = cx - 33.0
        top_y, bot_y, extrusion_h = 30.0, 615.0, 4.2
        lx, rx = cx - panel_w, cx

        if event.button != 1:
            return False
        if self.anim_state in ("opening", "closing"):
            return True

        if self.anim_state == "closed":
            is_inside = (rx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h)
        else:
            is_inside = (lx - 10.0 <= x <= rx + panel_w + 10.0 and top_y - 10.0 <= y <= bot_y + extrusion_h + 10.0)

        if not is_inside:
            if self.anim_state == "closed":
                self.close_and_quit()
            else:
                self.start_close_animation(quit_after=True)
            return True

        return self.drag_manager.handle_press(event, is_inside=True)

    def on_button_release(self, widget, event):
        if event.button == 1:
            return self.drag_manager.handle_release(event, on_click=self.handle_click)
        return False

    def handle_click(self, x, y):
        cx = OPEN_W / 2.0
        panel_w = cx - 33.0
        panel_h, top_y, extrusion_h = 585.0, 30.0, 4.2
        bot_y, rx = top_y + panel_h, cx

        if self.anim_state == "closed":
            if rx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h:
                self.start_open_animation()
            else:
                self.close_and_quit()
            return

        if self.anim_state in ("opening", "closing"):
            return

        pad_outer, pad_inner, pad_top, pad_bot = 27.0, 27.0, 36.0, 62.0
        rsx, rsy = rx + pad_inner, top_y + pad_top
        rsw, rsh = panel_w - pad_outer - pad_inner, panel_h - pad_top - pad_bot
        hcx, hcy = rsx + rsw / 2.0, rsy + rsh + pad_bot * 0.50
        if math.hypot(x - hcx, y - hcy) <= 28.0:
            self.start_close_animation()

    def on_motion_notify(self, widget, event):
        x, y = event.x, event.y
        if self.drag_manager.handle_motion(event):
            return True

        win = self.get_window()
        if win and not self.is_dragging:
            cx = OPEN_W / 2.0
            panel_w = cx - 33.0
            panel_h, top_y, extrusion_h = 585.0, 30.0, 4.2
            bot_y, lx, rx = top_y + panel_h, cx - panel_w, cx

            if self.anim_state == "closed":
                cursor = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab") if (rx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h) else None
                win.set_cursor(cursor)
            elif self.anim_state == "open":
                pad_outer, pad_inner, pad_top, pad_bot = 27.0, 27.0, 36.0, 62.0
                rsw, rsh = panel_w - pad_outer - pad_inner, panel_h - pad_top - pad_bot
                hcx, hcy = rx + pad_inner + rsw / 2.0, top_y + pad_top + rsh + pad_bot * 0.50
                if math.hypot(x - hcx, y - hcy) <= 28.0:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer"))
                elif lx <= x <= rx + panel_w and top_y <= y <= bot_y + extrusion_h:
                    win.set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "grab"))
                else:
                    win.set_cursor(None)
        return True

    def on_scroll(self, widget, event):
        if self.anim_state == "open":
            if event.direction == Gdk.ScrollDirection.UP:
                self.volume = min(100, self.volume + 5)
                AudioService.set_volume(self.volume)
                self.queue_draw()
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.volume = max(0, self.volume - 5)
                AudioService.set_volume(self.volume)
                self.queue_draw()
        return True

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.anim_state == "open":
                self.start_close_animation()
            else:
                self.close_and_quit()
            return True
        return False

    def update_volume_from_mouse(self, mx, my, cx, cy):
        ang = math.atan2(my - cy, mx - cx)
        start_ang, end_ang = -0.85 * math.pi, -0.15 * math.pi
        if ang < 0:
            prog = max(0.0, min(1.0, (ang - start_ang) / (end_ang - start_ang)))
            self.volume = int(prog * 100)
            AudioService.set_volume(self.volume)
            self.queue_draw()

    def update_brightness_from_mouse(self, mx, my, cx, cy):
        ang = math.atan2(my - cy, mx - cx)
        start_ang, end_ang = 0.15 * math.pi, 0.85 * math.pi
        if ang > 0:
            prog = max(0.0, min(1.0, (ang - start_ang) / (end_ang - start_ang)))
            self.brightness = int(prog * 100)
            BrightnessService.set_brightness(self.brightness)
            self.queue_draw()
