"""Desktop widget for Goal UP — floating progress overview window."""

import math
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Gdk, GLib, GObject, Adw
import cairo
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_color(color_str):
    """Return (r, g, b) floats in [0, 1] from any GTK color string."""
    if not color_str:
        return (0.5, 0.5, 0.5)
    color_str = color_str.strip()
    c = Gdk.RGBA()
    if c.parse(color_str):
        return (c.red, c.green, c.blue)
    # try rgb(...) / rgba(...) raw parse
    if color_str.startswith("rgb"):
        try:
            inside = color_str[color_str.find("(") + 1: color_str.rfind(")")]
            parts = [p.strip() for p in inside.split(",")]
            if len(parts) >= 3:
                r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                norm = lambda v: max(0.0, min(1.0, v / 255.0)) if v > 1.0 else max(0.0, min(1.0, v))
                return (norm(r), norm(g), norm(b))
        except Exception:
            pass
    return (0.5, 0.5, 0.5)


# ---------------------------------------------------------------------------
# Drawing area — two donut rings
# ---------------------------------------------------------------------------

class _RingsArea(Gtk.DrawingArea):
    """Draws two donut rings: Goals (left) and Tasks (right)."""

    def __init__(self):
        super().__init__()
        self.set_content_width(280)
        self.set_content_height(160)
        self.set_draw_func(self._draw)

        self._completed_goals = 0
        self._total_goals = 0
        self._completed_tasks = 0
        self._total_tasks = 0
        self._goals = []

        self._style_ctx = self.get_style_context()

    def update(self, completed_goals, total_goals, completed_tasks, total_tasks, goals):
        self._completed_goals = completed_goals
        self._total_goals = total_goals
        self._completed_tasks = completed_tasks
        self._total_tasks = total_tasks
        self._goals = goals
        self.queue_draw()

    # ------------------------------------------------------------------ draw

    def _draw(self, area, cr, width, height):
        lx = width * 0.28
        rx = width * 0.72
        cy = height * 0.50
        r  = min(width * 0.22, height * 0.44)

        self._draw_ring(cr, lx, cy, r,
                        self._completed_goals, self._total_goals,
                        "Goals",
                        fill_color=(0.22, 0.69, 0.95))

        self._draw_ring(cr, rx, cy, r,
                        self._completed_tasks, self._total_tasks,
                        "Tasks",
                        fill_color=(0.15, 0.78, 0.47))

    def _draw_ring(self, cr, cx, cy, r, done, total, label, fill_color):
        pct = done / total if total > 0 else 0.0
        inner = r * 0.58
        start = -math.pi / 2

        fg = self._style_ctx.get_color()
        is_dark = (0.2126 * fg.red + 0.7152 * fg.green + 0.0722 * fg.blue) > 0.5

        # Background track
        cr.new_path()
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.arc_negative(cx, cy, inner, 2 * math.pi, 0)
        cr.close_path()
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.18)
        cr.fill()

        # Filled arc (progress)
        if pct > 0:
            end = start + pct * 2 * math.pi
            cr.new_path()
            cr.arc(cx, cy, r, start, end)
            cr.arc_negative(cx, cy, inner, end, start)
            cr.close_path()
            cr.set_source_rgb(*fill_color)
            cr.fill()

        # Centre hole background
        cr.new_path()
        cr.arc(cx, cy, inner - 4, 0, 2 * math.pi)
        cr.set_source_rgba(0, 0, 0, 0.72) if not is_dark else cr.set_source_rgba(1, 1, 1, 0.92)
        cr.fill()

        # Percentage text
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(15)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
        pct_str = f"{int(pct * 100)}%"
        (tx, ty, tw, th, *_) = cr.text_extents(pct_str)
        cr.move_to(cx - tw / 2 - tx, cy + th / 2 - ty)
        cr.show_text(pct_str)

        # Label below ring
        cr.set_font_size(10)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        lbl = f"{label}: {done}/{total}"
        (lx2, ly2, lw, lh, *_) = cr.text_extents(lbl)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.75)
        cr.move_to(cx - lw / 2 - lx2, cy + r + 16)
        cr.show_text(lbl)


# ---------------------------------------------------------------------------
# Desktop widget window
# ---------------------------------------------------------------------------

