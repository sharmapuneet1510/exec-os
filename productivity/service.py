import logging
from datetime import date, timedelta
from typing import Optional

from .model import DailyMetric, ProductivityReport
from .store import JSONMetricsStore

logger = logging.getLogger(__name__)


class ProductivityService:
    def __init__(self, store: JSONMetricsStore):
        self._store = store

    def record_day(self, metric_date: date, planned: int, completed: int, overdue: int) -> DailyMetric:
        metric = DailyMetric(metric_date=metric_date, planned=planned,
                             completed=completed, overdue=overdue)
        self._store.save(metric)
        logger.info("Recorded metrics for %s: %d/%d completed, %d overdue",
                    metric_date, completed, planned, overdue)
        return metric

    def get_report(self, start: date, end: date) -> ProductivityReport:
        metrics = self._store.range(start, end)
        return ProductivityReport(start_date=start, end_date=end, metrics=metrics)

    def last_30_days(self) -> ProductivityReport:
        end = date.today()
        start = end - timedelta(days=29)
        return self.get_report(start, end)

    def last_quarter(self) -> ProductivityReport:
        end = date.today()
        start = end - timedelta(days=89)
        return self.get_report(start, end)
