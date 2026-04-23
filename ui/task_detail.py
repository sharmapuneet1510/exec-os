import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from tasks.model import Task
from tasks.notes import TaskNoteService


class TaskDetailScreen(tk.Frame):
    """Read-only task detail panel showing info, notes, and history."""

    def __init__(
        self,
        master,
        note_service: TaskNoteService,
        on_add_note: Optional[Callable[[str, str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._note_svc = note_service
        self._on_add_note = on_add_note
        self._task: Optional[Task] = None
        self._build()

    def _build(self) -> None:
        # Info section
        info_frame = tk.LabelFrame(self, text="Task Info", padx=8, pady=4)
        info_frame.pack(fill="x", padx=8, pady=(8, 4))

        for row, label in enumerate(("Title:", "Status:", "Priority:", "Due Date:", "Reminder:")):
            tk.Label(info_frame, text=label, anchor="e", width=10).grid(row=row, column=0, sticky="e")
            var = tk.StringVar()
            tk.Label(info_frame, textvariable=var, anchor="w").grid(row=row, column=1, sticky="w")
            setattr(self, f"_var_{label[:-1].lower().replace(' ', '_')}", var)

        # Notes section
        notes_frame = tk.LabelFrame(self, text="Notes", padx=8, pady=4)
        notes_frame.pack(fill="both", expand=True, padx=8, pady=4)

        notes_scroll = ttk.Scrollbar(notes_frame, orient="vertical")
        self._notes_list = tk.Listbox(notes_frame, yscrollcommand=notes_scroll.set, height=6)
        notes_scroll.config(command=self._notes_list.yview)
        self._notes_list.pack(side="left", fill="both", expand=True)
        notes_scroll.pack(side="right", fill="y")

        add_frame = tk.Frame(notes_frame)
        add_frame.pack(side="bottom", fill="x")
        self._note_entry = tk.Entry(add_frame)
        self._note_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(add_frame, text="Add Note", command=self._add_note).pack(side="right")

        # History section
        hist_frame = tk.LabelFrame(self, text="History", padx=8, pady=4)
        hist_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        hist_scroll = ttk.Scrollbar(hist_frame, orient="vertical")
        self._history_list = tk.Listbox(hist_frame, yscrollcommand=hist_scroll.set, height=6)
        hist_scroll.config(command=self._history_list.yview)
        self._history_list.pack(side="left", fill="both", expand=True)
        hist_scroll.pack(side="right", fill="y")

    def load_task(self, task: Task) -> None:
        self._task = task
        self._var_title.set(task.title)
        self._var_status.set(task.status)
        self._var_priority.set(task.priority)
        self._var_due_date.set(task.due_date.isoformat() if task.due_date else "—")
        self._var_reminder.set(task.reminder_date.isoformat() if task.reminder_date else "—")
        self._refresh_notes()
        self._refresh_history()

    def _refresh_notes(self) -> None:
        self._notes_list.delete(0, tk.END)
        if self._task is None:
            return
        for note in self._note_svc.get_notes(self._task.task_id):
            self._notes_list.insert(tk.END, f"{note.created_at[:10]}  {note.content}")

    def _refresh_history(self) -> None:
        self._history_list.delete(0, tk.END)
        if self._task is None:
            return
        for event in self._note_svc.get_history(self._task.task_id):
            self._history_list.insert(tk.END, f"{event.occurred_at[:10]}  [{event.event_type}]  {event.description}")

    def _add_note(self) -> None:
        if self._task is None:
            return
        content = self._note_entry.get().strip()
        if not content:
            return
        if self._on_add_note:
            self._on_add_note(self._task.task_id, content)
        else:
            self._note_svc.add_note(self._task.task_id, content)
        self._note_entry.delete(0, tk.END)
        self._refresh_notes()
        self._refresh_history()
