"""Main window for the Goal UP application."""

import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, Gio, GLib

from goal_row import GoalRow
from edit_dialog import EditGoalDialog
from storage import load_tasks, save_tasks, export_to_ics, export_backup, import_backup, load_settings, save_settings
from summary_widget import GoalPieChartsWidget, GoalTrendWidget, NotificationWidget, TimerWidget, CalendarWidget
from timeline_widget import TimelineWidget
from notification_manager import NotificationManager
from desktop_widget import DesktopWidget
from datetime import datetime, date
import random


class MainWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, app: Adw.Application):
        super().__init__(application=app)

        # Load settings
        self.settings = load_settings()
        self.current_theme = self.settings.get("theme", "light")
        
        self.set_title("Goal UP")
        self.set_default_size(1200, 850)
        
        # Set icon
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        # Add the directory containing the script to the icon search path
        # This allows finding 'icon.png' if it's in the same directory as window.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_theme.add_search_path(current_dir)

        icon_file = os.path.join(current_dir, "icon.png")
        if os.path.exists(icon_file):
            try:
                self.set_icon_from_file(icon_file)
            except Exception:
                # Fallback if file icon is unavailable
                self.set_icon_name("goal-up")
        else:
            self.set_icon_name("goal-up")

        if not icon_theme.has_icon("goal-up") and not os.path.exists(icon_file):
            # Final fallback to generic icon if bundle icon is unavailable
            self.set_icon_name("application-x-executable")

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Primary Menu
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        header.pack_end(menu_button)

        menu_model = Gio.Menu()
        menu_button.set_menu_model(menu_model)

        # About
        menu_model.append("About Goal UP", "win.about")

        # About Action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_clicked)
        self.add_action(about_action)

        # Data Menu
        data_menu = Gio.Menu()
        data_menu.append("Export to JSON (Backup)", "win.export-json")
        data_menu.append("Import from JSON (Restore)", "win.import-json")
        data_menu.append("Export to Calendar (ICS)", "win.export-ics")

        self.data_button = Gtk.MenuButton()
        self.data_button.set_icon_name("document-save-symbolic")
        self.data_button.set_tooltip_text("Data Management")
        self.data_button.set_menu_model(data_menu)
        header.pack_end(self.data_button)

        # Theme Toggle
        self.theme_button = Gtk.Button()
        self._update_theme_icon()
        self.theme_button.set_tooltip_text("Toggle Dark/Light Theme")
        self.theme_button.connect("clicked", self._on_theme_toggled)
        header.pack_end(self.theme_button)

        # Desktop Widget Toggle
        self.widget_toggle_button = Gtk.ToggleButton()
        self.widget_toggle_button.set_icon_name("view-grid-symbolic")
        self.widget_toggle_button.set_tooltip_text("Toggle Desktop Progress Widget")
        self.widget_toggle_button.connect("toggled", self._on_widget_toggled)
        header.pack_end(self.widget_toggle_button)

        # Actions for the menu
        export_ics_action = Gio.SimpleAction.new("export-ics", None)
        export_ics_action.connect("activate", self._on_export_ics_clicked)
        self.add_action(export_ics_action)

        export_json_action = Gio.SimpleAction.new("export-json", None)
        export_json_action.connect("activate", self._on_export_json_clicked)
        self.add_action(export_json_action)

        import_json_action = Gio.SimpleAction.new("import-json", None)
        import_json_action.connect("activate", self._on_import_json_clicked)
        self.add_action(import_json_action)

        # Content area (Sidebar + Main + Sidebar)
        content_horizontal_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.append(content_horizontal_box)

        # Timeline Sidebar
        self.timeline_widget = TimelineWidget()
        content_horizontal_box.append(self.timeline_widget)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        content_horizontal_box.append(separator)

        # Scrolled window for main content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content_horizontal_box.append(scrolled)

        # Clamp for responsive width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)
        clamp.set_tightening_threshold(400)
        scrolled.set_child(clamp)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        clamp.set_child(content_box)

        # Timer at the top
        self.timer_widget = TimerWidget()
        content_box.append(self.timer_widget)

        # Pie Charts
        self.pie_charts_widget = GoalPieChartsWidget()
        content_box.append(self.pie_charts_widget)

        # Entry section
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content_box.append(entry_box)

        self.goal_entry = Gtk.Entry()
        self.goal_entry.set_hexpand(True)
        self.goal_entry.set_placeholder_text("Add Goal")
        self.goal_entry.connect("activate", self._on_add_clicked)
        entry_box.append(self.goal_entry)

        self.color_button = Gtk.ColorButton()
        self.color_button.set_valign(Gtk.Align.CENTER)
        self._set_random_color()
        entry_box.append(self.color_button)

        add_button = Gtk.Button()
        add_button.set_icon_name("list-add-symbolic")
        add_button.add_css_class("suggested-action")
        add_button.connect("clicked", self._on_add_clicked)
        entry_box.append(add_button)

        # Goals list in a preferences group
        self.goals_group = Adw.PreferencesGroup()
        self.goals_group.set_title("Goals")
        content_box.append(self.goals_group)

        # Goal list box
        self.goal_list = Gtk.ListBox()
        self.goal_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.goal_list.add_css_class("boxed-list")
        self.goals_group.add(self.goal_list)

        # Empty state label
        self.empty_label = Gtk.Label(label="No goals yet. Add one above!")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_margin_top(24)
        self.empty_label.set_margin_bottom(24)
        content_box.append(self.empty_label)

        # Summary Trend Widget below goals
        self.summary_widget = GoalTrendWidget()
        content_box.append(self.summary_widget)

        # Right sidebar separator
        right_separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        content_horizontal_box.append(right_separator)

        # Right sidebar as scrollable content
        right_scrolled = Gtk.ScrolledWindow()
        right_scrolled.set_vexpand(True)
        right_scrolled.set_hexpand(False)
        right_scrolled.set_size_request(350, -1) # Increase width to 350
        right_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content_horizontal_box.append(right_scrolled)

        # Right sidebar box
        right_sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right_sidebar_box.set_margin_top(12)
        right_sidebar_box.set_margin_bottom(12)
        right_sidebar_box.set_margin_start(12)
        right_sidebar_box.set_margin_end(12)
        right_scrolled.set_child(right_sidebar_box)

        # Calendar Widget
        self.calendar_widget = CalendarWidget()
        right_sidebar_box.append(self.calendar_widget)

        # Notification Widget as right sidebar
        self.notification_widget = NotificationWidget()
        right_sidebar_box.append(self.notification_widget)

        # Trend widget no longer needed
        self.trend_widget = None

        # Load existing goals
        self._load_goals()
        self._update_empty_state()
        self._update_summary()

        # Initialize notifications
        self.notification_manager = NotificationManager(app)
        self._check_and_notify()

        # Apply initial theme
        self._apply_theme(self.current_theme)

        # Desktop widget (created after theme is applied)
        self.desktop_widget = DesktopWidget(app, self.settings, save_settings)
        # Restore toggle state
        if self.settings.get("widget_visible", False):
            self.widget_toggle_button.set_active(True)
            self.desktop_widget.present()

    def _apply_theme(self, theme: str) -> None:
        """Apply the specified theme."""
        style_manager = Adw.StyleManager.get_default()
        
        # We'll use our own CSS files as requested
        # First, remove existing providers if any (not strictly necessary for simple app)
        
        css_file = "gtk_dark.css" if theme == "dark" else "gtk_light.css"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(current_dir, css_file)
        
        if os.path.exists(css_path):
            provider = Gtk.CssProvider()
            provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            
            # Also set the libadwaita color scheme to match
            if theme == "dark":
                style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            else:
                style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        
        self.current_theme = theme
        self.settings["theme"] = theme
        save_settings(self.settings)
        self._update_theme_icon()

    def _update_theme_icon(self) -> None:
        """Update the theme button icon based on current theme."""
        if self.current_theme == "dark":
            self.theme_button.set_icon_name("display-brightness-symbolic")
        else:
            self.theme_button.set_icon_name("weather-clear-night-symbolic")

    def _on_theme_toggled(self, button: Gtk.Button) -> None:
        """Handle theme toggle button click."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new_theme)

    def _on_widget_toggled(self, button: Gtk.ToggleButton) -> None:
        """Show or hide the floating desktop widget."""
        visible = button.get_active()
        if visible:
            self.desktop_widget.present()
            # Feed current data immediately
            goals = self._get_goals_data()
            self.desktop_widget.update_data(goals)
        else:
            self.desktop_widget.hide()
        self.settings["widget_visible"] = visible
        save_settings(self.settings)

    def _check_and_notify(self) -> None:
        """Check for events due today and notify."""
        goals = self._get_goals_data()
        self.notification_manager.check_upcoming_events(goals)

    def _on_about_clicked(self, action: Gio.SimpleAction, parameter: GLib.Variant = None) -> None:
        """Show the About dialog."""
        about = Adw.AboutWindow()
        about.set_application_name("Goal UP")
        about.set_developer_name("Arun Sivaraman")
        about.set_version("1.0")
        about.set_copyright("© 2026 Arun Sivaraman")
        about.set_website("https://github.com/arunsivaramanneo/Goal-UP")
        about.set_issue_url("https://github.com/arunsivaramanneo/Goal-UP/issues")
        about.set_license_type(Gtk.License.MIT_X11)
        about.set_application_icon("goal-up")
        about.set_transient_for(self)
        about.present()

    def _on_export_ics_clicked(self, action: Gio.SimpleAction, parameter: GLib.Variant = None) -> None:
        """Handle export to ICS button click."""
        dialog = Gtk.FileDialog(title="Export to Calendar")
        dialog.set_initial_name("goals.ics")
        
        filter_ics = Gtk.FileFilter()
        filter_ics.set_name("iCalendar files")
        filter_ics.add_mime_type("text/calendar")
        filter_ics.add_suffix("ics")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_ics)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_ics_file_selected)

    def _on_export_ics_file_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Handle file selection for ICS export."""
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                goals = self._get_goals_data()
                if export_to_ics(goals, path):
                    notification = Gio.Notification.new("Export Successful")
                    notification.set_body(f"Calendar exported to {os.path.basename(path)}")
                    self.get_application().send_notification("export", notification)
                else:
                    print("Failed to export ICS")
        except Exception as e:
            print(f"Export error: {e}")

    def _on_export_json_clicked(self, action: Gio.SimpleAction, parameter: GLib.Variant = None) -> None:
        """Handle export to JSON button click."""
        dialog = Gtk.FileDialog(title="Export Backup (JSON)")
        dialog.set_initial_name("goals_backup.json")
        
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_mime_type("application/json")
        filter_json.add_suffix("json")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_json)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_json_file_selected)

    def _on_export_json_file_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Handle file selection for JSON export."""
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                goals = self._get_goals_data()
                if export_backup(goals, path):
                    notification = Gio.Notification.new("Backup Successful")
                    notification.set_body(f"Backup saved to {os.path.basename(path)}")
                    self.get_application().send_notification("export", notification)
                else:
                    print("Failed to export backup")
        except Exception as e:
            print(f"Export error: {e}")

    def _on_import_json_clicked(self, action: Gio.SimpleAction, parameter: GLib.Variant = None) -> None:
        """Handle import from JSON button click."""
        dialog = Gtk.FileDialog(title="Import Backup (JSON)")
        
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_mime_type("application/json")
        filter_json.add_suffix("json")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_json)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_import_json_file_selected)

    def _on_import_json_file_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Handle file selection for JSON import."""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                tasks = import_backup(path)
                if tasks is not None:
                    # Confirm with user before overwriting? 
                    # For now just import and save.
                    save_tasks(tasks)
                    self._load_goals()
                    self._update_empty_state()
                    self._update_summary()
                    
                    notification = Gio.Notification.new("Import Successful")
                    notification.set_body(f"Imported {len(tasks)} goals from backup")
                    self.get_application().send_notification("import", notification)
                else:
                    print("Failed to import backup")
        except Exception as e:
            print(f"Import error: {e}")


        
    def _get_goals_data(self) -> list:
        """Get all goals and tasks as a list of dictionaries."""
        goals = []
        row = self.goal_list.get_first_child()
        while row is not None:
            if isinstance(row, GoalRow):
                goals.append({
                    "id": row.id,
                    "parent_id": row.parent_id,
                    "title": row.goal_title,
                    "description": row.description,
                    "completed": row.completed,
                    "tasks": row.get_tasks(),
                    "created_at": row.created_at,
                    "end_date": row.end_date,
                    "completion_date": getattr(row, "_completion_date", ""),
                    "color": row.color,
                    "recurrence": row.recurrence,
                    "recurrence_days": row.recurrence_days
                })
            row = row.get_next_sibling()
        return goals

    def _on_add_clicked(self, widget: Gtk.Widget) -> None:
        """Handle add button click or entry activation."""
        text = self.goal_entry.get_text().strip()
        if not text:
            return

        color = self.color_button.get_rgba().to_string()
        self._add_goal(text, "", False, [], None, color=color)
        self.goal_entry.set_text("")
        self._set_random_color()
        self._reorder_goals()
        self._save_goals()
        self._update_empty_state()

    def _set_random_color(self) -> None:
        """Set a random color for the color button."""
        rgba = Gdk.RGBA()
        rgba.red = random.random()
        rgba.green = random.random()
        rgba.blue = random.random()
        rgba.alpha = 1.0
        self.color_button.set_rgba(rgba)

    def _add_goal(self, title: str, description: str, completed: bool, tasks: list, created_at: str = None, end_date: str = "", id: str = None, parent_id: str = "", depth: int = 0, color: str = None, end_time: str = "", recurrence: str = "none", recurrence_days: str = "") -> None:
        """Add a new goal to the list."""
        row = GoalRow(title, description, completed, tasks, created_at, end_date, id, parent_id, depth, color=color, end_time=end_time, recurrence=recurrence, recurrence_days=recurrence_days)
        row.connect("goal-changed", self._on_goal_changed)
        row.connect("goal-deleted", self._on_goal_deleted)
        row.connect("edit-requested", self._on_edit_requested)
        row.connect("reminder-set", self._on_reminder_set)
        self.goal_list.append(row)

    def _on_goal_changed(self, row: GoalRow) -> None:
        """Handle goal modification."""
        self._save_goals()

    def _on_goal_deleted(self, row: GoalRow) -> None:
        """Handle goal deletion."""
        self.goal_list.remove(row)
        self._save_goals()
        self._update_empty_state()

    def _on_reminder_set(self, row: GoalRow, task_text: str, date_str: str) -> None:
        """Handle reminder-set signal from a goal row."""
        title = "Reminder Set"
        body = f"Reminder set for '{task_text}' on {date_str}"
        self.notification_manager.send_notification(title, body, "reminder-set-feedback")

    def _on_edit_requested(self, row: GoalRow) -> None:
        """Handle edit request for a goal."""
        # Get possible parents (avoiding self and descendants)
        possible_parents = []
        all_goals = self._get_goals_data()
        
        # Get descendants
        descendants = set()
        to_check = [row.id]
        while to_check:
            curr_id = to_check.pop()
            for g in all_goals:
                if g.get("parent_id") == curr_id:
                    if g["id"] not in descendants:
                        descendants.add(g["id"])
                        to_check.append(g["id"])
        
        for g in all_goals:
                possible_parents.append((g["id"], g["title"]))

        dialog = EditGoalDialog(row.goal_title, row.description, row.end_date, row.parent_id, row.color, possible_parents, row.end_time, getattr(row, "_completion_date", ""))
        dialog.connect("save", self._on_edit_save, row)
        dialog.present(self)

    def _on_edit_save(self, dialog: EditGoalDialog, title: str, description: str, end_date: str, parent_id: str, color: str, end_time: str, completion_date: str, row: GoalRow) -> None:
        """Handle save from edit dialog."""
        row.update_details(title, description, end_date, parent_id, color, end_time, completion_date)
        self._reorder_goals()
        self._save_goals()

    def _load_goals(self) -> None:
        """Load goals from storage."""
        # Clear existing list
        row = self.goal_list.get_first_child()
        while row is not None:
            next_row = row.get_next_sibling()
            self.goal_list.remove(row)
            row = next_row
            
        goals = load_tasks()
        for goal in goals:
            self._add_goal(
                goal.get("title", goal.get("text", "")),  # Backward compat
                goal.get("description", ""),
                goal.get("completed", False),
                goal.get("tasks", []),
                goal.get("created_at"),
                goal.get("end_date"),
                goal.get("id"),
                goal.get("parent_id", ""),
                goal.get("depth", 0),
                goal.get("color", None),
                goal.get("end_time", ""),
                goal.get("recurrence") or "none",
                goal.get("recurrence_days") or ""
            )
            if goal.get("completion_date"):
                row = self.goal_list.get_last_child()
                if isinstance(row, GoalRow):
                    row._completion_date = goal["completion_date"]
                    row._update_days_remaining()
        
        self._reorder_goals()

    def _save_goals(self) -> None:
        """Save all goals to storage."""
        goals = []
        row = self.goal_list.get_first_child()
        while row is not None:
            if isinstance(row, GoalRow):
                goals.append({
                    "id": row.id,
                    "parent_id": row.parent_id,
                    "title": row.goal_title,
                    "description": row.description,
                    "completed": row.completed,
                    "tasks": row.get_tasks(),
                    "created_at": row.created_at,
                    "end_date": row.end_date,
                    "end_time": row.end_time,
                    "completion_date": getattr(row, "_completion_date", ""),
                    "color": row.color,
                    "recurrence": row.recurrence,
                    "recurrence_days": row.recurrence_days
                })
            row = row.get_next_sibling()
        save_tasks(goals)
        self._update_summary_from_list(goals)
    
    def _reorder_goals(self) -> None:
        """Reorder goals to show hierarchy and update indentation."""
        # 1. Collect all rows
        all_rows = []
        row = self.goal_list.get_first_child()
        while row is not None:
            if isinstance(row, GoalRow):
                all_rows.append(row)
            row = row.get_next_sibling()
        
        if not all_rows:
            return

        # 2. Identify hierarchy
        # Sort all_rows before building hierarchy to ensure consistent ordering within groups
        all_rows.sort(key=lambda r: (
            r.completed,
            r.end_date == "",
            r.end_date,
            r.end_time
        ))

        goals_by_parent = {}
        top_level = []
        rows_by_id = {r.id: r for r in all_rows}
        
        for r in all_rows:
            p_id = r.parent_id
            if not p_id or p_id not in rows_by_id:
                top_level.append(r)
            else:
                if p_id not in goals_by_parent:
                    goals_by_parent[p_id] = []
                goals_by_parent[p_id].append(r)
        
        # 3. Flatten hierarchy in DFS order
        ordered_rows = []
        def dfs(rows, depth):
            for r in rows:
                r.depth = depth
                ordered_rows.append(r)
                if r.id in goals_by_parent:
                    dfs(goals_by_parent[r.id], depth + 1)
        
        dfs(top_level, 0)
        
        # 4. Re-populate the Gtk.ListBox
        # Note: We can use Gtk.ListBox.reorder_child in Gtk 3, 
        # but in Gtk 4 we need to remove and re-append or use a sort function.
        # Actually, Gtk4 ListBox has insert() which can be used to reorder.
        # But removing and re-adding is easiest to ensure exact DFS order.
        
        for r in all_rows:
            self.goal_list.remove(r)
            
        for r in ordered_rows:
            self.goal_list.append(r)
    
    def _update_summary(self) -> None:
        """Update summary from current widget state."""
        goals = []
        row = self.goal_list.get_first_child()
        while row is not None:
            if isinstance(row, GoalRow):
                goals.append({
                    "title": row.goal_title,
                    "completed": row.completed,
                    "end_date": row.end_date,
                    "completion_date": getattr(row, "_completion_date", ""),
                    "tasks": row.get_tasks(),
                    "color": row.color
                })
            row = row.get_next_sibling()
        self._update_summary_from_list(goals)

    def _update_summary_from_list(self, goals: list) -> None:
        """Update the summary widget with the given list of goals."""
        total_goals = len(goals)
        completed_goals = sum(1 for g in goals if g.get("completed", False))
        
        total_tasks = 0
        completed_tasks = 0
        
        for goal in goals:
            tasks = goal.get("tasks", [])
            total_tasks += len(tasks)
            completed_tasks += sum(1 for t in tasks if t.get("completed", False))

        self.pie_charts_widget.update_data(completed_goals, total_goals, completed_tasks, total_tasks, goals)
        self.summary_widget.update_data(goals)
        self.timeline_widget.update_data(goals)
        self.timer_widget.update_data(goals)
        self.notification_widget.update_data(goals)
        self.calendar_widget.update_data(goals)
        # Update desktop widget if it exists
        if hasattr(self, "desktop_widget"):
            self.desktop_widget.update_data(goals)

    def _update_empty_state(self) -> None:
        """Show or hide the empty state message."""
        has_goals = self.goal_list.get_first_child() is not None
        self.empty_label.set_visible(not has_goals)
        self.goals_group.set_visible(has_goals)
