#!/usr/bin/env python3
"""Goal UP - A To Do List application built with libadwaita."""

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

from window import MainWindow


class GoalUpApplication(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.example.GoalUp",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:
        """Handle application activation."""
        window = self.get_active_window()
        if not window:
            window = MainWindow(self)
        window.present()


def main() -> int:
    """Application entry point."""
    app = GoalUpApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
