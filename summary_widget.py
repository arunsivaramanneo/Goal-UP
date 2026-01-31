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
        self.set_content_width(450)
        self.set_content_height(200)
        self.set_draw_func(self._draw_func)
        
        self._completed_goals = 0
        self._total_goals = 0
        self._completed_tasks = 0
        self._total_tasks = 0
        
        self._upcoming_events = []
        
        # Style context for colors
        self._style_context = self.get_style_context()

    def update_status(self, completed_goals: int, total_goals: int, completed_tasks: int, total_tasks: int, 
                      upcoming_events: list[dict] = None) -> None:
        """Update the progress status."""
        self._completed_goals = completed_goals
        self._total_goals = total_goals
        self._completed_tasks = completed_tasks
        self._total_tasks = total_tasks
        self._upcoming_events = upcoming_events or []
        self.queue_draw()

    def _draw_func(self, area, cr: cairo.Context, width: int, height: int) -> None:
        """Draw the progress chart."""
        # Use a fixed center for the rings to the left
        center_x = 100
        center_y = height / 2
        
        self._draw_ring(cr, center_x, center_y, width, height, is_inner=False)
        self._draw_ring(cr, center_x, center_y, width, height, is_inner=True)
        self._draw_text(cr, center_x, center_y, width, height)
        self._draw_upcoming_details(cr, center_x, center_y, width, height)

    def _draw_ring(self, cr: cairo.Context, center_x: float, center_y: float, width: int, height: int, is_inner: bool) -> None:
        line_width = 10
        margin = 10
        
        if is_inner:
            radius = 60 # Fixed radius for consistency
            total = self._total_tasks
            completed = self._completed_tasks
            base_color = (0.9, 0.4, 0.2) # Orange for tasks
        else:
            radius = 80 # Fixed radius for consistency
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

    def _draw_text(self, cr: cairo.Context, center_x: float, center_y: float, width: int, height: int) -> None:
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        
        # Goals Count
        cr.set_font_size(14)
        goals_text = f"{self._completed_goals}/{self._total_goals}"
        (gx, gy, g_width, g_height, gdx, gdy) = cr.text_extents(goals_text)
        
        cr.move_to(center_x - g_width / 2 - gx, center_y - 5)
        cr.set_source_rgb(0.2, 0.5, 0.8) # Blue
        cr.show_text(goals_text)

        # Tasks Count
        cr.set_font_size(14)
        tasks_text = f"{self._completed_tasks}/{self._total_tasks}"
        (tx, ty, t_width, t_height, tdx, tdy) = cr.text_extents(tasks_text)
        
        cr.move_to(center_x - t_width / 2 - tx, center_y + t_height + 5)
        cr.set_source_rgb(0.9, 0.4, 0.2) # Orange
        cr.show_text(tasks_text)

    def _draw_upcoming_details(self, cr: cairo.Context, center_x: float, center_y: float, width: int, height: int) -> None:
        """Draw upcoming events to the right of the rings."""
        start_x = 220
        start_y = center_y - 65 # Height adjustment for more items
        
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(13)
        
        # Header for Upcoming Events
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.move_to(start_x, start_y)
        cr.show_text("Upcoming Events ...")
        
        current_y = start_y + 25
        
        if not self._upcoming_events:
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
            cr.move_to(start_x + 15, current_y)
            cr.show_text("No upcoming events")
            return

        for event in self._upcoming_events:
            # Bullet
            cr.set_source_rgb(*event['color'])
            cr.arc(start_x + 5, current_y - 4, 3, 0, 2 * math.pi)
            cr.fill()
            
            # Text
            cr.set_source_rgb(*event['color'])
            text = event['text']
            # Limit length slightly more aggressively if needed, but 30 should be fine
            if len(text) > 30: text = text[:50] + "..."
            days = event['days']
            if days < 0:
                display_text = f"{text} (Overdue by {abs(days)}d)"
            else:
                display_text = f"{text} ({days}d left)"
                
            cr.move_to(start_x + 15, current_y)
            cr.show_text(display_text)
            current_y += 20
