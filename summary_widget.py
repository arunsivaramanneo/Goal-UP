"""Graphical summary widget for Goal UP."""

import math
import gi
import cairo
import calendar
from datetime import datetime, date, timedelta
from collections import defaultdict

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gdk, GObject, Adw, GLib

class GoalPieChartsWidget(Gtk.DrawingArea):
    """Widget that draws the pie charts for goals and tasks."""

    def __init__(self):
        super().__init__()
        self.set_content_width(450)
        self.set_content_height(250)
        self.set_draw_func(self._draw_func)
        
        self._completed_goals = 0
        self._total_goals = 0
        self._completed_tasks = 0
        self._total_tasks = 0
        self._goals = []
        
        self._style_context = self.get_style_context()
        self._goal_completed_color = (0.15, 0.68, 0.37)
        self._last_goal_slices = []
        self._last_task_slices = []

        self._motion = Gtk.EventControllerMotion()
        self._motion.connect("motion", self._on_motion)
        self._motion.connect("enter", self._on_pointer_enter)
        self._motion.connect("leave", self._on_pointer_leave)
        self.add_controller(self._motion)
        self.set_has_tooltip(True)

    def update_data(self, completed_goals, total_goals, completed_tasks, total_tasks, goals):
        self._completed_goals = completed_goals
        self._total_goals = total_goals
        self._completed_tasks = completed_tasks
        self._total_tasks = total_tasks
        self._goals = goals
        self.queue_draw()

    def _draw_func(self, area, cr, width, height):
        # Draw two pie charts side-by-side
        left_x = width * 0.25
        right_x = width * 0.75
        center_y = height * 0.45
        radius = min(width * 0.2, height * 0.4)
        
        total_tasks_all_goals = sum(len(g.get("tasks", [])) for g in self._goals)

        self._draw_goals_pie(cr, left_x, center_y, radius, self._goals, total_tasks_all_goals, "Goals")
        self._draw_pie(cr, right_x, center_y, radius, self._completed_tasks, self._total_tasks, 
                       (0.15, 0.68, 0.37), (0.9, 0.4, 0.2), "Tasks")

    def _parse_color(self, color_str):
        if not color_str: return (0.5, 0.5, 0.5)
        color_str = color_str.strip()
        if (color_str.startswith("rgb(") or color_str.startswith("rgba(")) and color_str.endswith(")"):
            try:
                inside = color_str[color_str.find("(") + 1: color_str.rfind(")")]
                parts = [p.strip() for p in inside.split(",")]
                if len(parts) >= 3:
                    r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                    def norm(v): return max(0.0, min(1.0, v / 255.0)) if v > 1.0 else max(0.0, min(1.0, v))
                    return (norm(r), norm(g), norm(b))
            except: pass
        c = Gdk.RGBA()
        if c.parse(color_str): return (c.red, c.green, c.blue)
        return (0.5, 0.5, 0.5)

    def _luminance(self, rgb):
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

    def _point_angle(self, cx, cy, x, y):
        ang = math.atan2(y - cy, x - cx)
        return ang + 2 * math.pi if ang < 0 else ang

    def _angle_in_range(self, angle, start, end):
        s, e, a = start % (2 * math.pi), end % (2 * math.pi), angle % (2 * math.pi)
        return s <= a <= e if s <= e else a >= s or a <= e

    def _distance(self, cx, cy, x, y):
        return math.hypot(x - cx, y - cy)

    def _on_pointer_enter(self, ctrl, x, y): self._on_motion(ctrl, x, y)
    def _on_pointer_leave(self, ctrl, *args): self.set_tooltip_text(None)

    def _on_motion(self, ctrl, x, y):
        for s in self._last_goal_slices:
            if s["inner_r"] <= self._distance(s["center_x"], s["center_y"], x, y) <= s["outer_r"]:
                ang = self._point_angle(s["center_x"], s["center_y"], x, y)
                if self._angle_in_range(ang, s["start"], s["end"]):
                    g, tc, cc = s["goal"], s["task_count"], s["completed_count"]
                    pg = int((cc / tc) * 100) if tc > 0 else 0
                    ps = int(s["percent"] * 100)
                    title = g.get("title", g.get("text", "Untitled"))
                    self.set_tooltip_text(f"{title}\nTasks: {cc}/{tc} ({pg}% complete)\nShare: {ps}%")
                    return
        for s in self._last_task_slices:
            if s["inner_r"] <= self._distance(s["center_x"], s["center_y"], x, y) <= s["outer_r"]:
                ang = self._point_angle(s["center_x"], s["center_y"], x, y)
                if self._angle_in_range(ang, s["start"], s["end"]):
                    k, v, t = s["kind"], s["value"], s["total"]
                    p = int((v / t) * 100) if t > 0 else 0
                    self.set_tooltip_text(f"{k.capitalize()}: {v}/{t} ({p}%)")
                    return
        self.set_tooltip_text(None)

    def _draw_goals_pie(self, cr, center_x, center_y, radius, goals, total_tasks, label):
        start_angle = -math.pi / 2
        inner_r = radius * 0.5
        if total_tasks == 0:
            cr.new_path(); cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
            cr.arc(center_x, center_y, inner_r, 2 * math.pi, 0); cr.close_path()
            cr.set_source_rgb(0.85, 0.85, 0.85); cr.fill()
        else:
            self._last_goal_slices = []
            current_angle = start_angle
            for goal in goals:
                task_count = len(goal.get("tasks", []))
                if task_count == 0: continue
                percent = task_count / total_tasks
                angle_span = percent * 2 * math.pi
                end_angle = current_angle + angle_span
                base_color = self._parse_color(goal.get("color", ""))
                cr.new_path(); cr.arc(center_x, center_y, radius, current_angle, end_angle)
                cr.arc(center_x, center_y, inner_r, end_angle, current_angle); cr.close_path()
                cr.set_source_rgb(*base_color); cr.fill_preserve()
                self._last_goal_slices.append({
                    "center_x": center_x, "center_y": center_y, "outer_r": radius, "inner_r": inner_r,
                    "start": current_angle, "end": end_angle, "goal": goal, "task_count": task_count,
                    "completed_count": sum(1 for t in goal.get("tasks", []) if t.get("completed")), "percent": percent
                })
                cr.set_line_width(1.5)
                cr.set_source_rgba(0, 0, 0, 0.2) if self._luminance(base_color) > 0.6 else cr.set_source_rgba(1, 1, 1, 0.2)
                cr.stroke()
                cc = sum(1 for t in goal.get("tasks", []) if t.get("completed"))
                if cc > 0:
                    gp = cc / task_count
                    or_, og, ob = self._goal_completed_color
                    sr, sg, sb, sa = (0,0,0,0.6) if self._luminance((or_, og, ob)) > 0.75 else (1,1,1,0.8)
                    cr.new_path(); cr.arc(center_x, center_y, radius * 0.9, current_angle, current_angle + angle_span * gp)
                    cr.arc(center_x, center_y, radius * 0.55, current_angle + angle_span * gp, current_angle); cr.close_path()
                    cr.set_source_rgba(or_, og, ob, 0.95); cr.fill_preserve()
                    cr.set_line_width(2.0); cr.set_source_rgba(sr, sg, sb, sa); cr.stroke()
                current_angle = end_angle

        p_goals = int((self._completed_goals / self._total_goals) * 100) if self._total_goals > 0 else 0
        fg = self._style_context.get_color()
        fgl = 0.2126 * fg.red + 0.7152 * fg.green + 0.0722 * fg.blue
        cr.set_source_rgba(0,0,0,0.75) if fgl > 0.5 else cr.set_source_rgba(1,1,1,0.95)
        cr.new_path(); cr.arc(center_x, center_y, inner_r - 6, 0, 2 * math.pi); cr.fill()
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); cr.set_font_size(18)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
        txt = f"{p_goals}%"; (tx, ty, tw, th, dx, dy) = cr.text_extents(txt)
        cr.move_to(center_x - tw / 2 - tx, center_y + th / 2 - ty); cr.show_text(txt)
        cr.set_font_size(16); lbl = f"{label}: {self._completed_goals}/{self._total_goals}"
        (lx, ly, lw, lh, ldx, ldy) = cr.text_extents(lbl)
        cr.move_to(center_x - lw / 2 - lx, center_y + radius + 30); cr.show_text(lbl)

    def _draw_pie(self, cr, center_x, center_y, radius, completed, total, completed_color, remaining_color, label):
        pc = completed / total if total > 0 else 0.0
        start_angle = -math.pi / 2
        sa, inner_r = start_angle, radius * 0.5
        self._last_task_slices = []
        if pc < 1.0:
            rs, re = sa + pc * 2 * math.pi, sa + 2 * math.pi
            cr.new_path(); cr.arc(center_x, center_y, radius, rs, re); cr.arc(center_x, center_y, inner_r, re, rs); cr.close_path()
            cr.set_source_rgb(*remaining_color); cr.fill_preserve(); cr.set_line_width(1.5)
            cr.set_source_rgba(0,0,0,0.2) if self._luminance(remaining_color) > 0.6 else cr.set_source_rgba(1,1,1,0.25); cr.stroke()
            self._last_task_slices.append({"center_x": center_x, "center_y": center_y, "outer_r": radius, "inner_r": inner_r, "start": rs, "end": re, "kind": "remaining", "value": total - completed, "total": total})
        if pc > 0:
            cs, ce = sa, sa + pc * 2 * math.pi
            cr.new_path(); cr.arc(center_x, center_y, radius, cs, ce); cr.arc(center_x, center_y, inner_r, ce, cs); cr.close_path()
            cr.set_source_rgb(*completed_color); cr.fill_preserve(); cr.set_line_width(1.5)
            cr.set_source_rgba(0,0,0,0.2) if self._luminance(completed_color) > 0.6 else cr.set_source_rgba(1,1,1,0.25); cr.stroke()
            self._last_task_slices.append({"center_x": center_x, "center_y": center_y, "outer_r": radius, "inner_r": inner_r, "start": cs, "end": ce, "kind": "completed", "value": completed, "total": total})
        fg = self._style_context.get_color()
        fgl = 0.2126 * fg.red + 0.7152 * fg.green + 0.0722 * fg.blue
        cr.set_source_rgba(0,0,0,0.75) if fgl > 0.5 else cr.set_source_rgba(1,1,1,0.95)
        cr.new_path(); cr.arc(center_x, center_y, inner_r - 6, 0, 2 * math.pi); cr.fill()
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); cr.set_font_size(18)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
        txt = f"{int(pc*100)}%"; (tx, ty, tw, th, dx, dy) = cr.text_extents(txt)
        cr.move_to(center_x - tw / 2 - tx, center_y + th / 2 - ty); cr.show_text(txt)
        cr.set_font_size(16); lbl = f"{label}: {completed}/{total}"
        (lx, ly, lw, lh, ldx, ldy) = cr.text_extents(lbl)
        cr.move_to(center_x - lw / 2 - lx, center_y + radius + 30); cr.show_text(lbl)


