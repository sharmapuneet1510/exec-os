# Unified Spacing System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate spacing and alignment inconsistencies across all 27 ExecOS pages by implementing a unified semantic CSS variable system.

**Architecture:** Add a CSS variable foundation layer that defines semantic spacing values (`--header-padding-top`, `--content-padding-sides`, etc.), then systematically update all page view containers, headers, and cards to reference these variables instead of using hardcoded inline styles. Apply global `box-sizing: border-box` to ensure borders are included in width calculations.

**Tech Stack:** HTML, CSS (no frameworks), Alpine.js (existing)

---

## File Structure

**Single file to modify:**
- `web/static/index.html` - All 27 page views, headers, cards, and containers

**Structure of changes:**
1. Add `<style>` block with semantic CSS variables (placed before existing inline styles)
2. Update 27 page view containers with `box-sizing: border-box`
3. Standardize 27 header sections with variable-based padding
4. Standardize card/content areas with variable-based padding and gaps
5. Remove duplicate spacing (margins + gaps)

---

## Tasks

### Task 1: Add CSS Variables Foundation

**Files:**
- Modify: `web/static/index.html` (add `<style>` block before line 2354 where `<main>` begins)

- [ ] **Step 1: Locate insertion point**

Open `web/static/index.html` and find line 2354 (the `<main>` tag). We'll insert the CSS variables block right before it.

- [ ] **Step 2: Create CSS variables block**

Add this `<style>` block immediately before the `<main>` tag (between `</style>` at line 2383 and `<main>` at 2354 - actually insert between the closing body section and main):

```html
  <style>
    /* Semantic spacing system */
    :root {
      /* Header spacing */
      --header-padding-top: 0px;
      --header-padding-bottom: 10px;
      --header-padding-sides: 20px;
      
      /* Content area spacing */
      --content-padding-top: 24px;
      --content-padding-sides: 28px;
      
      /* Card and internal spacing */
      --card-gap: 12px;
      --card-padding: 10px 14px;
      --card-border-width: 1px;
      --card-accent-border-width: 2px;
      --card-border-radius: 10px;
    }
    
    /* Global box-sizing for all elements */
    *, *::before, *::after {
      box-sizing: border-box;
    }
  </style>
```

Insert this right after the `@keyframes spin` style block (around line 2383).

- [ ] **Step 3: Verify CSS is loaded**

Open browser and navigate to any page. Open DevTools (F12) → Application → check that `:root` styles show the new variables. Should see `--header-padding-top: 0px` etc. in the computed styles.

- [ ] **Step 4: Commit**

```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
git add web/static/index.html
git commit -m "feat: add semantic spacing CSS variables foundation"
```

---

### Task 2: Add box-sizing to Main Container

**Files:**
- Modify: `web/static/index.html:2354` (the `<main>` tag)

- [ ] **Step 1: Locate main container**

Find line 2354: `<main style="flex:1;display:flex;flex-direction:column;overflow:hidden;">`

- [ ] **Step 2: Add box-sizing to main**

Update to:
```html
<main style="flex:1;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;">
```

- [ ] **Step 3: Add box-sizing to content wrapper**

Find line 2386: `<div style="flex:1;overflow-y:auto;padding:24px 28px;">`

Update to:
```html
<div style="flex:1;overflow-y:auto;padding:24px 28px;box-sizing:border-box;">
```

- [ ] **Step 4: Verify in browser**

Refresh page, inspect the main element and content div. Should show `box-sizing: border-box` in computed styles.

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add box-sizing border-box to main containers"
```

---

### Task 3: Standardize Dashboard View Header

**Files:**
- Modify: `web/static/index.html:2389-2392` (Dashboard view and stat tiles)

- [ ] **Step 1: Locate dashboard view container**

Find line 2389: `<div x-show="view==='dashboard'" x-cloak style="flex:1;display:flex;flex-direction:column;overflow:hidden;">`

- [ ] **Step 2: Add box-sizing to dashboard container**

Update to:
```html
<div x-show="view==='dashboard'" x-cloak style="flex:1;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;">
```

- [ ] **Step 3: Locate stat tiles section**

Find line 2392: `<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;padding:16px 20px 10px;flex-shrink:0;">`

- [ ] **Step 4: Update stat tiles padding**

Update to:
```html
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;padding:var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom);flex-shrink:0;box-sizing:border-box;">
```

- [ ] **Step 5: Test dashboard in browser**

Navigate to Operational dashboard. Verify stat tiles are aligned with content below, no excessive top padding.

