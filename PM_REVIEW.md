# ExecOS — Honest PM Review
**Reviewer role:** Project Manager, team of 20, primary tools: Jira + GitLab
**Date:** 2026-06-17
**Version reviewed:** current `main` branch

---

## Overall Score: 4.5 / 10

> The bones are there. The finish is not. This feels like a developer's personal dashboard that was never battle-tested by someone who actually needs to manage 20 people across multiple projects every day.

---

## Scores by Area

| Area | Score | Honest Take |
|------|-------|-------------|
| UI / UX | 4/10 | 30+ views crammed into one sidebar; emoji nav; 7,827-line single HTML file |
| Jira Integration | 4/10 | Works for basic fetch; no JQL filter input; single global config; leaks across apps |
| GitLab / Open MRs | 6/10 | Best feature — all open MRs by author, project summary, draft split |
| Book of Work | 3/10 | The `/api/my-work` endpoint reads MOCK tables, not real Jira/GitLab data |
| Team Review (20 people) | 4/10 | Can see workload by person but no JQL filter, no sprint scope, no bulk view |
| SOD / EOD Notifications | 5/10 | Email only (SMTP), no Jira/GitLab data in emails, no push/desktop notifications |
| Configuration | 3/10 | 6-7 screens to configure per application; no setup wizard; polluted test data in DB |
| Multi-project / Multi-Jira | 2/10 | One global Jira URL + PAT; multiple Jira instances impossible |

---

## Critical Issues (Blockers)

### 1. `my_work_routes.py` reads MOCK database tables, not real Jira/GitLab
**File:** `web/routers/my_work_routes.py`
The `/api/my-work` endpoint imports `MockJiraIssueORM` and `MockGitLabMRORM` — fake seed-data tables.
When a user opens "My Book of Work" in the UI, it calls `/api/team/me` (which does hit real Jira),
but the older `/api/my-work` API — still wired to team member views — returns empty arrays unless
you ran `seed_data.py`. There is live code shipping dead/mock paths.

### 2. No custom JQL filter input — the core PM workflow
As a PM reviewing 20 people, I need to type a JQL like:
```
assignee in (dev1, dev2, ..., dev20) AND sprint in openSprints() AND project in (PROJ1, PROJ2)
```
There is no JQL input anywhere in the UI. The JQL is auto-built from project keys in
`_build_jql()` with a hard-coded `statusCategory != "Done"` clause. You cannot filter by sprint,
assignee group, label, or any other criteria.
**File:** `web/routers/jira_routes.py:107`

### 3. Single global Jira config — shared and leaks between applications
**File:** `web/routers/app_integration_routes.py:72-86`
When you save Jira settings for App A, it writes to the single `JiraConfigORM(id=1)` row —
overwriting the base URL and PAT globally. If you have App B pointed at a different Jira
instance, saving App A breaks App B. Multiple Jira instances are architecturally impossible
without a schema change.

### 4. No "All Open MRs across all apps" view
The GitLab Open MRs view (`/api/gitlab/mrs`) requires an `?app_id=` parameter.
There is no aggregate view that shows ALL open MRs across ALL configured applications in one
list. As a PM, I want one place to see all open work regardless of which app it belongs to.

### 5. Database polluted with 22 test applications
Live DB contains entries like `TestApp_1778565563`, `ewe`, `hh`, `Modal Test App`,
`Final Test App` from development testing. These are visible to real users in the Applications
dropdown everywhere in the UI. No data cleanup, no soft-delete, no archive for apps.

### 6. SOD/EOD emails contain zero Jira/GitLab data
**File:** `web/email_sender.py`
The SOD/EOD emails are beautifully formatted but only pull from local SQLite tables
(tasks, projects, milestones, commitments). They do NOT fetch overdue Jira tickets,
unreviewed MRs, or team blockers. For a PM, the whole point of a morning briefing is
"what's happening in Jira and GitLab today."

### 7. Sprint Board requires manual sprint_id — no active sprint auto-detection
**File:** `web/routers/sprint_routes.py`
The sprint board needs you to manually enter a `sprint_id` (a Jira internal integer).
There is no "find active sprint" call. A PM switching between projects must look up
sprint IDs manually in Jira and paste them in. This breaks the workflow completely.

---

## Serious Issues (High Priority)

### 8. Identity setup is buried — the app doesn't know who you are by default
To get "My Work" working, you must navigate to Settings → Sprint Board, then set
`my_jira_email` and `my_gitlab_username`. There is no onboarding flow or setup wizard.
First-time users will see empty states and assume the integration is broken.

### 9. Hard-coded cap of 500 Jira issues, 20 GitLab projects, 50 MRs/project
**Files:** `jira_routes.py:143`, `gitlab_routes.py:115,125`
For a team of 20 with 2+ projects each carrying 30+ active issues, 500 is actually fine,
but 20 projects cap and 50 MRs/project cap will break silently — no warning shown in UI.

### 10. 7,827-line single `index.html` — unmaintainable
One giant Alpine.js SPA with all state, all views, all JS in a single file with no component
separation. Every feature addition increases collision risk. The file already has:
- Navigation registered in 4 different `x-show` expressions
- State variables scattered across the top-level Alpine data object
- No error boundaries — a JS error in any view breaks the entire app

### 11. `verify=False` on all Jira and GitLab HTTPS calls — security issue
**Files:** `jira_routes.py:82`, `gitlab_routes.py:47`, `sprint_routes.py:61`, `workload_routes.py:85`
SSL verification is disabled everywhere. Fine for internal networks, but there is no config
switch. If the app is used against cloud Jira (atlassian.net) or gitlab.com, this silently
bypasses certificate validation — a clear man-in-the-middle risk.

