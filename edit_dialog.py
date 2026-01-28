"""Edit dialog for Goal details."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, GObject
from datetime import datetime


class EditGoalDialog(Adw.Dialog):
    """Dialog for editing goal title, description, and end date."""

    __gtype_name__ = "EditGoalDialog"

    __gsignals__ = {
        "save": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str)),  # title, description, end_date
    }

    def __init__(self, title: str = "", description: str = "", end_date: str = ""):
        super().__init__()

        self.set_title("Edit Goal")
        self.set_content_width(400)
        self.set_content_height(380)

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

        # End date group (optional)
        date_group = Adw.PreferencesGroup()
        date_group.set_title("End Date (Optional)")
        date_group.set_description("Format: YYYY-MM-DD (e.g., 2026-02-15)")
        content_box.append(date_group)

        self.date_row = Adw.EntryRow()
        self.date_row.set_title("End Date")
        self.date_row.set_text(end_date or "")
        date_group.add(self.date_row)

        # Clear date button
        clear_date_btn = Gtk.Button(label="Clear End Date")
        clear_date_btn.add_css_class("flat")
        clear_date_btn.connect("clicked", lambda b: self.date_row.set_text(""))
        date_group.add(clear_date_btn)

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        """Handle save button click."""
        title = self.title_row.get_text().strip()
        description = self.desc_row.get_text().strip()
        end_date = self.date_row.get_text().strip()
        
        # Validate date format if provided
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                end_date = ""  # Invalid format, clear it
        

        if title:
            self.emit("save", title, description, end_date)
            self.close()


class EditTaskDialog(Adw.Dialog):
    """Dialog for editing a sub-task."""

    __gtype_name__ = "EditTaskDialog"

    __gsignals__ = {
        "save": (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # text
    }

    def __init__(self, text: str = ""):
        super().__init__()

        self.set_title("Edit Task")
        self.set_content_width(400)
        self.set_content_height(200)

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

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        """Handle save button click."""
        text = self.text_row.get_text().strip()
        if text:
            self.emit("save", text)
            self.close()
