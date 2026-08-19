"""Edit dialog for Goal details."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, GObject, GLib
from datetime import datetime, date


class EditGoalDialog(Adw.Dialog):
    """Dialog for editing goal title, description, and end date."""

    __gtype_name__ = "EditGoalDialog"

    __gsignals__ = {
        "save": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str, str, str, str)),  # title, description, end_date, parent_id, color, end_time, completion_date
    }

    def __init__(self, title: str = "", description: str = "", end_date: str = "", parent_id: str = "", color: str = "", possible_parents: list[tuple[str, str]] = None, end_time: str = "", completion_date: str = ""):
        super().__init__()

        self._parent_id = parent_id
        self._possible_parents = possible_parents or [] # List of (id, title)
        self._initial_color = color or "rgb(53,132,228)"
        self._chosen_time = end_time
        self._chosen_completion_date = completion_date

        self.set_title("Edit Goal")
        self.set_content_width(400)
        self.set_content_height(550)

        # Main layout
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_button)

        save_button = Gtk.Button(label="Save")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_clicked)
        header.pack_end(save_button)

        toolbar_view.add_top_bar(header)

        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        toolbar_view.set_content(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        clamp.set_child(content_box)

        # Title group
        title_group = Adw.PreferencesGroup()
        title_group.set_title("Goal Title")
        content_box.append(title_group)

        self.title_row = Adw.EntryRow()
        self.title_row.set_title("Title")
        self.title_row.set_text(title)
        title_group.add(self.title_row)

        # Description group
        desc_group = Adw.PreferencesGroup()
        desc_group.set_title("Description")
        content_box.append(desc_group)

        self.desc_row = Adw.EntryRow()
        self.desc_row.set_title("Description")
        self.desc_row.set_text(description)
        desc_group.add(self.desc_row)

        # End date group (Required)
        date_group = Adw.PreferencesGroup()
        date_group.set_title("End Date (Required)")
        content_box.append(date_group)

        self._chosen_date = end_date

        self.date_row = Adw.ActionRow()
        self.date_row.set_title("End Date")
        self.date_row.set_subtitle(self._chosen_date or "No date set")
        date_group.add(self.date_row)

        # Date picker button
        self.pick_date_btn = Gtk.Button()
        self.pick_date_btn.set_icon_name("calendar-symbolic")
        self.pick_date_btn.set_valign(Gtk.Align.CENTER)
        self.pick_date_btn.add_css_class("flat")
        self.pick_date_btn.connect("clicked", self._on_pick_date_clicked)
        self.date_row.add_suffix(self.pick_date_btn)

        # Clear date button
        clear_date_btn = Gtk.Button(label="Clear")
        clear_date_btn.add_css_class("flat")
        clear_date_btn.set_valign(Gtk.Align.CENTER)
        clear_date_btn.connect("clicked", self._on_clear_date_clicked)
        self.date_row.add_suffix(clear_date_btn)

        # End time group (optional)
        time_group = Adw.PreferencesGroup()
        time_group.set_title("End Time (Optional)")
        content_box.append(time_group)

        self.time_row = Adw.ActionRow()
        self.time_row.set_title("End Time")
        self.time_row.set_subtitle(end_time or "No time set")
        time_group.add(self.time_row)

        # Time picker button
        self.pick_time_btn = Gtk.Button()
        self.pick_time_btn.set_icon_name("document-properties-symbolic")
        self.pick_time_btn.set_valign(Gtk.Align.CENTER)
        self.pick_time_btn.add_css_class("flat")
        self.pick_time_btn.connect("clicked", self._on_pick_time_clicked)
        self.time_row.add_suffix(self.pick_time_btn)

        # Clear time button
        clear_time_btn = Gtk.Button(label="Clear")
        clear_time_btn.add_css_class("flat")
        clear_time_btn.set_valign(Gtk.Align.CENTER)
        clear_time_btn.connect("clicked", self._on_clear_time_clicked)
        self.time_row.add_suffix(clear_time_btn)

        # Completion date group (optional)
        comp_date_group = Adw.PreferencesGroup()
        comp_date_group.set_title("Completion Date (Optional)")
        content_box.append(comp_date_group)

        self.comp_date_row = Adw.ActionRow()
        self.comp_date_row.set_title("Completion Date")
        self.comp_date_row.set_subtitle(completion_date or "Not completed")
        comp_date_group.add(self.comp_date_row)

        # Completion date picker button
        self.pick_comp_date_btn = Gtk.Button()
        self.pick_comp_date_btn.set_icon_name("calendar-check-symbolic")
        self.pick_comp_date_btn.set_valign(Gtk.Align.CENTER)
        self.pick_comp_date_btn.add_css_class("flat")
        self.pick_comp_date_btn.connect("clicked", self._on_pick_comp_date_clicked)
        self.comp_date_row.add_suffix(self.pick_comp_date_btn)

        # Clear completion date button
        clear_comp_date_btn = Gtk.Button(label="Clear")
        clear_comp_date_btn.add_css_class("flat")
        clear_comp_date_btn.set_valign(Gtk.Align.CENTER)
        clear_comp_date_btn.connect("clicked", self._on_clear_comp_date_clicked)
        self.comp_date_row.add_suffix(clear_comp_date_btn)

        # Parent Selection group (Optional)
        parent_group = Adw.PreferencesGroup()
        parent_group.set_title("Dependency")
        content_box.append(parent_group)

        self.parent_row = Adw.ComboRow()
        self.parent_row.set_title("Parent Goal")
        self.parent_row.set_subtitle("Optional: Select a goal this one depends on")
        
        # Add "None" option
        model = Gtk.StringList()
        model.append("None")
        
        selected_index = 0
        for i, (p_id, p_title) in enumerate(self._possible_parents):
            model.append(p_title)
            if p_id == self._parent_id:
                selected_index = i + 1
        
        self.parent_row.set_model(model)
        self.parent_row.set_selected(selected_index)
        parent_group.add(self.parent_row)

        # Appearance group
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title("Appearance")
        content_box.append(appearance_group)
        
        self.color_row = Adw.ActionRow()
        self.color_row.set_title("Goal Color")
        appearance_group.add(self.color_row)
        
        self.color_button = Gtk.ColorButton()
        self.color_button.set_valign(Gtk.Align.CENTER)
        
        # Set initial color
        color = Gdk.RGBA()
        if color.parse(self._initial_color):
            self.color_button.set_rgba(color)
            
        self.color_row.add_suffix(self.color_button)

    def _on_pick_date_clicked(self, button: Gtk.Button) -> None:
        """Open a calendar popover."""
        print("Pick Date clicked")
        self._popover = Gtk.Popover()
        self._popover.set_parent(button)
        self._popover.set_autohide(True)
        
        calendar = Gtk.Calendar()
        # Set existing date if any
        if self._chosen_date:
            try:
                dt = datetime.strptime(self._chosen_date, "%Y-%m-%d")
                gdt = GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0)
                calendar.select_day(gdt)
                print(f"Calendar pre-selected: {self._chosen_date}")
            except Exception as e:
                print(f"Error setting calendar date: {e}")
                
        calendar.connect("day-selected", self._on_day_selected, self._popover)
        self._popover.set_child(calendar)
        self._popover.popup()

    def _on_day_selected(self, calendar: Gtk.Calendar, popover: Gtk.Popover) -> None:
        """Handle date selection in calendar."""
        gdt = calendar.get_date()
        year = gdt.get_year()
        month = gdt.get_month()
        day = gdt.get_day_of_month()
        
        self._chosen_date = f"{year:04d}-{month:02d}-{day:02d}"
        print(f"Date selected: {self._chosen_date}")
        self.date_row.set_subtitle(self._chosen_date)
        popover.popdown()

    def _on_clear_date_clicked(self, button: Gtk.Button) -> None:
        """Clear the chosen date."""
        self._chosen_date = ""
        self.date_row.set_subtitle("No date set")

    def _on_pick_comp_date_clicked(self, button: Gtk.Button) -> None:
        """Open a calendar popover for completion date."""
        self._comp_popover = Gtk.Popover()
        self._comp_popover.set_parent(button)
        self._comp_popover.set_autohide(True)
        
        calendar = Gtk.Calendar()
        if self._chosen_completion_date:
            try:
                dt = datetime.strptime(self._chosen_completion_date, "%Y-%m-%d")
                gdt = GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0)
                calendar.select_day(gdt)
            except: pass
                
        calendar.connect("day-selected", self._on_comp_day_selected, self._comp_popover)
        self._comp_popover.set_child(calendar)
        self._comp_popover.popup()

    def _on_comp_day_selected(self, calendar: Gtk.Calendar, popover: Gtk.Popover) -> None:
        """Handle completion date selection."""
        gdt = calendar.get_date()
        self._chosen_completion_date = f"{gdt.get_year():04d}-{gdt.get_month():02d}-{gdt.get_day_of_month():02d}"
        self.comp_date_row.set_subtitle(self._chosen_completion_date)
        popover.popdown()

    def _on_clear_comp_date_clicked(self, button: Gtk.Button) -> None:
        """Clear the completion date."""
        self._chosen_completion_date = ""
        self.comp_date_row.set_subtitle("Not completed")

    def _on_pick_time_clicked(self, button: Gtk.Button) -> None:
        """Open a time picker popover."""
        self._time_popover = Gtk.Popover()
        self._time_popover.set_parent(button)
        self._time_popover.set_autohide(True)

        # Time picker box
        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        time_box.set_margin_top(12)
        time_box.set_margin_bottom(12)
        time_box.set_margin_start(12)
        time_box.set_margin_end(12)

        # Hour spin button
        hour_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hour_label = Gtk.Label(label="Hour:")
        hour_label.set_size_request(40, -1)
        hour_adjustment = Gtk.Adjustment(value=0, lower=0, upper=23, step_increment=1)
        self.hour_spin = Gtk.SpinButton(adjustment=hour_adjustment)
        self.hour_spin.set_numeric(True)
        self.hour_spin.set_digits(0)
        hour_box.append(hour_label)
        hour_box.append(self.hour_spin)

        # Minute spin button
        minute_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        minute_label = Gtk.Label(label="Minute:")
        minute_label.set_size_request(40, -1)
        minute_adjustment = Gtk.Adjustment(value=0, lower=0, upper=59, step_increment=1)
        self.minute_spin = Gtk.SpinButton(adjustment=minute_adjustment)
        self.minute_spin.set_numeric(True)
        self.minute_spin.set_digits(0)
        minute_box.append(minute_label)
        minute_box.append(self.minute_spin)

        # Parse existing time if available
        if self._chosen_time:
            try:
                parts = self._chosen_time.split(":")
                self.hour_spin.set_value(int(parts[0]))
                self.minute_spin.set_value(int(parts[1]))
            except (ValueError, IndexError):
                pass

        time_box.append(hour_box)
        time_box.append(minute_box)

        # OK button
        ok_button = Gtk.Button(label="OK")
        ok_button.add_css_class("suggested-action")
        ok_button.connect("clicked", self._on_time_selected, self._time_popover)
        time_box.append(ok_button)

        self._time_popover.set_child(time_box)
        self._time_popover.popup()

    def _on_time_selected(self, button: Gtk.Button, popover: Gtk.Popover) -> None:
        """Handle time selection."""
        hour = int(self.hour_spin.get_value())
        minute = int(self.minute_spin.get_value())
        self._chosen_time = f"{hour:02d}:{minute:02d}"
        self.time_row.set_subtitle(self._chosen_time)
        popover.popdown()

    def _on_clear_time_clicked(self, button: Gtk.Button) -> None:
        """Clear the chosen time."""
        self._chosen_time = ""
        self.time_row.set_subtitle("No time set")

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        """Handle save button click."""
        title = self.title_row.get_text().strip()
        description = self.desc_row.get_text().strip()
        end_date = self._chosen_date

        if not title:
            dialog = Adw.MessageDialog(
                heading="Missing Title",
                body="Please enter a title for the goal."
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return

        if not end_date:
            dialog = Adw.MessageDialog(
                heading="Missing End Date",
                body="Goals without an end date will remain Dreams"
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return

        parent_idx = self.parent_row.get_selected()
        if parent_idx == 0:
            parent_id = ""
        else:
            parent_id = self._possible_parents[parent_idx - 1][0]
        
        color = self.color_button.get_rgba().to_string()
        self.emit("save", title, description, end_date, parent_id, color, self._chosen_time, self._chosen_completion_date)
        self.close()


class EditTaskDialog(Adw.Dialog):
    """Dialog for editing a sub-task."""

    __gtype_name__ = "EditTaskDialog"

    __gsignals__ = {
        "save": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str, str, str, str)),  # text, end_date, parent_id, end_time, completion_date, recurrence, recurrence_days
    }

    def __init__(self, text: str = "", end_date: str = "", parent_id: str = "", possible_parents: list[tuple[str, str]] = None, end_time: str = "", completion_date: str = "", recurrence: str = "none", recurrence_days: str = ""):
        super().__init__()

        self._parent_id = parent_id
        self._possible_parents = possible_parents or []
        self._chosen_time = end_time
        self._chosen_completion_date = completion_date
        self._recurrence = recurrence or "none"
        self._recurrence_days = recurrence_days or ""

        self.set_title("Edit Task")
        self.set_content_width(400)
        self.set_content_height(500)

        # Main layout
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_button)

        save_button = Gtk.Button(label="Save")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_clicked)
        header.pack_end(save_button)

        toolbar_view.add_top_bar(header)

        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        toolbar_view.set_content(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        clamp.set_child(content_box)

        # Task text group
        group = Adw.PreferencesGroup()
        group.set_title("Task")
        content_box.append(group)

        self.text_row = Adw.EntryRow()
        self.text_row.set_title("Task Description")
        self.text_row.set_text(text)
        group.add(self.text_row)

        # End date group (Required)
        date_group = Adw.PreferencesGroup()
        date_group.set_title("End Date (Required)")
        content_box.append(date_group)

        self._chosen_date = end_date

        self.date_row = Adw.ActionRow()
        self.date_row.set_title("End Date")
        self.date_row.set_subtitle(self._chosen_date or "No date set")
        date_group.add(self.date_row)

        # Date picker button
        self.pick_date_btn = Gtk.Button()
        self.pick_date_btn.set_icon_name("calendar-symbolic")
        self.pick_date_btn.set_valign(Gtk.Align.CENTER)
        self.pick_date_btn.add_css_class("flat")
        self.pick_date_btn.connect("clicked", self._on_pick_date_clicked)
        self.date_row.add_suffix(self.pick_date_btn)

        # Clear date button
        clear_date_btn = Gtk.Button(label="Clear")
        clear_date_btn.add_css_class("flat")
        clear_date_btn.set_valign(Gtk.Align.CENTER)
        clear_date_btn.connect("clicked", self._on_clear_date_clicked)
        self.date_row.add_suffix(clear_date_btn)

        # End time group (optional)
        time_group = Adw.PreferencesGroup()
        time_group.set_title("End Time (Optional)")
        content_box.append(time_group)

        self.time_row = Adw.ActionRow()
        self.time_row.set_title("End Time")
        self.time_row.set_subtitle(end_time or "No time set")
        time_group.add(self.time_row)

        # Time picker button
        self.pick_time_btn = Gtk.Button()
        self.pick_time_btn.set_icon_name("document-properties-symbolic")
        self.pick_time_btn.set_valign(Gtk.Align.CENTER)
        self.pick_time_btn.add_css_class("flat")
        self.pick_time_btn.connect("clicked", self._on_pick_time_clicked)
        self.time_row.add_suffix(self.pick_time_btn)

        # Clear time button
        clear_time_btn = Gtk.Button(label="Clear")
        clear_time_btn.add_css_class("flat")
        clear_time_btn.set_valign(Gtk.Align.CENTER)
        clear_time_btn.connect("clicked", self._on_clear_time_clicked)
        self.time_row.add_suffix(clear_time_btn)

        # Completion date group (optional)
        comp_date_group = Adw.PreferencesGroup()
        comp_date_group.set_title("Completion Date (Optional)")
        content_box.append(comp_date_group)

        self.comp_date_row = Adw.ActionRow()
        self.comp_date_row.set_title("Completion Date")
        self.comp_date_row.set_subtitle(completion_date or "Not completed")
        comp_date_group.add(self.comp_date_row)

        # Completion date picker button
        self.pick_comp_date_btn = Gtk.Button()
        self.pick_comp_date_btn.set_icon_name("calendar-check-symbolic")
        self.pick_comp_date_btn.set_valign(Gtk.Align.CENTER)
        self.pick_comp_date_btn.add_css_class("flat")
        self.pick_comp_date_btn.connect("clicked", self._on_pick_comp_date_clicked)
        self.comp_date_row.add_suffix(self.pick_comp_date_btn)

        # Clear completion date button
        clear_comp_date_btn = Gtk.Button(label="Clear")
        clear_comp_date_btn.add_css_class("flat")
        clear_comp_date_btn.set_valign(Gtk.Align.CENTER)
        clear_comp_date_btn.connect("clicked", self._on_clear_comp_date_clicked)
        self.comp_date_row.add_suffix(clear_comp_date_btn)

        # Parent Selection group (Optional)
        parent_group = Adw.PreferencesGroup()
        parent_group.set_title("Dependency")
        content_box.append(parent_group)

        self.parent_row = Adw.ComboRow()
        self.parent_row.set_title("Parent Task")
        self.parent_row.set_subtitle("Optional: Select a task this one depends on")
        
        model = Gtk.StringList()
        model.append("None")
        
        selected_index = 0
        for i, (p_id, p_title) in enumerate(self._possible_parents):
            model.append(p_title)
            if p_id == self._parent_id:
                selected_index = i + 1
        
        self.parent_row.set_model(model)
        self.parent_row.set_selected(selected_index)
        parent_group.add(self.parent_row)

        # Reminder group
        reminder_group = Adw.PreferencesGroup()
        reminder_group.set_title("Reminder")
        content_box.append(reminder_group)

        self.recurrence_row = Adw.ComboRow()
        self.recurrence_row.set_title("Type")
        recurrence_model = Gtk.StringList()
        recurrence_options = ["None", "Daily", "Weekly", "Monthly"]
        for opt in recurrence_options:
            recurrence_model.append(opt)
        
        self.recurrence_row.set_model(recurrence_model)
        
        # Set selected recurrence
        initial_recurrence_idx = 0
        if self._recurrence.lower() in [o.lower() for o in recurrence_options]:
            initial_recurrence_idx = [o.lower() for o in recurrence_options].index(self._recurrence.lower())
        self.recurrence_row.set_selected(initial_recurrence_idx)
        self.recurrence_row.connect("notify::selected", self._on_recurrence_changed)
        reminder_group.add(self.recurrence_row)

        # Days of week for weekly recurrence
        self.days_row = Adw.ActionRow()
        self.days_row.set_title("Days of Week")
        self.days_row.set_visible(self._recurrence.lower() == "weekly")
        reminder_group.add(self.days_row)

        days_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        days_box.set_valign(Gtk.Align.CENTER)
        self.days_row.add_suffix(days_box)

        self.day_buttons = []
        day_labels = ["M", "T", "W", "T", "F", "S", "S"]
        active_days = self._recurrence_days.split(",") if self._recurrence_days else []
        
        for i, label in enumerate(day_labels):
            btn = Gtk.ToggleButton(label=label)
            btn.add_css_class("circular")
            if str(i) in active_days:
                btn.set_active(True)
            days_box.append(btn)
            self.day_buttons.append(btn)

    def _on_recurrence_changed(self, row: Adw.ComboRow, pspec) -> None:
        """Handle recurrence change."""
        selected_idx = row.get_selected()
        # Options: None, Daily, Weekly, Monthly
        # Weekly is index 2
        self.days_row.set_visible(selected_idx == 2)

    def _on_pick_date_clicked(self, button: Gtk.Button) -> None:
        """Open a calendar popover."""
        print("Task Pick Date clicked")
        self._popover = Gtk.Popover()
        self._popover.set_parent(button)
        self._popover.set_autohide(True)
        
        calendar = Gtk.Calendar()
        if self._chosen_date:
            try:
                dt = datetime.strptime(self._chosen_date, "%Y-%m-%d")
                gdt = GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0)
                calendar.select_day(gdt)
                print(f"Task Calendar pre-selected: {self._chosen_date}")
            except Exception as e:
                print(f"Error setting task calendar date: {e}")
                
        calendar.connect("day-selected", self._on_day_selected, self._popover)
        self._popover.set_child(calendar)
        self._popover.popup()

    def _on_day_selected(self, calendar: Gtk.Calendar, popover: Gtk.Popover) -> None:
        """Handle date selection in calendar."""
        gdt = calendar.get_date()
        year = gdt.get_year()
        month = gdt.get_month()
        day = gdt.get_day_of_month()
        
        self._chosen_date = f"{year:04d}-{month:02d}-{day:02d}"
        print(f"Task Date selected: {self._chosen_date}")
        self.date_row.set_subtitle(self._chosen_date)
        popover.popdown()

    def _on_clear_date_clicked(self, button: Gtk.Button) -> None:
        """Clear the chosen date."""
        self._chosen_date = ""
        self.date_row.set_subtitle("No date set")

    def _on_pick_comp_date_clicked(self, button: Gtk.Button) -> None:
        """Open a calendar popover for completion date."""
        self._comp_popover = Gtk.Popover()
        self._comp_popover.set_parent(button)
        self._comp_popover.set_autohide(True)
        
        calendar = Gtk.Calendar()
        if self._chosen_completion_date:
            try:
                dt = datetime.strptime(self._chosen_completion_date, "%Y-%m-%d")
                gdt = GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0)
                calendar.select_day(gdt)
            except: pass
                
        calendar.connect("day-selected", self._on_comp_day_selected, self._comp_popover)
        self._comp_popover.set_child(calendar)
        self._comp_popover.popup()

    def _on_comp_day_selected(self, calendar: Gtk.Calendar, popover: Gtk.Popover) -> None:
        """Handle completion date selection."""
        gdt = calendar.get_date()
        self._chosen_completion_date = f"{gdt.get_year():04d}-{gdt.get_month():02d}-{gdt.get_day_of_month():02d}"
        self.comp_date_row.set_subtitle(self._chosen_completion_date)
        popover.popdown()

    def _on_clear_comp_date_clicked(self, button: Gtk.Button) -> None:
        """Clear the completion date."""
        self._chosen_completion_date = ""
        self.comp_date_row.set_subtitle("Not completed")

    def _on_pick_time_clicked(self, button: Gtk.Button) -> None:
        """Open a time picker popover."""
        self._time_popover = Gtk.Popover()
        self._time_popover.set_parent(button)
        self._time_popover.set_autohide(True)

        # Time picker box
        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        time_box.set_margin_top(12)
        time_box.set_margin_bottom(12)
        time_box.set_margin_start(12)
        time_box.set_margin_end(12)

        # Hour spin button
        hour_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hour_label = Gtk.Label(label="Hour:")
        hour_label.set_size_request(40, -1)
        hour_adjustment = Gtk.Adjustment(value=0, lower=0, upper=23, step_increment=1)
        self.hour_spin = Gtk.SpinButton(adjustment=hour_adjustment)
        self.hour_spin.set_numeric(True)
        self.hour_spin.set_digits(0)
        hour_box.append(hour_label)
        hour_box.append(self.hour_spin)

        # Minute spin button
        minute_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        minute_label = Gtk.Label(label="Minute:")
        minute_label.set_size_request(40, -1)
        minute_adjustment = Gtk.Adjustment(value=0, lower=0, upper=59, step_increment=1)
        self.minute_spin = Gtk.SpinButton(adjustment=minute_adjustment)
        self.minute_spin.set_numeric(True)
        self.minute_spin.set_digits(0)
        minute_box.append(minute_label)
        minute_box.append(self.minute_spin)

        # Parse existing time if available
        if self._chosen_time:
            try:
                parts = self._chosen_time.split(":")
                self.hour_spin.set_value(int(parts[0]))
                self.minute_spin.set_value(int(parts[1]))
            except (ValueError, IndexError):
                pass

        time_box.append(hour_box)
        time_box.append(minute_box)

        # OK button
        ok_button = Gtk.Button(label="OK")
        ok_button.add_css_class("suggested-action")
        ok_button.connect("clicked", self._on_time_selected, self._time_popover)
        time_box.append(ok_button)

        self._time_popover.set_child(time_box)
        self._time_popover.popup()

    def _on_time_selected(self, button: Gtk.Button, popover: Gtk.Popover) -> None:
        """Handle time selection."""
        hour = int(self.hour_spin.get_value())
        minute = int(self.minute_spin.get_value())
        self._chosen_time = f"{hour:02d}:{minute:02d}"
        self.time_row.set_subtitle(self._chosen_time)
        popover.popdown()

    def _on_clear_time_clicked(self, button: Gtk.Button) -> None:
        """Clear the chosen time."""
        self._chosen_time = ""
        self.time_row.set_subtitle("No time set")

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        """Handle save button click."""
        text = self.text_row.get_text().strip()
        end_date = self._chosen_date

        if not text:
            dialog = Adw.MessageDialog(
                heading="Missing Description",
                body="Please enter a description for the task."
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return

        if not end_date:
            dialog = Adw.MessageDialog(
                heading="Missing End Date",
                body="Goals without an end date will remain Dreams"
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return
        
        parent_idx = self.parent_row.get_selected()
        if parent_idx == 0:
            parent_id = ""
        else:
            parent_id = self._possible_parents[parent_idx - 1][0]

        # Get recurrence info
        recurrence_idx = self.recurrence_row.get_selected()
        recurrence_options = ["none", "daily", "weekly", "monthly"]
        recurrence = recurrence_options[recurrence_idx]
        
        recurrence_days_list = []
        for i, btn in enumerate(self.day_buttons):
            if btn.get_active():
                recurrence_days_list.append(str(i))
        recurrence_days = ",".join(recurrence_days_list)

        self.emit("save", text, end_date, parent_id, self._chosen_time, self._chosen_completion_date, recurrence, recurrence_days)
        self.close()
