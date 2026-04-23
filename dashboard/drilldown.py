from dataclasses import dataclass
from typing import List, Literal, Optional
from .operational import TaskSummary

FilterType = Literal["overdue", "blocked", "completed", "all"]


@dataclass
class DrillDownFilter:
    filter_type: FilterType = "all"
    project_id: Optional[str] = None
    search_text: Optional[str] = None


class DrillDownService:
    def filtered_tasks(self, tasks: List[TaskSummary], f: DrillDownFilter) -> List[TaskSummary]:
        result = tasks
        if f.filter_type == "overdue":
            result = [t for t in result if t.is_overdue and not t.is_completed]
        elif f.filter_type == "blocked":
            result = [t for t in result if t.is_blocked and not t.is_completed]
        elif f.filter_type == "completed":
            result = [t for t in result if t.is_completed]
        if f.search_text:
            q = f.search_text.lower()
            result = [t for t in result if q in t.title.lower()]
        return result
