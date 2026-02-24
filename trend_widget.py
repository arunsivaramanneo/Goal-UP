"""Trend graph widget for Goal UP."""

import gi
import cairo
import math
from datetime import datetime, date, timedelta
from collections import defaultdict

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gdk


class TrendGraphWidget(Gtk.DrawingArea):
    """Widget that draws a line graph of completion trends over time."""

    def __init__(self):
        super().__init__()
        self.set_content_width(450)
        self.set_content_height(250)
        self.set_draw_func(self._draw_func)
        
        self._monthly_data = []  # List of (month_label, completed_count, total_count)
        self._style_context = self.get_style_context()

    def update_data(self, goals: list = None) -> None:
        """Update the trend graph with goal completion data."""
        if goals is None:
            goals = []
        
        self._monthly_data = self._calculate_monthly_trends(goals)
        self.queue_draw()

    def _calculate_monthly_trends(self, goals: list) -> list:
        """Calculate monthly completion trends from goals and their tasks."""
        monthly_stats = defaultdict(lambda: {"completed": 0, "total": 0})
        
        # Get current date and calculate range (last 12 months)
        today = date.today()
        months_back = 12
        current_date = today.replace(day=1)
        
        # Initialize all months in range with 0 values
        for i in range(months_back):
            month_date = current_date - timedelta(days=30 * i)
            month_key = month_date.strftime("%Y-%m")
            monthly_stats[month_key] = {"completed": 0, "total": 0}
        
        # Process goals
        for goal in goals:
            # Count goal tasks
            tasks = goal.get("tasks", [])
            goal_created_date = None
            
            # Try to parse goal's creation date as fallback
            try:
                if goal.get("created_at"):
                    goal_created_date = datetime.fromisoformat(goal["created_at"]).date()
            except (ValueError, AttributeError):
                pass
            
            for task in tasks:
                try:
                    # Determine which date to use for categorizing this task
                    task_date = None
                    
                    # For completed tasks, use completion date
                    if task.get("completed") and task.get("completion_date"):
                        task_date = datetime.fromisoformat(task["completion_date"]).date()
                    # For incomplete tasks, use goal's creation date if available
                    elif not task.get("completed") and goal_created_date:
                        task_date = goal_created_date
                    # Otherwise skip this task
                    else:
                        continue
                    
                    month_key = task_date.strftime("%Y-%m")
                    
                    # Only include if within our tracking range
                    if month_key in monthly_stats:
                        monthly_stats[month_key]["total"] += 1
                        if task.get("completed", False):
                            monthly_stats[month_key]["completed"] += 1
                except (ValueError, AttributeError, TypeError):
                    pass
        
        # Sort by month and create result list
        sorted_months = sorted(monthly_stats.keys(), reverse=False)
        result = []
        for month_key in sorted_months:
            stats = monthly_stats[month_key]
            month_date = datetime.strptime(month_key, "%Y-%m").date()
            month_label = month_date.strftime("%b %y")
            result.append((month_label, stats["completed"], stats["total"]))
        
        return result

    def _draw_func(self, area, cr: cairo.Context, width: int, height: int) -> None:
        """Draw the trend line graph."""
        padding = 40
        graph_width = width - 2 * padding
        graph_height = height - 2 * padding - 20
        
        # Get theme colors
        fg_color = self._style_context.get_color()
        
        # Draw background
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.05)
        cr.rectangle(padding, padding, graph_width, graph_height)
        cr.fill()
        
        # If no data, draw empty message
        if not self._monthly_data:
            cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(14)
            text = "No completion data yet"
            (tx, ty, tw, th, dx, dy) = cr.text_extents(text)
            cr.move_to(width / 2 - tw / 2 - tx, height / 2 + th / 2 - ty)
            cr.show_text(text)
            return
        
        # Calculate scales
        data_points = len(self._monthly_data)
        if data_points < 2:
            return
        
        # Find max value for Y scale
        max_value = max([total for _, _, total in self._monthly_data])
        if max_value == 0:
            max_value = 1
        
        x_step = graph_width / (data_points - 1) if data_points > 1 else 0
        y_scale = graph_height / max_value
        
        # Draw grid lines
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.2)
        cr.set_line_width(1.0)
        
        # Y-axis grid lines
        for i in range(int(max_value) + 1):
            y = padding + graph_height - (i * y_scale)
            cr.move_to(padding, y)
            cr.line_to(padding + graph_width, y)
            cr.stroke()
        
        # Draw axes
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.6)
        cr.set_line_width(2.5)
        cr.move_to(padding, padding + graph_height)
        cr.line_to(padding + graph_width, padding + graph_height)
        cr.stroke()
        
        cr.move_to(padding, padding)
        cr.line_to(padding, padding + graph_height)
        cr.stroke()
        
        # Draw Y-axis labels
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.7)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)
        
        for i in range(int(max_value) + 1):
            y = padding + graph_height - (i * y_scale)
            (tx, ty, tw, th, dx, dy) = cr.text_extents(str(i))
            cr.move_to(padding - tw - 8, y + th / 2 - ty)
            cr.show_text(str(i))
        
        # Prepare points for completed and total lines
        completed_points = []
        total_points = []
        
        for idx, (month_label, completed, total) in enumerate(self._monthly_data):
            x = padding + idx * x_step
            y_completed = padding + graph_height - (completed * y_scale)
            y_total = padding + graph_height - (total * y_scale)
            completed_points.append((x, y_completed))
            total_points.append((x, y_total))
        
        # Draw total line (Grey color)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)  # Grey
        cr.set_line_width(2.5)
        for i, (x, y) in enumerate(total_points):
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()
        
        # Draw completed line (green)
        cr.set_source_rgba(0.15, 0.68, 0.37, 0.8)  # Green
        cr.set_line_width(2.5)
        for i, (x, y) in enumerate(completed_points):
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()
        
        # Draw points on completed line
        cr.set_source_rgba(0.15, 0.68, 0.37, 0.9)
        cr.set_line_width(1.5)
        for x, y in completed_points:
            cr.new_path()
            cr.arc(x, y, 3, 0, 2 * math.pi)
            cr.fill()
        
        # Draw points on total line
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
        for x, y in total_points:
            cr.new_path()
            cr.arc(x, y, 3, 0, 2 * math.pi)
            cr.fill()
        
        # Draw X-axis labels (every 2nd month to avoid crowding)
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.7)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)
        
        label_step = max(1, data_points // 6)  # Show max 6 labels
        for idx in range(0, data_points, label_step):
            if idx < len(self._monthly_data):
                month_label = self._monthly_data[idx][0]
                x = padding + idx * x_step
                (tx, ty, tw, th, dx, dy) = cr.text_extents(month_label)
                cr.move_to(x - tw / 2 - tx, padding + graph_height + 20)
                cr.show_text(month_label)
        
        # Draw legend
        legend_y = padding + graph_height + 35
        
        # Green square for completed
        cr.set_source_rgba(0.15, 0.68, 0.37, 0.9)
        cr.rectangle(padding, legend_y, 10, 10)
        cr.fill()
        
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.8)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)
        (tx, ty, tw, th, dx, dy) = cr.text_extents("Completed")
        cr.move_to(padding + 16, legend_y + 8 - ty)
        cr.show_text("Completed")
        
        # Grey square for total
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
        cr.rectangle(padding + 120, legend_y, 10, 10)
        cr.fill()
        
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.8)
        (tx, ty, tw, th, dx, dy) = cr.text_extents("Pending")
        cr.move_to(padding + 136, legend_y + 8 - ty)
        cr.show_text("Pending")