- [ ] **Step 6: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize dashboard view spacing with variables"
```

---

### Task 4: Standardize My Book of Work Page

**Files:**
- Modify: `web/static/index.html:5688-5714` (My Book of Work view)

- [ ] **Step 1: Locate my-work view container**

Find line 5688: `<div x-show="view==='my-work'" x-cloak style="flex:1;display:flex;flex-direction:column;overflow:hidden;">`

- [ ] **Step 2: Add box-sizing to my-work container**

Update to:
```html
<div x-show="view==='my-work'" x-cloak style="flex:1;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;">
```

- [ ] **Step 3: Update header padding**

Find line 5689: `<div style="padding:0px 20px 10px;flex-shrink:0;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;flex-wrap:wrap;box-sizing:border-box;">`

Confirm padding is already `0px 20px 10px` (should be from previous fix). Update to use variables:

```html
<div style="padding:var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom);flex-shrink:0;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;flex-wrap:wrap;box-sizing:border-box;">
```

- [ ] **Step 4: Update tab container**

Find line 5692: `<div style="display:flex;background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:2px;gap:2px;margin-left:0;box-sizing:border-box;">`

Confirm `margin-left:0` is set (should be from previous fix). Add explicit `box-sizing:border-box` if not present.

- [ ] **Step 5: Update content area**

Find line 5714: `<div style="flex:1;overflow-y:auto;padding:16px 20px;box-sizing:border-box;">`

Update padding to use variables:
```html
<div style="flex:1;overflow-y:auto;padding:var(--content-padding-top) var(--content-padding-sides);box-sizing:border-box;">
```

- [ ] **Step 6: Test in browser**

Navigate to My Book of Work. Verify no excessive gap at top, cards properly aligned.

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize my-work page spacing with variables"
```

---

### Task 5: Standardize All Card-Based Pages (Part 1/2)

**Files:**
- Modify: `web/static/index.html` (Summaries, Tasks, Commitments, Alerts views)

- [ ] **Step 1: Standardize Summaries view**

Find line where `x-show="view==='summaries'"` appears. Add `box-sizing:border-box` to the container style.

Find the header in that section (should have `padding:12px 20px...`) and update to:
```html
padding:var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom)
```

Find any content divs with `padding:16px 20px` and update to:
```html
padding:var(--content-padding-top) var(--content-padding-sides)
```

- [ ] **Step 2: Standardize Tasks view**

Repeat the same process for the Tasks view (find `x-show="view==='tasks'"`)

- [ ] **Step 3: Standardize Commitments view**

Repeat for Commitments view

- [ ] **Step 4: Standardize Alerts view**

Repeat for Alerts view

- [ ] **Step 5: Update card borders in these views**

For all cards in these views, find patterns like `border:1px solid var(--border);border-left:3px` and update to:
```html
border:var(--card-border-width) solid var(--border);border-left:var(--card-accent-border-width) solid
```

- [ ] **Step 6: Test in browser**

Navigate to Summaries, Tasks, Commitments, Alerts. Verify consistent spacing across all.

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize card-based pages spacing (summaries, tasks, commitments, alerts)"
```

---

### Task 6: Standardize All Card-Based Pages (Part 2/2)

**Files:**
- Modify: `web/static/index.html` (Day Planner, Applications, Project Tracker, Release Tracker, Milestones views)

- [ ] **Step 1: Standardize Day Planner view**

Find `x-show="view==='planner'"` and apply same changes as Task 5:
- Add `box-sizing:border-box` to container
- Update header padding to use variables
- Update content padding to use variables
- Update card borders to use variables

- [ ] **Step 2: Standardize Applications view**

Repeat for Applications view

- [ ] **Step 3: Standardize Project Tracker view**

Repeat for Project Tracker view

- [ ] **Step 4: Standardize Release Tracker view**

Repeat for Release Tracker view

- [ ] **Step 5: Standardize Milestones view**

Repeat for Milestones view

- [ ] **Step 6: Test in browser**

Navigate to each page and verify spacing is consistent.

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize card-based pages spacing (day-planner, applications, project-tracker, release-tracker, milestones)"
```

---

### Task 7: Standardize Specialized Card Pages

**Files:**
- Modify: `web/static/index.html` (Jira Team, My Hub views)

- [ ] **Step 1: Standardize Jira Team view**

Find `x-show="view==='jira-team'"` and apply standard changes:
- Add `box-sizing:border-box` to container
- Update header padding to variables
- Update content padding to variables
- Update card borders to variables

- [ ] **Step 2: Standardize My Hub view**

Repeat for My Hub view

- [ ] **Step 3: Test in browser**

Navigate to both pages and verify spacing consistency.

