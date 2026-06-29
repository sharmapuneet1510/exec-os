# Release Planner — Design Spec

**Date:** 2026-06-29
**Status:** Draft for review
**Workstream:** 1 of 2 (Release Planner). The Command Deck UI overhaul is a separate spec.

## Goal

Extend the existing `releases` feature into a **Release Planner** that tracks each release through a
fixed delivery pipeline with **planned vs. actual gate dates**, derives an overall status, detects
**breached** and **at-risk** gates, and surfaces those breaches in the **SOD/EOD briefings**.

## Scope

In scope:
- New stage-gate date columns on `releases` (planned + actual per gate).
- A `stage` field (pipeline phase) that drives a derived `status`.
- Breach / at-risk computation per gate and rolled up per release.
- Release Planner UI: stage stepper + planned/actual gate timeline + edit modal.
- SOD/EOD endpoints + email briefings gain a "Releases at risk" section.

Out of scope (separate workstream):
- The Command Deck dark visual overhaul. The Planner UI is built with the existing component
  classes (`.card`, `.chip`, `.btn-primary`, plus new `.stepper`/`.gate` classes defined via design
  tokens) so it inherits whatever theme is active — graphite today, Command Deck after the overhaul.

## Data Model

### Pipeline stages (ordered)

```
requirement_gathering → development → qa → uat → in_prod
```

Stored in a new `stage` column (`String`, default `"requirement_gathering"`).

### Gates (each = planned + actual date)

| Gate              | Ends stage             | Planned column            | Actual column            | Legacy source        |
|-------------------|------------------------|---------------------------|--------------------------|----------------------|
| Requirement Cut   | requirement_gathering  | `requirement_cut_planned` | `requirement_cut_actual` | —                    |
| Dev Completion    | development            | `dev_done_planned`        | `dev_done_actual`        | —                    |
| QA Completion     | qa                     | `qa_done_planned`         | `qa_done_actual`         | —                    |
| UAT Completion    | uat                    | `uat_done_planned`        | `uat_done_actual`        | `uat_date` → planned |
| UAT Sign-off      | uat                    | `uat_signoff_planned`     | `uat_signoff_actual`     | `sign_off_date` → actual |
| Release Date      | in_prod                | `due_date` (reused)       | `release_actual`         | —                    |

Notes:
- `due_date` already represents the planned go-live; it **is** the Release-Date planned value (no new
  planned column — keep one source of truth). A new `release_actual` records actual go-live.
- Legacy `uat_date` and `sign_off_date` are copied into the new columns by the migration and then left
  in place for backward compatibility (no destructive drop).
- All new columns are `Date`, nullable.

### Status derivation (stage drives status)

`status` is **computed**, not hand-set, exposed in `ReleaseOut`:
- `COMPLETED` — `release_actual` is set (shipped).
- `TODO` — `stage == requirement_gathering` AND no gate actuals recorded.
- `IN_PROGRESS` — anything in between.

The legacy free-text `status` column is retained but no longer authoritative; the API returns the
derived value. (We keep the column to avoid a destructive migration and to not break existing filters
immediately; a follow-up can remove it.)

## Breach / At-Risk Computation

A pure service function `compute_release_health(release, today)` returns, per gate:

- `done` — actual date is set.
- `breached` — actual empty AND planned `< today`.
- `at_risk` — actual empty AND `today <= planned <= today + RISK_WINDOW` (default 3 days) AND the
  gate's stage has not yet been completed.
- `upcoming` — actual empty AND planned `> today + RISK_WINDOW`.
- `unset` — no planned date.

Rolled up to a release-level health:
- `breached` if any gate is breached,
- else `at_risk` if any gate is at risk,
- else `on_track`.

`RISK_WINDOW` is a module constant (3 days) so it's trivially tunable.

## API Changes

- `ReleaseOut` gains: all new planned/actual columns, `stage`, derived `status`, and a `health` block:
  `{ level: "on_track|at_risk|breached", gates: [{ key, label, planned, actual, state, days }] }`.
- `POST /api/releases` and `PATCH /api/releases/{id}` accept the new gate dates and `stage`.
- No new endpoints required for CRUD; health is computed on read.

### SOD / EOD

`GET /api/dashboard/sod` and `/eod` gain a `releases_at_risk` array:

```json
"releases_at_risk": [
  { "release_id": "...", "name": "Platform v2.0 — GA", "gate": "Dev Completion",
    "state": "breached", "planned": "2026-06-20", "days": 9 }
]
```

Built by iterating active releases (status != COMPLETED), running `compute_release_health`, and
emitting one entry per breached/at-risk gate. The email briefing renderer adds a "Releases at risk"
section when this array is non-empty, honoring the existing SOD/EOD enable flags.

## UI — Release Planner View

Reachable from the existing `releases` / `planner` nav. Per release card:
- Header: name, version, **Jira version**, application, target date.
- Badges: release health (`On Track`/`At Risk`/`Breached`), derived status, current stage.
- **Stage stepper**: 5 steps (Req Gathering → Dev → QA → UAT → In Prod); done = check, current =
  filled, a stage whose gate is breached = red.
- **Gate timeline**: 6 gate tiles, each showing Planned vs Actual and a state pill
  (`Done` / `In Progress` / `At Risk · Nd` / `Breached Nd` / `Upcoming`).
- Filters: by application and by health.

### Edit modal

Existing release modal extended with: a `stage` selector and, per gate, a **Planned** and **Actual**
date input. Status is shown read-only (derived). Saving PATCHes the new fields.

## Migration

Append idempotent statements to the existing `_migrate()` list in `db/init_db.py` (each wrapped by the
existing duplicate-column-tolerant executor):

```sql
ALTER TABLE releases ADD COLUMN stage TEXT DEFAULT 'requirement_gathering';
ALTER TABLE releases ADD COLUMN requirement_cut_planned DATE;
ALTER TABLE releases ADD COLUMN requirement_cut_actual  DATE;
ALTER TABLE releases ADD COLUMN dev_done_planned DATE;
ALTER TABLE releases ADD COLUMN dev_done_actual  DATE;
ALTER TABLE releases ADD COLUMN qa_done_planned DATE;
ALTER TABLE releases ADD COLUMN qa_done_actual  DATE;
ALTER TABLE releases ADD COLUMN uat_done_planned DATE;
ALTER TABLE releases ADD COLUMN uat_done_actual  DATE;
ALTER TABLE releases ADD COLUMN uat_signoff_planned DATE;
ALTER TABLE releases ADD COLUMN uat_signoff_actual  DATE;
ALTER TABLE releases ADD COLUMN release_actual DATE;
```

Plus a one-time backfill (guarded so it only runs when targets are null):
`uat_done_planned := uat_date`, `uat_signoff_actual := sign_off_date`.

## Testing

- `compute_release_health` unit tests: each gate state (done/breached/at_risk/upcoming/unset) and the
  rollup, with a fixed `today` and boundary cases (planned == today, planned == today+RISK_WINDOW).
- Status derivation tests (TODO / IN_PROGRESS / COMPLETED).
- API test: create release with gate dates → `health` block correct; PATCH actual flips a gate to done.
- SOD/EOD test: a breached + an at-risk release appear in `releases_at_risk`; completed releases excluded.
- Migration test: columns exist after `create_all`; legacy backfill populates new columns.

## Assumptions

- `RISK_WINDOW` = 3 calendar days (not business days) for v1.
- "Stage drives status" — stage is the single field users set to advance the pipeline; status is never
  written directly.
- Existing releases with only legacy dates still render (missing gates show as `unset`, not breached).