class GoalProgressBarWidget(Gtk.DrawingArea):
    """Custom graphical progress bar for a goal showing monthly progress."""

    def __init__(self, color_hex, completed_prior, completed_month, total_tasks):
        super().__init__()
        self.set_content_height(20)
        self.set_hexpand(True)
        self.set_draw_func(self._draw_func)

        self._color_hex = color_hex
        self._completed_prior = completed_prior
        self._completed_month = completed_month
        self._total_tasks = max(total_tasks, 1)

    def update_data(self, color_hex, completed_prior, completed_month, total_tasks):
        self._color_hex = color_hex
        self._completed_prior = completed_prior
        self._completed_month = completed_month
        self._total_tasks = max(total_tasks, 1)
        self.queue_draw()

    def _parse_color(self, color_str):
        if not color_str: return (0.2, 0.5, 0.9)
        color_str = color_str.strip()
        if (color_str.startswith("rgb(") or color_str.startswith("rgba(")) and color_str.endswith(")"):
            try:
                inside = color_str[color_str.find("(") + 1: color_str.rfind(")")]
                parts = [p.strip() for p in inside.split(",")]
                if len(parts) >= 3:
                    r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                    def norm(v): return max(0.0, min(1.0, v / 255.0)) if v > 1.0 else max(0.0, min(1.0, v))
                    return (norm(r), norm(g), norm(b))
            except: pass
        c = Gdk.RGBA()
        if c.parse(color_str): return (c.red, c.green, c.blue)
        return (0.2, 0.5, 0.9)

    def _draw_func(self, area, cr, width, height):
        r, g, b = self._parse_color(self._color_hex)
        bar_h = 12
        y0 = (height - bar_h) / 2
        radius = bar_h / 2

        # Draw track background
        cr.new_path()
        cr.arc(width - radius, y0 + radius, radius, -math.pi/2, math.pi/2)
        cr.arc(radius, y0 + radius, radius, math.pi/2, 3*math.pi/2)
        cr.close_path()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.15)
        cr.fill()

        n = self._total_tasks
        p = self._completed_prior
        m = self._completed_month
        total_done = p + m

        w_prior = (p / n) * width
        w_month = (m / n) * width
        w_total = min(width, (total_done / n) * width)

        # Draw prior completed segment (muted goal color)
        if p > 0 and w_prior > 0:
            cr.new_path()
            if w_prior >= width - 1:
                cr.arc(width - radius, y0 + radius, radius, -math.pi/2, math.pi/2)
            else:
                cr.rectangle(w_prior - 2, y0, 2, bar_h)
            cr.arc(radius, y0 + radius, radius, math.pi/2, 3*math.pi/2)
            cr.close_path()
            cr.set_source_rgba(r * 0.6, g * 0.6, b * 0.6, 0.75)
            cr.fill()

        # Draw month completed segment (vibrant goal color)
        if m > 0 and w_month > 0:
            x_start = w_prior
            x_end = w_total
            cr.new_path()
            if x_start <= 1:
                cr.arc(radius, y0 + radius, radius, math.pi/2, 3*math.pi/2)
            else:
                cr.rectangle(x_start, y0, 2, bar_h)

            if x_end >= width - 1:
                cr.arc(width - radius, y0 + radius, radius, -math.pi/2, math.pi/2)
            else:
                cr.rectangle(x_end - 2, y0, 2, bar_h)

            cr.rectangle(x_start, y0, max(0, x_end - x_start), bar_h)
            cr.close_path()
            cr.set_source_rgba(r, g, b, 0.95)
            cr.fill()

        # Outline border
        cr.new_path()
        cr.arc(width - radius, y0 + radius, radius, -math.pi/2, math.pi/2)
        cr.arc(radius, y0 + radius, radius, math.pi/2, 3*math.pi/2)
        cr.close_path()
        cr.set_source_rgba(0, 0, 0, 0.15)
        cr.set_line_width(1.0)
        cr.stroke()


