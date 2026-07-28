"""Timeline widget for Goal UP."""

import gi
from datetime import datetime, date

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GObject, GLib


class TimelineRow(Adw.ActionRow):
    """A row in the timeline representing a specific event."""

    def __init__(
        self,
        date_str: str,
        text: str,
        completed: bool,
        color: str = None,
        days_remaining: int = None,
    ):
        super().__init__()
        self.set_title(text)

        subtitle = date_str
        if not completed and days_remaining is not None:
            if days_remaining < 0:
                subtitle += f" ({abs(days_remaining)}d overdue)"
            else:
                subtitle += f" ({days_remaining}d left)"
        self.set_subtitle(subtitle)

        if completed:
            check_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check_icon.add_css_class("success")
            self.add_prefix(check_icon)
            self.add_css_class("dim-label")
        else:
            bullet_icon = Gtk.Image.new_from_icon_name("non-starred-symbolic")
            self.add_prefix(bullet_icon)

        if color and not completed:
            rgba = Gdk.RGBA()
            if rgba.parse(color):
                r = int(rgba.red * 255)
                g = int(rgba.green * 255)
                b = int(rgba.blue * 255)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                escaped_text = GLib.markup_escape_text(text)
                markup = f"<span foreground='{hex_color}'>{escaped_text}</span>"
                self.set_title(markup)
                self.set_use_markup(True)


