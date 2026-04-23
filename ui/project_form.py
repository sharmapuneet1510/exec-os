import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from typing import Callable, Optional

from projects.model import Project, ProjectStatus
from projects.service import ProjectService


class ProjectFormScreen(tk.Toplevel):
    """Modal dialog for creating or editing a project."""

    STATUSES: list = ["active", "on_hold", "completed", "archived"]

    def __init__(
        self,
        master,
        project_service: ProjectService,
        project: Optional[Project] = None,
        on_save: Optional[Callable[[Project], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._svc = project_service
        self._project = project
        self._on_save = on_save
        self.title("Edit Project" if project else "New Project")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if project:
            self._populate(project)

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}
        frame = tk.Frame(self, padx=16, pady=12)
        frame.pack(fill="both", expand=True)

        # Name
        tk.Label(frame, text="Name *", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self._name_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._name_var, width=36).grid(row=0, column=1, sticky="ew", **pad)

        # Description
        tk.Label(frame, text="Description", anchor="w").grid(row=1, column=0, sticky="nw", **pad)
        self._desc_text = tk.Text(frame, width=36, height=4)
        self._desc_text.grid(row=1, column=1, sticky="ew", **pad)

        # Status
        tk.Label(frame, text="Status", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        self._status_var = tk.StringVar(value="active")
        ttk.Combobox(
            frame, textvariable=self._status_var,
            values=self.STATUSES, state="readonly", width=14,
        ).grid(row=2, column=1, sticky="w", **pad)

        # Owner
        tk.Label(frame, text="Owner", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        self._owner_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._owner_var, width=24).grid(row=3, column=1, sticky="w", **pad)

        # Due Date
        tk.Label(frame, text="Due Date (YYYY-MM-DD)", anchor="w").grid(row=4, column=0, sticky="w", **pad)
        self._due_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._due_var, width=14).grid(row=4, column=1, sticky="w", **pad)

        # Buttons
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(12, 0))
        tk.Button(btn_frame, text="Save", width=10, command=self._save).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=4)

        frame.columnconfigure(1, weight=1)

    def _populate(self, project: Project) -> None:
        self._name_var.set(project.name)
        self._desc_text.insert("1.0", project.description)
        self._status_var.set(project.status)
        if project.owner:
            self._owner_var.set(project.owner)
        if project.due_date:
            self._due_var.set(project.due_date.isoformat())

    def _save(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("Validation", "Project name is required.", parent=self)
            return

        description = self._desc_text.get("1.0", tk.END).strip()
        status: ProjectStatus = self._status_var.get()
        owner = self._owner_var.get().strip() or None
        due_str = self._due_var.get().strip()
        due_date = None
        if due_str:
            try:
                due_date = date.fromisoformat(due_str)
            except ValueError:
                messagebox.showerror("Validation", "Due date must be YYYY-MM-DD.", parent=self)
                return

        if self._project:
            project = self._svc.update(
                self._project.project_id,
                name=name, description=description, status=status,
                owner=owner, due_date=due_date,
            )
        else:
            project = self._svc.create(
                name, description=description, status=status,
                owner=owner, due_date=due_date,
            )

        if self._on_save:
            self._on_save(project)
        self.destroy()
