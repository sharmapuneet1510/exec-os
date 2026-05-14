import tkinter as tk
from tkinter import ttk
from datetime import date
from typing import Callable, List, Optional

from tasks.model import Task
from tasks.views import TaskFilter


class TaskListScreen(tk.Frame):
    """Scrollable task list with filter bar and selection callback."""

    COLUMNS = ("title", "status", "priority", "due_date")
    COLUMN_WIDTHS = {"title": 280, "status": 90, "priority": 80, "due_date": 100}
    COLUMN_HEADERS = {"title": "Title", "status": "Status", "priority": "Priority", "due_date": "Due Date"}

    def __init__(
        self,
        master,
        on_select: Optional[Callable[[Task], None]] = None,
        on_new: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._tasks: List[Task] = []
        self._on_select = on_select
        self._on_new = on_new
        self._build()

    def _build(self) -> None:
        toolbar = tk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(toolbar, text="Search:").pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(toolbar, textvariable=self._search_var, width=20).pack(side="left", padx=(4, 12))

        tk.Label(toolbar, text="Status:").pack(side="left")
        self._status_var = tk.StringVar(value="all")
        status_cb = ttk.Combobox(
            toolbar, textvariable=self._status_var, width=12,
            values=["all", "todo", "in_progress", "done", "cancelled"], state="readonly",
        )
        status_cb.pack(side="left", padx=(4, 12))
        self._status_var.trace_add("write", lambda *_: self._apply_filter())

        tk.Label(toolbar, text="Priority:").pack(side="left")
        self._priority_var = tk.StringVar(value="all")
        priority_cb = ttk.Combobox(
            toolbar, textvariable=self._priority_var, width=10,
            values=["all", "low", "medium", "high", "critical"], state="readonly",
        )
        priority_cb.pack(side="left", padx=(4, 12))
        self._priority_var.trace_add("write", lambda *_: self._apply_filter())

        if self._on_new:
            tk.Button(toolbar, text="+ New Task", command=self._on_new).pack(side="right")

        # Treeview
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        self._tree = ttk.Treeview(
            frame, columns=self.COLUMNS, show="headings",
            yscrollcommand=scrollbar.set, selectmode="browse",
        )
        scrollbar.config(command=self._tree.yview)
        scrollbar.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)

        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COLUMN_HEADERS[col])
            self._tree.column(col, width=self.COLUMN_WIDTHS[col], anchor="w")

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._id_map: dict = {}

    def load_tasks(self, tasks: List[Task]) -> None:
        self._tasks = list(tasks)
        self._apply_filter()

    def _apply_filter(self) -> None:
        from tasks.views import apply_filter

        search = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        status_val = self._status_var.get() if hasattr(self, "_status_var") else "all"
        priority_val = self._priority_var.get() if hasattr(self, "_priority_var") else "all"

        f = TaskFilter(
            search_text=search or None,
            status=None if status_val == "all" else status_val,
            priority=None if priority_val == "all" else priority_val,
        )
        filtered = apply_filter(self._tasks, f)
        self._render(filtered)

    def _render(self, tasks: List[Task]) -> None:
        self._tree.delete(*self._tree.get_children())
        self._id_map.clear()
        today = date.today()
        for t in tasks:
            due_str = t.due_date.isoformat() if t.due_date else ""
            iid = self._tree.insert(
                "", "end",
                values=(t.title, t.status, t.priority, due_str),
                tags=("overdue",) if t.due_date and t.due_date < today and t.status not in ("done", "cancelled") else (),
            )
            self._id_map[iid] = t
        self._tree.tag_configure("overdue", foreground="red")

    def _on_tree_select(self, _event) -> None:
        sel = self._tree.selection()
        if sel and self._on_select:
            self._on_select(self._id_map[sel[0]])

    def selected_task(self) -> Optional[Task]:
        sel = self._tree.selection()
        return self._id_map.get(sel[0]) if sel else None
