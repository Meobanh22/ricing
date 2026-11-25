#!/usr/bin/env python3
# panels/calendar_widget.py — Interactive 3D calendar widget beneath weather card.

import calendar
import datetime

import cairo
from gi.repository import GLib, Gtk, PangoCairo

from panels.common import (
    VIVID_RED,
    WINE_RED,
    DARK_RUBY,
    PURE_WHITE,
    MUTED_PINK,
    HAS_LAYER_SHELL,
    GtkLayerShell,
    on_window_draw_clear,
)
from ui_core import draw_tactile_3d_text

MONTHS_EN = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]


class Tactile3DMonthWidget(Gtk.DrawingArea):
    """Renders 3D cel-shaded month title directly onto Cairo."""

    def __init__(self, month_str="NOVEMBER"):
        super().__init__()
        self._month = str(month_str).upper()
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_size_request(130, 38)
        self.connect("draw", self.on_draw)

    def set_month(self, month_str):
        self._month = str(month_str).upper()
        self.queue_draw()

    def on_draw(self, widget, cr):
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        layout = PangoCairo.create_layout(cr)
        n = len(self._month)
        if n <= 4:
            fsize = 21000
        elif n <= 6:
            fsize = 19000
        elif n <= 8:
            fsize = 17000
        else:
            fsize = 15000

        layout.set_markup(f"<span font_family='Inter, Sans' weight='900' size='{fsize}'>{self._month}</span>", -1)
        ink, _ = layout.get_pixel_extents()
        start_x = (w - ink.width) / 2.0 - ink.x
        start_y = (h - ink.height) / 2.0 - ink.y - 1.0

        draw_tactile_3d_text(
            cr,
            layout,
            start_x,
            start_y,
            core_color=WINE_RED,
            dark_color=DARK_RUBY,
            white_color=PURE_WHITE,
            extrusion_h=3.8,
            white_w=4.2,
            dark_extra=1.5,
        )
        return False


class DesktopCalendarWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Calendar Widget")
        self.set_name("desktop-calendar-window")
        self.set_decorated(False)
        self.set_resizable(False)

        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_namespace(self, "desktop-widgets")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 28)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 408)
            GtkLayerShell.set_exclusive_zone(self, 0)
        else:
            self.set_wmclass("desktop-widgets", "desktop-widgets")
            self.set_position(Gtk.WindowPosition.NONE)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.set_app_paintable(True)
        self.connect("draw", on_window_draw_clear)

        today = datetime.date.today()
        self._cached_today = today
        self._view_year = today.year
        self._view_month = today.month

        self.build_ui()
        GLib.timeout_add_seconds(30, self.on_check_date_tick)

    def build_ui(self):
        card_event = Gtk.EventBox()
        card_event.set_visible_window(False)

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card_box.get_style_context().add_class("desktop-widget-card")
        card_box.get_style_context().add_class("widget-calendar-card")
        card_box.set_size_request(269, -1)

        card_event.connect("enter-notify-event", lambda w, e: card_box.get_style_context().add_class("card-hover"))
        card_event.connect("leave-notify-event", lambda w, e: card_box.get_style_context().remove_class("card-hover"))

        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero_box.get_style_context().add_class("tactile-hero-box")
        hero_box.get_style_context().add_class("gradient-sunset")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_event = Gtk.EventBox()
        title_event.set_visible_window(False)
        title_event.connect("button-press-event", self.on_reset_today)
        lbl_title = Gtk.Label()
        lbl_title.get_style_context().add_class("calendar-hero-title")
        lbl_title.set_markup(f"<span font='9.5' weight='800' color='{WINE_RED}'>CALENDAR</span>")
        lbl_title.set_halign(Gtk.Align.START)
        lbl_title.set_valign(Gtk.Align.CENTER)
        title_event.add(lbl_title)
        top_row.pack_start(title_event, False, False, 0)

        self.lbl_year = Gtk.Label()
        self.lbl_year.get_style_context().add_class("calendar-hero-title")
        self.lbl_year.set_markup(f"<span font='10' weight='800' color='{WINE_RED}'>{self._view_year}</span>")
        self.lbl_year.set_halign(Gtk.Align.END)
        self.lbl_year.set_valign(Gtk.Align.CENTER)
        top_row.pack_end(self.lbl_year, False, False, 0)
        hero_box.pack_start(top_row, False, False, 0)

        month_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        btn_prev = Gtk.EventBox()
        btn_prev.set_visible_window(False)
        btn_prev.get_style_context().add_class("calendar-nav-btn")
        lbl_prev = Gtk.Label()
        lbl_prev.set_markup(f"<span font='13' weight='900' color='{WINE_RED}'>❮</span>")
        btn_prev.add(lbl_prev)
        btn_prev.connect("button-press-event", self.on_prev_month)

        month_event = Gtk.EventBox()
        month_event.set_visible_window(False)
        month_event.set_size_request(130, 38)
        month_event.connect("button-press-event", self.on_reset_today)

        self.tactile_month = Tactile3DMonthWidget(MONTHS_EN[self._view_month - 1])
        month_event.add(self.tactile_month)

        btn_next = Gtk.EventBox()
        btn_next.set_visible_window(False)
        btn_next.get_style_context().add_class("calendar-nav-btn")
        lbl_next = Gtk.Label()
        lbl_next.set_markup(f"<span font='13' weight='900' color='{WINE_RED}'>❯</span>")
        btn_next.add(lbl_next)
        btn_next.connect("button-press-event", self.on_next_month)

        month_row.pack_start(btn_prev, False, False, 0)
        month_row.pack_start(month_event, True, True, 0)
        month_row.pack_end(btn_next, False, False, 0)
        hero_box.pack_start(month_row, False, False, 1)
        card_box.pack_start(hero_box, False, False, 2)

        grid_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        grid_container.get_style_context().add_class("tactile-calendar-box")

        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_homogeneous(True)
        self.cal_grid.set_row_homogeneous(True)
        self.cal_grid.set_column_spacing(2)
        self.cal_grid.set_row_spacing(2)
        self.rebuild_calendar_grid()
        grid_container.pack_start(self.cal_grid, True, True, 0)

        card_box.pack_start(grid_container, False, False, 2)
        card_event.add(card_box)
        self.add(card_event)

    def update_month_title(self):
        self.tactile_month.set_month(MONTHS_EN[self._view_month - 1])
        self.lbl_year.set_markup(f"<span font='10' weight='800' color='{WINE_RED}'>{self._view_year}</span>")

    def rebuild_calendar_grid(self):
        for child in self.cal_grid.get_children():
            self.cal_grid.remove(child)

        for col_idx, d_name in enumerate(['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']):
            lbl = Gtk.Label()
            lbl.get_style_context().add_class("calendar-day-header")
            col = VIVID_RED if col_idx >= 5 else WINE_RED
            lbl.set_markup(f"<span font='8.5' weight='800' color='{col}'>{d_name}</span>")
            self.cal_grid.attach(lbl, col_idx, 0, 1, 1)

        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(self._view_year, self._view_month)
        today = datetime.date.today()

        for row_idx, week in enumerate(weeks):
            for col_idx, d in enumerate(week):
                cell_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                cell_lbl = Gtk.Label()

                if d == today:
                    cell_box.get_style_context().add_class("calendar-cell-today")
                    cell_lbl.set_markup(f"<span font='9' weight='800' color='{PURE_WHITE}'>{d.day}</span>")
                elif d.month == self._view_month:
                    cell_box.get_style_context().add_class("calendar-cell-current")
                    col = VIVID_RED if col_idx >= 5 else DARK_RUBY
                    cell_lbl.set_markup(f"<span font='9' weight='700' color='{col}'>{d.day}</span>")
                else:
                    cell_box.get_style_context().add_class("calendar-cell-other")
                    cell_lbl.set_markup(f"<span font='9' weight='500' color='{MUTED_PINK}'>{d.day}</span>")

                cell_box.set_size_request(28, 20)
                cell_lbl.set_halign(Gtk.Align.CENTER)
                cell_lbl.set_valign(Gtk.Align.CENTER)
                cell_box.pack_start(cell_lbl, True, True, 0)
                self.cal_grid.attach(cell_box, col_idx, row_idx + 1, 1, 1)

        self.cal_grid.show_all()

    def on_prev_month(self, widget, event):
        if event.button == 1:
            if self._view_month == 1:
                self._view_month = 12
                self._view_year -= 1
            else:
                self._view_month -= 1
            self.update_month_title()
            self.rebuild_calendar_grid()
            return True
        return False

    def on_next_month(self, widget, event):
        if event.button == 1:
            if self._view_month == 12:
                self._view_month = 1
                self._view_year += 1
            else:
                self._view_month += 1
            self.update_month_title()
            self.rebuild_calendar_grid()
            return True
        return False

    def on_reset_today(self, widget, event):
        if event.button == 1:
            today = datetime.date.today()
            self._view_year = today.year
            self._view_month = today.month
            self.update_month_title()
            self.rebuild_calendar_grid()
            return True
        return False

    def on_check_date_tick(self):
        today = datetime.date.today()
        if today != self._cached_today:
            self._cached_today = today
            self._view_year = today.year
            self._view_month = today.month
            self.update_month_title()
            self.rebuild_calendar_grid()
        return True
