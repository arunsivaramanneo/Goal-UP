"""Goal row widget with expandable tasks."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, GObject

from datetime import datetime, date

from edit_dialog import EditTaskDialog


class SubTaskRow(Adw.ActionRow):
    """A row widget representing a sub-task within a goal."""

    __gtype_name__ = "SubTaskRow"

    __gsignals__ = {
        "task-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "task-deleted": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "task-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, text: str, completed: bool = False, end_date: str = ""):
        super().__init__()

        self._text = text
        self._completed = completed
        self._end_date = end_date

        self.set_title(text)

        # Checkbox
        self.check_button = Gtk.CheckButton()
        self.check_button.set_active(completed)
        self.check_button.set_valign(Gtk.Align.CENTER)
        self.check_button.connect("toggled", self._on_check_toggled)
        self.add_prefix(self.check_button)

        # Days remaining label (only shown if end_date is set)
        self.remaining_label = Gtk.Label(label="")
        self.remaining_label.set_valign(Gtk.Align.CENTER)
        self.remaining_label.add_css_class("dim-label")
        self.remaining_label.set_margin_end(8)
        self.add_suffix(self.remaining_label)
        self._update_days_remaining()

        # Action buttons box
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_suffix(actions_box)

        # Edit button
        edit_button = Gtk.Button()
        edit_button.set_icon_name("document-edit-symbolic")
        edit_button.set_valign(Gtk.Align.CENTER)
        edit_button.add_css_class("flat")
        edit_button.add_css_class("circular")
        edit_button.connect("clicked", self._on_edit_clicked)
        actions_box.append(edit_button)

        # Delete button
        delete_button = Gtk.Button()
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.add_css_class("flat")
        delete_button.add_css_class("circular")
        delete_button.connect("clicked", self._on_delete_clicked)
        actions_box.append(delete_button)

        self._update_style()

    @property
    def task_text(self) -> str:
        return self._text

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def end_date(self) -> str:
        return self._end_date

    def _on_check_toggled(self, button: Gtk.CheckButton) -> None:
        self._completed = button.get_active()
        if self._completed:
            self._end_date = date.today().isoformat()
        self._update_days_remaining()
        self._update_style()
        self.emit("task-toggled", self._completed)

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        self.emit("task-deleted")

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        dialog = EditTaskDialog(self._text, self._end_date)
        dialog.connect("save", self._on_edit_save)
        # Find the root window to present the dialog
        root = self.get_root()
        if root:
            dialog.present(root)

    def _on_edit_save(self, dialog: EditTaskDialog, text: str, end_date: str) -> None:
        self._text = text
        self._end_date = end_date
        self._update_days_remaining()
        self._update_style()
        self.emit("task-changed", self._text)

    def _update_style(self) -> None:
        if self._completed:
            self.add_css_class("dim-label")
            self.set_title(f"<s>{self._text}</s>")
            self.set_use_markup(True)
        else:
            self.remove_css_class("dim-label")
            self.set_title(self._text)
            self.set_use_markup(False)

    def _update_days_remaining(self) -> None:
        """Update the days remaining label based on end date."""
        if not self._end_date:
            self.remaining_label.set_label("")
            return

        try:
            end_date = datetime.strptime(self._end_date, "%Y-%m-%d").date()
            today = date.today()
            days = (end_date - today).days
            
            if days < 0:
                self.remaining_label.set_label(f"Overdue by {abs(days)}d")
                self.remaining_label.add_css_class("error")
            else:
                self.remaining_label.set_label(f"{days}d left")
                self.remaining_label.remove_css_class("error")
                
        except (ValueError, TypeError):
            self.remaining_label.set_label("")


class GoalRow(Adw.ExpanderRow):
    """An expandable row widget representing a goal with sub-tasks."""

    __gtype_name__ = "GoalRow"

    __gsignals__ = {
        "goal-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "goal-deleted": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "edit-requested": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, title: str, description: str = "", completed: bool = False, tasks: list = None, created_at: str = None, end_date: str = ""):
        super().__init__()

        self._title = title
        self._description = description
        self._completed = completed
        self._tasks = tasks or []
        self._subtask_rows = []  # Track sub-task rows for persistence
        self._created_at = created_at or datetime.now().isoformat()
        self._end_date = end_date or ""

        self.set_title(title)
        if description:
            self.set_subtitle(description)

        # Checkbox for goal completion
        self.check_button = Gtk.CheckButton()
        self.check_button.set_active(completed)
        self.check_button.set_valign(Gtk.Align.CENTER)
        self.check_button.connect("toggled", self._on_check_toggled)
        self.add_prefix(self.check_button)

        # Percentage completion label
        self.progress_label = Gtk.Label(label="0%")
        self.progress_label.set_valign(Gtk.Align.CENTER)
        self.progress_label.add_css_class("dim-label")
        self.progress_label.set_margin_end(4)
        self.add_suffix(self.progress_label)

        # Task count label
        self.count_label = Gtk.Label(label="0/0")
        self.count_label.set_valign(Gtk.Align.CENTER)
        self.count_label.add_css_class("dim-label")
        self.count_label.set_margin_end(8)
        self.add_suffix(self.count_label)

        # Days elapsed label
        self.days_label = Gtk.Label(label="0d")
        self.days_label.set_valign(Gtk.Align.CENTER)
        self.days_label.add_css_class("dim-label")
        self.days_label.set_margin_end(4)
        self.add_suffix(self.days_label)
        self._update_days_elapsed()

        # Days remaining label (only shown if end_date is set)
        self.remaining_label = Gtk.Label(label="")
        self.remaining_label.set_valign(Gtk.Align.CENTER)
        self.remaining_label.add_css_class("dim-label")
        self.remaining_label.set_margin_end(8)
        self.add_suffix(self.remaining_label)
        self._update_days_remaining()

        self._update_days_remaining()

        # Add task entry row
        self._add_task_row = Adw.ActionRow()
        self._add_task_row.set_title("Add Task")
        self._add_task_row.add_css_class("dim-label")
        
        add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        add_icon.set_valign(Gtk.Align.CENTER)
        self._add_task_row.add_prefix(add_icon)

        self.task_entry = Gtk.Entry()
        self.task_entry.set_placeholder_text("New task...")
        self.task_entry.set_valign(Gtk.Align.CENTER)
        self.task_entry.set_hexpand(True)
        self.task_entry.connect("activate", self._on_add_task)
        self._add_task_row.add_suffix(self.task_entry)

        add_button = Gtk.Button()
        add_button.set_icon_name("list-add-symbolic")
        add_button.set_valign(Gtk.Align.CENTER)
        add_button.add_css_class("flat")
        add_button.connect("clicked", self._on_add_task)
        self._add_task_row.add_suffix(add_button)

        self.add_row(self._add_task_row)

        # Load existing tasks
        for task in self._tasks:
            self._add_subtask(task.get("text", ""), task.get("completed", False), task.get("end_date", ""))

        self._update_style()
        self._update_progress()

        # Action buttons box at the very end
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_suffix(actions_box)

        # Edit button
        edit_button = Gtk.Button()
        edit_button.set_icon_name("document-edit-symbolic")
        edit_button.set_valign(Gtk.Align.CENTER)
        edit_button.add_css_class("flat")
        edit_button.add_css_class("circular")
        edit_button.connect("clicked", self._on_edit_clicked)
        actions_box.append(edit_button)

        # Delete button
        delete_button = Gtk.Button()
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.add_css_class("flat")
        delete_button.add_css_class("circular")
        delete_button.connect("clicked", self._on_delete_clicked)
        actions_box.append(delete_button)

    @property
    def goal_title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def end_date(self) -> str:
        return self._end_date

    def get_tasks(self) -> list:
        """Get all sub-tasks as list of dicts."""
        tasks = []
        for row in self._subtask_rows:
            tasks.append({
                "text": row.task_text,
                "completed": row.completed,
                "end_date": row.end_date
            })
        return tasks

    def update_details(self, title: str, description: str, end_date: str = "") -> None:
        """Update goal title, description, and end date."""
        self._title = title
        self._description = description
        self._end_date = end_date
        self.set_title(title)
        self.set_subtitle(description if description else "")
        self._update_days_remaining()
        self.emit("goal-changed")

    def _add_subtask(self, text: str, completed: bool, end_date: str = "") -> None:
        """Add a sub-task row."""
        row = SubTaskRow(text, completed, end_date)
        row.connect("task-toggled", self._on_subtask_toggled)
        row.connect("task-changed", self._on_subtask_changed)
        row.connect("task-deleted", self._on_subtask_deleted, row)
        self._subtask_rows.append(row)
        self.add_row(row)

    def _on_subtask_toggled(self, row: SubTaskRow, completed: bool) -> None:
        """Handle sub-task toggle."""
        self._update_progress()
        self.emit("goal-changed")

    def _on_subtask_changed(self, row: SubTaskRow, text: str) -> None:
        """Handle sub-task change."""
        self.emit("goal-changed")

    def _on_add_task(self, widget: Gtk.Widget) -> None:
        """Handle add task action."""
        text = self.task_entry.get_text().strip()
        if not text:
            return
        self._add_subtask(text, False)
        self.task_entry.set_text("")
        self._update_progress()
        self.emit("goal-changed")

    def _on_subtask_deleted(self, subtask_row: SubTaskRow, row: SubTaskRow) -> None:
        """Handle sub-task deletion."""
        if row in self._subtask_rows:
            self._subtask_rows.remove(row)
        self.remove(row)
        self._update_progress()
        self.emit("goal-changed")

    def _on_check_toggled(self, button: Gtk.CheckButton) -> None:
        self._completed = button.get_active()
        if self._completed:
            self._end_date = date.today().isoformat()
        self._update_days_remaining()
        self._update_style()
        self.emit("goal-changed")

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        self.emit("edit-requested")

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        self.emit("goal-deleted")

    def _update_style(self) -> None:
        if self._completed:
            self.add_css_class("dim-label")
        else:
            self.remove_css_class("dim-label")

    def _update_progress(self) -> None:
        """Update the percentage completion label based on sub-tasks."""
        tasks = self.get_tasks()
        if not tasks:
            self.progress_label.set_label("0%")
            self.count_label.set_label("0/0")
            return
        
        completed_count = sum(1 for t in tasks if t.get("completed", False))
        total_count = len(tasks)
        percentage = int((completed_count / total_count) * 100)
        self.progress_label.set_label(f"{percentage}%")
        self.count_label.set_label(f"{completed_count}/{total_count}")
    def _update_days_elapsed(self) -> None:
        """Update the days elapsed label based on creation date."""
        try:
            created_date = datetime.fromisoformat(self._created_at).date()
            today = date.today()
            days = (today - created_date).days
            self.days_label.set_label(f"{days}d")
        except (ValueError, TypeError):
            self.days_label.set_label("0d")

    def _update_days_remaining(self) -> None:
        """Update the days remaining label based on end date."""
        if not self._end_date:
            self.remaining_label.set_label("")
            return

        try:
            end_date = datetime.strptime(self._end_date, "%Y-%m-%d").date()
            today = date.today()
            days = (end_date - today).days
            
            if days < 0:
                self.remaining_label.set_label(f"Overdue by {abs(days)}d")
                self.remaining_label.add_css_class("error")
            else:
                self.remaining_label.set_label(f"{days}d left")
                self.remaining_label.remove_css_class("error")
                
        except (ValueError, TypeError):
            self.remaining_label.set_label("")
