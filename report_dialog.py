"""Yearly accomplishment slideshow for Goal UP."""

from collections import defaultdict
from datetime import date, datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk


MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _parse_date(value: str):
    """Parse an ISO date or datetime value from stored goal data."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None


def build_yearly_report(goals: list[dict], year: int | None = None) -> dict:
    """Build completed accomplishments grouped by month for a calendar year."""
    year = year or date.today().year
    months = defaultdict(list)
    completed_goals = 0
    completed_tasks = 0
    started_items = 0

    for goal in goals:
        goal_title = goal.get("title", goal.get("text", "Untitled"))
        if goal.get("completed"):
            completed_goals += 1
        goal_date = _parse_date(goal.get("completion_date", ""))
        if goal_date and goal_date.year == year and goal.get("completed"):
            months[goal_date.month].append({
                "title": goal_title,
                "kind": "Goal completed",
                "date": goal_date,
                "color": goal.get("color"),
            })

        for task in goal.get("tasks", []):
            if task.get("completed"):
                completed_tasks += 1
            task_date = _parse_date(task.get("completion_date", ""))
            if task_date and task_date.year == year and task.get("completed"):
                months[task_date.month].append({
                    "title": task.get("text", "Untitled task"),
                    "kind": f"Task completed · {goal_title}",
                    "date": task_date,
                    "color": goal.get("color"),
                })

        created_date = _parse_date(goal.get("created_at", ""))
        if created_date and created_date.year == year:
            started_items += 1
            if not goal.get("completed") and not goal_date:
                months[created_date.month].append({
                    "title": goal_title,
                    "kind": "Goal started",
                    "date": created_date,
                    "color": goal.get("color"),
                })

    for entries in months.values():
        entries.sort(key=lambda item: item["date"])

    return {
        "year": year,
        "months": dict(months),
        "completed_goals": completed_goals,
        "completed_tasks": completed_tasks,
        "started_items": started_items,
    }


class YearlyReportDialog(Adw.Dialog):
    """A navigable and auto-playing year-in-review slideshow."""

    def __init__(self, goals: list[dict], year: int | None = None):
        super().__init__()
        self._report = build_yearly_report(goals, year)
        self._slide_index = 0
        self._play_source = None

        self.set_title("Year in Review")
        self.set_content_width(680)
        self.set_content_height(560)

        toolbar = Adw.ToolbarView()
        self.set_child(toolbar)

        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(True)
        header.set_show_end_title_buttons(True)
        toolbar.add_top_bar(header)

        self._play_button = Gtk.ToggleButton(label="Play")
        self._play_button.set_icon_name("media-playback-start-symbolic")
        self._play_button.set_tooltip_text("Play slideshow automatically")
        self._play_button.connect("toggled", self._on_play_toggled)
        header.pack_end(self._play_button)

        self._slide_label = Gtk.Label()
        self._slide_label.add_css_class("dim-label")
        header.set_title_widget(self._slide_label)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(28)
        content.set_margin_bottom(24)
        content.set_margin_start(32)
        content.set_margin_end(32)
        toolbar.set_content(content)

        self._accent = Gtk.Label()
        self._accent.add_css_class("title-1")
        self._accent.set_halign(Gtk.Align.CENTER)
        content.append(self._accent)

        self._headline = Gtk.Label()
        self._headline.add_css_class("title-2")
        self._headline.set_wrap(True)
        self._headline.set_justify(Gtk.Justification.CENTER)
        content.append(self._headline)

        self._details = Gtk.Label()
        self._details.add_css_class("body")
        self._details.set_wrap(True)
        self._details.set_justify(Gtk.Justification.CENTER)
        self._details.set_vexpand(True)
        self._details.set_valign(Gtk.Align.CENTER)
        content.append(self._details)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_halign(Gtk.Align.CENTER)
        content.append(controls)

        previous = Gtk.Button(label="Previous")
        previous.set_icon_name("go-previous-symbolic")
        previous.connect("clicked", self._on_previous_clicked)
        controls.append(previous)

        next_button = Gtk.Button(label="Next")
        next_button.set_icon_name("go-next-symbolic")
        next_button.add_css_class("suggested-action")
        next_button.connect("clicked", self._on_next_clicked)
        controls.append(next_button)

        self._render_slide()

    def _slide_count(self) -> int:
        return 13

    def _render_slide(self) -> None:
        year = self._report["year"]
        if self._slide_index == 0:
            goals = self._report["completed_goals"]
            tasks = self._report["completed_tasks"]
            started = self._report["started_items"]
            self._accent.set_text(str(year))
            self._headline.set_text("Your year in progress")
            self._details.set_text(
                f"{goals} goals completed\n{tasks} tasks completed\n{started} goals started"
            )
            self._slide_label.set_text("Overview")
        else:
            month = self._slide_index
            entries = self._report["months"].get(month, [])
            self._accent.set_text(MONTH_NAMES[month - 1])
            self._slide_label.set_text(f"{month} / 12")
            if entries:
                self._headline.set_text(f"{len(entries)} accomplishment" + ("s" if len(entries) != 1 else ""))
                lines = [f"{item['date'].strftime('%b %d')}  ·  {item['title']}\n{item['kind']}" for item in entries]
                self._details.set_text("\n\n".join(lines))
            else:
                self._headline.set_text("A quiet month")
                self._details.set_text("No dated accomplishments recorded.")

    def _on_previous_clicked(self, button: Gtk.Button) -> None:
        self._slide_index = (self._slide_index - 1) % self._slide_count()
        self._render_slide()

    def _on_next_clicked(self, button: Gtk.Button) -> None:
        self._slide_index = (self._slide_index + 1) % self._slide_count()
        self._render_slide()

    def _on_play_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active():
            button.set_label("Pause")
            button.set_icon_name("media-playback-pause-symbolic")
            self._play_source = GLib.timeout_add_seconds(4, self._advance_slide)
        else:
            button.set_label("Play")
            button.set_icon_name("media-playback-start-symbolic")
            if self._play_source is not None:
                GLib.source_remove(self._play_source)
                self._play_source = None

    def _advance_slide(self) -> bool:
        self._slide_index = (self._slide_index + 1) % self._slide_count()
        self._render_slide()
        return True

    def close(self) -> None:
        if self._play_source is not None:
            GLib.source_remove(self._play_source)
            self._play_source = None
        super().close()
