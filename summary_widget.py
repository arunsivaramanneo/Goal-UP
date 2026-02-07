"""Graphical summary widget for Goal UP."""

import math
import gi
import cairo
from datetime import datetime, date, timedelta
from collections import defaultdict

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gdk, GObject

class GoalSummaryWidget(Gtk.DrawingArea):
    """Widget that draws a circular progress summary of goals."""

    def __init__(self):
        super().__init__()
        self.set_content_width(450)
        self.set_content_height(950)
        self.set_draw_func(self._draw_func)
        
        self._completed_goals = 0
        self._total_goals = 0
        self._completed_tasks = 0
        self._total_tasks = 0
        
        # Style context for colors
        self._style_context = self.get_style_context()

        # Completed-task color for goal insets (shared across all goals)
        self._goal_completed_color = (0.15, 0.68, 0.37)  # green, same as Tasks completed color by default

        # Track last-drawn slice geometry for hover tooltips
        self._last_goal_slices = []  # list of dicts: center_x, center_y, inner_r, outer_r, start, end, goal, task_count, completed_count, percent
        self._last_task_slices = []  # same structure for tasks pie

        # Motion controller for hover tooltips
        self._motion = Gtk.EventControllerMotion()
        self._motion.connect("motion", self._on_motion)
        self._motion.connect("enter", self._on_pointer_enter)
        self._motion.connect("leave", self._on_pointer_leave)
        self.add_controller(self._motion)
        self.set_has_tooltip(True)

    def update_status(self, completed_goals: int, total_goals: int, completed_tasks: int, total_tasks: int, goals: list = None) -> None:
        """Update the progress status."""
        self._completed_goals = completed_goals
        self._total_goals = total_goals
        self._completed_tasks = completed_tasks
        self._total_tasks = total_tasks
        self._goals = goals or []
        self.queue_draw()

    def _draw_func(self, area, cr: cairo.Context, width: int, height: int) -> None:
        """Draw the progress chart."""
        # Split into three areas: pie charts and bar chart
        center_x = width / 2
        top_center_y = height * 0.15
        bottom_pie_y = height * 0.45
        
        pie_radius = 100
        
        # Calculate total tasks across all goals (denominator for left chart)
        total_tasks_all_goals = 0
        for g in self._goals:
             total_tasks_all_goals += len(g.get("tasks", []))

        # Draw Goals Pie Chart (Top)
        self._draw_goals_pie(cr, center_x, top_center_y, pie_radius, 
                             self._goals, total_tasks_all_goals, "Goals")

        # Draw Tasks Pie Chart (Below goals)
        self._draw_pie(cr, center_x, bottom_pie_y, pie_radius, 
                       self._completed_tasks, self._total_tasks, 
                       (0.15, 0.68, 0.37), (0.9, 0.4, 0.2), "Tasks")

        # Draw Monthly Bar Chart (Bottom)
        bar_chart_y = height * 0.65
        bar_chart_height = height * 0.35
        bar_chart_x = 20
        bar_chart_width = width - 40
        self._draw_monthly_bar_chart(cr, bar_chart_x, bar_chart_y, bar_chart_width, bar_chart_height)

    def _parse_color(self, color_str: str) -> tuple:
        """Parse a CSS color string into a (r, g, b) tuple scaled 0.0-1.0.

        Supports formats produced by the color picker (e.g. "rgb(r,g,b)" or "rgba(r,g,b,a)"),
        hex strings ("#rrggbb"), named colors and anything that Gdk.RGBA.parse() accepts.
        If values are in 0-255 range they will be normalized to 0-1 for Cairo.
        """
        if not color_str:
            return (0.5, 0.5, 0.5)  # Default Gray

        color_str = color_str.strip()

        # Handle 'rgb(r,g,b)' and 'rgba(r,g,b,a)'
        if (color_str.startswith("rgb(") or color_str.startswith("rgba(")) and color_str.endswith(")"):
            try:
                inside = color_str[color_str.find("(") + 1: color_str.rfind(")")]
                parts = [p.strip() for p in inside.split(",")]
                if len(parts) >= 3:
                    r = float(parts[0])
                    g = float(parts[1])
                    b = float(parts[2])

                    def norm(v: float) -> float:
                        # If value seems like 0-255 integers, normalize; else assume already 0-1
                        if v > 1.0:
                            return max(0.0, min(1.0, v / 255.0))
                        return max(0.0, min(1.0, v))

                    return (norm(r), norm(g), norm(b))
            except Exception:
                return (0.5, 0.5, 0.5)

        # Fallback to Gdk.RGBA parsing (handles hex and named colors)
        c = Gdk.RGBA()
        if c.parse(color_str):
            return (c.red, c.green, c.blue)

        return (0.5, 0.5, 0.5)

    def _luminance(self, rgb: tuple) -> float:
        """Return perceived luminance of an RGB tuple (0..1)."""
        r, g, b = rgb
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _point_angle(self, cx: float, cy: float, x: float, y: float) -> float:
        """Return angle in radians from center to point, normalized 0..2pi."""
        ang = math.atan2(y - cy, x - cx)
        if ang < 0:
            ang += 2 * math.pi
        return ang

    def _angle_in_range(self, angle: float, start: float, end: float) -> bool:
        """Return True if angle is within the start..end arc (angles in 0..2pi), handling wrap."""
        # Normalize to 0..2pi
        s = start % (2 * math.pi)
        e = end % (2 * math.pi)
        a = angle % (2 * math.pi)
        if s <= e:
            return s <= a <= e
        else:
            # wrapped around 2pi
            return a >= s or a <= e

    def _distance(self, cx: float, cy: float, x: float, y: float) -> float:
        return math.hypot(x - cx, y - cy)

    def _on_pointer_enter(self, controller, x: float, y: float) -> None:
        """Called when pointer enters; forward to motion handler to show tooltip immediately."""
        try:
            self._on_motion(controller, x, y)
        except Exception:
            pass

    def _on_pointer_leave(self, controller, *args) -> None:
        """Clear tooltip when leaving widget."""
        try:
            self.set_tooltip_text(None)
        except Exception:
            pass

    def _on_motion(self, controller, x: float, y: float) -> None:
        """Handle motion events over the drawing area and show contextual tooltips."""
        # First check goals slices
        for s in getattr(self, "_last_goal_slices", []):
            d = self._distance(s["center_x"], s["center_y"], x, y)
            if s["inner_r"] <= d <= s["outer_r"]:
                ang = self._point_angle(s["center_x"], s["center_y"], x, y)
                if self._angle_in_range(ang, s["start"], s["end"]):
                    g = s.get("goal")
                    task_count = s.get("task_count", 0)
                    completed = s.get("completed_count", 0)
                    pct_goal = int((completed / task_count) * 100) if task_count > 0 else 0
                    pct_share = int(s.get("percent", 0) * 100)
                    title = g.get("title", g.get("text", "Untitled")) if g else "Goal"
                    tooltip = f"{title}\nTasks: {completed}/{task_count} ({pct_goal}% complete)\nShare of total: {pct_share}%"
                    self.set_tooltip_text(tooltip)
                    return
        # Then check task pie slices
        for s in getattr(self, "_last_task_slices", []):
            d = self._distance(s["center_x"], s["center_y"], x, y)
            if s["inner_r"] <= d <= s["outer_r"]:
                ang = self._point_angle(s["center_x"], s["center_y"], x, y)
                if self._angle_in_range(ang, s["start"], s["end"]):
                    kind = s.get("kind")
                    val = s.get("value")
                    total = s.get("total")
                    pct = int((val / total) * 100) if total > 0 else 0
                    if kind == "completed":
                        tooltip = f"Completed: {val}/{total} ({pct}%)"
                    else:
                        tooltip = f"Remaining: {val}/{total} ({pct}%)"
                    self.set_tooltip_text(tooltip)
                    return
        # If nothing found, clear tooltip
        try:
            self.set_tooltip_text(None)
        except Exception:
            pass

    def _overlay_color(self, rgb: tuple) -> tuple:
        """Generate an overlay (lighter) RGBA color and a contrasting stroke color.

        Returns (r, g, b, a, stroke_r, stroke_g, stroke_b, stroke_a)
        """
        r, g, b = rgb
        # Mix with white to get a light, pastel overlay
        def mix_with_white(c, f=0.6):
            return max(0.0, min(1.0, c * (1 - f) + 1.0 * f))

        or_, og, ob = mix_with_white(r), mix_with_white(g), mix_with_white(b)
        oa = 0.9

        # Choose stroke color (contrast with overlay brightness)
        avg = (or_ + og + ob) / 3.0
        if avg > 0.75:
            # overlay is very light, use semi-transparent black for stroke
            sr, sg, sb, sa = 0.0, 0.0, 0.0, 0.6
        else:
            # overlay is mid/dark, use semi-transparent white
            sr, sg, sb, sa = 1.0, 1.0, 1.0, 0.8

        return (or_, og, ob, oa, sr, sg, sb, sa)

    def _draw_goals_pie(self, cr: cairo.Context, center_x: float, center_y: float, radius: float, 
                        goals: list, total_tasks: int, label: str) -> None:
        """Draw the goals pie chart based on task distribution."""
        
        start_angle = -math.pi / 2
        
        # If no tasks at all, draw a placeholder donut
        if total_tasks == 0:
            outer_r = radius
            inner_r = radius * 0.5
            cr.new_path()
            cr.arc(center_x, center_y, outer_r, 0, 2 * math.pi)
            cr.arc(center_x, center_y, inner_r, 2 * math.pi, 0)
            cr.close_path()
            cr.set_source_rgb(0.85, 0.85, 0.85)  # Light gray donut
            cr.fill()
        else:
            # reset previous geometry
            self._last_goal_slices = []
            current_angle = start_angle
            for goal in goals:
                task_count = len(goal.get("tasks", []))
                if task_count == 0:
                    continue

                percent = task_count / total_tasks
                angle_span = percent * 2 * math.pi
                end_angle = current_angle + angle_span

                # Get Color
                base_color = self._parse_color(goal.get("color", ""))

                # Draw donut slice (outer arc and inner arc reversed)
                outer_r = radius
                inner_r = radius * 0.5

                cr.new_path()
                cr.arc(center_x, center_y, outer_r, current_angle, end_angle)
                cr.arc(center_x, center_y, inner_r, end_angle, current_angle)
                cr.close_path()

                cr.set_source_rgb(*base_color)
                cr.fill_preserve()

                # store geometry for hover
                self._last_goal_slices.append({
                    "center_x": center_x,
                    "center_y": center_y,
                    "outer_r": outer_r,
                    "inner_r": inner_r,
                    "start": current_angle,
                    "end": end_angle,
                    "goal": goal,
                    "task_count": task_count,
                    "completed_count": sum(1 for t in goal.get("tasks", []) if t.get("completed", False)),
                    "percent": percent
                })
                # Subtle stroke to separate slices
                cr.set_line_width(0.8)
                # use translucent white or black depending on luminance to give separation in both themes
                if self._luminance(base_color) > 0.6:
                    cr.set_source_rgba(0, 0, 0, 0.15)
                else:
                    cr.set_source_rgba(1, 1, 1, 0.12)
                cr.stroke()

                # Draw completed progress INSIDE the slice as an inset ring if some tasks are completed
                completed_count = sum(1 for t in goal.get("tasks", []) if t.get("completed", False))
                if completed_count > 0 and task_count > 0:
                    goal_progress = completed_count / task_count
                    if goal_progress > 0:
                        # Use shared completed color for inset instead of a tinted variant of the goal color
                        overlay_r, overlay_g, overlay_b = self._goal_completed_color
                        overlay_a = 0.95

                        # Choose stroke color based on luminance of the overlay color for contrast
                        if self._luminance((overlay_r, overlay_g, overlay_b)) > 0.75:
                            sr, sg, sb, sa = 0.0, 0.0, 0.0, 0.6
                        else:
                            sr, sg, sb, sa = 1.0, 1.0, 1.0, 0.8

                        # Place overlay inside the ring (inset)
                        overlay_outer = radius * 0.9
                        overlay_inner = radius * 0.55

                        start = current_angle
                        end_overlay = current_angle + angle_span * goal_progress

                        # Create ring segment path (outer arc then inner arc reversed)
                        cr.new_path()
                        cr.arc(center_x, center_y, overlay_outer, start, end_overlay)
                        cr.arc(center_x, center_y, overlay_inner, end_overlay, start)
                        cr.close_path()

                        cr.set_source_rgba(overlay_r, overlay_g, overlay_b, overlay_a)
                        cr.fill_preserve()

                        # Stroke with contrasting color to make it visible on both light/dark backgrounds
                        cr.set_line_width(1.0)
                        cr.set_source_rgba(sr, sg, sb, sa)
                        cr.stroke()

                current_angle = end_angle

        # Draw center completion indicator (donut hole)
        # Compute overall goals completion % for center display
        try:
            pct_goals = int((self._completed_goals / self._total_goals) * 100) if self._total_goals > 0 else 0
        except Exception:
            pct_goals = 0

        # Pick a contrasting center fill based on current text color
        fg_color = self._style_context.get_color()
        fg_lum = 0.2126 * fg_color.red + 0.7152 * fg_color.green + 0.0722 * fg_color.blue
        if fg_lum > 0.5:
            # light text => dark center
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.75)
        else:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)

        # inner_r was defined when drawing donut; use it and inset slightly
        center_inner = inner_r - 6
        if center_inner < 8:
            center_inner = inner_r * 0.8

        cr.new_path()
        cr.arc(center_x, center_y, center_inner, 0, 2 * math.pi)
        cr.fill()

        # Draw percentage text on top of the center circle
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        # Use theme foreground for text (contrasts with chosen center background)
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
        pct_text = f"{pct_goals}%"
        (tx, ty, tw, th, dx, dy) = cr.text_extents(pct_text)
        cr.move_to(center_x - tw / 2 - tx, center_y + th / 2 - ty)
        cr.show_text(pct_text)

        # Label (below)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)

        full_label = f"{label}: {self._completed_goals}/{self._total_goals}"  # Keep the "Goals: X/Y" text for context
        cr.set_font_size(16)
        (lx, ly, l_width, l_height, ldx, ldy) = cr.text_extents(full_label)
        cr.move_to(center_x - l_width / 2 - lx, center_y + radius + 30)
        cr.show_text(full_label)

        # Label (below)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        fg_color = self._style_context.get_color()
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
        
        full_label = f"{label}: {self._completed_goals}/{self._total_goals}" # Keep the "Goals: X/Y" text for context
        cr.set_font_size(16)
        (lx, ly, l_width, l_height, ldx, ldy) = cr.text_extents(full_label)
        cr.move_to(center_x - l_width / 2 - lx, center_y + radius + 30)
        cr.show_text(full_label)

    def _draw_pie(self, cr: cairo.Context, center_x: float, center_y: float, radius: float, 
                  completed: int, total: int, completed_color: tuple, remaining_color: tuple, label: str) -> None:
        """Draw a single pie chart with legend."""
        
        # Calculate Percentage
        if total > 0:
            percent_complete = completed / total
        else:
            percent_complete = 0.0
            
        start_angle = -math.pi / 2
        
        remaining_angle_span = (1.0 - percent_complete) * 2 * math.pi
        completed_angle_span = percent_complete * 2 * math.pi
        
        split_angle = start_angle + completed_angle_span
        
        outer_r = radius
        inner_r = radius * 0.5

        # reset previous geometry
        self._last_task_slices = []

        # 1. Remaining Slice
        if percent_complete < 1.0:
            rem_start = split_angle
            rem_end = start_angle + 2 * math.pi
            cr.new_path()
            cr.arc(center_x, center_y, outer_r, rem_start, rem_end)
            cr.arc(center_x, center_y, inner_r, rem_end, rem_start)
            cr.close_path()
            cr.set_source_rgb(*remaining_color)
            cr.fill_preserve()

            # subtle stroke
            cr.set_line_width(0.8)
            if self._luminance(remaining_color) > 0.6:
                cr.set_source_rgba(0, 0, 0, 0.12)
            else:
                cr.set_source_rgba(1, 1, 1, 0.12)
            cr.stroke()

            # store geometry
            self._last_task_slices.append({
                "center_x": center_x,
                "center_y": center_y,
                "outer_r": outer_r,
                "inner_r": inner_r,
                "start": rem_start,
                "end": rem_end,
                "kind": "remaining",
                "value": int((1.0 - percent_complete) * total),
                "total": total
            })

        # 2. Completed Slice
        if percent_complete > 0:
            comp_start = start_angle
            comp_end = split_angle
            cr.new_path()
            cr.arc(center_x, center_y, outer_r, comp_start, comp_end)
            cr.arc(center_x, center_y, inner_r, comp_end, comp_start)
            cr.close_path()
            cr.set_source_rgb(*completed_color)
            cr.fill_preserve()

            # subtle stroke
            cr.set_line_width(0.8)
            if self._luminance(completed_color) > 0.6:
                cr.set_source_rgba(0, 0, 0, 0.12)
            else:
                cr.set_source_rgba(1, 1, 1, 0.12)
            cr.stroke()

            # store geometry
            self._last_task_slices.append({
                "center_x": center_x,
                "center_y": center_y,
                "outer_r": outer_r,
                "inner_r": inner_r,
                "start": comp_start,
                "end": comp_end,
                "kind": "completed",
                "value": completed,
                "total": total
            })


        # Draw center completion indicator (donut hole for tasks)
        try:
            pct_tasks = int(percent_complete * 100)
        except Exception:
            pct_tasks = 0

        fg_color = self._style_context.get_color()
        fg_lum = 0.2126 * fg_color.red + 0.7152 * fg_color.green + 0.0722 * fg_color.blue
        if fg_lum > 0.5:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.75)
        else:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)

        center_inner = inner_r - 6
        if center_inner < 8:
            center_inner = inner_r * 0.8

        cr.new_path()
        cr.arc(center_x, center_y, center_inner, 0, 2 * math.pi)
        cr.fill()

        # Percentage text
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
        pct_text = f"{pct_tasks}%"
        (tx, ty, tw, th, dx, dy) = cr.text_extents(pct_text)
        cr.move_to(center_x - tw / 2 - tx, center_y + th / 2 - ty)
        cr.show_text(pct_text)

        # 3. Label and Count (below)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
        
        full_label = f"{label}: {completed}/{total}"
        cr.set_font_size(16)
        (lx, ly, l_width, l_height, ldx, ldy) = cr.text_extents(full_label)
        cr.move_to(center_x - l_width / 2 - lx, center_y + radius + 30)
        cr.show_text(full_label)

    def _draw_monthly_bar_chart(self, cr: cairo.Context, x: float, y: float, width: float, height: float) -> None:
        """Draw a bar chart showing monthly completion trends."""
        # Calculate monthly data
        monthly_data = self._calculate_monthly_data()
        
        if not monthly_data:
            # No data to display
            return

        # Get the last 6 months of data
        months = list(monthly_data.keys())[-6:]
        max_total = max([monthly_data[m].get('total', 0) for m in months], default=1)
        max_completed = max([monthly_data[m].get('completed', 0) for m in months], default=0)
        # Use the larger of total/completed for scaling
        scale_max = max(max_total, max_completed, 1)
        
        # Draw title
        fg_color = self._style_context.get_color()
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(12)
        title_text = "Monthly Completions"
        (tx, ty, tw, th, dx, dy) = cr.text_extents(title_text)
        title_x = x + width / 2 - tw / 2 - tx  # Center the title
        cr.move_to(title_x, y - 10)
        cr.show_text(title_text)
        
        # Chart area and axes
        axis_x = x + 40
        axis_y = y + height - 30
        chart_width = width - 60
        chart_height = height - 60

        # Draw Y axis
        cr.set_line_width(1)
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.5)
        cr.move_to(axis_x, axis_y)
        cr.line_to(axis_x, y + 10)
        cr.stroke()

        # Draw X axis
        cr.move_to(axis_x, axis_y)
        cr.line_to(axis_x + chart_width, axis_y)
        cr.stroke()

        # Draw bars (single completed bar per month)
        if len(months) > 0:
            bar_width = chart_width / len(months) * 0.7
            bar_spacing = chart_width / len(months)

            for i, month_key in enumerate(months):
                month_data = monthly_data[month_key]
                completed = month_data['completed']

                # Calculate bar height
                if max_completed > 0:
                    bar_height = (completed / max_completed) * (chart_height - 20)
                else:
                    bar_height = 0

                # Draw bar
                bar_x = axis_x + i * bar_spacing + (bar_spacing - bar_width) / 2
                bar_y = axis_y - bar_height

                # Green bar for completed
                cr.set_source_rgb(0.15, 0.68, 0.37)
                cr.rectangle(bar_x, bar_y, bar_width, bar_height)
                cr.fill()

                # Draw month label
                cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.7)
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(10)
                # Format month key "2026-02" as "Feb 26"
                try:
                    date_obj = datetime.strptime(month_key, '%Y-%m')
                    month_str = date_obj.strftime('%b %y')  # e.g., "Feb 26"
                except (ValueError, AttributeError):
                    month_str = month_key
                (tx, ty, tw, th, dx, dy) = cr.text_extents(month_str)
                cr.move_to(bar_x + bar_width / 2 - tw / 2 - tx, axis_y + 15)
                cr.show_text(month_str)

                # Draw value on top of bar
                if completed > 0:
                    cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
                    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                    cr.set_font_size(9)
                    val_str = str(int(completed))
                    (tx, ty, tw, th, dx, dy) = cr.text_extents(val_str)
                    cr.move_to(bar_x + bar_width / 2 - tw / 2 - tx, bar_y - 5)
                    cr.show_text(val_str)

    def _calculate_monthly_data(self) -> dict:
        """Calculate monthly completion data from goals.
        
        Returns a dict with keys as "YYYY-MM" and values as dicts with 'completed' count.
        """
        monthly = defaultdict(lambda: {'completed': 0})
        
        for goal in self._goals:
            completion_date_str = goal.get('completion_date', '')
            if completion_date_str:
                try:
                    # Parse completion date
                    comp_date = datetime.strptime(completion_date_str, '%Y-%m-%d').date()
                    month_key = comp_date.strftime('%Y-%m')
                    monthly[month_key]['completed'] += 1
                except (ValueError, AttributeError):
                    pass
            
            # Also count completed tasks
            for task in goal.get('tasks', []):
                if task.get('completed', False):
                    # Try to get task completion date, or use goal's completion date
                    task_date_str = task.get('completion_date', completion_date_str)
                    if task_date_str:
                        try:
                            task_date = datetime.strptime(task_date_str, '%Y-%m-%d').date()
                            month_key = task_date.strftime('%Y-%m')
                            monthly[month_key]['completed'] += 1
                        except (ValueError, AttributeError):
                            pass
        
        return dict(sorted(monthly.items()))

    def _draw_slice_text(self, cr: cairo.Context, x: float, y: float, text: str) -> None:
        """Helper to draw text centered at x, y."""
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(14)
        # White text usually looks good on colors
        cr.set_source_rgb(1, 1, 1) 
        
        (tx, ty, width, height, dx, dy) = cr.text_extents(text)
        cr.move_to(x - width / 2 - tx, y + height / 2 - ty)
        cr.show_text(text)
