import logging
from datetime import date, timedelta
from typing import List

from .model import CarryForwardRecord, DailyPlan
from .store import JSONPlanStore

logger = logging.getLogger(__name__)


class CarryForwardService:
    """
    Identifies incomplete tasks at EOD and carries them into the next day's plan.
    On login the following day, carried tasks are visible in the new plan.
    """

    def __init__(self, store: JSONPlanStore):
        self._store = store

    def identify_incomplete(self, plan_date: date) -> List[str]:
        """Return task IDs that are planned but not completed for the given date."""
        plan = self._store.load(plan_date)
        if not plan:
            return []
        return plan.incomplete_task_ids()

    def carry_forward(self, from_date: date) -> DailyPlan:
        """
        Carry incomplete tasks from from_date into from_date+1.
        Returns the updated next-day plan.
        Already-carried tasks have their carry_count incremented.
        Tasks already completed are excluded.
        """
        to_date = from_date + timedelta(days=1)
        source = self._store.load_or_create(from_date)
        target = self._store.load_or_create(to_date)

        incomplete = source.incomplete_task_ids()
        if not incomplete:
            logger.info("No incomplete tasks on %s — nothing to carry forward", from_date)
            return target

        # Build a lookup of existing carry records on source to propagate carry_count
        source_carry_counts = {r.task_id: r.carry_count for r in source.carry_forward_records}

        carried = 0
        for task_id in incomplete:
            if task_id not in target.task_ids:
                target.task_ids.append(task_id)

            # Update or create carry record on target
            existing = next((r for r in target.carry_forward_records if r.task_id == task_id), None)
            if existing:
                existing.carry_count += 1
            else:
                original_date = next(
                    (r.original_date for r in source.carry_forward_records if r.task_id == task_id),
                    from_date,
                )
                prior_count = source_carry_counts.get(task_id, 0)
                target.carry_forward_records.append(CarryForwardRecord(
                    task_id=task_id,
                    original_date=original_date,
                    carried_date=to_date,
                    carry_count=prior_count + 1,
                ))
            carried += 1

        self._store.save(target)
        logger.info("Carried %d task(s) from %s → %s", carried, from_date, to_date)
        return target

    def get_carried_tasks(self, plan_date: date) -> List[CarryForwardRecord]:
        """Return carry-forward records for tasks that were carried into the given date."""
        plan = self._store.load(plan_date)
        if not plan:
            return []
        return plan.carry_forward_records