class DesktopWidget(Gtk.Window):
    """Floating always-on-top widget showing goal/task progress and timer."""

    def __init__(self, app, settings: dict, save_settings_fn):
        super().__init__(application=app)

        self._settings = settings
        self._save_settings = save_settings_fn
        self._goals = []
        self._next_deadline = None
        self._next_item_title = ""

        # ---- Window chrome ----
        self.set_decorated(False)
        self.set_resizable(False)

        # Attempt keep-above via X11 surface (GTK4 removed Gtk.Window.set_keep_above).
        # Wrapped in try/except so it degrades gracefully on Wayland.
        self.connect("realize", self._try_set_keep_above)

        self.set_default_size(300, 240)

        # ---- Root container ----
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.add_css_class("card")

        # Custom CSS for the widget
        provider = Gtk.CssProvider()
        provider.load_from_data(b"""
            .dw-frame {
                background-color: alpha(@window_bg_color, 0.92);
                border-radius: 14px;
                border: 1px solid alpha(@borders, 0.5);
            }
            .dw-title-bar {
                padding: 6px 10px 4px 12px;
                border-radius: 14px 14px 0 0;
                background: alpha(@headerbar_bg_color, 0.95);
                border-bottom: 1px solid alpha(@borders, 0.4);
            }
            .dw-body {
                padding: 8px 12px 12px 12px;
            }
            .dw-timer-lbl {
                font-family: monospace;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            .dw-deadline-lbl {
                font-size: 10px;
                opacity: 0.7;
            }
            .dw-section-title {
                font-size: 10px;
                font-weight: bold;
                opacity: 0.55;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 2px;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        outer.add_css_class("dw-frame")
        self.set_child(outer)

        # ---- Title bar ----
        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        title_bar.add_css_class("dw-title-bar")
        outer.append(title_bar)

        icon_lbl = Gtk.Label(label="🎯  Goal UP")
        icon_lbl.add_css_class("caption")
        icon_lbl.set_hexpand(True)
        icon_lbl.set_halign(Gtk.Align.START)
        title_bar.append(icon_lbl)

        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.add_css_class("flat")
        close_btn.add_css_class("circular")
        close_btn.set_valign(Gtk.Align.CENTER)
        close_btn.connect("clicked", lambda _: self.hide())
        title_bar.append(close_btn)

        # ---- Body ----
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.add_css_class("dw-body")
        outer.append(body)

        # -- Rings area --
        progress_title = Gtk.Label(label="PROGRESS")
        progress_title.add_css_class("dw-section-title")
        progress_title.set_halign(Gtk.Align.START)
        body.append(progress_title)

        self._rings = _RingsArea()
        body.append(self._rings)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        body.append(sep)

        # -- Timer section --
        timer_title = Gtk.Label(label="NEXT DEADLINE")
        timer_title.add_css_class("dw-section-title")
        timer_title.set_halign(Gtk.Align.START)
        body.append(timer_title)

        self._timer_lbl = Gtk.Label(label="00 : 00 : 00 : 00")
        self._timer_lbl.add_css_class("dw-timer-lbl")
        self._timer_lbl.set_halign(Gtk.Align.CENTER)
        body.append(self._timer_lbl)

        self._deadline_lbl = Gtk.Label(label="No upcoming deadlines")
        self._deadline_lbl.add_css_class("dw-deadline-lbl")
        self._deadline_lbl.set_halign(Gtk.Align.CENTER)
        self._deadline_lbl.set_ellipsize_mode = None
        self._deadline_lbl.set_max_width_chars(36)
        self._deadline_lbl.set_wrap(True)
        body.append(self._deadline_lbl)

        # ---- Drag support ----
        # Strategy: record the window's screen-origin at drag-begin, then
        # move by the accumulated (offset_x, offset_y) on each update.
        # _drag_origin_{x,y} = window top-left at drag-start (screen coords).
        self._drag_origin_x = 0
        self._drag_origin_y = 0

        drag_ctrl = Gtk.GestureDrag()
        drag_ctrl.set_exclusive(True)
        drag_ctrl.connect("drag-begin", self._on_drag_begin)
        drag_ctrl.connect("drag-update", self._on_drag_update)
        drag_ctrl.connect("drag-end", self._on_drag_end)
        title_bar.add_controller(drag_ctrl)

        # ---- Restore saved position ----
        wx = self._settings.get("widget_x", 40)
        wy = self._settings.get("widget_y", 40)
        # GTK4 doesn't have move() — we set initial position via set_default_size
        # and rely on the window manager. We try via surface after realize.
        self.connect("realize", lambda _: self._restore_position(wx, wy))

        # ---- Tick timer ----
        GLib.timeout_add_seconds(1, self._on_tick)

    # ------------------------------------------------------------------ drag

    # ------------------------------------------------------------------ keep-above

    def _try_set_keep_above(self, window):
        """Try to set keep-above via X11 surface after the window is realized."""
        try:
            surface = self.get_surface()
            if surface is None:
                return
            # GdkX11Surface has set_type_hint and set_skip_taskbar_hint etc.
            # We attempt to import the X11-specific class; on Wayland this will
            # simply not be available and we silently skip.
            try:
                from gi.repository import GdkX11  # type: ignore
                if isinstance(surface, GdkX11.X11Surface):
                    surface.set_type_hint(Gdk.SurfaceTypeHint.UTILITY)
            except (ImportError, AttributeError):
                pass
        except Exception:
            pass

    # ------------------------------------------------------------------ drag

    def _on_drag_begin(self, gesture, start_x, start_y):
        """Record the window's screen-origin at drag start using X11 APIs."""
        self._drag_origin_x = self._settings.get("widget_x", 40)
        self._drag_origin_y = self._settings.get("widget_y", 40)
        surface = self.get_surface()
        if surface is None:
            return
        try:
            from gi.repository import GdkX11  # type: ignore
            if isinstance(surface, GdkX11.X11Surface):
                # get_x_origin / get_y_origin return the window's top-left
                # in root (screen) coordinates on X11 — exactly what we need.
                self._drag_origin_x = surface.get_x_origin()
                self._drag_origin_y = surface.get_y_origin()
        except (ImportError, AttributeError):
            pass

    def _on_drag_update(self, gesture, offset_x, offset_y):
        """Move the window by the accumulated drag offset."""
        surface = self.get_surface()
        if surface is None:
            return
        new_x = int(self._drag_origin_x + offset_x)
        new_y = int(self._drag_origin_y + offset_y)
        try:
            surface.move(new_x, new_y)
        except Exception:
            return
        self._settings["widget_x"] = new_x
        self._settings["widget_y"] = new_y

    def _on_drag_end(self, gesture, offset_x, offset_y):
        """Persist the final position when the drag finishes."""
        surface = self.get_surface()
        if surface is not None:
            try:
                from gi.repository import GdkX11  # type: ignore
                if isinstance(surface, GdkX11.X11Surface):
                    self._settings["widget_x"] = surface.get_x_origin()
                    self._settings["widget_y"] = surface.get_y_origin()
            except (ImportError, AttributeError):
                pass
        self._save_settings(self._settings)

    def _restore_position(self, wx, wy):
        surface = self.get_surface()
        if surface:
            try:
                surface.move(int(wx), int(wy))
            except Exception:
                pass

    # ------------------------------------------------------------------ data

    def update_data(self, goals: list) -> None:
        """Feed fresh goals data to the widget."""
        self._goals = goals
        total_goals = len(goals)
        completed_goals = sum(1 for g in goals if g.get("completed"))
        total_tasks = sum(len(g.get("tasks", [])) for g in goals)
        completed_tasks = sum(
            sum(1 for t in g.get("tasks", []) if t.get("completed"))
            for g in goals
        )
        self._rings.update(completed_goals, total_goals, completed_tasks, total_tasks, goals)
        self._find_next_deadline()

    def _find_next_deadline(self):
        now = datetime.now()
        upcoming = []

        for g in self._goals:
            if not g.get("completed") and g.get("end_date"):
                try:
                    dt_str = g["end_date"]
                    if g.get("end_time"):
                        dt_str += " " + g["end_time"]
                    else:
                        dt_str += " 23:59:59"
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    if dt > now:
                        upcoming.append((dt, f"Goal – {g['title']}"))
                except Exception:
                    pass

            for t in g.get("tasks", []):
                if not t.get("completed") and t.get("end_date"):
                    try:
                        dt_str = t["end_date"]
                        if t.get("end_time"):
                            dt_str += " " + t["end_time"]
                        else:
                            dt_str += " 23:59:59"
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        if dt > now:
                            upcoming.append((dt, f"{t['text']} ({g['title']})"))
                    except Exception:
                        pass

        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            self._next_deadline, self._next_item_title = upcoming[0]
            self._deadline_lbl.set_text(self._next_item_title)
        else:
            self._next_deadline = None
            self._next_item_title = ""
            self._deadline_lbl.set_text("No upcoming deadlines")
            self._timer_lbl.set_text("-- : -- : -- : --")

    # ------------------------------------------------------------------ tick

    def _on_tick(self) -> bool:
        if not self._next_deadline:
            return True
        now = datetime.now()
        diff = self._next_deadline - now
        if diff.total_seconds() <= 0:
            self._find_next_deadline()
            return True
        days = diff.days
        hours, rem = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        self._timer_lbl.set_text(f"{days:02d} : {hours:02d} : {minutes:02d} : {seconds:02d}")
        return True
