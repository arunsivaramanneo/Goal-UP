"""Graphical summary widget for Goal UP."""

import math
import gi
import cairo
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
                cr.set_line_width(0.8)
                cr.set_source_rgba(0, 0, 0, 0.15) if self._luminance(base_color) > 0.6 else cr.set_source_rgba(1, 1, 1, 0.12)
                cr.stroke()
                cc = sum(1 for t in goal.get("tasks", []) if t.get("completed"))
                if cc > 0:
                    gp = cc / task_count
                    or_, og, ob = self._goal_completed_color
                    sr, sg, sb, sa = (0,0,0,0.6) if self._luminance((or_, og, ob)) > 0.75 else (1,1,1,0.8)
                    cr.new_path(); cr.arc(center_x, center_y, radius * 0.9, current_angle, current_angle + angle_span * gp)
                    cr.arc(center_x, center_y, radius * 0.55, current_angle + angle_span * gp, current_angle); cr.close_path()
                    cr.set_source_rgba(or_, og, ob, 0.95); cr.fill_preserve()
                    cr.set_line_width(1.0); cr.set_source_rgba(sr, sg, sb, sa); cr.stroke()
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
            cr.set_source_rgb(*remaining_color); cr.fill_preserve(); cr.set_line_width(0.8)
            cr.set_source_rgba(0,0,0,0.12) if self._luminance(remaining_color) > 0.6 else cr.set_source_rgba(1,1,1,0.12); cr.stroke()
            self._last_task_slices.append({"center_x": center_x, "center_y": center_y, "outer_r": radius, "inner_r": inner_r, "start": rs, "end": re, "kind": "remaining", "value": total - completed, "total": total})
        if pc > 0:
            cs, ce = sa, sa + pc * 2 * math.pi
            cr.new_path(); cr.arc(center_x, center_y, radius, cs, ce); cr.arc(center_x, center_y, inner_r, ce, cs); cr.close_path()
            cr.set_source_rgb(*completed_color); cr.fill_preserve(); cr.set_line_width(0.8)
            cr.set_source_rgba(0,0,0,0.12) if self._luminance(completed_color) > 0.6 else cr.set_source_rgba(1,1,1,0.12); cr.stroke()
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


