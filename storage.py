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