- [ ] **Step 4: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize specialized card pages spacing (jira-team, my-hub)"
```

---

### Task 8: Standardize Table-Based Pages

**Files:**
- Modify: `web/static/index.html` (Team List, Team Workload, Resourcing, Estimate views)

- [ ] **Step 1: Standardize Team List view**

Find `x-show="view==='team-list'"` (line 5638). Update container:
```html
<div x-show="view==='team-list'" x-cloak style="flex:1;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;">
```

Find header and content areas, apply variable-based padding.

- [ ] **Step 2: Standardize Team Workload view**

Find `x-show="view==='team-workload'"` and apply same changes.

- [ ] **Step 3: Standardize Resourcing view**

Find `x-show="view==='resourcing'"` and apply same changes.

- [ ] **Step 4: Standardize Estimate view**

Find `x-show="view==='estimate'"` and apply same changes.

- [ ] **Step 5: Test in browser**

Navigate to each table page and verify alignment is consistent.

- [ ] **Step 6: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize table-based pages spacing (team-list, team-workload, resourcing, estimate)"
```

---

### Task 9: Standardize Complex Layout Pages (Boards/Planners)

**Files:**
- Modify: `web/static/index.html` (Sprint Board, Proj Planner, Delivery, Inbox views)

- [ ] **Step 1: Standardize Sprint Board view**

Find `x-show="view==='sprint-board'"` and add `box-sizing:border-box` to container.

- [ ] **Step 2: Standardize Proj Planner view**

Repeat for Proj Planner

- [ ] **Step 3: Standardize Delivery view**

Repeat for Delivery

- [ ] **Step 4: Standardize Inbox view**

Repeat for Inbox

- [ ] **Step 5: Test in browser**

Navigate to each complex page and verify spacing doesn't break layouts.

- [ ] **Step 6: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize complex layout pages spacing (sprint-board, proj-planner, delivery, inbox)"
```

---

### Task 10: Standardize Form/Admin Pages

**Files:**
- Modify: `web/static/index.html` (Admin, API Tokens, Email Briefing, Activity Log views)

- [ ] **Step 1: Standardize Admin view**

Find `x-show="view==='admin'"` and add `box-sizing:border-box` to container.
Update any section headers and content areas to use padding variables.

- [ ] **Step 2: Standardize API Tokens view**

Find `x-show="view==='api-tokens'"` (line 6444) and apply same changes.

- [ ] **Step 3: Standardize Email Briefing view**

Repeat for Email Briefing view

- [ ] **Step 4: Standardize Activity Log view**

Repeat for Activity Log view

- [ ] **Step 5: Test in browser**

Navigate to each admin page and verify forms align properly.

- [ ] **Step 6: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize form/admin pages spacing (admin, api-tokens, email-briefing, activity-log)"
```

---

### Task 11: Standardize Remaining Views

**Files:**
- Modify: `web/static/index.html` (Executive, Operational, Inbox, Delivery views if not completed)

- [ ] **Step 1: Identify any remaining views**

Search for `x-show="view==='` patterns to find views not yet covered:
- Executive
- Operational
- Any others

- [ ] **Step 2: Apply standardization to remaining views**

For each remaining view:
- Add `box-sizing:border-box` to main container
- Update header padding to use variables
- Update content padding to use variables
- Update card borders to use variables

- [ ] **Step 3: Test in browser**

Navigate to all pages and verify consistent spacing.

- [ ] **Step 4: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize remaining pages spacing (executive, operational, and others)"
```

---

### Task 12: Remove Duplicate Spacing from Tab Containers

**Files:**
- Modify: `web/static/index.html` (all pages with tab toggles)

- [ ] **Step 1: Search for duplicate margin-gap patterns**

Search for `margin-left:12px` in tab containers throughout the file.

For each occurrence, verify it's already been updated to `margin-left:0` from previous fixes.

- [ ] **Step 2: Verify no other duplicate spacing**

Search for patterns where both margin and flex gap appear on the same elements.

- [ ] **Step 3: Test in browser**

Navigate to My Work, Team Work, and any other pages with tab toggles. Verify spacing is correct.

- [ ] **Step 4: Commit (if changes made)**

```bash
git add web/static/index.html
git commit -m "feat: remove duplicate spacing from tab containers"
```

---

### Task 13: Standardize Card Gaps Across All Pages

**Files:**
- Modify: `web/static/index.html` (all pages with card layouts)

- [ ] **Step 1: Find flex containers with hardcoded gaps**

Search for `gap:12px` and `gap:10px` patterns in flex containers that hold cards.

- [ ] **Step 2: Replace hardcoded gaps with variable**

Update all `gap:12px` to `gap:var(--card-gap)` in card container flex layouts.

- [ ] **Step 3: Update card padding values**

Find card header padding patterns like `padding:10px 14px` and update to:
```html
padding:var(--card-padding)
```

- [ ] **Step 4: Test in browser**

Navigate to all card-based pages and verify gaps are consistent.

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: standardize card gaps and padding with variables"
```

