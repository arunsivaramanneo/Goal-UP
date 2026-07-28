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
            application_id="io.github.arunsivaramanneo.GoalUp",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        # Use window icon setup in MainWindow; avoid unsupported Gio call on Adw.Application

    def do_activate(self) -> None:
        """Handle application activation — always raise the MainWindow."""
        # Search for an existing MainWindow among all application windows.
        # We must NOT use get_active_window() here because the floating
        # DesktopWidget is also an app window and may be the "active" one,
        # which would cause the launcher click to only raise the widget
        # instead of opening the full application.
        main_window = None
        for win in self.get_windows():
            if isinstance(win, MainWindow):
                main_window = win
                break
        if main_window is None:
            main_window = MainWindow(self)
        main_window.present()


def main() -> int:
    """Application entry point."""
    app = GoalUpApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
