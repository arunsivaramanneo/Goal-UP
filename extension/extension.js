import GLib from 'gi://GLib';
import St from 'gi://St';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import { Extension, gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';

const TASKS_PATH = GLib.get_home_dir() + '/.local/share/goal-up/tasks.json';

export default class GoalUPExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, 'Goal-UP Indicator', false);

        let box = new St.BoxLayout({
            vertical: false,
            style_class: 'panel-status-menu-box',
        });

        this._icon = new St.Icon({
            icon_name: 'appointment-soon-symbolic',
            style_class: 'system-status-icon',
        });
        box.add_child(this._icon);

        this._label = new St.Label({
            text: 'Loading...',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'goal-up-panel-label',
        });
        box.add_child(this._label);

        this._indicator.add_child(box);

        this._clickHandlerId = this._indicator.connect('button-press-event', this._onIndicatorClicked.bind(this));

        Main.panel.addToStatusArea(this.uuid, this._indicator);

        this._updateLoop();
        this._refreshData();
    }

    disable() {
        if (this._clickHandlerId) {
            this._indicator.disconnect(this._clickHandlerId);
            this._clickHandlerId = null;
        }
        if (this._timeout) {
            GLib.Source.remove(this._timeout);
            this._timeout = null;
        }
        if (this._dataTimeout) {
            GLib.Source.remove(this._dataTimeout);
            this._dataTimeout = null;
        }
        this._indicator.destroy();
        this._indicator = null;
    }

    _updateLoop() {
        this._updateDisplay();
        this._timeout = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._updateDisplay();
            return GLib.SOURCE_CONTINUE;
        });

        // Data refresh loop (every 60s)
        this._dataTimeout = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60, () => {
            this._refreshData();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _refreshData() {
        try {
            let file = Gio.File.new_for_path(TASKS_PATH);
            let [success, contents] = file.load_contents(null);
            if (success) {
                this._tasks = JSON.parse(new TextDecoder().decode(contents));
                this._findNextDeadline();
            }
        } catch (e) {
            console.error(`Goal-UP: Error loading data: ${e}`);
        }
    }

    _findNextDeadline() {
        if (!this._tasks) return;
        let now = new Date();
        let upcoming = [];

        this._tasks.forEach(g => {
            if (!g.completed && g.end_date) {
                let dtStr = g.end_date;
                if (g.end_time) dtStr += ' ' + g.end_time;
                else dtStr += ' 23:59:59';

                let dt = new Date(dtStr.replace(/-/g, '/')); // Compatibility with Date.parse
                if (dt > now) {
                    upcoming.push({ dt, title: g.title, type: 'Goal' });
                }
            }

            (g.tasks || []).forEach(t => {
                if (!t.completed && t.end_date) {
                    let dtStr = t.end_date;
                    if (t.end_time) dtStr += ' ' + t.end_time;
                    else dtStr += ' 23:59:59';

                    let dt = new Date(dtStr.replace(/-/g, '/'));
                    if (dt > now) {
                        upcoming.push({ dt, title: t.text, type: 'Task' });
                    }
                }
            });
        });

        if (upcoming.length > 0) {
            upcoming.sort((a, b) => a.dt - b.dt);
            this._nextDeadline = upcoming[0];
        } else {
            this._nextDeadline = null;
        }
    }

    _updateDisplay() {
        if (!this._nextDeadline) {
            this._label.set_text('No Deadlines');
            return;
        }

        let now = new Date();
        let diff = this._nextDeadline.dt - now;

        if (diff <= 0) {
            this._refreshData();
            return;
        }

        let seconds = Math.floor(diff / 1000);
        let days = Math.floor(seconds / 86400);
        seconds %= 86400;
        let hours = Math.floor(seconds / 3600);
        seconds %= 3600;
        let minutes = Math.floor(seconds / 60);
        seconds %= 60;

        let timeStr = '';
        if (days > 0) timeStr += `${days}d `;
        timeStr += `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        this._label.set_text(`${this._nextDeadline.title}: ${timeStr}`);
    }

    _onIndicatorClicked(_actor, event) {
        if (event.get_button() !== Clutter.BUTTON_PRIMARY) {
            return Clutter.EVENT_PROPAGATE;
        }

        this._openGoalUpApp();
        return Clutter.EVENT_STOP;
    }

    _openGoalUpApp() {
        let app;

        try {
            app = Gio.DesktopAppInfo.new('goal-up.desktop');
            if (app) {
                app.launch([], null);
                return;
            }
        } catch (e) {
            log(`Goal-UP: desktop entry launch failed: ${e}`);
        }

        try {
            app = Gio.AppInfo.create_from_commandline('goal-up', 'Goal-UP', Gio.AppInfoCreateFlags.NONE);
            if (app) {
                app.launch([], null);
            }
        } catch (e) {
            log(`Goal-UP: fallback command launch failed: ${e}`);
        }
    }
}

