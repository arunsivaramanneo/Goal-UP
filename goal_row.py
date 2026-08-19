"""Goal row widget with expandable tasks."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, GObject
import cairo

import uuid
from edit_dialog import EditTaskDialog
from datetime import datetime, date, timedelta


class SubTaskRow(Adw.ActionRow):
    """A row widget representing a sub-task within a goal."""

    __gtype_name__ = "SubTaskRow"

    __gsignals__ = {
        "task-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "task-deleted": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "task-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "reminder-set": (GObject.SignalFlags.RUN_FIRST, None, (str,)), # date string
    }

    def __init__(self, text: str, completed: bool = False, end_date: str = "", id: str = None, parent_id: str = "", depth: int = 0, end_time: str = "", recurrence: str = "none", recurrence_days: str = "", created_at: str = None):
        super().__init__()

        self._id = id or uuid.uuid4().hex
        self._parent_id = parent_id
        self._depth = depth
        self._text = text
        self._completed = completed
        self._created_at = created_at or datetime.now().isoformat()
        self._end_date = end_date
        self._end_time = end_time
        self._completion_date = ""  # Initialized later if provided
        self._recurrence = recurrence or "none"
        self._recurrence_days = recurrence_days or ""

        self.set_title(text)
        self.set_margin_start(self._depth * 24)

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

    @property
    def end_time(self) -> str:
        return self._end_time

    @property
    def id(self) -> str:
        return self._id

    @property
    def parent_id(self) -> str:
        return self._parent_id

    @property
    def created_at(self) -> str:
        return self._created_at

    @parent_id.setter
    def parent_id(self, value: str) -> None:
        self._parent_id = value

    @property
    def recurrence(self) -> str:
        return self._recurrence

    @property
    def recurrence_days(self) -> str:
        return self._recurrence_days

    @property
    def depth(self) -> int:
        return self._depth

    @depth.setter
    def depth(self, value: int) -> None:
        self._depth = value
        self.set_margin_start(value * 24)

    def _on_check_toggled(self, button: Gtk.CheckButton) -> None:
        self._completed = button.get_active()
        if self._completed:
            self._completion_date = date.today().isoformat()
        else:
            self._completion_date = ""
        self._update_days_remaining()
        self._update_style()
        self.emit("task-toggled", self._completed)

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        """Show confirmation dialog before deletion."""
        dialog = Adw.MessageDialog(
            heading="Delete Task?",
            body="Are you sure you want to delete this task? This action cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_delete_response)
        
        # Present dialog
        root = self.get_root()
        if root:
            dialog.set_transient_for(root); dialog.present()
            
    def _on_delete_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        """Handle delete confirmation response."""
        if response == "delete":
            self.emit("task-deleted")

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        # Get list of possible parents (all OTHER tasks in this goal to avoid cycles for now)
        # This is simplified; window.py will handle complex cycle detection if needed
        # For now, just allow selecting any task that isn't this one or a descendant.
        possible_parents = []
        parent_goal = self._get_parent_goal()
        if parent_goal:
            all_tasks = parent_goal.get_tasks_with_ids()
            # Filter out self and potential descendants to avoid cycles
            descendants = self._get_descendant_ids(all_tasks)
            for t_id, t_text in all_tasks:
                if t_id != self._id and t_id not in descendants:
                    possible_parents.append((t_id, t_text))

        dialog = EditTaskDialog(self._text, self._end_date, self._parent_id, possible_parents, self._end_time, self._completion_date, self._recurrence, self._recurrence_days)
        dialog.connect("save", self._on_edit_save)
        # Find the root window to present the dialog
        root = self.get_root()
        if root:
            dialog.present(root)

    def _get_parent_goal(self):
        """Find the GoalRow containing this subtask."""
        widget = self.get_parent()
        while widget and not isinstance(widget, GoalRow):
            widget = widget.get_parent()
        return widget

    def _get_descendant_ids(self, all_tasks_data):
        """Find all recursive descendant IDs of this task."""
        # all_tasks_data is list of (id, text, parent_id)
        # Wait, get_tasks_with_ids needs to return parent_id too
        descendants = set()
        to_check = [self._id]
        
        # Need a more complete list for this
        parent_goal = self._get_parent_goal()
        if not parent_goal:
            return descendants
            
        full_tasks = parent_goal.get_tasks_full()
        
        while to_check:
            current_id = to_check.pop()
            for t in full_tasks:
                if t.get("parent_id") == current_id:
                    if t["id"] not in descendants:
                        descendants.add(t["id"])
                        to_check.append(t["id"])
        return descendants

    def _on_edit_save(self, dialog: EditTaskDialog, text: str, end_date: str, parent_id: str, end_time: str, completion_date: str, recurrence: str, recurrence_days: str) -> None:
        self._text = text
        self._end_date = end_date
        self._end_time = end_time
        self._parent_id = parent_id
        self._completion_date = completion_date
        self._recurrence = recurrence or "none"
        self._recurrence_days = recurrence_days or ""
        if self._completion_date and not self._completed:
            # If user manually sets a completion date, mark as completed
            self.check_button.set_active(True)
            self._completed = True
        elif not self._completion_date and self._completed:
             # If user clears completion date, mark as incomplete
             self.check_button.set_active(False)
             self._completed = False
        self._update_days_remaining()
        self._update_style()
        
        # Check if reminder was just set or updated
        if self._recurrence != "none" and self._end_date:
            self.emit("reminder-set", self._end_date)
            
        self.emit("task-changed", self._text)
        # Re-trigger reordering in parent goal
        parent_goal = self._get_parent_goal()
        if parent_goal:
            parent_goal.reorder_tasks()

    def _update_style(self) -> None:
        recur_sym = " 🔄" if self._recurrence != "none" else ""
        if self._completed:
            self.add_css_class("dim-label")
            self.set_title(f"<s>{self._text}{recur_sym}</s>")
            self.set_use_markup(True)
        else:
            self.remove_css_class("dim-label")
            self.set_title(f"{self._text}{recur_sym}")
            self.set_use_markup(True)

    def _update_days_remaining(self) -> None:
        """Update the days remaining label based on end date and completion status."""
        if not self._end_date and not self._completed:
            self.remaining_label.set_label("")
            return

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
            
        # Update completion info if completed
        if self._completed:
            if self._completion_date:
                self.remaining_label.set_label(f"Completed on {self._completion_date}")
            else:
                self.remaining_label.set_label("Completed")
            self.remaining_label.remove_css_class("error")


class GoalRow(Adw.ExpanderRow):
    """An expandable row widget representing a goal with sub-tasks."""

    __gtype_name__ = "GoalRow"

    __gsignals__ = {
        "goal-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "goal-deleted": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "edit-requested": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "reminder-set": (GObject.SignalFlags.RUN_FIRST, None, (str, str)), # task_text, date
    }

    def __init__(self, title: str, description: str = "", completed: bool = False, tasks: list = None, created_at: str = None, end_date: str = "", id: str = None, parent_id: str = "", depth: int = 0, color: str = None, end_time: str = "", recurrence: str = "none", recurrence_days: str = ""):
        super().__init__()

        self._id = id or uuid.uuid4().hex
        self._parent_id = parent_id
        self._depth = depth
        self._title = title
        self._description = description
        self._completed = completed
        self._tasks = tasks or []
        self._subtask_rows = []  # Track sub-task rows for persistence
        self._created_at = created_at or datetime.now().isoformat()
        self._end_date = end_date or ""
        self._end_time = end_time or ""
        self._completion_date = ""  # Initialized later if provided
        self._color = color or "rgb(53,132,228)" # Default blue
        self._recurrence = recurrence or "none"
        self._recurrence_days = recurrence_days or ""

        self.set_title(title)
        if description:
            self.set_subtitle(description)
        
        self.set_margin_start(self._depth * 24)

        # Color indicator
        self.color_indicator = Gtk.Image.new_from_icon_name("media-record-symbolic")
        self.color_indicator.set_valign(Gtk.Align.CENTER)
        
        # We need to parse color string to Gdk.RGBA to set it
        rgba = Gdk.RGBA()
        if rgba.parse(self._color):
            # Create a snapshot to draw the colored circle? 
            # Or just use CSS. But CSS is hard with dynamic colors.
            # Best is to use custom drawing or a snapshot. 
            # Actually Gtk.Image doesn't easily support arbitrary colors without CSS provider.
            # Let's try drawing a crude circle with Gtk.DrawingArea? Too heavy.
            # Let's use CSS provider with a unique class name? Maybe too many classes.
            # Let's use a Gtk.Box with a background color using CSS (but inline style is not supported directly in Gtk4 without parsing).
            # Actually, we can use Gtk.Widget.set_cursor or something? No.
            
            # Use a simple helper to apply color to the icon?
            # In Gtk4, we can use a custom paintable?
            # Or simpler: Just use a label with a colored unicode circle? 🔴 🟠 🟡 🟢 🔵 🟣 🟤 ⚫ ⚪
            # But user can pick ANY color.
            
            # Let's try inserting a small DrawingArea.
            self.color_indicator = Gtk.DrawingArea()
            self.color_indicator.set_content_width(12)
            self.color_indicator.set_content_height(12)
            self.color_indicator.set_valign(Gtk.Align.CENTER)
            self.color_indicator.set_draw_func(self._draw_color_indicator)
            
        self.add_prefix(self.color_indicator)

        self.set_title(title)
        if description:
            self.set_subtitle(description)
        
        self.set_margin_start(self._depth * 24)

        # Checkbox for goal completion
        self.check_button = Gtk.CheckButton()
        self.check_button.set_active(completed)
        self.check_button.set_valign(Gtk.Align.CENTER)
        self.check_button.connect("toggled", self._on_check_toggled)
        self.add_prefix(self.check_button)

        # Percentage completion label
        self.progress_label = Gtk.Label(label="0%")
        self.count_label = Gtk.Label(label="0/0")
        self.days_label = Gtk.Label(label="0d")
        self.remaining_label = Gtk.Label(label="")

        self._update_days_elapsed()
        self._update_days_remaining()
        self._update_subtitle()

        # Add task entry row (at the top)
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

        # Add the "Add Task" row first (at the top)
        self.add_row(self._add_task_row)

        # Load existing tasks (they will appear below the Add Task row)
        if tasks:
            # We'll re-add them in window/_load_goals or use a helper
            # But here we need to handle the structure.
            # For now, just add them as flat, window.py will handle the full hierarchy.
            for task in tasks:
                self._add_subtask_from_dict(task)

        self._extend_end_date_to_tasks()
        self.reorder_tasks()

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

    @property
    def end_time(self) -> str:
        return self._end_time

    @property
    def id(self) -> str:
        return self._id

    @property
    def parent_id(self) -> str:
        return self._parent_id

    @parent_id.setter
    def parent_id(self, value: str) -> None:
        self._parent_id = value

    @property
    def depth(self) -> int:
        return self._depth

    @depth.setter
    def depth(self, value: int) -> None:
        self._depth = value
        self.set_margin_start(value * 24)

    @property
    def recurrence(self) -> str:
        return self._recurrence

    @property
    def recurrence_days(self) -> str:
        return self._recurrence_days

    def get_tasks(self) -> list:
        """Get all sub-tasks as list of dicts."""
        tasks = []
        for row in self._subtask_rows:
            tasks.append({
                "id": row.id,
                "parent_id": row.parent_id,
                "text": row.task_text,
                "completed": row.completed,
                "end_date": row.end_date,
                "end_time": row.end_time,
                "completion_date": getattr(row, "_completion_date", ""),
                "created_at": row.created_at,
                "recurrence": row.recurrence,
                "recurrence_days": row.recurrence_days
            })
        return tasks

    def get_tasks_full(self) -> list:
        """Alias for get_tasks() used for internal logic."""
        return self.get_tasks()

    def get_tasks_with_ids(self) -> list[tuple[str, str]]:
        """Return list of (id, text) for possible parents."""
        return [(row.id, row.task_text) for row in self._subtask_rows]

    @property
    def color(self) -> str:
        return self._color

    def update_details(self, title: str, description: str, end_date: str = "", parent_id: str = "", color: str = None, end_time: str = "", completion_date: str = "") -> None:
        """Update goal details including completion date."""
        self._title = title
        self._description = description
        self._end_date = end_date
        self._end_time = end_time
        self._parent_id = parent_id
        self._completion_date = completion_date
        self._extend_end_date_to_tasks()
        
        if self._completion_date and not self._completed:
            self.check_button.set_active(True)
            self._completed = True
        elif not self._completion_date and self._completed:
            self.check_button.set_active(False)
            self._completed = False

        if color:
            self._color = color
            self.color_indicator.queue_draw()
            
        self.set_title(title)
        self._update_days_remaining()
        self._update_subtitle()
        self.emit("goal-changed")

    def _draw_color_indicator(self, area, cr: cairo.Context, width: int, height: int) -> None:
        """Draw the color indicator circle."""
        rgba = Gdk.RGBA()
        if rgba.parse(self._color):
            cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
        else:
            cr.set_source_rgb(0.2, 0.5, 0.8) # Fallback blue
            
        # Draw circle
        radius = min(width, height) / 2
        cr.arc(width / 2, height / 2, radius, 0, 2 * 3.14159)
        cr.fill()

    def _add_subtask(self, text: str, completed: bool, end_date: str = "", id: str = None, parent_id: str = "", depth: int = 0, end_time: str = "", recurrence: str = "none", recurrence_days: str = "", created_at: str = None) -> SubTaskRow:
        """Add a sub-task row."""
        row = SubTaskRow(text, completed, end_date, id, parent_id, depth, end_time, recurrence, recurrence_days, created_at)
        row.connect("task-toggled", self._on_subtask_toggled)
        row.connect("task-changed", self._on_subtask_changed)
        row.connect("task-deleted", self._on_subtask_deleted, row)
        row.connect("reminder-set", self._on_reminder_set)
        self._subtask_rows.append(row)
        self.add_row(row)
        return row
        
    def _add_subtask_from_dict(self, task: dict) -> SubTaskRow:
        row = self._add_subtask(
            task.get("text", ""),
            task.get("completed", False),
            task.get("end_date", ""),
            task.get("id"),
            task.get("parent_id", ""),
            task.get("depth", 0),
            task.get("end_time", ""),
            task.get("recurrence", "none"),
            task.get("recurrence_days", ""),
            task.get("created_at")
        )
        if row and task.get("completion_date"):
            row._completion_date = task["completion_date"]
            row._update_days_remaining()
        return row

    def reorder_tasks(self) -> None:
        """Reorder subtask rows to show hierarchy and update indentation."""
        # This will remove all rows and re-add them in depth-first order
        # We need to preserve the "Add Task" row at the top.
        
        # 1. Identify hierarchy
        # Sort _subtask_rows before building hierarchy to ensure consistent ordering within groups
        self._subtask_rows.sort(key=lambda r: (
            r.completed,
            r.end_date == "",
            r.end_date,
            r.end_time
        ))

        tasks_by_parent = {}
        top_level = []
        rows_by_id = {row.id: row for row in self._subtask_rows}
        
        for row in self._subtask_rows:
            p_id = row.parent_id
            if not p_id or p_id not in rows_by_id:
                top_level.append(row)
            else:
                if p_id not in tasks_by_parent:
                    tasks_by_parent[p_id] = []
                tasks_by_parent[p_id].append(row)
        
        # 2. Flatten hierarchy in DFS order
        ordered_rows = []
        def dfs(rows, depth):
            for r in rows:
                r.depth = depth
                ordered_rows.append(r)
                if r.id in tasks_by_parent:
                    dfs(tasks_by_parent[r.id], depth + 1)
        
        dfs(top_level, 0)
        
        # 3. Update the UI
        # Removing and re-adding might be flickery, but it's the simplest way with Gtk.ListBox via Adw.ExpanderRow
        # Adw.ExpanderRow manages its own internal listbox.
        
        # We need to find the internal listbox to reorder.
        # Actually, since we use `add_row`, we can't easily reorder without removing.
        # Let's hope removing and re-adding is fine.
        
        # First, detach all rows EXCEPT the "Add Task" row
        for row in self._subtask_rows:
            self.remove(row)
        
        # Re-add in order AFTER the "Add Task" row
        # Adw.ExpanderRow.add_row appends. So we need to remove "Add Task" row too and re-add it at the top.
        self.remove(self._add_task_row)
        
        # Add "Add Task" row first (at the top)
        self.add_row(self._add_task_row)
        
        # Then add all task rows in order
        for row in ordered_rows:
            self.add_row(row)
        
        # Update our internal list to match the new order for next time
        self._subtask_rows = ordered_rows

    def _on_reminder_set(self, row: SubTaskRow, date_str: str) -> None:
        """Bubble up reminder-set signal."""
        self.emit("reminder-set", row.task_text, date_str)

    def _on_subtask_toggled(self, row: SubTaskRow, completed: bool) -> None:
        """Handle sub-task toggle."""
        if completed and row.recurrence != "none":
            # Generate next occurrence
            self._handle_recurrence(row)
            
        self._update_progress()
        self._check_auto_complete()
        self.emit("goal-changed")

    def _check_auto_complete(self) -> None:
        """Auto-complete the goal when every task under it is complete."""
        tasks = self.get_tasks()
        if not tasks:
            return  # No tasks → don't auto-complete
        if self._completed:
            return  # Already complete

        if all(t.get("completed", False) for t in tasks):
            # Determine the most recent task completion date
            completion_dates = []
            for t in tasks:
                ds = t.get("completion_date") or t.get("end_date")
                if ds:
                    completion_dates.append(ds)
            if completion_dates:
                last_date = max(completion_dates)
            else:
                last_date = date.today().isoformat()

            self._completion_date = last_date
            self._completed = True
            # Update the checkbox without triggering _on_check_toggled recursively
            self.check_button.handler_block_by_func(self._on_check_toggled)
            self.check_button.set_active(True)
            self.check_button.handler_unblock_by_func(self._on_check_toggled)
            self._update_style()
            self._update_days_remaining()

    def _handle_recurrence(self, row: SubTaskRow) -> None:
        """Create the next instance of a recurring task."""
        current_date_str = row.end_date or date.today().isoformat()
        next_date = self.calculate_next_recurrence(current_date_str, row.recurrence, row.recurrence_days)
        
        if next_date:
            self._add_subtask(
                row.task_text,
                False,
                next_date.isoformat(),
                None,
                row.parent_id,
                row.depth,
                row.end_time,
                row.recurrence,
                row.recurrence_days
            )
            # Reorder to place new task correctly
            self.reorder_tasks()

    def calculate_next_recurrence(self, current_date_str: str, recurrence: str, recurrence_days: str) -> date | None:
        """Calculate the next date based on recurrence rules."""
        try:
            current_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            current_date = date.today()

        if recurrence == "daily":
            return current_date + timedelta(days=1)
        
        elif recurrence == "monthly":
            # Rough monthly jump
            month = current_date.month % 12 + 1
            year = current_date.year + (current_date.month // 12)
            try:
                return current_date.replace(year=year, month=month)
            except ValueError:
                # Handle end of month issues (e.g. Jan 31 -> Feb 28)
                return (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
        elif recurrence == "weekly":
            if not recurrence_days:
                return current_date + timedelta(days=7)
            
            allowed_days = [int(d) for d in recurrence_days.split(",") if d.strip()]
            if not allowed_days:
                return current_date + timedelta(days=7)
            
            # Find next allowed day
            # Gtk/Python weekday is 0-6 (Mon-Sun)
            current_weekday = current_date.weekday()
            
            for i in range(1, 8):
                next_candidate = current_date + timedelta(days=i)
                if next_candidate.weekday() in allowed_days:
                    return next_candidate
                    
        return None

    def _on_subtask_changed(self, row: SubTaskRow, text: str) -> None:
        """Handle sub-task change."""
        self._extend_end_date_to_tasks()
        self.emit("goal-changed")

    def _on_add_task(self, widget: Gtk.Widget) -> None:
        """Handle add task action."""
        text = self.task_entry.get_text().strip()
        if not text:
            return
        possible_parents = [(row.id, row.task_text) for row in self._subtask_rows]
        dialog = EditTaskDialog(text, possible_parents=possible_parents)
        dialog.connect("save", self._on_new_task_save)
        root = self.get_root()
        if root:
            dialog.present(root)

    def _on_new_task_save(self, dialog: EditTaskDialog, text: str, end_date: str, parent_id: str, end_time: str, completion_date: str, recurrence: str, recurrence_days: str) -> None:
        """Add a task created through the quick-add field."""
        self._add_subtask(text, False, end_date=end_date, parent_id=parent_id, end_time=end_time, recurrence=recurrence, recurrence_days=recurrence_days)
        self.task_entry.set_text("")
        self._extend_end_date_to_tasks()
        self.reorder_tasks()
        self._update_progress()
        self.emit("goal-changed")

    def _extend_end_date_to_tasks(self) -> None:
        """Keep the goal end date at least as late as every task date."""
        task_dates = []
        for task in self._subtask_rows:
            if not task.end_date:
                continue
            try:
                task_dates.append(datetime.strptime(task.end_date, "%Y-%m-%d").date())
            except (TypeError, ValueError):
                continue

        if not task_dates:
            return

        latest_task_date = max(task_dates)
        try:
            goal_date = datetime.strptime(self._end_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            goal_date = None

        if goal_date is None or latest_task_date > goal_date:
            self._end_date = latest_task_date.isoformat()
            self._update_days_remaining()

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
            self._completion_date = date.today().isoformat()
        else:
            self._completion_date = ""
        self._update_style()
        self.emit("goal-changed")

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        self.emit("edit-requested")

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        """Show confirmation dialog before deletion."""
        dialog = Adw.MessageDialog(
            heading="Delete Goal?",
            body="Are you sure you want to delete this goal? All sub-tasks will also be deleted. This action cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_delete_response)
        
        # Present dialog
        root = self.get_root()
        if root:
            dialog.set_transient_for(root); dialog.present()

    def _on_delete_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        """Handle delete confirmation response."""
        if response == "delete":
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
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        """Update the consolidated subtitle with all details."""
        lines = []
        if self._description:
            lines.append(self._description)
        
        details = []
        details.append(f"<b>Progress:</b> {self.progress_label.get_label()}")
        details.append(f"<b>Tasks:</b> {self.count_label.get_label()}")
        details.append(f"<b>Age:</b> {self.days_label.get_label()}")
        
        status = self.remaining_label.get_label()
        if status:
            details.append(f"<b>Status:</b> {status}")
        
        lines.append(" | ".join(details))
        
        self.set_subtitle("\n".join(lines))
    def _update_days_elapsed(self) -> None:
        """Update the days elapsed label based on creation date."""
        try:
            created_date = datetime.fromisoformat(self._created_at).date()
            today = date.today()
            days = (today - created_date).days
            self.days_label.set_label(f"{days}d")
            self._update_subtitle()
        except (ValueError, TypeError):
            self.days_label.set_label("0d")

    def _update_days_remaining(self) -> None:
        """Update the days remaining label based on end date and completion status."""
        if self._completed:
            if self._completion_date:
                self.remaining_label.set_label(f"Completed on {self._completion_date}")
            else:
                self.remaining_label.set_label("Completed")
            self.remaining_label.remove_css_class("error")
            return

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
        
        if self._completed:
            if self._completion_date:
                self.remaining_label.set_label(f"Completed on {self._completion_date}")
            else:
                self.remaining_label.set_label("Completed")
            self.remaining_label.remove_css_class("error")
        
        self._update_subtitle()
