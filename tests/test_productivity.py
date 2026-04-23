from datetime import date, timedelta
import pytest
from productivity.model import DailyMetric, ProductivityReport
from productivity.store import JSONMetricsStore
from productivity.service import ProductivityService

D1, D2, D3 = date(2026,4,20), date(2026,4,21), date(2026,4,22)

@pytest.fixture
def store(tmp_path): return JSONMetricsStore(tmp_path / "metrics")
@pytest.fixture
def svc(store): return ProductivityService(store)

# Model
def test_completion_rate(): assert DailyMetric(D1,10,7,2).completion_rate == 0.7
def test_completion_rate_zero_planned(): assert DailyMetric(D1,0,0,0).completion_rate == 0.0
def test_daily_metric_round_trip():
    m = DailyMetric(D1,5,4,1)
    assert DailyMetric.from_dict(m.to_dict()) == m

def test_report_totals():
    r = ProductivityReport(D1, D3, [DailyMetric(D1,10,8,1), DailyMetric(D2,5,5,0)])
    assert r.total_planned == 15
    assert r.total_completed == 13
    assert r.total_overdue == 1

def test_report_avg_completion_rate():
    r = ProductivityReport(D1, D2, [DailyMetric(D1,10,10,0), DailyMetric(D2,10,5,0)])
    assert r.avg_completion_rate == 0.75

def test_report_overdue_trend():
    r = ProductivityReport(D1, D2, [DailyMetric(D2,5,3,2), DailyMetric(D1,5,4,1)])
    assert r.overdue_trend == [1, 2]  # sorted by date

# Store
def test_store_load_missing(store): assert store.load(D1) is None
def test_store_save_load(store):
    store.save(DailyMetric(D1,10,8,1))
    m = store.load(D1)
    assert m.completed == 8

def test_store_range(store):
    for d, pl, co, ov in [(D1,10,8,1),(D2,8,6,2),(D3,5,5,0)]:
        store.save(DailyMetric(d,pl,co,ov))
    results = store.range(D1, D2)
    assert len(results) == 2
    assert results[0].metric_date == D1

# Service
def test_record_day(svc):
    m = svc.record_day(D1, 10, 7, 2)
    assert m.planned == 10
    assert m.completion_rate == 0.7

def test_get_report(store, svc):
    store.save(DailyMetric(D1,10,9,0))
    store.save(DailyMetric(D3,5,3,1))
    r = svc.get_report(D1, D3)
    assert len(r.metrics) == 2

def test_last_30_days_returns_report(svc):
    r = svc.last_30_days()
    assert r.start_date <= r.end_date
