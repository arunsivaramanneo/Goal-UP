"""Graphical summary widget for Goal UP."""

import math
import gi
import cairo

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gdk, GObject

class GoalSummaryWidget(Gtk.DrawingArea):
    """Widget that draws a circular progress summary of goals."""

    def __init__(self):
        super().__init__()
        self.set_content_width(200)
        self.set_content_height(180)
        self.set_draw_func(self._draw_func)
        
        self._completed_goals = 0
        self._total_goals = 0
        self._completed_tasks = 0
        self._total_tasks = 0
        
        # Style context for colors
        self._style_context = self.get_style_context()

    def update_status(self, completed_goals: int, total_goals: int, completed_tasks: int, total_tasks: int) -> None:
        """Update the progress status."""
        self._completed_goals = completed_goals
        self._total_goals = total_goals
        self._completed_tasks = completed_tasks
        self._total_tasks = total_tasks
        self.queue_draw()

    def _draw_func(self, area, cr: cairo.Context, width: int, height: int) -> None:
        """Draw the progress chart."""
        self._draw_ring(cr, width, height, is_inner=False)
        self._draw_ring(cr, width, height, is_inner=True)
        self._draw_text(cr, width, height)

    def _draw_ring(self, cr: cairo.Context, width: int, height: int, is_inner: bool) -> None:
        center_x = width / 2
        center_y = height / 2
        line_width = 10
        margin = 10
        
        if is_inner:
            radius = (min(width, height) / 2) - line_width - margin - 15  # Smaller radius
            total = self._total_tasks
            completed = self._completed_tasks
            base_color = (0.9, 0.4, 0.2) # Orange for tasks
        else:
            radius = (min(width, height) / 2) - margin
            total = self._total_goals
            completed = self._completed_goals
            base_color = (0.2, 0.5, 0.8) # Blue for goals

        # Background circle (dimmed)
        cr.set_line_width(line_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        
        # Get theme colors
        fg_color = self._style_context.get_color()
        
        # Draw background track
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, 0.1)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()
        
        # Draw progress arc
        if total > 0:
            percentage = completed / total
            angle = percentage * 2 * math.pi
            
            # Start from top (-90 degrees or -pi/2)
            start_angle = -math.pi / 2
            end_angle = start_angle + angle
            
            # Use specific color
            cr.set_source_rgb(*base_color)
                
            cr.arc(center_x, center_y, radius, start_angle, end_angle)
            cr.stroke()

    def _draw_text(self, cr: cairo.Context, width: int, height: int) -> None:
        center_x = width / 2
        center_y = height / 2
        fg_color = self._style_context.get_color()
        
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        
        # Goals Text
        cr.set_font_size(14)
        goals_text = f"Goals: {self._completed_goals}/{self._total_goals}"
        (gx, gy, g_width, g_height, gdx, gdy) = cr.text_extents(goals_text)
        
        # Tasks Text
        tasks_text = f"Tasks: {self._completed_tasks}/{self._total_tasks}"
        (tx, ty, t_width, t_height, tdx, tdy) = cr.text_extents(tasks_text)
        
        # Draw Goals text above center
        cr.move_to(center_x - g_width / 2 - gx, center_y - 5)
        cr.set_source_rgb(0.2, 0.5, 0.8) # Blue
        cr.show_text(goals_text)
        
        # Draw Tasks text below center
        cr.move_to(center_x - t_width / 2 - tx, center_y + t_height + 5)
        cr.set_source_rgb(0.9, 0.4, 0.2) # Orange
        cr.show_text(tasks_text)