---

### Task 14: Visual Verification and Testing

**Files:**
- Test: Manual verification in browser (no code changes)

- [ ] **Step 1: Test all 27 pages in browser**

Open ExecOS app and navigate to each page:

**Card-Based Pages:**
- [ ] My Work
- [ ] Summaries
- [ ] Tasks
- [ ] Commitments
- [ ] Alerts
- [ ] Day Planner
- [ ] Applications
- [ ] Project Tracker
- [ ] Release Tracker
- [ ] Milestones
- [ ] Jira Team
- [ ] My Hub

**Table Pages:**
- [ ] Team List
- [ ] Team Workload
- [ ] Resourcing
- [ ] Estimate

**Dashboard/Grid:**
- [ ] Operational
- [ ] Executive
- [ ] Dashboard

**Complex Layouts:**
- [ ] Sprint Board
- [ ] Proj Planner
- [ ] Delivery
- [ ] Inbox

**Form/Admin:**
- [ ] Admin
- [ ] API Tokens
- [ ] Email Briefing
- [ ] Activity Log

- [ ] **Step 2: Verify for each page**

For each page, check:
- ✓ No excessive gap between top bar and page content
- ✓ Headers aligned flush with content area
- ✓ Card borders are consistent (1px + 2px accent)
- ✓ Gaps between cards are uniform (12px)
- ✓ No content overflow or misalignment
- ✓ Visual spacing rhythm is consistent with other pages

- [ ] **Step 3: Take browser console screenshot**

Check DevTools console for any errors. Should be clean with no new spacing-related errors.

- [ ] **Step 4: Document any issues found**

If any page has spacing issues, note the page name and specific issue for fixing.

- [ ] **Step 5: Fix any issues (if found)**

If issues found, make targeted fixes to those specific pages and re-test.

- [ ] **Step 6: Final verification**

Do one final pass through all 27 pages to confirm everything is aligned and spaced consistently.

- [ ] **Step 7: No commit needed**

This is purely verification. No code changes in this task.

---

### Task 15: Final Cleanup and Documentation

**Files:**
- Modify: `web/static/index.html` (final review and cleanup)

- [ ] **Step 1: Search for any remaining hardcoded spacing values**

Search the entire file for patterns that should use variables but don't:
- `padding:12px 20px`
- `padding:16px 20px`
- `gap:12px`
- `gap:10px`

- [ ] **Step 2: Replace with variables where appropriate**

For main structural spacing, replace with variables. For component-specific spacing, can leave as-is if it's intentional.

- [ ] **Step 3: Add comment explaining CSS variables**

At the top of the CSS variables `<style>` block, add:

```html
<style>
  /* 
    Semantic Spacing System
    These variables define consistent spacing across all pages.
    Update these values to change spacing globally.
    
    Variables:
    - header-padding-*: Section header spacing
    - content-padding-*: Main content area spacing
    - card-*: Card container spacing and styling
  */
  :root {
    /* ... rest of variables ... */
```

- [ ] **Step 4: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add spacing documentation and finalize unified spacing system"
```

---

## Verification Checklist

After all tasks complete, verify:

- [ ] All 27 pages load without console errors
- [ ] No excessive gaps at top of any page
- [ ] Headers align flush with content (0px top padding)
- [ ] Card borders are consistent (1px + 2px accent)
- [ ] Card gaps are uniform (12px)
- [ ] Content padding is consistent (24px top, 28px sides)
- [ ] No duplicate spacing (margin + gap combinations)
- [ ] `box-sizing: border-box` applied globally
- [ ] All pages use CSS variables for spacing
- [ ] Visual rhythm is consistent across all pages
- [ ] No content overflow or misalignment issues
- [ ] All commits are atomic and well-described

---

## Success Criteria

✅ All 27 pages use semantic CSS variables for spacing  
✅ Global `box-sizing: border-box` applied  
✅ No excessive gaps between topbar and page content  
✅ Card borders consistent (1px + 2px accent)  
✅ Spacing rhythm uniform across all page types  
✅ No content overflow or alignment issues  
✅ Clean browser console (no spacing-related errors)  
✅ Each task committed separately with clear messages  

---

## Notes for Implementation

- **Order matters**: Complete tasks in order. CSS variables (Task 1) must exist before being referenced in later tasks.
- **Testing**: After each task, navigate to at least one page of that type in the browser to verify spacing looks correct.
- **Commits**: Each task should result in one commit. This makes it easy to track changes and revert if needed.
- **Consistency**: Apply the same pattern to every page - don't skip pages or assume they're already correct.
- **Line numbers**: Line numbers in this plan are approximate based on the current file. Find exact locations by searching for `x-show="view==='` patterns.
