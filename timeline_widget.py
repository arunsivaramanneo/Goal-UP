"""Timeline widget for Goal UP."""

import gi
from datetime import datetime, date

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GObject

class TimelineRow(Adw.ActionRow):
    """A row in the timeline representing a specific event."""
    def __init__(self, date_str: str, text: str, completed: bool):
        super().__init__()
        self.set_title(text)
        self.set_subtitle(date_str)
        
        if completed:
            check_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check_icon.add_css_class("success")
            self.add_prefix(check_icon)
            self.add_css_class("dim-label")
        else:
            bullet_icon = Gtk.Image.new_from_icon_name("non-starred-symbolic")
            self.add_prefix(bullet_icon)

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
        
        for goal in goals:
            # Goal itself
            g_date_str = goal.get("completion_date") or goal.get("end_date")
            if g_date_str:
                try:
                    ev_date = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                    if ev_date >= start_of_year:
                        events.append({
                            "date": ev_date,
                            "text": f"Goal: {goal['title']}",
                            "completed": goal.get("completed", False)
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
                            events.append({
                                "date": ev_date,
                                "text": f"{goal['title']} : {task['text']}",
                                "completed": task.get("completed", False)
                            })
                    except (ValueError, TypeError):
                        pass
        
        # Sort by date
        events.sort(key=lambda x: x["date"])
        
        if not events:
            self.list_box.append(self._empty_label)
        else:
            for ev in events:
                row = TimelineRow(ev["date"].strftime("%b %d"), ev["text"], ev["completed"])
                self.list_box.append(row)
