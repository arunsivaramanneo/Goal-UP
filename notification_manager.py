"""Notification manager for Goal UP."""

import gi
from datetime import datetime, date

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gio, GLib

class NotificationManager:
    """Manages application notifications."""

    def __init__(self, app: Gio.Application):
        self._app = app

    def send_notification(self, title: str, body: str, notification_id: str = None) -> None:
        """Send a desktop notification."""
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        notification.set_default_action("app.activate")
        
        self._app.send_notification(notification_id, notification)

    def check_upcoming_events(self, goals: list) -> None:
        """Check for events due today and notify the user."""
        today = date.today()
        due_today_count = 0
        upcoming_tasks = []

        for goal in goals:
            if not goal.get("completed", False) and goal.get("end_date"):
                if goal["end_date"] == today.isoformat():
                    due_today_count += 1
            
            for task in goal.get("tasks", []):
                if not task.get("completed", False) and task.get("end_date"):
                    if task["end_date"] == today.isoformat():
                        due_today_count += 1
                        upcoming_tasks.append(f"{goal['title']}: {task['text']}")

        if due_today_count > 0:
            title = "Goal UP: Tasks due today!"
            body = f"You have {due_today_count} items due today."
            if upcoming_tasks:
                 body += " Including: " + ", ".join(upcoming_tasks[:2])
                 if len(upcoming_tasks) > 2:
                     body += "..."
            
            self.send_notification(title, body, "upcoming-events")
