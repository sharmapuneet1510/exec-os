---
title: Admin Applications UI — Stakeholders & Integrations
date: 2026-05-12
status: design
---

# Admin Applications UI Design

## Overview

Enhance the existing Applications view with:
- **Stakeholder management** (reusable people with name, email, role)
- **Multiple GitLab namespace integrations** (1-to-many per application)
- **Multiple Jira project integrations** (1-to-many per application)
- **Global token management** (centralized GitLab and Jira credentials)
- **Compact admin UI** with left sidebar navigation

## Database Schema

### New Tables (SQLite)

#### `stakeholders`
Store reusable people across all applications.

```sql
CREATE TABLE stakeholders (
    stakeholder_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT,  -- e.g., "Product Owner", "Tech Lead", "QA Lead"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `application_stakeholders`
Many-to-many junction table linking applications to stakeholders.

```sql
CREATE TABLE application_stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id TEXT NOT NULL,
    stakeholder_id TEXT NOT NULL,
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE,
    FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(stakeholder_id) ON DELETE CASCADE,
    UNIQUE(application_id, stakeholder_id)
);
```

#### `gitlab_integrations`
One or more GitLab namespaces per application.

```sql
CREATE TABLE gitlab_integrations (
    gitlab_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    namespace TEXT NOT NULL,  -- GitLab namespace/group path
    project_name TEXT,        -- optional, for reference
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE
);
```

#### `jira_integrations`
One or more Jira projects per application.

```sql
CREATE TABLE jira_integrations (
    jira_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    project_key TEXT NOT NULL,  -- e.g., "EXEC", "INFRA"
    project_name TEXT,          -- optional, for reference
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE
);
```

#### `integration_tokens`
Global credentials (singleton pattern, only 1 row).

```sql
CREATE TABLE integration_tokens (
    id INTEGER PRIMARY KEY DEFAULT 1,
    gitlab_base_url TEXT,        -- e.g., "https://gitlab.com"
    gitlab_token TEXT,           -- Personal Access Token (stored plaintext)
    jira_base_url TEXT,          -- e.g., "https://company.atlassian.net"
    jira_token TEXT,             -- API token or Personal Access Token (plaintext)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Changes to Existing Tables

**`applications` table:**
- No schema changes (existing `status` field covers enable/disable)
- Relationships now exist via foreign keys in new junction/integration tables

## API Endpoints

### Stakeholders

```
GET    /api/stakeholders
POST   /api/stakeholders
GET    /api/stakeholders/{id}
PATCH  /api/stakeholders/{id}
DELETE /api/stakeholders/{id}
```

**POST/PATCH body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "Product Owner"
}
```

### Application Stakeholders (many-to-many)

```
GET    /api/applications/{app_id}/stakeholders
POST   /api/applications/{app_id}/stakeholders
DELETE /api/applications/{app_id}/stakeholders/{stakeholder_id}
```

**POST body:**
```json
{
  "stakeholder_id": "<uuid>"
}
```

### GitLab Integrations

```
GET    /api/applications/{app_id}/gitlab
POST   /api/applications/{app_id}/gitlab
PATCH  /api/applications/{app_id}/gitlab/{gitlab_id}
DELETE /api/applications/{app_id}/gitlab/{gitlab_id}
```

**POST/PATCH body:**
```json
{
  "namespace": "my-group/my-project",
  "project_name": "My Project"  -- optional
}
```

### Jira Integrations

```
GET    /api/applications/{app_id}/jira
POST   /api/applications/{app_id}/jira
PATCH  /api/applications/{app_id}/jira/{jira_id}
DELETE /api/applications/{app_id}/jira/{jira_id}
```

**POST/PATCH body:**
```json
{
  "project_key": "EXEC",
  "project_name": "Executive Board"  -- optional
}
```

### Integration Tokens (Global Settings)

```
GET    /api/settings/tokens
PATCH  /api/settings/tokens
POST   /api/settings/tokens/validate
```

**PATCH body:**
```json
{
  "gitlab_base_url": "https://gitlab.com",
  "gitlab_token": "glpat-xxxxxxxxxxxx",
  "jira_base_url": "https://company.atlassian.net",
  "jira_token": "your_api_token_here"
}
```

**POST /validate body (same as PATCH):**
Returns `{valid: true}` if tokens work, `{valid: false, errors: [...]}` otherwise.

## Frontend Structure

### Left Sidebar

Add two new items to the existing navigation:
- **Applications** (icon: 🏛) — list and manage all applications
- **Settings** (icon: ⚙️) — manage global tokens

### Applications View

**Main Layout:**
- Top: "+ New Application" button (right-aligned, compact)
- Main: Table or compact card grid of all applications
  - Columns: Name | Description | Owner | Status (enable/disable toggle) | Actions

**Actions per App:**
- Edit (opens modal)
- Delete (with confirmation)
- Status toggle (active/inactive)

### Application Modal (Tabbed)

When editing or creating an application, modal opens with **4 tabs:**

1. **Overview**
   - Name (required)
   - Description (optional)
   - Owner (optional)
   - Status (dropdown: active/inactive)

2. **Stakeholders**
   - Multi-select dropdown showing all existing stakeholders
   - "Create New Stakeholder" link inside dropdown or below
   - List of linked stakeholders with remove buttons (compact)

3. **GitLab**
   - List of linked GitLab namespaces (table: Namespace | Actions)
   - "+ Add Namespace" button
   - Inline add/edit forms (compact, minimal expansion)

4. **Jira**
   - List of linked Jira projects (table: Project Key | Project Name | Actions)
   - "+ Add Project" button
   - Inline add/edit forms

### Settings View

**Compact two-section layout:**

**GitLab**
- Base URL (text input)
- Token (password input, masked)
- "Test Connection" button

**Jira**
- Base URL (text input)
- Token (password input, masked)
- "Test Connection" button

**Global Actions:**
- "Save" button (saves both)

## User Workflows

### Creating a New Application

1. Click "+ New Application"
2. Modal opens (Overview tab active)
3. Enter name, description, owner, status
4. Switch to Stakeholders tab → select from dropdown or create new
5. Switch to GitLab tab → click "+ Add Namespace" → enter namespace → save
6. Switch to Jira tab → click "+ Add Project" → enter project key → save
7. Click "Save Application" → POST to backend → modal closes, list refreshes

### Editing an Application

1. Click "Edit" on any application card/row
2. Modal opens pre-populated with existing data
3. Make changes in any tab
4. Click "Save Application" → PATCH to backend → modal closes, list refreshes

### Managing Global Tokens

1. Click "Settings" in sidebar
2. Enter GitLab and/or Jira credentials
3. Click "Test Connection" for each (validates without saving)
4. Click "Save" to persist both tokens

### Adding a Stakeholder

**Option A (Quick):**
- Open application modal → Stakeholders tab
- Click "Create New Stakeholder" link
- Modal/inline form appears with name, email, role
- Create and link in one action

**Option B (Reusable):**
- Manage in Stakeholders list (if we add a dedicated view later)
- For now, creation happens inline

## Error Handling & Validation

**Frontend:**
- Required fields: application name
- Email uniqueness: validate in UI before submit
- Duplicate namespace/project_key per app: prevent in UI

**Backend (API):**
- 400: missing required field, invalid email format, duplicate email
- 404: application/stakeholder/integration not found
- 409: duplicate association (app-stakeholder, namespace, project_key)
- 500: database error

**Token Validation:**
- "Test Connection" makes API call to GitLab/Jira
- Shows error toast if credentials invalid
- Does NOT save if test fails (user must fix and test again)

## UI Design Notes (Compact)

- Modal width: ~500px
- Form fields: standard spacing (8px vertical gap)
- Tables: minimal padding (8px row height)
- Font sizes: labels 12px, inputs 13px, secondary text 11px
- Use existing color scheme (indigo, grays, status colors)
- List items with inline edit/delete buttons (no extra rows)
- Dropdowns: use Alpine.js native or simple select for compactness

## Data Model Relationships

```
Application (1) ─── (N) ApplicationStakeholder ─── (1) Stakeholder
         ↓
         ├─ (1) ─── (N) GitLabIntegration
         └─ (1) ─── (N) JiraIntegration

IntegrationTokens (singleton, id=1, shared globally)
```

## Implementation Order

1. Create SQLAlchemy ORM models for new tables
2. Create API routers for each resource (stakeholders, integrations, tokens)
3. Update existing application routes to include relationships
4. Add database migration/init for new tables
5. Build Settings view (token management)
6. Enhance Applications view with tabbed modal
7. Test all workflows
8. Style for compact UI

## Out of Scope (Phase 2)

- Jira sprint management UI (sprints exist in Jira, we store project_key only)
- GitLab MR/issue sync (integration setup only, not sync logic)
- Audit logging for token changes
- Email notifications on stakeholder changes
- Role-based permissions for applications
