"""Soft stage beams inspired by plymouth/spotlight/generate_theme.py."""

import math

import cairo


class StageSpotlight:
    def __init__(self, palette):
        self.cream = self.rgb(palette['text_primary'])
        self.pink = self.rgb(palette['text_secondary'])
        self.size = None
        self.surface = None

    @staticmethod
    def rgb(color):
        return tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))

    def beam(self, context, apex, target, top_width, bottom_width, strength):
        # Mesh alpha fades across the cone and at its lower end. This provides
        # soft edges without blurring a full-screen image on every music frame.
        mesh = cairo.MeshPattern()
        across, down = 20, 10
        for row in range(down):
            for column in range(across):
                corners = ((column, row), (column + 1, row),
                           (column + 1, row + 1), (column, row + 1))
                mesh.begin_patch()
                for corner, (horizontal, vertical) in enumerate(corners):
                    u = -1.25 + 2.5 * horizontal / across
                    t = vertical / down
                    center = apex[0] + (target[0] - apex[0]) * t
                    half_width = top_width + (bottom_width - top_width) * t
                    point = (center + u * half_width,
                             apex[1] + (target[1] - apex[1]) * t)
                    if corner == 0:
                        mesh.move_to(*point)
                    else:
                        mesh.line_to(*point)
                    core = math.exp(-u * u * 3.2)
                    edge_fade = max(0, min(1, 1 - (t - 0.85) / 0.15))
                    alpha = strength * core * (0.7 + 0.3 * t) * edge_fade
                    color = tuple(a + (b - a) * core for a, b in zip(self.pink, self.cream))
                    mesh.set_corner_color_rgba(corner, *color, alpha)
                mesh.end_patch()
        context.set_source(mesh)
        context.paint()

    def pool(self, context, x, y, radius_x, radius_y, strength):
        context.save()
        context.translate(x, y)
        context.scale(radius_x, radius_y)
        gradient = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
        for position, alpha in ((0, strength), (0.35, strength * 0.6),
                                (0.7, strength * 0.12), (1, 0)):
            gradient.add_color_stop_rgba(position, *self.cream, alpha)
        context.set_source(gradient)
        context.arc(0, 0, 1, 0, math.tau)
        context.fill()
        context.restore()

    def build(self, width, height):
        # Build the reference's 1920x1080 stage at modest resolution. The scaled
        # result is cached once, avoiding live mesh construction and resampling.
        scale = min(1.0, 640 / max(1, width))
        cache_width = max(1, round(width * scale))
        cache_height = max(1, round(height * scale))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, cache_width, cache_height)
        context = cairo.Context(surface)
        context.scale(cache_width / 1920, cache_height / 1080)
        floor = 1080 * 0.74
        for apex_x, target_x, offset in ((120, 400, 28), (380, 620, -6),
                                          (680, 820, -24), (1240, 1100, -24),
                                          (1540, 1300, -6), (1800, 1520, 28)):
            self.beam(context, (apex_x, -45), (target_x, floor + offset), 24, 125, 0.10)
            self.pool(context, target_x, floor + offset, 155, 45, 0.065)
        self.beam(context, (960, -45), (960, floor + 44), 40, 330, 0.24)
        self.pool(context, 960, floor + 44, 410, 110, 0.18)
        return surface

    def paint(self, context, width, height, opacity=1.0):
        if width <= 0 or height <= 0 or opacity <= 0:
            return
        if self.size != (width, height):
            source = self.build(width, height)
            self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            scaled = cairo.Context(self.surface)
            scaled.scale(width / source.get_width(), height / source.get_height())
            scaled.set_source_surface(source, 0, 0)
            scaled.get_source().set_filter(cairo.FILTER_BILINEAR)
            scaled.paint()
            self.size = (width, height)
        context.save()
        context.set_source_surface(self.surface, 0, 0)
        context.paint_with_alpha(max(0.0, min(1.0, opacity)))
        context.restore()