class GoalTrendWidget(Gtk.DrawingArea):
    """Widget that draws the monthly completion trend bar chart."""

    def __init__(self):
        super().__init__()
        self.set_content_width(300)
        self.set_content_height(400)
        self.set_draw_func(self._draw_func)
        self._goals = []
        self._style_context = self.get_style_context()

    def update_data(self, goals):
        self._goals = goals
        self.queue_draw()

    def _draw_func(self, area, cr, width, height):
        self._draw_monthly_bar_chart(cr, 10, 20, width - 20, height - 40)

    def _draw_monthly_bar_chart(self, cr, x, y, width, height):
        monthly_data = self._calculate_monthly_data()
        if not monthly_data: return
        
        # Get last 12 months
        sorted_keys = sorted(monthly_data.keys())
        months = sorted_keys[-12:] if len(sorted_keys) >= 12 else sorted_keys
        
        scale_max = max([max(monthly_data[mk]['total'], monthly_data[mk]['completed']) for mk in months] + [1])
        fg = self._style_context.get_color()
        cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL); cr.set_font_size(12)
        txt = "Monthly Completions"; (tx, ty, tw, th, dx, dy) = cr.text_extents(txt)
        cr.move_to(x + width/2 - tw/2 - tx, y - 5); cr.show_text(txt)
        
        ax, ay, cw, ch = x + 30, y + 20, width - 40, height - 60
        cr.set_line_width(1); cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.5)
        cr.move_to(ax, ay); cr.line_to(ax, ay + ch); cr.line_to(ax + cw, ay + ch); cr.stroke()
        
        if months:
            bw, bs = (cw / len(months) * 0.7), (cw / len(months))
            for i, mk in enumerate(months):
                d = monthly_data[mk]; c, t = d['completed'], d['total']
                th_, ch_ = (t / scale_max) * ch, (c / scale_max) * ch
                bx = ax + i * bs + (bs - bw) / 2
                
                # Draw total bar (light gray)
                cr.set_source_rgba(0.85, 0.85, 0.85, 0.9)
                cr.rectangle(bx, ay + ch - th_, bw, th_)
                cr.fill()
                
                # Draw completed bar (green) overlapping
                cr.set_source_rgb(0.15, 0.68, 0.37)
                cr.rectangle(bx, ay + ch - ch_, bw, ch_)
                cr.fill()
                
                # Draw month labels (rotated)
                cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.9); cr.set_font_size(10)
                try: ms = datetime.strptime(mk, '%Y-%m').strftime('%b')
                except: ms = mk
                (tx, ty, tw_, th, dx, dy) = cr.text_extents(ms)
                
                cr.save()
                cr.move_to(bx + bw/2 + th/2, ay + ch + 10)
                cr.rotate(math.pi / 2)
                cr.show_text(ms)
                cr.restore()
                
                # Draw values
                if t > 0:
                    vs = f"{int(c)}/{int(t)}"
                    cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
                    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); cr.set_font_size(8)
                    (tx, ty, tw_, th, dx, dy) = cr.text_extents(vs)
                    cr.move_to(bx + bw/2 - tw_/2 - tx, ay + ch - max(th_, ch_) - 5)
                    cr.show_text(vs)
            
            # Draw Legend
            lx, ly = ax + cw - 120, y - 5
            
            # Completed legend
            cr.set_source_rgb(0.15, 0.68, 0.37)
            cr.rectangle(lx, ly, 10, 10)
            cr.fill()
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.8)
            cr.set_font_size(10)
            cr.move_to(lx + 15, ly + 9)
            cr.show_text("Completed")
            
            # Total/Pending legend
            cr.set_source_rgba(0.85, 0.85, 0.85, 0.9)
            cr.rectangle(lx + 70, ly, 10, 10)
            cr.fill()
            cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.8)
            cr.move_to(lx + 85, ly + 9)
            cr.show_text("Pending")

    def _calculate_monthly_data(self):
        monthly = defaultdict(lambda: {'completed': 0, 'total': 0})
        
        # Ensure last 12 months exist in data
        today = date.today()
        for i in range(12):
            m = (today.month - i - 1) % 12 + 1
            y = today.year + (today.month - i - 1) // 12
            mk = f"{y}-{m:02}"
            monthly[mk] = {'completed': 0, 'total': 0}

        for g in self._goals:
            cd, ed = g.get('completion_date', ''), g.get('end_date', '')
            if cd:
                try:
                    mk = datetime.strptime(cd, '%Y-%m-%d').strftime('%Y-%m')
                    monthly[mk]['completed'] += 1; monthly[mk]['total'] += 1
                except: pass
            elif ed:
                try:
                    mk = datetime.strptime(ed, '%Y-%m-%d').strftime('%Y-%m')
                    monthly[mk]['total'] += 1
                except: pass
            for t in g.get('tasks', []):
                tc, tcs, tes = t.get('completed'), t.get('completion_date') or '', t.get('end_date') or ''
                if tc:
                    ds = tcs or tes or cd or ed
                    if ds:
                        try:
                            mk = datetime.strptime(ds, '%Y-%m-%d').strftime('%Y-%m')
                            monthly[mk]['completed'] += 1; monthly[mk]['total'] += 1
                        except: pass
                else:
                    ds = tes or ed
                    if ds:
                        try:
                            mk = datetime.strptime(ds, '%Y-%m-%d').strftime('%Y-%m')
                            monthly[mk]['total'] += 1
                        except: pass
        return dict(sorted(monthly.items()))


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
        
        overdue = []
        upcoming = [] # List of (date, text) tuples
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
                            upcoming.append((d, f"Goal: {g['title']}"))
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
                                upcoming.append((d, f"{label_prefix} {t['text']} ({g['title']}){recur_sym}"))
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
                # Project future recurring task instances
                if is_recurring:
                    try:
                        # Determine starting point for projection: task creation or today
                        created_str = t.get("created_at")
                        if created_str:
                            # Handle potential ISO format with T separator or just date
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

                        # Projection loop starting from created_at
                        # We calculate all occurrences and only show those in the upcoming week
                        projection_date = start_date - timedelta(days=1)
                        found_count = 0
                        
                        while True:
                            next_date = self._calculate_next_date(projection_date, t.get("recurrence"), t.get("recurrence_days"))
                            
                            # Break if logic fails or we passed both the task end and the week boundary
                            if not next_date: break
                            if next_date > week_later: break
                            if task_end and next_date > task_end: break

                            # Only show occurrences from today onwards
                            if next_date >= today:
                                if not t.get("completed") or next_date > today: # Show today's if incomplete
                                    # Avoid duplicates
                                    exists = any(u[0] == next_date and t['text'] in u[1] for u in upcoming)
                                    if not exists:
                                        upcoming.append((next_date, f"{label_prefix} {t['text']} ({g['title']}){recur_sym}"))
                                        found_count += 1
                                        
                                        # Limit daily as requested
                                        if t.get("recurrence") == "daily":
                                            break
                            
                            projection_date = next_date
                            # Safety break to prevent infinite loops if logic has bugs
                            if projection_date > week_later + timedelta(days=365): break

                    except Exception as e:
                        print(f"Error projecting recurring task: {e}")

        # Add "Overdue" section
        if overdue:
            self._add_header("Overdue", "error")
            for item in overdue:
                self._add_item(item, "error")

        # Add "Upcoming this week" section
        if upcoming:
            upcoming.sort(key=lambda x: x[0]) # Sort by date
            self._add_header("Upcoming Week", "accent")
            for d, text in upcoming:
                # Format: ddd - notification
                date_str = d.strftime("%a")
                self._add_item(f"{date_str} - {text}")

        # Alert if no progress
        if not any_completed_recently and self._goals:
            self._add_header("Alert", "warning")
            self._add_item("No progress made in the last week!", "warning")

        if not overdue and not upcoming and (any_completed_recently or not self._goals):
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

