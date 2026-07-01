# Release Planner — Design Spec (v2, on Delivery subsystem)

**Date:** 2026-06-29 (revised 2026-07-01)
**Status:** Draft for review
**Branch:** `feat/release-planner`
**Workstream:** 1 of 2 (Release Planner). The Command Deck UI overhaul is a separate spec.

## Why v2

The original v1 spec added gate columns to the simple `releases` table (`ReleaseORM`). Investigation
found a fuller **Delivery subsystem** already exists and is the correct foundation:

- `DeliveryTemplate` → `DeliveryTemplateItem`: a template is an ordered checklist of steps
  (`category` = pre_release/release/post_release, `responsible_role`, `is_required`).
- `DeliveryRelease` → `DeliveryReleaseItem`: a release instantiates a template; each item tracks
  `status` (pending/in_progress/done/skipped/blocked), `assignee`, `notes`, and **`completed_at`**
  (auto-set when marked done). Release has `target_date`, `release_date`, `uat_date`, `sign_off_date`,
  `release_manager`, `status`.
- Jira sprint endpoints (`/api/jira/sprints/{release_id}`, `.../{sprint_id}/issues`) already run on
  `DeliveryRelease`.

We build on Delivery. This reduces new schema and reuses completion timestamps + sprint wiring.

## Goal

Turn Delivery into a **Release Planner** with: named delivery **stages**, **planned vs. actual** gate
dates, a **derived TODO/IN_PROGRESS/COMPLETED status**, **breach / at-risk** detection surfaced in
**SOD/EOD** briefings, **curated multi-sprint attachment** (issues become the release work list, with
"mine" flagged), and a **completion history** timeline.

## Scope

In scope: schema additions to Delivery items + a sprint-attachment table; a seeded default stage
template; health/status derivation service; sprint attach/detach + issues API; SOD/EOD breach section;
Delivery view UI (stepper, planned/actual gate timeline, sprint attach, completion history).

Out of scope: the Command Deck dark reskin (separate workstream); removing the legacy `ReleaseORM` /
`releases` view (left intact; a later cleanup can consolidate).

## Pipeline stages

```
requirement_gathering → development → qa → uat → in_prod
```

Stored as a new `stage` column on template items and release items.

## Data Model Changes

### `DeliveryTemplateItemORM`
- add `stage TEXT DEFAULT 'development'`
- add `planned_offset_days INTEGER` (nullable) — days from release `start_date`/`target_date` used to
  seed an item's planned date when a release is created from the template (optional convenience).

### `DeliveryReleaseItemORM`
- add `stage TEXT` (copied from template item on instantiation)
- add `planned_date DATE` (nullable) — the gate's **planned** date. `completed_at` is the **actual**.

### New: `DeliveryReleaseSprintORM` (`delivery_release_sprints`)
Curated sprint attachment (a release ↔ many sprints):
```
attach_id    String PK
release_id   FK → delivery_releases.release_id (CASCADE)
board_id     String
sprint_id    String
sprint_name  String
added_at     DateTime
```
(The existing `/api/jira/sprints/{release_id}` lists *all* project sprints — used only to populate the
attach picker. Attached sprints are the curated subset stored here.)

### Seed: default stage template
On startup (idempotent), ensure a `"Standard Release"` template exists with 6 items, each mapped to a
stage/category:

| Item              | stage                 | category     |
|-------------------|-----------------------|--------------|
| Requirement Cut   | requirement_gathering | pre_release  |
| Dev Completion    | development           | pre_release  |
| QA Completion     | qa                    | pre_release  |
| UAT Completion    | uat                   | pre_release  |
| UAT Sign-off      | uat                   | release      |
| Release Date      | in_prod               | release      |

## Derivation & Health (pure service: `services/release_health.py`)

`derive_status(items)`:
- `COMPLETED` — all required items `done` (or the `in_prod` item done).
- `TODO` — no item `in_progress`/`done`.
- `IN_PROGRESS` — otherwise.

`current_stage(items)` — stage of the earliest non-done required item; `in_prod` if all done.

