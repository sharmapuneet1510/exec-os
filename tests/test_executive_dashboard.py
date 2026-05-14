from datetime import date, timedelta
from dashboard.executive import (CommitmentRisk, ExecutiveDashboard, ExecutiveDashboardService,
                                  ProjectHealthSummary, ReleaseReadiness)
TODAY = date(2026, 4, 22)
svc = ExecutiveDashboardService()

def test_projects_at_risk():
    d = ExecutiveDashboard(TODAY, project_health=[
        ProjectHealthSummary("p1","A",is_at_risk=True),
        ProjectHealthSummary("p2","B",is_at_risk=False)])
    assert d.projects_at_risk == 1

def test_releases_delayed():
    d = ExecutiveDashboard(TODAY, release_readiness=[
        ReleaseReadiness("r1","R1",TODAY,is_delayed=True),
        ReleaseReadiness("r2","R2",TODAY,is_delayed=False)])
    assert d.releases_delayed == 1

def test_commitment_risk_score_zero(): assert CommitmentRisk().risk_score == 0.0
def test_commitment_risk_score(): assert CommitmentRisk(10,2,4).risk_score == 0.4
def test_commitment_risk_score_missed_only(): assert CommitmentRisk(5,5,0).risk_score == 1.0

def test_to_dict_has_required_keys():
    keys = svc.build(TODAY).to_dict().keys()
    assert "projects_at_risk" in keys and "commitment_risk_score" in keys

def test_build_empty(): d = svc.build(TODAY); assert d.as_of_date == TODAY
def test_build_with_data():
    d = svc.build(TODAY,
        project_health=[ProjectHealthSummary("p1","A",is_at_risk=True)],
        total_overdue=3)
    assert d.projects_at_risk == 1 and d.total_overdue == 3

def test_build_no_risk(): d = svc.build(TODAY); assert d.projects_at_risk == 0
def test_build_commitment_risk():
    d = svc.build(TODAY, commitment_risk=CommitmentRisk(10, 1, 2))
    assert d.commitment_risk.risk_score == 0.2