class TimelineWidget(Gtk.Box):
    """Widget that displays a vertical timeline of goals and tasks,
    with an optional per-goal filter."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_size_request(260, -1)
        self.add_css_class("timeline")

        self._goals: list = []
        self._selected_goal_id: str | None = None   # None → show all

        # ------------------------------------------------------------------ #
        # Header                                                               #
        # ------------------------------------------------------------------ #
        header_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6
        )
        header_box.set_margin_top(12)
        header_box.set_margin_bottom(8)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        self.append(header_box)

        title_label = Gtk.Label(label="Timeline")
        title_label.add_css_class("title-4")
        title_label.set_halign(Gtk.Align.CENTER)
        header_box.append(title_label)

        # ── Goal filter dropdown ──────────────────────────────────────────── #
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_box.set_margin_top(4)
        header_box.append(filter_box)

        filter_lbl = Gtk.Label(label="Filter:")
        filter_lbl.add_css_class("caption")
        filter_lbl.add_css_class("dim-label")
        filter_lbl.set_valign(Gtk.Align.CENTER)
        filter_box.append(filter_lbl)

        # We use a Gtk.DropDown backed by a Gtk.StringList so it's simple.
        self._filter_store = Gtk.StringList()
        self._filter_store.append("All Goals")

        self._filter_drop = Gtk.DropDown(model=self._filter_store)
        self._filter_drop.set_hexpand(True)
        self._filter_drop.set_valign(Gtk.Align.CENTER)
        # Keep the signal handler id so we can block it during rebuilds
        self._filter_handler = self._filter_drop.connect(
            "notify::selected", self._on_filter_changed
        )
        filter_box.append(self._filter_drop)

        # ------------------------------------------------------------------ #
        # Scrolled list                                                        #
        # ------------------------------------------------------------------ #
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("navigation-sidebar")
        scrolled.set_child(self.list_box)

        self._empty_label = Gtk.Label(label="No events this year")
        self._empty_label.add_css_class("dim-label")
        self._empty_label.set_margin_top(20)
        self.list_box.append(self._empty_label)

    # ---------------------------------------------------------------------- #
    # Filter dropdown handler                                                  #
    # ---------------------------------------------------------------------- #

    def _on_filter_changed(self, drop_down, _pspec):
        idx = drop_down.get_selected()
        if idx == 0:
            # "All Goals" selected
            self._selected_goal_id = None
        else:
            # Map dropdown index → goal id
            # Index 0 = "All Goals", 1..n = goals in self._goals order
            goal_idx = idx - 1
            if 0 <= goal_idx < len(self._goals):
                self._selected_goal_id = self._goals[goal_idx].get("id") or self._goals[goal_idx].get("title", "")
            else:
                self._selected_goal_id = None
        self._rebuild_list()

    # ---------------------------------------------------------------------- #
    # Public API                                                               #
    # ---------------------------------------------------------------------- #

    def update_data(self, goals: list) -> None:
        """Feed fresh goals data; rebuilds filter dropdown + event list."""
        self._goals = goals

        # Rebuild the dropdown — block signal to avoid spurious rebuilds
        self._filter_drop.handler_block(self._filter_handler)
        try:
            # Clear existing entries
            while self._filter_store.get_n_items() > 0:
                self._filter_store.remove(0)

            self._filter_store.append("All Goals")
            for g in goals:
                title = g.get("title", "Untitled")
                self._filter_store.append(title)

            # Restore selection: find the previously selected goal by id
            selected_idx = 0
            if self._selected_goal_id is not None:
                for i, g in enumerate(goals):
                    gid = g.get("id") or g.get("title", "")
                    if gid == self._selected_goal_id:
                        selected_idx = i + 1  # +1 because "All Goals" is index 0
                        break
                else:
                    # Goal no longer exists → reset to All
                    self._selected_goal_id = None

            self._filter_drop.set_selected(selected_idx)
        finally:
            self._filter_drop.handler_unblock(self._filter_handler)

        self._rebuild_list()

    # ---------------------------------------------------------------------- #
    # Internal event building                                                  #
    # ---------------------------------------------------------------------- #

    def _rebuild_list(self) -> None:
        """Clear and repopulate the list box according to current filter."""
        # Clear
        while True:
            row = self.list_box.get_first_child()
            if row is None:
                break
            self.list_box.remove(row)

        events = self._build_events()
        events.sort(key=lambda x: x["date"])

        if not events:
            self.list_box.append(self._empty_label)
        else:
            # If a specific goal is selected, add a section header
            if self._selected_goal_id is not None:
                # Find goal
                goal = next(
                    (
                        g
                        for g in self._goals
                        if (g.get("id") or g.get("title", "")) == self._selected_goal_id
                    ),
                    None,
                )
                if goal:
                    header_row = Adw.ActionRow()
                    title = goal.get("title", "")
                    status = "✓ Complete" if goal.get("completed") else "In Progress"
                    header_row.set_title(f"<b>{GLib.markup_escape_text(title)}</b>")
                    header_row.set_subtitle(status)
                    header_row.set_use_markup(True)
                    header_row.add_css_class("accent")
                    self.list_box.append(header_row)

            for ev in events:
                row = TimelineRow(
                    ev["date"].strftime("%b %d"),
                    ev["text"],
                    ev["completed"],
                    ev.get("color"),
                    ev.get("days"),
                )
                self.list_box.append(row)

    def _build_events(self) -> list:
        """Return list of event dicts for the current filter setting."""
        events = []
        current_year = date.today().year
        start_of_year = date(current_year, 1, 1)
        today = date.today()

        # Decide which goals to iterate
        if self._selected_goal_id is None:
            goals_to_show = self._goals
        else:
            goals_to_show = [
                g
                for g in self._goals
                if (g.get("id") or g.get("title", "")) == self._selected_goal_id
            ]

        for goal in goals_to_show:
            color = goal.get("color")

            # ── Goal row itself ───────────────────────────────────────────── #
            g_date_str = goal.get("completion_date") or goal.get("end_date")
            if g_date_str:
                try:
                    ev_date = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                    if ev_date >= start_of_year:
                        days = (ev_date - today).days
                        events.append(
                            {
                                "date": ev_date,
                                "text": f"🎯 Goal: {goal['title']}",
                                "completed": goal.get("completed", False),
                                "color": color,
                                "days": days,
                                "kind": "goal",
                            }
                        )
                except (ValueError, TypeError):
                    pass

            # ── Tasks ─────────────────────────────────────────────────────── #
            for task in goal.get("tasks", []):
                t_date_str = task.get("completion_date") or task.get("end_date")
                if t_date_str:
                    try:
                        ev_date = datetime.strptime(t_date_str, "%Y-%m-%d").date()
                        if ev_date >= start_of_year:
                            days = (ev_date - today).days

                            # Label differently depending on filter mode
                            if self._selected_goal_id is not None:
                                text = task["text"]
                            else:
                                text = f"{goal['title']} : {task['text']}"

                            events.append(
                                {
                                    "date": ev_date,
                                    "text": text,
                                    "completed": task.get("completed", False),
                                    "color": color,
                                    "days": days,
                                    "kind": "task",
                                }
                            )
                    except (ValueError, TypeError):
                        pass

        return events
