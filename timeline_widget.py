"""Timeline widget for Goal UP."""

import gi
from datetime import datetime, date

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GObject, GLib

class TimelineRow(Adw.ActionRow):
    """A row in the timeline representing a specific event."""
    def __init__(self, date_str: str, text: str, completed: bool, color: str = None, days_remaining: int = None):
        super().__init__()
        # Ensure title is set; markup will override if needed
        self.set_title(text)
        
        subtitle = date_str
        if not completed and days_remaining is not None:
            if days_remaining < 0:
                 subtitle += f" ({abs(days_remaining)}d overdue)"
            else:
                 subtitle += f" ({days_remaining}d left)"
        self.set_subtitle(subtitle)
        
        if completed:
            check_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check_icon.add_css_class("success")
            self.add_prefix(check_icon)
            self.add_css_class("dim-label")
        else:
            bullet_icon = Gtk.Image.new_from_icon_name("non-starred-symbolic")
            self.add_prefix(bullet_icon)

        if color and not completed:
            # Parse the color string (e.g. rgb(..)) to Gdk.RGBA to get components
            rgba = Gdk.RGBA()
            if rgba.parse(color):
                # Convert to hex for Pango
                r = int(rgba.red * 255)
                g = int(rgba.green * 255)
                b = int(rgba.blue * 255)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                
                escaped_text = GLib.markup_escape_text(text)
                markup = f"<span foreground='{hex_color}'>{escaped_text}</span>"
                self.set_title(markup)
                self.set_use_markup(True)

class TimelineWidget(Gtk.Box):
    """Widget that displays a vertical timeline of goals and tasks."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_size_request(250, -1)
        self.add_css_class("background")
        
        # Header
        header_box = Gtk.CenterBox()
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(12)
        
        title_label = Gtk.Label(label="Timeline")
        title_label.add_css_class("title-4")
        header_box.set_center_widget(title_label)
        self.append(header_box)
        
        # Scrolled Window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)
        
        # ListBox
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("navigation-sidebar")
        scrolled.set_child(self.list_box)
        
        self._empty_label = Gtk.Label(label="No events this year")
        self._empty_label.add_css_class("dim-label")
        self._empty_label.set_margin_top(20)
        self.list_box.append(self._empty_label)

    def update_data(self, goals: list) -> None:
        """Update the timeline with current goals and tasks."""
        # Clear existing
        while True:
            row = self.list_box.get_first_child()
            if row is None:
                break
            self.list_box.remove(row)
            
        events = []
        current_year = date.today().year
        start_of_year = date(current_year, 1, 1)
        today = date.today()
        
        for goal in goals:
            color = goal.get("color")
            # Goal itself
            g_date_str = goal.get("completion_date") or goal.get("end_date")
            if g_date_str:
                try:
                    ev_date = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                    if ev_date >= start_of_year:
                        days = (ev_date - today).days
                        events.append({
                            "date": ev_date,
                            "text": f"Goal: {goal['title']}",
                            "completed": goal.get("completed", False),
                            "color": color,
                            "days": days
                        })
                except (ValueError, TypeError):
                    pass
            
            # Tasks
            for task in goal.get("tasks", []):
                t_date_str = task.get("completion_date") or task.get("end_date")
                if t_date_str:
                    try:
                        ev_date = datetime.strptime(t_date_str, "%Y-%m-%d").date()
                        if ev_date >= start_of_year:
                            days = (ev_date - today).days
                            events.append({
                                "date": ev_date,
                                "text": f"{goal['title']} : {task['text']}",
                                "completed": task.get("completed", False),
                                "color": color, # Inherit goal color
                                "days": days
                            })
                    except (ValueError, TypeError):
                        pass
        
        # Sort by date
        events.sort(key=lambda x: x["date"])
        
        if not events:
            self.list_box.append(self._empty_label)
        else:
            for ev in events:
                row = TimelineRow(
                    ev["date"].strftime("%b %d"), 
                    ev["text"], 
                    ev["completed"], 
                    ev.get("color"),
                    ev.get("days")
                )
                self.list_box.append(row)
