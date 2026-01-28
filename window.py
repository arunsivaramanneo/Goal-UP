"""Main window for the Goal UP application."""

import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk

from goal_row import GoalRow
from edit_dialog import EditGoalDialog
from storage import load_tasks, save_tasks
from summary_widget import GoalSummaryWidget


class MainWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, app: Adw.Application):
        super().__init__(application=app)

        self.set_title("Goal UP")
        self.set_default_size(500, 700)
        
        # Set icon
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        # Add the directory containing the script to the icon search path
        # This allows finding 'icon.png' if it's in the same directory as window.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_theme.add_search_path(current_dir)
        
        # Also check standard XDG paths (usually handled by default, but ensuring reliability)
        # If installed, the icon might be in /share/icons, which is covered by standard paths.
        
        self.set_icon_name("goal-up") # Use 'goal-up' to match desktop file icon name, fallback handled later
        if not icon_theme.has_icon("goal-up"):
             # Fallback for local development if installed icon not found
             self.set_icon_name("icon") # The local file is icon.png

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Scrolled window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.append(scrolled)

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

        # Summary Widget
        self.summary_widget = GoalSummaryWidget()
        content_box.append(self.summary_widget)

        # Entry section
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content_box.append(entry_box)

        self.goal_entry = Gtk.Entry()
        self.goal_entry.set_hexpand(True)
        self.goal_entry.set_placeholder_text("Add Goal")
        self.goal_entry.connect("activate", self._on_add_clicked)
        entry_box.append(self.goal_entry)

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

        # Load existing goals
        self._load_goals()
        self._update_empty_state()
        self._update_summary()

    def _on_add_clicked(self, widget: Gtk.Widget) -> None:
        """Handle add button click or entry activation."""
        text = self.goal_entry.get_text().strip()
        if not text:
            return

        self._add_goal(text, "", False, [], None)
        self.goal_entry.set_text("")
        self._save_goals()
        self._update_empty_state()

    def _add_goal(self, title: str, description: str, completed: bool, tasks: list, created_at: str = None, end_date: str = "") -> None:
        """Add a new goal to the list."""
        row = GoalRow(title, description, completed, tasks, created_at, end_date)
        row.connect("goal-changed", self._on_goal_changed)
        row.connect("goal-deleted", self._on_goal_deleted)
        row.connect("edit-requested", self._on_edit_requested)
        self.goal_list.append(row)

    def _on_goal_changed(self, row: GoalRow) -> None:
        """Handle goal modification."""
        self._save_goals()

    def _on_goal_deleted(self, row: GoalRow) -> None:
        """Handle goal deletion."""
        self.goal_list.remove(row)
        self._save_goals()
        self._update_empty_state()

    def _on_edit_requested(self, row: GoalRow) -> None:
        """Handle edit request for a goal."""
        dialog = EditGoalDialog(row.goal_title, row.description)
        dialog.connect("save", self._on_edit_save, row)
        dialog.present(self)

    def _on_edit_save(self, dialog: EditGoalDialog, title: str, description: str, end_date: str, row: GoalRow) -> None:
        """Handle save from edit dialog."""
        row.update_details(title, description, end_date)
        self._save_goals()

    def _load_goals(self) -> None:
        """Load goals from storage."""
        goals = load_tasks()
        for goal in goals:
            self._add_goal(
                goal.get("title", goal.get("text", "")),  # Backward compat
                goal.get("description", ""),
                goal.get("completed", False),
                goal.get("tasks", []),
                goal.get("created_at"),
                goal.get("end_date")
            )

    def _save_goals(self) -> None:
        """Save all goals to storage."""
        goals = []
        row = self.goal_list.get_first_child()
        while row is not None:
            if isinstance(row, GoalRow):
                goals.append({
                    "title": row.goal_title,
                    "description": row.description,
                    "completed": row.completed,
                    "tasks": row.get_tasks(),
                    "created_at": row.created_at,
                    "end_date": row.end_date
                })
            row = row.get_next_sibling()
        save_tasks(goals)
        self._update_summary_from_list(goals)
    
    def _update_summary(self) -> None:
        """Update summary from current widget state."""
        goals = []
        row = self.goal_list.get_first_child()
        while row is not None:
            if isinstance(row, GoalRow):
                goals.append({
                    "completed": row.completed,
                    "tasks": row.get_tasks()
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

        self.summary_widget.update_status(completed_goals, total_goals, completed_tasks, total_tasks)

    def _update_empty_state(self) -> None:
        """Show or hide the empty state message."""
        has_goals = self.goal_list.get_first_child() is not None
        self.empty_label.set_visible(not has_goals)
        self.goals_group.set_visible(has_goals)
