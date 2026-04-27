"""Test web UI views and components."""


def test_team_workload_view_exists():
    """Verify team workload view HTML exists in index.html"""
    with open("/Users/puneetsharma/Workspace/projects/ai-lab/command-center/web/static/index.html", "r") as f:
        html = f.read()

    assert "view==='team-workload'" in html or "view===\"team-workload\"" in html
    assert "Team Workload" in html or "team workload" in html.lower()