class GoalTrendWidget(Gtk.Box):
    """
    Motivational heatmap widget — GitHub-style daily contribution graph
    showing task/goal completions over the past year, plus streak stats
    and monthly goal progress details.
    """

    # Heatmap colour levels (light → vibrant) — works on both themes
    _HEAT_COLORS = [
        (0.15, 0.15, 0.15, 0.18),   # level 0 — empty
        (0.13, 0.55, 0.13, 0.60),   # level 1 — 1 completion
        (0.10, 0.75, 0.20, 0.78),   # level 2 — 2-3
        (0.05, 0.90, 0.30, 0.90),   # level 3 — 4-6
        (0.00, 1.00, 0.42, 1.00),   # level 4 — 7+
    ]

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._goals = []
        self._daily_counts = {}   # date → int completions
        self._tooltip_text = ""

        # ── Streak stats row ────────────────────────────────────────────────
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        stats_box.set_margin_top(4)
        stats_box.set_margin_bottom(6)
        stats_box.set_margin_start(8)
        stats_box.set_margin_end(8)
        self.append(stats_box)

        def _stat_card(icon, label_text, color_class):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            card.set_hexpand(True)
            card.add_css_class("card")
            card.set_margin_start(4)
            card.set_margin_end(4)
            card.set_margin_top(2)
            card.set_margin_bottom(2)

            ico = Gtk.Label(label=icon)
            ico.set_halign(Gtk.Align.CENTER)

            val = Gtk.Label(label="0")
            val.add_css_class("title-2")
            val.add_css_class(color_class)
            val.set_halign(Gtk.Align.CENTER)

            lbl = Gtk.Label(label=label_text)
            lbl.add_css_class("caption")
            lbl.add_css_class("dim-label")
            lbl.set_halign(Gtk.Align.CENTER)

            card.append(ico)
            card.append(val)
            card.append(lbl)
            return card, val, lbl

        streak_card, self._streak_val, self._streak_lbl = _stat_card("🔥", "Current Streak", "accent")
        best_card,   self._best_val,   self._best_lbl   = _stat_card("🏆", "Best Streak",    "success")
        total_card,  self._total_val,  self._total_lbl  = _stat_card("✅", "Total Done",      "")

        stats_box.append(streak_card)
        stats_box.append(best_card)
        stats_box.append(total_card)

        # ── Section title ────────────────────────────────────────────────────
        title_lbl = Gtk.Label(label="Completion Activity")
        title_lbl.add_css_class("heading")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_margin_start(12)
        title_lbl.set_margin_bottom(2)
        self.append(title_lbl)

        # ── Drawing area ─────────────────────────────────────────────────────
        self._canvas = Gtk.DrawingArea()
        self._canvas.set_content_width(300)
        self._canvas.set_content_height(120)
        self._canvas.set_vexpand(False)
        self._canvas.set_hexpand(True)
        self._canvas.set_margin_start(8)
        self._canvas.set_margin_end(8)
        self._canvas.set_margin_bottom(4)
        self._canvas.set_draw_func(self._draw_heatmap)
        self._canvas.set_has_tooltip(True)
        self._canvas.connect("query-tooltip", self._on_query_tooltip)
        self.append(self._canvas)

        # ── Motivational month labels (drawn below the heatmap) ──────────────
        self._month_canvas = Gtk.DrawingArea()
        self._month_canvas.set_content_height(18)
        self._month_canvas.set_hexpand(True)
        self._month_canvas.set_margin_start(8)
        self._month_canvas.set_margin_end(8)
        self._month_canvas.set_draw_func(self._draw_month_labels)
        self.append(self._month_canvas)

        # ── Legend ───────────────────────────────────────────────────────────
        legend_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        legend_box.set_halign(Gtk.Align.END)
        legend_box.set_margin_end(12)
        legend_box.set_margin_top(2)
        legend_box.set_margin_bottom(4)
        less_lbl = Gtk.Label(label="Less")
        less_lbl.add_css_class("caption")
        less_lbl.add_css_class("dim-label")
        legend_box.append(less_lbl)
        self._legend_canvas = Gtk.DrawingArea()
        self._legend_canvas.set_content_width(70)
        self._legend_canvas.set_content_height(12)
        self._legend_canvas.set_draw_func(self._draw_legend)
        legend_box.append(self._legend_canvas)
        more_lbl = Gtk.Label(label="More")
        more_lbl.add_css_class("caption")
        more_lbl.add_css_class("dim-label")
        legend_box.append(more_lbl)
        self.append(legend_box)

        # ── Monthly Goal Progress Section ────────────────────────────────────
        self._progress_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._progress_section.set_margin_top(14)
        self._progress_section.set_margin_bottom(8)
        self._progress_section.set_margin_start(8)
        self._progress_section.set_margin_end(8)
        self.append(self._progress_section)

        # Mouse tracking for tooltip
        self._hover_date = None
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", lambda *_: self._set_hover(None))
        self._canvas.add_controller(motion)

        # Geometry cache (set in draw)
        self._cell_size = 11
        self._cell_gap  = 2
        self._left_pad  = 24   # space for weekday labels
        self._top_pad   = 2
        self._num_weeks = 53

    # ── public API ────────────────────────────────────────────────────────────

    def update_data(self, goals):
        self._goals = goals
        self._rebuild_daily_counts()
        self._update_streak_labels()
        self._update_monthly_progress_section()
        self._canvas.queue_draw()
        self._month_canvas.queue_draw()
        self._legend_canvas.queue_draw()

    # ── data helpers ──────────────────────────────────────────────────────────

    def _rebuild_daily_counts(self):
        counts = defaultdict(int)
        items = defaultdict(list)
        for g in self._goals:
            g_title = g.get("title", g.get("text", "Untitled Goal"))
            if g.get("completed"):
                ds = (g.get("completion_date") or g.get("end_date") or "")[:10]
                d = None
                if ds:
                    try:
                        d = datetime.strptime(ds, "%Y-%m-%d").date()
                    except Exception:
                        pass
                if not d:
                    d = date.today()
                counts[d] += 1
                items[d].append(f"🎯 Goal: {g_title}")

            for t in g.get("tasks", []):
                t_text = t.get("text", "Untitled Task")
                if t.get("completed"):
                    ds = (t.get("completion_date") or t.get("end_date") or "")[:10]
                    d = None
                    if ds:
                        try:
                            d = datetime.strptime(ds, "%Y-%m-%d").date()
                        except Exception:
                            pass
                    if not d:
                        d = date.today()
                    counts[d] += 1
                    items[d].append(f"✅ Task: {t_text} ({g_title})")
        self._daily_counts = dict(counts)
        self._daily_items = dict(items)

    def _count_for(self, d):
        return self._daily_counts.get(d, 0)

    def _heat_level(self, count):
        if count == 0: return 0
        if count == 1: return 1
        if count <= 3: return 2
        if count <= 6: return 3
        return 4

    def _calc_streaks(self):
        """Calculate Current Month completions and Best Month max completions."""
        today = date.today()
        monthly_counts = defaultdict(int)
        for d, count in self._daily_counts.items():
            if count > 0:
                monthly_counts[(d.year, d.month)] += count

        curr_y, curr_m = today.year, today.month
        current_month_done = monthly_counts.get((curr_y, curr_m), 0)
        current_month_name = today.strftime("%b")

        if monthly_counts:
            best_ym = max(monthly_counts, key=monthly_counts.get)
            best_month_max = monthly_counts[best_ym]
            best_month_name = date(best_ym[0], best_ym[1], 1).strftime("%b")
        else:
            best_month_max = 0
            best_month_name = today.strftime("%b")

        return current_month_done, current_month_name, best_month_max, best_month_name

    def _update_streak_labels(self):
        curr_done, curr_month, best_max, best_month = self._calc_streaks()
        total = sum(self._daily_counts.values())
        self._streak_val.set_text(str(curr_done))
        self._streak_lbl.set_text(f"Current Streak - {curr_month}")

        self._best_val.set_text(str(best_max))
        self._best_lbl.set_text(f"Best Streak - {best_month}")

        self._total_val.set_text(str(total))
        self._total_lbl.set_text("Total Done")

    def _update_monthly_progress_section(self):
        # Clear previous items
        child = self._progress_section.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._progress_section.remove(child)
            child = next_child

        today = date.today()
        curr_y, curr_m = today.year, today.month
        month_name = today.strftime("%B")

        # Section Header
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr_box.set_margin_bottom(4)

        hdr_lbl = Gtk.Label(label=f"Goals Progressed in {month_name}")
        hdr_lbl.add_css_class("heading")
        hdr_lbl.set_halign(Gtk.Align.START)
        hdr_lbl.set_hexpand(True)
        hdr_box.append(hdr_lbl)

        self._progress_section.append(hdr_box)

        # Collect progress per goal for this month
        progressed_goals = []
        for g in self._goals:
            g_title = g.get("title", g.get("text", "Untitled Goal"))
            color_hex = g.get("color") or "#3584e4"
            tasks = g.get("tasks", [])
            total_tasks = len(tasks)

            completed_month = 0
            completed_prior = 0

            for t in tasks:
                if t.get("completed"):
                    cd = t.get("completion_date") or t.get("end_date") or ""
                    t_date = None
                    if cd:
                        try:
                            t_date = datetime.strptime(cd[:10], "%Y-%m-%d").date()
                        except: pass
                    if not t_date:
                        t_date = today

                    if t_date.year == curr_y and t_date.month == curr_m:
                        completed_month += 1
                    else:
                        completed_prior += 1

            # Check if goal itself was completed this month
            g_completed_this_month = False
            if g.get("completed"):
                gcd = g.get("completion_date") or g.get("end_date") or ""
                g_date = None
                if gcd:
                    try:
                        g_date = datetime.strptime(gcd[:10], "%Y-%m-%d").date()
                    except: pass
                if not g_date:
                    g_date = today
                if g_date.year == curr_y and g_date.month == curr_m:
                    g_completed_this_month = True

            if completed_month > 0 or g_completed_this_month:
                eff_total = max(total_tasks, 1 if g_completed_this_month else 0)
                eff_month = completed_month if completed_month > 0 else (1 if g_completed_this_month else 0)
                progressed_goals.append({
                    "goal": g,
                    "title": g_title,
                    "color": color_hex,
                    "total_tasks": eff_total,
                    "completed_month": eff_month,
                    "completed_prior": completed_prior,
                    "is_goal_completed": g_completed_this_month
                })

        if not progressed_goals:
            empty_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            empty_card.add_css_class("card")
            empty_card.set_margin_top(4)
            empty_card.set_margin_bottom(4)
            empty_card.set_margin_start(4)
            empty_card.set_margin_end(4)

            lbl = Gtk.Label(label=f"No goals progressed yet in {month_name}")
            lbl.add_css_class("body")
            lbl.add_css_class("dim-label")
            lbl.set_halign(Gtk.Align.CENTER)
            empty_card.append(lbl)

            sub_lbl = Gtk.Label(label="Complete tasks to see monthly goal activity here!")
            sub_lbl.add_css_class("caption")
            sub_lbl.add_css_class("dim-label")
            sub_lbl.set_halign(Gtk.Align.CENTER)
            empty_card.append(sub_lbl)

            self._progress_section.append(empty_card)
        else:
            for item in progressed_goals:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                card.add_css_class("card")
                card.set_margin_top(4)
                card.set_margin_bottom(4)
                card.set_margin_start(4)
                card.set_margin_end(4)

                # Header row in card
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                
                # Color dot/pill
                dot = Gtk.Box()
                dot.set_size_request(10, 10)
                dot.set_valign(Gtk.Align.CENTER)
                c_clean = item["color"] if (item["color"].startswith("#") or item["color"].startswith("rgb")) else f"#{item['color']}"
                provider = Gtk.CssProvider()
                provider.load_from_data(f"box {{ background-color: {c_clean}; border-radius: 5px; }}".encode())
                dot.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                row.append(dot)

                # Title
                t_lbl = Gtk.Label(label=item["title"])
                t_lbl.add_css_class("title-4")
                t_lbl.set_halign(Gtk.Align.START)
                t_lbl.set_hexpand(True)
                t_lbl.set_ellipsize(3)
                row.append(t_lbl)

                # Badge showing task count completed this month
                c_count = item["completed_month"]
                badge_text = f"{c_count} task{'s' if c_count != 1 else ''} completed this month"
                badge = Gtk.Label(label=badge_text)
                badge.add_css_class("caption")
                badge.add_css_class("accent")
                badge.set_halign(Gtk.Align.END)
                row.append(badge)

                card.append(row)

                # Graphical Progress Bar area
                bar = GoalProgressBarWidget(
                    item["color"],
                    item["completed_prior"],
                    item["completed_month"],
                    item["total_tasks"]
                )
                card.append(bar)

                # Caption row showing exact task breakdown
                tot_done = item["completed_prior"] + item["completed_month"]
                pct = int((tot_done / max(1, item["total_tasks"])) * 100)
                sub_txt = f"{tot_done}/{item['total_tasks']} total tasks ({pct}% overall progress)"
                sub_lbl = Gtk.Label(label=sub_txt)
                sub_lbl.add_css_class("caption")
                sub_lbl.add_css_class("dim-label")
                sub_lbl.set_halign(Gtk.Align.START)
                card.append(sub_lbl)

                self._progress_section.append(card)

    # ── drawing ───────────────────────────────────────────────────────────────

    def _week_start(self):
        """Return the Sunday that starts the grid (53 weeks back from today)."""
        today = date.today()
        # Align to Sunday
        start = today - timedelta(days=today.weekday() + 1)  # last Sunday
        start = start - timedelta(weeks=self._num_weeks - 1)
        return start

    def _draw_heatmap(self, area, cr, width, height):
        lp = self._left_pad
        available_w = width - lp - 4
        if available_w > 100:
            step = available_w / self._num_weeks
            cs = max(4.0, step - 2.0)
            cg = step - cs
        else:
            cs = self._cell_size
            cg = self._cell_gap
            step = cs + cg

        start = self._week_start()

        fg = self._canvas.get_style_context().get_color()

        # Row weekday labels (Mon, Wed, Fri)
        cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.5)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(min(8, int(cs)))
        day_labels = {1: "Mon", 3: "Wed", 5: "Fri"}
        for r, lbl in day_labels.items():
            cr.move_to(2, self._top_pad + r * step + cs - 2)
            cr.show_text(lbl)

        # Draw cells
        today_date = date.today()
        for col in range(self._num_weeks):
            for row in range(7):
                d = start + timedelta(days=col * 7 + row)
                if d > today_date:
                    continue

                x0 = lp + col * step
                y0 = self._top_pad + row * step

                lvl = self._heat_level(self._count_for(d))
                r_, g_, b_, a_ = self._HEAT_COLORS[lvl]

                # Rounded rectangle cell
                cs_dyn = cs
                radius = max(1.0, min(2.0, cs_dyn * 0.2))
                cr.new_path()
                cr.arc(x0 + cs_dyn - radius, y0 + radius, radius, -math.pi/2, 0)
                cr.arc(x0 + cs_dyn - radius, y0 + cs_dyn - radius, radius, 0, math.pi/2)
                cr.arc(x0 + radius, y0 + cs_dyn - radius, radius, math.pi/2, math.pi)
                cr.arc(x0 + radius, y0 + radius, radius, math.pi, 3*math.pi/2)
                cr.close_path()

                cr.set_source_rgba(r_, g_, b_, a_)
                cr.fill_preserve()

                # Cell border
                if lvl == 0:
                    cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.08)
                else:
                    cr.set_source_rgba(0, 0, 0, 0.25)
                cr.set_line_width(0.8)
                cr.stroke()

                # Highlight today
                if d == today_date:
                    cr.new_path()
                    cr.arc(x0 + cs_dyn - radius, y0 + radius, radius, -math.pi/2, 0)
                    cr.arc(x0 + cs_dyn - radius, y0 + cs_dyn - radius, radius, 0, math.pi/2)
                    cr.arc(x0 + radius, y0 + cs_dyn - radius, radius, math.pi/2, math.pi)
                    cr.arc(x0 + radius, y0 + radius, radius, math.pi, 3*math.pi/2)
                    cr.close_path()
                    cr.set_source_rgba(1.0, 0.85, 0.0, 0.9)
                    cr.set_line_width(1.5)
                    cr.stroke()

    def _draw_month_labels(self, area, cr, width, height):
        lp = self._left_pad
        available_w = width - lp - 4
        if available_w > 100:
            step = available_w / self._num_weeks
        else:
            step = self._cell_size + self._cell_gap
        start = self._week_start()

        fg = self._canvas.get_style_context().get_color()
        cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.6)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(9)

        last_month = -1
        for col in range(self._num_weeks):
            d = start + timedelta(days=col * 7)
            if d.month != last_month:
                last_month = d.month
                label = d.strftime("%b")
                x0 = lp + col * step
                cr.move_to(x0, 12)
                cr.show_text(label)

    def _draw_legend(self, area, cr, width, height):
        num = len(self._HEAT_COLORS)
        sz = 10
        gap = (width - num * sz) / (num + 1)
        for i, (r_, g_, b_, a_) in enumerate(self._HEAT_COLORS):
            x0 = gap + i * (sz + gap)
            cr.rectangle(x0, 1, sz, sz)
            cr.set_source_rgba(r_, g_, b_, max(a_, 0.4))
            cr.fill()

    # ── tooltip / hover ───────────────────────────────────────────────────────

    def _cell_for_pos(self, x, y):
        lp = self._left_pad
        w = self._canvas.get_allocated_width()
        if w <= 1:
            w = 300
        available_w = w - lp - 4
        if available_w > 100:
            step = available_w / self._num_weeks
        else:
            step = self._cell_size + self._cell_gap
        col = int((x - lp) // step)
        row = int((y - self._top_pad) // step)
        if 0 <= col < self._num_weeks and 0 <= row < 7:
            start = self._week_start()
            d = start + timedelta(days=col * 7 + row)
            if d <= date.today():
                return d
        return None

    def _on_motion(self, ctrl, x, y):
        self._set_hover(self._cell_for_pos(x, y))

    def _set_hover(self, d):
        self._hover_date = d

    def _on_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        d = self._cell_for_pos(x, y)
        if d is None:
            return False
        count = self._count_for(d)
        label = d.strftime("%a, %d %b %Y")
        if count == 0:
            tooltip.set_text(f"{label}\nNo completions")
        else:
            completed_list = self._daily_items.get(d, [])
            if completed_list:
                items_str = "\n".join(completed_list)
                header = f"{label} ({count} completion{'s' if count > 1 else ''}):"
                tooltip.set_text(f"{header}\n{items_str}")
            else:
                tooltip.set_text(f"{label}\n{count} completion{'s' if count > 1 else ''}")
        return True


class NotificationWidget(Adw.Bin):
    """Widget that shows notifications for overdue/upcoming tasks and progress alerts."""

    def __init__(self):
        super().__init__()
        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("boxed-list")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        label = Gtk.Label(label="Notifications")
        label.add_css_class("title-4")
        label.set_halign(Gtk.Align.START)
        box.append(label)
        box.append(self._list_box)
        
        self.set_child(box)
        self._goals = []

    def update_data(self, goals):
        self._goals = goals
        self._refresh()

    def _refresh(self):
        # Clear existing items
        row = self._list_box.get_first_child()
        while row:
            next_row = row.get_next_sibling()
            self._list_box.remove(row)
            row = next_row

        today = date.today()
        week_later = today + timedelta(days=7)
        month_later = today + timedelta(days=30)
        
        overdue = []
        upcoming_week = []   # List of (date, text) tuples for next 7 days
        upcoming_month = []  # List of (date, text) tuples for days 8-30
        any_completed_recently = False
        
        for g in self._goals:
            # Check goal itself
            if not g.get("completed"):
                ed = g.get("end_date")
                if ed:
                    try:
                        d = datetime.strptime(ed, "%Y-%m-%d").date()
                        if d < today:
                            overdue.append(f"Goal: {g['title']}")
                        elif d <= week_later:
                            upcoming_week.append((d, f"Goal: {g['title']}"))
                        elif d <= month_later:
                            upcoming_month.append((d, f"Goal: {g['title']}"))
                    except: pass
            else:
                cd = g.get("completion_date")
                if cd:
                    try:
                        d = datetime.strptime(cd, "%Y-%m-%d").date()
                        if (today - d).days <= 7:
                            any_completed_recently = True
                    except: pass

            # Check tasks
            for t in g.get("tasks", []):
                is_recurring = t.get("recurrence", "none") != "none"
                recur_sym = " 🔄" if is_recurring else ""
                label_prefix = "Reminder:" if is_recurring else "Task:"
                
                if not t.get("completed"):
                    ted = t.get("end_date")
                    if ted:
                        try:
                            d = datetime.strptime(ted, "%Y-%m-%d").date()
                            if d < today:
                                overdue.append(f"{label_prefix} {t['text']} ({g['title']}){recur_sym}")
                            elif d <= week_later:
                                upcoming_week.append((d, f"{label_prefix} {t['text']} ({g['title']}){recur_sym}"))
                            elif d <= month_later:
                                upcoming_month.append((d, f"{label_prefix} {t['text']} ({g['title']}){recur_sym}"))
                        except: pass
                else:
                    tcd = t.get("completion_date")
                    if tcd:
                        try:
                            d = datetime.strptime(tcd, "%Y-%m-%d").date()
                            if (today - d).days <= 7:
                                any_completed_recently = True
                        except: pass

                # Project future recurring task instances
                if is_recurring:
                    try:
                        # Determine starting point for projection: task creation or today
                        created_str = t.get("created_at")
                        if created_str:
                            if "T" in created_str:
                                start_date = datetime.strptime(created_str.split("T")[0], "%Y-%m-%d").date()
                            else:
                                start_date = datetime.strptime(created_str, "%Y-%m-%d").date()
                        else:
                            start_date = today

                        # Boundary for stopping projection
                        task_end = None
                        if t.get("end_date"):
                            try:
                                task_end = datetime.strptime(t["end_date"], "%Y-%m-%d").date()
                            except: pass

                        projection_date = start_date - timedelta(days=1)
                        found_count = 0
                        
                        while True:
                            next_date = self._calculate_next_date(projection_date, t.get("recurrence"), t.get("recurrence_days"))
                            
                            if not next_date: break
                            if next_date > month_later: break
                            if task_end and next_date > task_end: break

                            # Only show occurrences from today onwards
                            if next_date >= today:
                                if not t.get("completed") or next_date > today:
                                    target_list = upcoming_week if next_date <= week_later else upcoming_month
                                    exists = any(u[0] == next_date and t['text'] in u[1] for u in (upcoming_week + upcoming_month))
                                    if not exists:
                                        target_list.append((next_date, f"{label_prefix} {t['text']} ({g['title']}){recur_sym}"))
                                        found_count += 1
                                        
                                        if t.get("recurrence") == "daily":
                                            break
                            
                            projection_date = next_date
                            if projection_date > month_later + timedelta(days=365): break

                    except Exception as e:
                        print(f"Error projecting recurring task: {e}")

        # Add "Overdue" section
        if overdue:
            self._add_header("Overdue", "error")
            for item in overdue:
                self._add_item(item, "error")

        # Add "Upcoming Week" section
        if upcoming_week:
            upcoming_week.sort(key=lambda x: x[0])
            self._add_header("Upcoming Week", "accent")
            for d, text in upcoming_week:
                date_str = d.strftime("%a")
                self._add_item(f"{date_str} - {text}")

        # Add "Upcoming Month" section
        if upcoming_month:
            upcoming_month.sort(key=lambda x: x[0])
            self._add_header("Upcoming Month", "accent")
            for d, text in upcoming_month:
                date_str = d.strftime("%b %d")
                self._add_item(f"{date_str} - {text}")

        # Alert if no progress
        if not any_completed_recently and self._goals:
            self._add_header("Alert", "warning")
            self._add_item("No progress made in the last week!", "warning")

        if not overdue and not upcoming_week and not upcoming_month and (any_completed_recently or not self._goals):
            empty_row = Adw.ActionRow()
            empty_row.set_title("No notifications")
            empty_row.add_css_class("dim-label")
            self._list_box.append(empty_row)

    def _add_header(self, title, css_class=None):
        row = Adw.ActionRow()
        row.set_title(f"<b>{title}</b>")
        row.set_use_markup(True)
        if css_class:
            row.add_css_class(css_class)
        self._list_box.append(row)

    def _add_item(self, text, css_class=None):
        row = Adw.ActionRow()
        row.set_title(text)
        if css_class:
            row.add_css_class(css_class)
        self._list_box.append(row)

    def _calculate_next_date(self, current_date, recurrence, recurrence_days):
        """Calculate the next date based on recurrence rules (Same logic as GoalRow)."""
        if recurrence == "daily":
            return current_date + timedelta(days=1)
        
        elif recurrence == "monthly":
            # Rough monthly jump
            month = current_date.month % 12 + 1
            year = current_date.year + (current_date.month // 12)
            try:
                return current_date.replace(year=year, month=month)
            except ValueError:
                # Handle end of month issues
                return (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
        elif recurrence == "weekly":
            if not recurrence_days:
                return current_date + timedelta(days=7)
            
            allowed_days = [int(d) for d in recurrence_days.split(",") if d.strip()]
            if not allowed_days:
                return current_date + timedelta(days=7)
            
            # Find next allowed day
            for i in range(1, 8):
                next_candidate = current_date + timedelta(days=i)
                if next_candidate.weekday() in allowed_days:
                    return next_candidate
                    
        return None


class TimerWidget(Adw.Bin):
    """Widget that shows a countdown timer to the next upcoming task or goal."""

    def __init__(self):
        super().__init__()
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._box.set_halign(Gtk.Align.CENTER)
        self._box.set_margin_top(10)
        self._box.set_margin_bottom(10)
        
        self._title_label = Gtk.Label(label="Next Deadline")
        self._title_label.add_css_class("dim-label")
        self._title_label.add_css_class("caption")
        self._box.append(self._title_label)
        
        # Timer columns box
        self._timer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self._timer_box.set_halign(Gtk.Align.CENTER)
        self._box.append(self._timer_box)
        
        # Helper to create units
        def create_unit_box(label_text):
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vbox.set_halign(Gtk.Align.CENTER)
            
            num_label = Gtk.Label(label="00")
            num_label.add_css_class("title-1")
            num_label.set_markup("<span font_family='monospace' size='xx-large' weight='bold'>00</span>")
            
            desc_label = Gtk.Label(label=label_text)
            desc_label.add_css_class("caption")
            desc_label.add_css_class("dim-label")
            
            vbox.append(num_label)
            vbox.append(desc_label)
            return vbox, num_label

        self._days_box, self._days_num = create_unit_box("DAYS")
        self._hrs_box, self._hrs_num = create_unit_box("HRS")
        self._min_box, self._min_num = create_unit_box("MIN")
        self._sec_box, self._sec_num = create_unit_box("SEC")
        
        def create_colon():
            lbl = Gtk.Label(label=":")
            lbl.add_css_class("title-1")
            lbl.set_valign(Gtk.Align.START)
            lbl.set_margin_top(4)
            return lbl

        self._timer_box.append(self._days_box)
        self._timer_box.append(create_colon())
        self._timer_box.append(self._hrs_box)
        self._timer_box.append(create_colon())
        self._timer_box.append(self._min_box)
        self._timer_box.append(create_colon())
        self._timer_box.append(self._sec_box)
        
        self._item_label = Gtk.Label(label="No upcoming deadlines")
        self._item_label.add_css_class("body")
        self._item_label.set_margin_top(4)
        self._box.append(self._item_label)
        
        self.set_child(self._box)
        self._goals = []
        self._next_deadline = None
        self._next_item_title = ""
        
        # Start timer
        GLib.timeout_add_seconds(1, self._on_tick)

    def update_data(self, goals):
        self._goals = goals
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
                    
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") if " " in dt_str else datetime.strptime(dt_str, "%Y-%m-%d")
                    if dt > now:
                        upcoming.append((dt, f"Goal - {g['title']}"))
                except: pass
            
            for t in g.get("tasks", []):
                if not t.get("completed") and t.get("end_date"):
                    try:
                        dt_str = t["end_date"]
                        if t.get("end_time"):
                            dt_str += " " + t["end_time"]
                        else:
                            dt_str += " 23:59:59"
                            
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") if " " in dt_str else datetime.strptime(dt_str, "%Y-%m-%d")
                        if dt > now:
                            upcoming.append((dt, f"Task - {t['text']} ({g['title']})"))
                    except: pass
        
        if upcoming:
            upcoming.sort(key=lambda x: x[0])
            self._next_deadline, self._next_item_title = upcoming[0]
            self._item_label.set_text(self._next_item_title)
        else:
            self._next_deadline = None
            self._item_label.set_text("No upcoming deadlines")
            self._reset_labels()

    def _reset_labels(self):
        for lbl in [self._days_num, self._hrs_num, self._min_num, self._sec_num]:
            lbl.set_markup("<span font_family='monospace' size='xx-large' weight='bold'>00</span>")

    def _on_tick(self):
        if not self._next_deadline:
            return True
        
        now = datetime.now()
        diff = self._next_deadline - now
        
        if diff.total_seconds() <= 0:
            self._find_next_deadline()
            return True
        
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        def set_num(lbl, val):
            lbl.set_markup(f"<span font_family='monospace' size='xx-large' weight='bold'>{val:02}</span>")

        set_num(self._days_num, days)
        set_num(self._hrs_num, hours)
        set_num(self._min_num, minutes)
        set_num(self._sec_num, seconds)
        
        return True


class CalendarWidget(Adw.Bin):
    """Monthly calendar widget showing tasks and goals as dots."""

    def __init__(self):
        super().__init__()
        self._goals = []
        self._view_date = date.today().replace(day=1)
        
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_child(self._main_box)
        
        # Header: Month Year + Navigation
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._main_box.append(header_box)
        
        self._month_label = Gtk.Label()
        self._month_label.add_css_class("title-4")
        self._month_label.set_hexpand(True)
        self._month_label.set_halign(Gtk.Align.START)
        header_box.append(self._month_label)
        
        prev_btn = Gtk.Button(icon_name="go-previous-symbolic")
        prev_btn.add_css_class("flat")
        prev_btn.connect("clicked", self._on_prev_clicked)
        header_box.append(prev_btn)
        
        next_btn = Gtk.Button(icon_name="go-next-symbolic")
        next_btn.add_css_class("flat")
        next_btn.connect("clicked", self._on_next_clicked)
        header_box.append(next_btn)
        
        # Day headers (Mon-Sun)
        self._grid = Gtk.Grid()
        self._grid.set_column_homogeneous(True)
        self._grid.set_row_spacing(8)
        self._grid.set_column_spacing(4)
        self._main_box.append(self._grid)
        
        self._refresh()

    def update_data(self, goals):
        self._goals = goals
        self._refresh()

    def _on_prev_clicked(self, btn):
        year = self._view_date.year
        month = self._view_date.month - 1
        if month == 0:
            month = 12
            year -= 1
        self._view_date = date(year, month, 1)
        self._refresh()

    def _on_next_clicked(self, btn):
        year = self._view_date.year
        month = self._view_date.month + 1
        if month == 13:
            month = 1
            year += 1
        self._view_date = date(year, month, 1)
        self._refresh()

    def _refresh(self):
        # Update month label
        self._month_label.set_text(self._view_date.strftime("%B %Y"))
        
        # Clear previous grid content
        while True:
            child = self._grid.get_first_child()
            if not child: break
            self._grid.remove(child)

        days_of_week = ["M", "T", "W", "T", "F", "S", "S"]
        for i, d in enumerate(days_of_week):
            lbl = Gtk.Label(label=d)
            lbl.add_css_class("dim-label")
            lbl.add_css_class("caption")
            lbl.set_margin_bottom(4)
            self._grid.attach(lbl, i, 0, 1, 1)

        cal = calendar.monthcalendar(self._view_date.year, self._view_date.month)
        today = date.today()
        
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue
                
                day_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                day_box.set_valign(Gtk.Align.CENTER)
                day_box.set_halign(Gtk.Align.CENTER)
                day_box.set_spacing(2)
                day_box.set_size_request(30, 40)
                
                day_label = Gtk.Label(label=str(day))
                day_label.add_css_class("caption")
                
                curr_date = date(self._view_date.year, self._view_date.month, day)
                if curr_date == today:
                    day_label.add_css_class("accent")
                    day_label.set_markup(f"<b>{day}</b>")
                
                day_box.append(day_label)
                
                # Dots for tasks/goals
                dots_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                dots_box.set_halign(Gtk.Align.CENTER)
                day_box.append(dots_box)
                
                colors = self._get_colors_for_date(curr_date)
                for color in colors[:3]: # Limit to 3 dots to avoid overcrowding
                    dot = Gtk.Box()
                    dot.set_size_request(6, 6)
                    
                    # Ensure color is in a format CSS likes
                    clean_color = color if color.startswith('#') or color.startswith('rgb') else f"#{color}"
                    
                    provider = Gtk.CssProvider()
                    # We use a unique class or just target the widget
                    css = f"box {{ background-color: {clean_color}; border-radius: 3px; }}"
                    provider.load_from_data(css.encode())
                    dot.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                    dots_box.append(dot)

                details = self._get_details_for_date(curr_date)
                if details:
                    day_box.set_tooltip_text("\n".join(details))
                    day_box.set_has_tooltip(True)
                
                self._grid.attach(day_box, col_idx, row_idx + 1, 1, 1)

    def _get_colors_for_date(self, target_date):
        target_str = target_date.strftime("%Y-%m-%d")
        colors = []
        for g in self._goals:
            # Check goal date
            if g.get("completed"):
                date_to_match = g.get("completion_date") or g.get("end_date")
                if date_to_match:
                    date_to_match = date_to_match.split("T")[0]
                if date_to_match == target_str:
                    colors.append(g.get("color") or "#808080")
            else:
                if g.get("end_date") == target_str:
                    colors.append(g.get("color") or "#808080")
            
            # Check tasks
            for t in g.get("tasks", []):
                is_on_date = False
                if t.get("completed"):
                    date_to_match = t.get("completion_date") or t.get("end_date")
                    if date_to_match:
                        date_to_match = date_to_match.split("T")[0]
                    if date_to_match == target_str:
                        is_on_date = True
                else:
                    if t.get("end_date") == target_str:
                        is_on_date = True
                    elif t.get("recurrence", "none") != "none":
                        if self._is_on_date(target_date, t):
                            is_on_date = True

                if is_on_date:
                    colors.append(g.get("color") or "#808080")
                            
        # Return unique colors
        seen = set()
        unique_colors = []
        for c in colors:
            if c and c not in seen:
                unique_colors.append(c)
                seen.add(c)
        return unique_colors

    def _get_details_for_date(self, target_date):
        target_str = target_date.strftime("%Y-%m-%d")
        details = []
        for g in self._goals:
            # Check goal date
            is_goal_on_date = False
            if g.get("completed"):
                date_to_match = g.get("completion_date") or g.get("end_date")
                if date_to_match:
                    date_to_match = date_to_match.split("T")[0]
                if date_to_match == target_str:
                    is_goal_on_date = True
            else:
                if g.get("end_date") == target_str:
                    is_goal_on_date = True
            
            if is_goal_on_date:
                status = "✓ " if g.get("completed") else "○ "
                details.append(f"{status}Goal: {g['title']}")
            
            # Check tasks
            for t in g.get("tasks", []):
                is_on_date = False
                if t.get("completed"):
                    date_to_match = t.get("completion_date") or t.get("end_date")
                    if date_to_match:
                        date_to_match = date_to_match.split("T")[0]
                    if date_to_match == target_str:
                        is_on_date = True
                else:
                    if t.get("end_date") == target_str:
                        is_on_date = True
                    elif t.get("recurrence", "none") != "none":
                        if self._is_on_date(target_date, t):
                            is_on_date = True
                
                if is_on_date:
                    status = "✓ " if t.get("completed") else "○ "
                    is_recurring = " 🔄" if t.get("recurrence", "none") != "none" else ""
                    details.append(f"{status}Task: {t['text']} ({g['title']}){is_recurring}")
        return details

    def _is_on_date(self, target_date, task):
        recurrence = task.get("recurrence")
        created_str = task.get("created_at")
        if not created_str: return False
        
        try:
            if "T" in created_str:
                created_date = datetime.strptime(created_str.split("T")[0], "%Y-%m-%d").date()
            else:
                created_date = datetime.strptime(created_str, "%Y-%m-%d").date()
        except:
            return False
            
        if target_date < created_date:
            return False
            
        task_end = None
        if task.get("end_date"):
            try:
                task_end = datetime.strptime(task["end_date"], "%Y-%m-%d").date()
            except: pass
            
        if task_end and target_date > task_end:
            return False
            
        if recurrence == "daily":
            return True
        elif recurrence == "monthly":
            return target_date.day == created_date.day
        elif recurrence == "weekly":
            days_str = task.get("recurrence_days", "")
            if not days_str: return False
            allowed_days = [int(d) for d in days_str.split(",") if d.strip()]
            return target_date.weekday() in allowed_days
            
        return False
