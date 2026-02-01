"""Data persistence module for Goal UP To Do List application."""

import json
import os
from pathlib import Path


def get_data_path() -> Path:
    """Get the path to the tasks JSON file."""
    data_dir = Path.home() / ".local" / "share" / "goal-up"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "tasks.json"


def load_tasks() -> list[dict]:
    """Load tasks from the JSON file."""
    path = get_data_path()
    if not path.exists():
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_tasks(tasks: list[dict]) -> None:
    """Save tasks to the JSON file."""
    path = get_data_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def export_to_ics(tasks: list[dict], output_path: str) -> bool:
    """Export goals and tasks to an ICS file."""
    import uuid
    from datetime import datetime, timezone
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Goal UP//NONSGML v1.0//EN"
    ]
    
    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    for goal in tasks:
        if goal.get("end_date"):
            try:
                dt = datetime.strptime(goal["end_date"], "%Y-%m-%d")
                date_str = dt.strftime("%Y%m%d")
                
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uuid.uuid4()}",
                    f"DTSTAMP:{now_str}",
                    f"DTSTART;VALUE=DATE:{date_str}",
                    f"SUMMARY:Goal: {goal['title']}",
                    f"DESCRIPTION:{goal.get('description', '')}",
                    "END:VEVENT"
                ])
            except ValueError:
                pass
        
        for task in goal.get("tasks", []):
            if task.get("end_date"):
                try:
                    dt = datetime.strptime(task["end_date"], "%Y-%m-%d")
                    date_str = dt.strftime("%Y%m%d")
                    
                    lines.extend([
                        "BEGIN:VEVENT",
                        f"UID:{uuid.uuid4()}",
                        f"DTSTAMP:{now_str}",
                        f"DTSTART;VALUE=DATE:{date_str}",
                        f"SUMMARY:Task: {task['text']} (Goal: {goal['title']})",
                        "END:VEVENT"
                    ])
                except ValueError:
                    pass
    
    lines.append("END:VCALENDAR")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    except IOError:
        return False


def export_backup(tasks: list[dict], output_path: str) -> bool:
    """Export goals and tasks to a JSON file for backup."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def import_backup(input_path: str) -> list[dict] | None:
    """Import goals and tasks from a JSON backup file."""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
