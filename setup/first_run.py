"""
First-run setup wizard shown when no settings file exists.
Three steps: Work Hours → Notifications → Startup Behaviour.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from settings.manager import SettingsManager
from settings.model import UserSettings


class FirstRunWizard:
    def __init__(self, manager: SettingsManager):
        self._manager = manager
        self._settings = UserSettings()

        self._root = tk.Tk()
        self._root.title("CommandDesk — First-time Setup")
        self._root.resizable(False, False)
        self._root.geometry("480x360")

        self._step = 0
        self._steps = [self._build_step_work_hours, self._build_step_notifications, self._build_step_startup]
        self._frame: tk.Frame | None = None

        self._show_step()
        self._root.mainloop()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _show_step(self):
        if self._frame:
            self._frame.destroy()
        self._frame = tk.Frame(self._root, padx=20, pady=20)
        self._frame.pack(fill="both", expand=True)
        self._steps[self._step]()
        self._build_nav()

    def _build_nav(self):
        nav = tk.Frame(self._frame)
        nav.pack(side="bottom", fill="x", pady=(16, 0))

        is_last = self._step == len(self._steps) - 1
        label = "Finish" if is_last else "Next →"

        if self._step > 0:
            tk.Button(nav, text="← Back", width=10, command=self._prev).pack(side="left")

        tk.Button(nav, text=label, width=10, command=self._next_or_finish,
                  bg="#2563eb", fg="white").pack(side="right")

        step_lbl = tk.Label(nav, text=f"Step {self._step + 1} of {len(self._steps)}", fg="grey")
        step_lbl.pack(side="right", padx=8)

    def _prev(self):
        self._step -= 1
        self._show_step()

    def _next_or_finish(self):
        self._collect_current_step()
        if self._step < len(self._steps) - 1:
            self._step += 1
            self._show_step()
        else:
            self._manager.save(self._settings)
            messagebox.showinfo("Setup Complete", "Your preferences have been saved. Welcome to CommandDesk!")
            self._root.destroy()

    # ── Step builders ─────────────────────────────────────────────────────────

    def _build_step_work_hours(self):
        tk.Label(self._frame, text="Work Hours & Daily Summaries",
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(self._frame, text="Tell CommandDesk when your workday starts and ends.",
                 fg="grey").pack(anchor="w", pady=(2, 16))

        grid = tk.Frame(self._frame)
        grid.pack(anchor="w")

        def row(label, attr, default):
            tk.Label(grid, text=label, width=28, anchor="w").grid(row=row.i, column=0)
            var = tk.StringVar(value=getattr(self._settings, attr, default))
            entry = tk.Entry(grid, textvariable=var, width=8)
            entry.grid(row=row.i, column=1)
            tk.Label(grid, text="  HH:MM", fg="grey").grid(row=row.i, column=2, sticky="w")
            setattr(self, f"_var_{attr}", var)
            row.i += 1

        row.i = 0
        row("Work day starts at:", "work_hours_start", "09:00")
        row("Work day ends at:", "work_hours_end", "18:00")
        row("Start-of-day summary at:", "sod_time", "08:45")
        row("End-of-day summary at:", "eod_time", "18:15")

        tk.Label(grid, text="Reminder interval (minutes):", width=28, anchor="w").grid(row=row.i, column=0)
        self._var_reminder = tk.IntVar(value=self._settings.reminder_interval_minutes)
        tk.Spinbox(grid, from_=5, to=120, increment=5, textvariable=self._var_reminder,
                   width=6).grid(row=row.i, column=1, sticky="w")

    def _build_step_notifications(self):
        tk.Label(self._frame, text="Notification Preferences",
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(self._frame, text="Choose how CommandDesk alerts you.",
                 fg="grey").pack(anchor="w", pady=(2, 16))

        self._var_desktop_notif = tk.BooleanVar(value=self._settings.desktop_notifications_enabled)
        self._var_email_notif = tk.BooleanVar(value=self._settings.email_notifications_enabled)
        self._var_default_view = tk.StringVar(value=self._settings.default_view)

        ttk.Checkbutton(self._frame, text="Desktop notifications",
                        variable=self._var_desktop_notif).pack(anchor="w")
        ttk.Checkbutton(self._frame, text="Email notifications",
                        variable=self._var_email_notif).pack(anchor="w", pady=(4, 16))

        tk.Label(self._frame, text="Default view on launch:").pack(anchor="w")
        for view in ("tasks", "projects", "dashboard", "commitments"):
            ttk.Radiobutton(self._frame, text=view.capitalize(),
                            variable=self._var_default_view, value=view).pack(anchor="w", padx=16)

    def _build_step_startup(self):
        tk.Label(self._frame, text="Startup Behaviour",
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(self._frame, text="Control how CommandDesk behaves when your system starts.",
                 fg="grey").pack(anchor="w", pady=(2, 16))

        self._var_startup_on_boot = tk.BooleanVar(value=self._settings.startup_on_boot)
        self._var_minimize_to_tray = tk.BooleanVar(value=self._settings.minimize_to_tray)

        ttk.Checkbutton(self._frame, text="Launch CommandDesk on system startup",
                        variable=self._var_startup_on_boot).pack(anchor="w")
        ttk.Checkbutton(self._frame, text="Minimize to system tray instead of closing",
                        variable=self._var_minimize_to_tray).pack(anchor="w", pady=(8, 0))

    # ── Collectors ────────────────────────────────────────────────────────────

    def _collect_current_step(self):
        if self._step == 0:
            self._settings.work_hours_start = self._var_work_hours_start.get()
            self._settings.work_hours_end = self._var_work_hours_end.get()
            self._settings.sod_time = self._var_sod_time.get()
            self._settings.eod_time = self._var_eod_time.get()
            self._settings.reminder_interval_minutes = self._var_reminder.get()
        elif self._step == 1:
            self._settings.desktop_notifications_enabled = self._var_desktop_notif.get()
            self._settings.email_notifications_enabled = self._var_email_notif.get()
            self._settings.default_view = self._var_default_view.get()
        elif self._step == 2:
            self._settings.startup_on_boot = self._var_startup_on_boot.get()
            self._settings.minimize_to_tray = self._var_minimize_to_tray.get()


def run_if_first_time(manager: SettingsManager) -> bool:
    """Show the wizard if this is the first run. Returns True if wizard was shown."""
    if manager.is_first_run():
        FirstRunWizard(manager)
        return True
    return False
