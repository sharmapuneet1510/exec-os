"""
Preferences screen — lets users edit all settings after initial setup.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from settings.manager import SettingsManager


class PreferencesScreen:
    def __init__(self, manager: SettingsManager, parent: tk.Tk | tk.Toplevel | None = None):
        self._manager = manager
        self._settings = manager.get()

        if parent:
            self._win = tk.Toplevel(parent)
        else:
            self._win = tk.Tk()

        self._win.title("Preferences")
        self._win.resizable(False, False)
        self._win.geometry("520x460")

        self._build()

        if not parent:
            self._win.mainloop()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        notebook = ttk.Notebook(self._win)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_tab_work(notebook)
        self._build_tab_notifications(notebook)
        self._build_tab_startup(notebook)

        btn_frame = tk.Frame(self._win)
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(btn_frame, text="Restore Defaults", command=self._reset).pack(side="left")
        tk.Button(btn_frame, text="Cancel", command=self._win.destroy, width=10).pack(side="right", padx=(4, 0))
        tk.Button(btn_frame, text="Save", command=self._save,
                  bg="#2563eb", fg="white", width=10).pack(side="right")

    def _build_tab_work(self, nb: ttk.Notebook):
        frame = ttk.Frame(nb, padding=16)
        nb.add(frame, text="Work Hours")

        def row(label, attr, default, r):
            tk.Label(frame, text=label, width=30, anchor="w").grid(row=r, column=0, pady=4)
            var = tk.StringVar(value=getattr(self._settings, attr, default))
            tk.Entry(frame, textvariable=var, width=8).grid(row=r, column=1, sticky="w")
            tk.Label(frame, text="  HH:MM", fg="grey").grid(row=r, column=2, sticky="w")
            setattr(self, f"_var_{attr}", var)

        row("Work day starts at:", "work_hours_start", "09:00", 0)
        row("Work day ends at:", "work_hours_end", "18:00", 1)
        row("Start-of-day summary at:", "sod_time", "08:45", 2)
        row("End-of-day summary at:", "eod_time", "18:15", 3)

        tk.Label(frame, text="Reminder interval (minutes):", width=30, anchor="w").grid(row=4, column=0, pady=4)
        self._var_reminder_interval_minutes = tk.IntVar(value=self._settings.reminder_interval_minutes)
        tk.Spinbox(frame, from_=5, to=120, increment=5,
                   textvariable=self._var_reminder_interval_minutes,
                   width=6).grid(row=4, column=1, sticky="w")

    def _build_tab_notifications(self, nb: ttk.Notebook):
        frame = ttk.Frame(nb, padding=16)
        nb.add(frame, text="Notifications")

        self._var_desktop_notifications_enabled = tk.BooleanVar(
            value=self._settings.desktop_notifications_enabled)
        self._var_email_notifications_enabled = tk.BooleanVar(
            value=self._settings.email_notifications_enabled)
        self._var_default_view = tk.StringVar(value=self._settings.default_view)

        ttk.Checkbutton(frame, text="Desktop notifications",
                        variable=self._var_desktop_notifications_enabled).pack(anchor="w")
        ttk.Checkbutton(frame, text="Email notifications",
                        variable=self._var_email_notifications_enabled).pack(anchor="w", pady=(4, 16))

        tk.Label(frame, text="Default view on launch:").pack(anchor="w")
        for view in ("tasks", "projects", "dashboard", "commitments"):
            ttk.Radiobutton(frame, text=view.capitalize(),
                            variable=self._var_default_view, value=view).pack(anchor="w", padx=16)

    def _build_tab_startup(self, nb: ttk.Notebook):
        frame = ttk.Frame(nb, padding=16)
        nb.add(frame, text="Startup")

        self._var_startup_on_boot = tk.BooleanVar(value=self._settings.startup_on_boot)
        self._var_minimize_to_tray = tk.BooleanVar(value=self._settings.minimize_to_tray)

        ttk.Checkbutton(frame, text="Launch CommandDesk on system startup",
                        variable=self._var_startup_on_boot).pack(anchor="w")
        ttk.Checkbutton(frame, text="Minimize to system tray instead of closing",
                        variable=self._var_minimize_to_tray).pack(anchor="w", pady=(8, 0))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _save(self):
        self._manager.update(
            work_hours_start=self._var_work_hours_start.get(),
            work_hours_end=self._var_work_hours_end.get(),
            sod_time=self._var_sod_time.get(),
            eod_time=self._var_eod_time.get(),
            reminder_interval_minutes=self._var_reminder_interval_minutes.get(),
            desktop_notifications_enabled=self._var_desktop_notifications_enabled.get(),
            email_notifications_enabled=self._var_email_notifications_enabled.get(),
            default_view=self._var_default_view.get(),
            startup_on_boot=self._var_startup_on_boot.get(),
            minimize_to_tray=self._var_minimize_to_tray.get(),
        )
        messagebox.showinfo("Preferences", "Settings saved.")
        self._win.destroy()

    def _reset(self):
        if messagebox.askyesno("Restore Defaults", "Reset all settings to defaults?"):
            self._settings = self._manager.reset_to_defaults()
            self._win.destroy()
            PreferencesScreen(self._manager)
