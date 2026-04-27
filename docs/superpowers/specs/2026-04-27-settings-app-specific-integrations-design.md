# Settings — App-Specific Integrations Design

**Date:** 2026-04-27  
**Status:** Approved

## Problem

The Settings page (`admin` view) currently shows global Jira, GitLab, and Sprint cards that write to singleton DB rows (`id=1`). Per-application versions of the same configs already exist in the Applications view with an "Activate" button that copies them to the global singleton. This dual-path is confusing and creates divergence between what's configured per-app and what the live views actually use.

## Goal

- Settings page integrations become application-scoped (selected via dropdown)
- Live views (Sprint Board, Team Workload, Open MRs) each get their own app selector
- Remove the global singleton write path and the "Activate" pattern entirely
- Database remains SQLite throughout (no Postgres)

## Design

### 1. Settings Page (Frontend)

Replace the three flat global integration cards (Jira, GitLab, Sprint) with a single **Integrations** card containing:

- **Application dropdown** at the top — populated from `/api/applications`
- Selecting an app fetches and renders that app's Jira, GitLab, and Sprint config via:
  - `GET /api/applications/{app_id}/integrations/jira`
  - `GET /api/applications/{app_id}/integrations/gitlab`
  - `GET /api/applications/{app_id}/integrations/sprint`
- Save buttons write back to the same per-app endpoints (POST)
- **Remove** "Activate" buttons from both Settings and the Applications view tabs
- Alpine.js state: replace `jiraCfg` / `gitlabCfg` / `sprintCfg` globals with `settingsApp` (selected app object) + `settingsAppCfg: { jira:{}, gitlab:{}, sprint:{} }`
- On `admin` nav: load app list, default-select first app, load its configs
- "Test Connection" buttons pass `?app_id=` to the test endpoints

### 2. Live Views — App Selector Dropdown

Each live view gets a compact app selector at the top of its panel:

| View | localStorage key | Integration |
|------|-----------------|-------------|
| Sprint Board | `execos_sprint_app` | Sprint + Jira |
| Team Workload | `execos_jira_app` | Jira |
| Open MRs | `execos_gitlab_app` | GitLab |

Behaviour:
- App list loaded once on init, shared via `appList` state
- Selecting an app fetches that app's integration config then triggers live data fetch
- If no app selected or integration disabled → show existing "not connected" placeholder with link to Settings
- Selected app_id persisted in localStorage, restored on page load

### 3. Backend

#### Remove activate endpoints
Delete from `app_integration_routes.py`:
- `POST /api/applications/{app_id}/integrations/jira/activate`
- `POST /api/applications/{app_id}/integrations/gitlab/activate`
- `POST /api/applications/{app_id}/integrations/sprint/activate`

#### Update live-data routes to accept `app_id`
All three route files gain `app_id: str` as a required query parameter:

- `jira_routes.py` — `GET /api/jira/team?app_id=`, `POST /api/jira/test?app_id=`, `POST /api/jira/refresh?app_id=`
- `gitlab_routes.py` — `GET /api/gitlab/mrs?app_id=`, `POST /api/gitlab/test?app_id=`, `POST /api/gitlab/refresh?app_id=`
- `sprint_routes.py` — `GET /api/sprint/board?app_id=`, `GET /api/sprint/boards?app_id=`, `GET /api/sprint/sprints?app_id=`, `POST /api/sprint/refresh?app_id=`

Each route fetches config from `AppJiraConfigORM` / `AppGitLabConfigORM` / `AppSprintConfigORM` instead of the global `JiraConfigORM` / `GitLabConfigORM` / `SprintConfigORM`.

#### Remove global config read/write routes
Delete (no longer written to from UI):
- `GET/POST /api/jira/config`
- `GET/POST /api/gitlab/config`
- `GET/POST /api/sprint/config`

#### ORM / DB
`JiraConfigORM`, `GitLabConfigORM`, `SprintConfigORM` classes and their SQLite tables are left in place — no migration required, tables just go unused.

### 4. Startup Init & Nav Badges

Currently `loadJiraConfig()` and `loadGitLabConfig()` run at startup to set `jiraCfg.enabled` / `gitlabCfg.enabled`, which drive:
- The `JIRA` and `GL` badge chips in the sidebar nav
- The "not connected" guards in the Team Workload and Open MRs views

Post-refactor:
- Remove `loadJiraConfig` / `loadGitLabConfig` / `loadSprintConfig` from the startup `init` chain
- Nav badges are removed (integration status is now per-app, not global)
- "Not connected" guards in live views check the **selected app's** config (loaded when the app dropdown is set)

### 5. Sprint Board Config Save

The Sprint Board view has an inline config panel that calls `saveSprintConfig()` via `POST /api/sprint/config`. This must be updated to use `POST /api/applications/{app_id}/integrations/sprint` using the Sprint Board view's selected app dropdown value.

## What Is Not Changed

- Database engine: SQLite only (`~/.commanddesk/execos.db`)
- Per-app config tabs in the Applications view — retained as a second entry point
- All other Settings cards (Database info, Outlook, Email Briefings) — unchanged
- `AppJiraConfigORM`, `AppGitLabConfigORM`, `AppSprintConfigORM` schema — unchanged

## Out of Scope

- Migrating existing global config data into per-app rows
- Adding a "default application" system-wide concept
- Any changes to task/project/milestone/commitment/alert features