`item_health(item, today, RISK_WINDOW=3)`:
- `done` — status `done` (uses `completed_at` as actual).
- `breached` — `planned_date < today` and status not `done`/`skipped`.
- `at_risk` — `today ≤ planned_date ≤ today+RISK_WINDOW`, status `pending`, stage not yet reached.
- `upcoming` / `unset` otherwise.

`release_health(...)` rolls up: `breached` if any item breached, else `at_risk` if any at risk, else
`on_track`. `RISK_WINDOW` is a module constant.

## API Changes (`/api/delivery`)

- `ReleaseItemPatch` gains `planned_date` and `stage`; `_rel_item_out` returns both.
- `TemplateItemIn` / template-item output gain `stage`, `planned_offset_days`.
- Release detail (`GET /releases/{id}`) and list gain a computed `health` block:
  `{ level, derived_status, current_stage, items:[{item_id,title,stage,planned_date,completed_at,state,days}] }`.
- Sprint attachment:
  - `GET  /releases/{id}/sprints` → attached sprints, each with issues (via `jira_service.get_sprint_issues`),
    flagging `mine` when issue assignee matches the configured user identity.
  - `POST /releases/{id}/sprints` `{board_id, sprint_id, sprint_name}` → attach.
  - `DELETE /releases/{id}/sprints/{attach_id}` → detach.

### SOD / EOD
`GET /api/dashboard/sod` and `/eod` gain `releases_at_risk`:
```json
{ "release_id":"…","name":"Platform v2.0","item":"Dev Completion",
  "stage":"development","state":"breached","planned":"2026-06-20","days":9 }
```
Built by iterating non-completed delivery releases, running `release_health`, emitting one entry per
breached/at-risk item. The email briefing renderer adds a "Releases at risk" section when non-empty,
honoring existing SOD/EOD enable flags.

## UI — Delivery view (Release Planner)

Extend the existing `delivery` view (built with existing component classes so it inherits the Command
Deck theme when that workstream lands). Per release:
- header: name, version, Jira version, application, target date, sprint summary (`N sprints · M issues`);
- badges: release health, derived status, current stage;
- **stage stepper** (5 stages; done/current/breached);
- **gate timeline**: items grouped/ordered by stage, each showing Planned (`planned_date`) vs Actual
  (`completed_at`) + a state pill;
- **Jira Sprints** panel: attached sprints + their issues (`mine` flagged), attach/detach;
- **Completion History**: items with `completed_at`, chronological.

Item edit: set `status` (auto-stamps `completed_at`), `planned_date`, `assignee`, `notes`.

## Migration (`db/init_db.py._migrate()` — idempotent)

```sql
ALTER TABLE delivery_template_items ADD COLUMN stage TEXT DEFAULT 'development';
ALTER TABLE delivery_template_items ADD COLUMN planned_offset_days INTEGER;
ALTER TABLE delivery_release_items  ADD COLUMN stage TEXT;
ALTER TABLE delivery_release_items  ADD COLUMN planned_date DATE;
```
Plus `create_all` creates `delivery_release_sprints`, and a guarded seeder inserts the default
"Standard Release" template if absent.

## Testing

- `release_health` / `derive_status` / `current_stage` unit tests: each item state, rollup, boundary
  cases (`planned == today`, `planned == today+RISK_WINDOW`), and status derivation.
- API: create release from default template → items carry stage + can set `planned_date`; PATCH item to
  `done` stamps `completed_at` and flips health.
- Sprint attach/detach: attach two sprints → both returned with issues; `mine` flag correct; detach removes.
- SOD/EOD: a breached + an at-risk release appear in `releases_at_risk`; completed releases excluded.
- Migration/seed: new columns exist; default template seeded exactly once.

## Assumptions

- `RISK_WINDOW` = 3 calendar days.
- "mine" = Jira issue assignee matches the configured sprint/user identity (existing `my_work` identity).
- Legacy `releases` table and `ReleaseORM` remain; not migrated in this workstream.
- Attaching a sprint stores board/sprint id + name; issues are fetched live from Jira on read.
