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
        # Split into two areas
        left_center_x = width * 0.25
        right_center_x = width * 0.75
        center_y = height / 2
        radius = 70
        
        # Draw Goals Pie Chart (Left)
        # Completed: Green (0.2, 0.7, 0.3)
        # Remaining: Blue (0.2, 0.5, 0.8)
        self._draw_pie(cr, left_center_x, center_y, radius, 
                       self._completed_goals, self._total_goals, 
                       (0.15, 0.68, 0.37), (0.2, 0.5, 0.8), "Goals") # Green / Blue

        # Draw Tasks Pie Chart (Right)
        # Completed: Green (0.2, 0.7, 0.3)
        # Remaining: Orange (0.9, 0.4, 0.2)
        self._draw_pie(cr, right_center_x, center_y, radius, 
                       self._completed_tasks, self._total_tasks, 
                       (0.15, 0.68, 0.37), (0.9, 0.4, 0.2), "Tasks") # Green / Orange

    def _draw_pie(self, cr: cairo.Context, center_x: float, center_y: float, radius: float, 
                  completed: int, total: int, completed_color: tuple, remaining_color: tuple, label: str) -> None:
        """Draw a single pie chart with legend."""
        
        # Calculate Percentage
        if total > 0:
            percent_complete = completed / total
        else:
            percent_complete = 0.0
            
        start_angle = -math.pi / 2
        
        # 1. Remaining Slice (Background)
        # Even if 100% complete, we can draw it underneath or just skip? 
        # Safest is to draw full circle first as background if not 100%, 
        # but to place text correctly we might want to know the angle.
        # Actually, let's draw two proper arcs.
        
        remaining_angle_span = (1.0 - percent_complete) * 2 * math.pi
        completed_angle_span = percent_complete * 2 * math.pi
        
        # Draw Remaining Arc (from end of completed to start)
        # Completed ends at start_angle + completed_angle_span
        split_angle = start_angle + completed_angle_span
        
        if percent_complete < 1.0:
            cr.set_source_rgb(*remaining_color)
            cr.move_to(center_x, center_y)
            cr.arc(center_x, center_y, radius, split_angle, start_angle + 2*math.pi) # Draw remaining part
            cr.close_path()
            cr.fill()
            
            # Text on Remaining Slice
            # Calculate mid-angle
            mid_angle = split_angle + remaining_angle_span / 2
            # Position: 2/3 radius out
            text_x = center_x + (radius * 0.6) * math.cos(mid_angle)
            text_y = center_y + (radius * 0.6) * math.sin(mid_angle)
            
            # Only draw if slice is big enough (e.g. > 10%)
            if (1.0 - percent_complete) > 0.1:
                rem_pct = int((1.0 - percent_complete) * 100)
                rem_text = f"{rem_pct}%"
                self._draw_slice_text(cr, text_x, text_y, rem_text)

        # 2. Completed Slice
        if percent_complete > 0:
            cr.set_source_rgb(*completed_color)
            cr.move_to(center_x, center_y)
            cr.arc(center_x, center_y, radius, start_angle, split_angle)
            cr.close_path()
            cr.fill()
            
            # Text on Completed Slice
            mid_angle = start_angle + completed_angle_span / 2
            text_x = center_x + (radius * 0.6) * math.cos(mid_angle)
            text_y = center_y + (radius * 0.6) * math.sin(mid_angle)
            
            if percent_complete > 0.1:
                comp_pct = int(percent_complete * 100)
                comp_text = f"{comp_pct}%"
                self._draw_slice_text(cr, text_x, text_y, comp_text)

        # 3. Label and Count (below)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        fg_color = self._style_context.get_color()
        cr.set_source_rgba(fg_color.red, fg_color.green, fg_color.blue, fg_color.alpha)
        
        full_label = f"{label}: {completed}/{total}"
        cr.set_font_size(16)
        (lx, ly, l_width, l_height, ldx, ldy) = cr.text_extents(full_label)
        cr.move_to(center_x - l_width / 2 - lx, center_y + radius + 30)
        cr.show_text(full_label)

    def _draw_slice_text(self, cr: cairo.Context, x: float, y: float, text: str) -> None:
        """Helper to draw text centered at x, y."""
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(14)
        # White text usually looks good on colors
        cr.set_source_rgb(1, 1, 1) 
        
        (tx, ty, width, height, dx, dy) = cr.text_extents(text)
        cr.move_to(x - width / 2 - tx, y + height / 2 - ty)
        cr.show_text(text)