### 12. No pagination in the Tasks view
The Tasks view loads all tasks with `GET /api/tasks` (no limit) and filters client-side.
At 1,000+ tasks this will lock the browser tab.

### 13. Jira project keys stored as JSON strings, not structured
`jira_projects` on `ApplicationORM` is a raw JSON string field (`"[\"PROJ1\",\"PROJ2\"]"`).
Same for `gitlab_projects`. There is no referential integrity, no validation. Typos in project
keys fail silently at fetch time with no clear error message shown to users.

---

## Usability Issues (Medium Priority)

### 14. No bulk actions anywhere
Can't bulk-close tasks, bulk-reassign, bulk-change priority. For a PM managing 20 people
this is a daily need.

### 15. "Applications" model is confusing overhead for a PM
The data hierarchy is: Application → Project → Task. But Jira has its own project hierarchy.
The "Application" concept maps awkwardly to Jira — you end up creating an "Application" in
ExecOS just to configure Jira project keys, which feels like double data entry.

### 16. No task ↔ Jira ticket linking
Local tasks and Jira tickets are completely separate. There is no way to say "this local
task is tracking PROJ-123". You end up maintaining two parallel lists.

### 17. Team workload view shows ALL Jira projects, not sprint-scoped
The Jira Team Workload view (`/api/jira/team`) shows all open non-done issues across all
configured project keys. A PM wants to see "what is my team doing THIS sprint" — not the
entire backlog. No sprint filter is available.

### 18. No cross-app sprint view
Each app has its own sprint config. There is no "show me all active sprints across all my
apps in one board" view.

### 19. Open MRs view groups by author, but a PM needs "review queue" first
The GitLab MRs view groups by author. What a PM actually needs first is:
- MRs awaiting review (no reviewer or reviewer hasn't approved)
- MRs blocked by conflicts
- MRs that have been open > N days

A simple grouping "by author" buries the actionable signal.

### 20. SOD/EOD is email-only — no push/desktop/browser notification
The scheduler fires SMTP emails. There is no browser notification (Web Push API),
no tray notification (the tray module exists but is disconnected from SOD/EOD),
and no in-app notification bell for these events.

### 21. Configuration requires 6-7 steps per application — not simple
Minimum steps to onboard one application with Jira + GitLab:
1. Global Settings → Jira (URL, PAT, enable)
2. Global Settings → GitLab (URL, token, enable)
3. Create Application
4. Application → Integrations → Jira (project keys, enable)
5. Application → Integrations → GitLab (project IDs, enable)
6. Settings → Sprint Board (board ID, sprint ID, your email, your GitLab username)
7. Settings → Email (SMTP host, port, credentials, SOD/EOD times)

This is not simple configuration. For 3 applications that's 15+ forms.

### 22. No "Team JQL Review" feature — the headline PM use case is missing
A PM reviewing their 20-person team should be able to:
- Write a JQL like `project = PROJ AND sprint in openSprints() AND assignee in membersOf("team")`
- See results grouped by assignee
- Click through to Jira ticket
- Add a comment or flag from ExecOS

None of this exists. The Jira integration is read-only and JQL is not user-configurable.

---

## What Works Well

- **GitLab Open MRs view** — fetches all open MRs regardless of author, shows draft/ready split,
  links back to GitLab, grouped by author. This is genuinely useful.
- **Project health scoring** — completion rate + overdue penalty is a clean signal.
- **No external dependencies** — SQLite + Python, zero infra. Runs instantly.
- **SOD/EOD email format** — the HTML email templates are well-designed and readable.
- **Operational dashboard** — overdue count, in-progress, upcoming in 7 days — solid daily view.
- **Commitment tracking** — simple and effective for promises made to stakeholders.
- **Activity log** — audit trail is a real PM need.

---

## Prioritised Fix List

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| 1 | Add JQL filter input to Jira Team view | S | Critical |
| 2 | Fix `my_work_routes.py` to call real Jira/GitLab APIs | M | Critical |
| 3 | Add sprint_id auto-detection (active sprint lookup) | S | High |
| 4 | Add "All apps" aggregate MR + Jira view (no app_id required) | M | High |
| 5 | Include Jira overdue + MRs needing review in SOD/EOD email | M | High |
| 6 | Add onboarding wizard / identity setup on first run | M | High |
| 7 | Clean up test data — archive or hard-delete dummy apps | XS | Medium |
| 8 | Add browser push notification option for SOD/EOD | M | Medium |
| 9 | Add `verify=True` config toggle for SSL (default safe) | XS | Medium |
| 10 | Paginate tasks API + Tasks UI | S | Medium |
| 11 | Add MR review queue view (needs-review, blocked, stale) | M | Medium |
| 12 | Allow per-application Jira instance URL (multi-tenant Jira) | L | Medium |
| 13 | Break `index.html` into components (or use Jinja2 partials) | XL | Low (tech debt) |
| 14 | Add bulk task actions | S | Low |
| 15 | Add Jira ticket ↔ local task linking | L | Low |

---

## Bottom Line

ExecOS is a solid **solo developer productivity dashboard** that has been stretched toward
PM use. The core data model is sound. The FastAPI backend is clean. But the two things a PM
needs most — **custom JQL to review team work** and **a single aggregate view of all open
MRs across projects** — are either missing or broken.

The single biggest miss: the "My Book of Work" feature, which is literally the advertised
headline for PM use, still reads from seed/mock data tables instead of the real Jira API.

Fix the five critical issues and this becomes genuinely useful for a 20-person team.
As-is, you would supplement it with Jira and GitLab dashboards directly, defeating the
purpose of having a command center.
