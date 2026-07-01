"""Beautiful HTML email generator and SMTP sender for ExecOS SOD/EOD briefings."""

import json
import logging
import smtplib
import urllib.parse
import urllib3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, datetime, timedelta
from html import escape as _he
from sqlalchemy.orm import Session

import requests

from db.models import (
    TaskORM, ProjectORM, MilestoneORM, CommitmentORM, EmailConfigORM, ApplicationORM,
    JiraConfigORM, AppGitLabConfigORM, SprintConfigORM, ReminderORM,
)
from web.config import get_ssl_verify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_email_log = logging.getLogger("execos.email")


# ── tiny helpers ──────────────────────────────────────────────────────────────

_PRIORITY_COLORS = {
    "critical": ("FFF1F2", "E11D48"),
    "high":     ("FFF7ED", "EA580C"),
    "medium":   ("EFF6FF", "2563EB"),
    "low":      ("F0FDF4", "16A34A"),
}

_HEALTH_STYLES = {
    "green":  ("F0FDF4", "16A34A", "On Track"),
    "yellow": ("FEFCE8", "CA8A04", "At Risk"),
    "red":    ("FFF1F2", "E11D48", "Off Track"),
    "grey":   ("F8FAFC", "64748B", "No Data"),
}


def _pill(text, bg, fg):
    return (f'<span style="display:inline-block;padding:2px 10px;border-radius:99px;'
            f'font-size:11px;font-weight:700;background:#{bg};color:#{fg};">{text}</span>')


def _priority_pill(p):
    bg, fg = _PRIORITY_COLORS.get(p, ("F8FAFC", "64748B"))
    return _pill(p.title(), bg, fg)


def _health_badge(h):
    bg, fg, label = _HEALTH_STYLES.get(h, ("F8FAFC", "64748B", h.title()))
    return _pill(label, bg, fg)


def _progress_bar(pct, health):
    color = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444"}.get(health, "#94A3B8")
    w = min(max(pct, 0), 100)
    return (f'<div style="background:#F1F5F9;border-radius:99px;height:7px;overflow:hidden;margin-top:7px;">'
            f'<div style="background:{color};width:{w}%;height:7px;border-radius:99px;"></div></div>')


def _days_overdue(due_str):
    try:
        delta = (date.today() - date.fromisoformat(due_str)).days
        if delta <= 0: return ""
        return f"{delta} day{'s' if delta != 1 else ''} overdue"
    except Exception:
        return ""


def _project_health(tasks, today_str):
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == "done")
    ov = sum(1 for t in tasks if t.due_date and str(t.due_date) < today_str and t.status not in ("done", "cancelled"))
    pct = round(done / total * 100) if total else 0
    if ov > 0:
        health = "red"
    elif pct >= 50:
        health = "green"
    elif pct >= 20:
        health = "yellow"
    else:
        health = "grey"
    return health, pct, done, total, ov


def _task_to_app_names(tasks, db: Session) -> dict:
    """Map task_id → application name. Returns dict with 'app_name' key added to tasks."""
    projects = {p.project_id: (p.name, p.application_id) for p in db.query(ProjectORM).all()}
    apps = {a.application_id: a.name for a in db.query(ApplicationORM).all()} if db.query(ApplicationORM).count() else {}

    result = []
    for t in tasks:
        proj_info = projects.get(t.project_id)
        app_name = "Unassigned"
        if proj_info:
            proj_name, app_id = proj_info
            app_name = apps.get(app_id, "Unassigned")
        # Add app_name as attribute for easy access in templates
        t._email_app_name = app_name
        result.append(t)
    return result


# ── email wrapper ─────────────────────────────────────────────────────────────

def _wrap(body_html, preheader=""):
    pre = (f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader}&nbsp;</div>'
           if preheader else "")
    ts = datetime.now().strftime("%B %d, %Y  %I:%M %p")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>ExecOS</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:#EEF2F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,Helvetica,sans-serif;-webkit-text-size-adjust:100%;color:#1E293B;">
{pre}
<table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#EEF2F7;">
  <tr><td align="center" style="padding:24px 16px;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="max-width:620px;">
      <tr><td>
{body_html}
        <!-- footer -->
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr><td style="padding:20px 8px 8px;text-align:center;font-size:12px;color:#94A3B8;line-height:1.6;">
            ExecOS Command Center &nbsp;·&nbsp; {ts}<br>
            <span style="font-size:11px;">You're receiving this because SOD/EOD emails are enabled in ExecOS.</span>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def _card(title, icon, content_html, accent="#6366F1", empty_msg=""):
    if not content_html.strip():
        if empty_msg:
            content_html = f'<p style="margin:0;color:#94A3B8;font-size:13px;">{empty_msg}</p>'
        else:
            return ""
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" role="presentation"
  style="background:#FFFFFF;border-radius:18px;margin-bottom:14px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.07);">
  <tr>
    <td style="padding:18px 22px 14px;border-bottom:1.5px solid #F1F5F9;">
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
        <tr>
          <td width="34">
            <div style="width:34px;height:34px;border-radius:10px;background:{accent};
              display:flex;align-items:center;justify-content:center;
              font-size:16px;text-align:center;line-height:34px;">{icon}</div>
          </td>
          <td style="padding-left:10px;">
            <span style="font-size:11.5px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:#334155;">{title}</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr><td style="padding:14px 22px 18px;">{content_html}</td></tr>
</table>"""


def _task_row(title, priority, project="", note="", note_color="#94A3B8", check_color=""):
    check = ""
    if check_color:
        check = (f'<td width="24" valign="top" style="padding-top:2px;">'
                 f'<div style="width:20px;height:20px;border-radius:6px;background:{check_color};'
                 f'text-align:center;line-height:20px;font-size:11px;font-weight:800;'
                 f'color:{"#10B981" if check_color=="#D1FAE5" else "#EF4444"};">'
                 f'{"✓" if check_color=="#D1FAE5" else "✕"}</div></td>')
    meta_parts = []
    if note:
        meta_parts.append(f'<span style="color:{note_color};font-size:11.5px;font-weight:600;">{note}</span>')
    if project:
        meta_parts.append(f'<span style="color:#94A3B8;font-size:11.5px;">{project}</span>')
    meta = ('&nbsp;·&nbsp;'.join(meta_parts)) if meta_parts else ""
    return f"""
<tr>
  {check}
  <td style="padding:9px 0;border-bottom:1px solid #F8FAFC;vertical-align:top;">
    <div style="font-size:13.5px;font-weight:600;color:#1E293B;line-height:1.4;">{title}</div>
    {"<div style='margin-top:4px;'>"+meta+"</div>" if meta else ""}
  </td>
  <td width="80" style="padding:9px 0;border-bottom:1px solid #F8FAFC;vertical-align:top;text-align:right;">
    {_priority_pill(priority)}
  </td>
</tr>"""


# ── live-data helpers ────────────────────────────────────────────────────────

def _releases_at_risk_section(db) -> str:
    """Render breached/at-risk release gates as an email card (empty string if none)."""
    from web.routers.dashboard import _releases_at_risk
    rows = _releases_at_risk(db)
    if not rows:
        return ""
    body = ""
    for r in rows:
        color = "#DC2626" if r["state"] == "breached" else "#D97706"
        label = f'{"Breached" if r["state"] == "breached" else "At risk"} {r["days"]}d'
        body += _task_row(f'{r["name"]} — {r["item"]}', "", note=label, note_color=color)
    table = f'<table width="100%" cellpadding="0" cellspacing="0" role="presentation">{body}</table>'
    return _card("Releases at risk", "🚦", table, accent="#DC2626")


def _get_sprint_cfg(db):
    cfg = db.query(SprintConfigORM).first()
    return cfg or SprintConfigORM()


def _get_jira_cfg(db):
    cfg = db.query(JiraConfigORM).first()
    return cfg or JiraConfigORM()


def _get_gl_configs(db):
    return db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.enabled == True).all()


def _fetch_my_jira_issues(db, jql: str) -> list:
    jira_cfg = _get_jira_cfg(db)
    if not getattr(jira_cfg, 'enabled', False) or not getattr(jira_cfg, 'pat', None):
        return []
    try:
        resp = requests.get(
            f"{jira_cfg.base_url.rstrip('/')}/rest/api/2/search",
            headers={"Authorization": f"Bearer {jira_cfg.pat}", "Accept": "application/json"},
            params={"jql": jql, "maxResults": 50,
                    "fields": "summary,status,priority,issuetype,project,duedate,updated"},
            timeout=10,
            verify=get_ssl_verify(),
        )
        if resp.ok:
            issues = []
            for i in resp.json().get("issues", []):
                f = i.get("fields", {}) or {}
                issues.append({
                    "key":      i["key"],
                    "summary":  f.get("summary", ""),
                    "status":   (f.get("status")    or {}).get("name", ""),
                    "priority": (f.get("priority")  or {}).get("name", ""),
                    "type":     (f.get("issuetype") or {}).get("name", ""),
                    "project":  (f.get("project")   or {}).get("key", ""),
                    "due_date": f.get("duedate"),
                    "web_url":  f"{jira_cfg.base_url.rstrip('/')}/browse/{i['key']}",
                })
            return issues
    except Exception as exc:
        _email_log.warning("Jira fetch for email failed: %s", exc)
    return []


def _fetch_open_mrs_for_email(db) -> list:
    gl_cfgs = _get_gl_configs(db)
    mrs = []
    for gl_cfg in gl_cfgs:
        if not gl_cfg.access_token:
            continue
        raw_ids = json.loads(gl_cfg.project_ids or "[]")
        base = gl_cfg.base_url.rstrip("/")
        for pid in raw_ids[:10]:
            encoded = urllib.parse.quote(str(pid), safe="")
            try:
                resp = requests.get(
                    f"{base}/api/v4/projects/{encoded}/merge_requests",
                    headers={"PRIVATE-TOKEN": gl_cfg.access_token},
                    params={"state": "opened", "per_page": 20, "order_by": "updated_at"},
                    timeout=8,
                    verify=get_ssl_verify(),
                )
                if resp.ok:
                    for mr in resp.json():
                        mrs.append({
                            "iid":     mr["iid"],
                            "title":   mr.get("title", ""),
                            "draft":   mr.get("draft", False),
                            "web_url": mr.get("web_url", ""),
                            "author":  (mr.get("author") or {}).get("name", ""),
                            "project": str(pid),
                        })
            except Exception as exc:
                _email_log.warning("GitLab fetch for email failed (%s): %s", pid, exc)
    return mrs


def _get_active_reminders(db) -> list:
    try:
        return db.query(ReminderORM).filter(ReminderORM.is_active == True).all()
    except Exception as exc:
        _email_log.warning("Reminder fetch for email failed: %s", exc)
        return []


def _reminders_section(reminders, accent="#8B5CF6") -> str:
    if not reminders:
        return ""
    rows = "".join(
        f'<tr>'
        f'<td style="padding:5px 8px;font-size:13px;">{_he(r.title)}</td>'
        f'<td style="padding:5px 8px;font-size:12px;color:#64748b;">{_he(r.trigger_value)}</td>'
        f'</tr>'
        for r in reminders
    )
    return (
        f'<div style="margin:20px 0;">'
        f'<h3 style="font-size:14px;font-weight:700;color:#1e293b;margin:0 0 8px;">'
        f'Reminders ({len(reminders)})</h3>'
        f'<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;border:1px solid #e2e8f0;">'
        f'<thead><tr style="background:#f8fafc;">'
        f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">REMINDER</th>'
        f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">SCHEDULE</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


# ── SOD email ─────────────────────────────────────────────────────────────────

def build_sod_html(db: Session) -> str:
    today = date.today()
    today_str = today.isoformat()
    week_str = (today + timedelta(days=7)).isoformat()

    # ── live Jira + GitLab data ───────────────────────────────────────────────
    sod_jql = ('assignee = currentUser() AND statusCategory != "Done" '
               'AND duedate <= now() ORDER BY duedate ASC')
    jira_issues = _fetch_my_jira_issues(db, sod_jql)
    open_mrs = _fetch_open_mrs_for_email(db)
    sod_reminders = [r for r in _get_active_reminders(db) if r.include_in_sod]

    proj_names = {p.project_id: p.name for p in db.query(ProjectORM).all()}

    overdue_tasks = _task_to_app_names((db.query(TaskORM)
                     .filter(TaskORM.due_date < today_str, TaskORM.status.notin_(["done", "cancelled"]))
                     .order_by(TaskORM.due_date).all()), db)

    due_today = _task_to_app_names((db.query(TaskORM)
                 .filter(TaskORM.due_date == today_str, TaskORM.status.notin_(["done", "cancelled"]))
                 .order_by(TaskORM.priority).all()), db)

    in_progress_ids = {t.task_id for t in due_today}
    carry_forward = _task_to_app_names([t for t in
                     db.query(TaskORM).filter(TaskORM.status == "in_progress").all()
                     if t.task_id not in in_progress_ids], db)

    milestones = (db.query(MilestoneORM)
                  .filter(MilestoneORM.due_date >= today_str, MilestoneORM.due_date <= week_str,
                          MilestoneORM.status != "completed")
                  .order_by(MilestoneORM.due_date).all())

    commitments = (db.query(CommitmentORM)
                   .filter(CommitmentORM.status == "pending")
                   .order_by(CommitmentORM.due_date).all())

    active_projects = db.query(ProjectORM).filter(ProjectORM.status == "active").all()
    proj_stats = []
    for p in sorted(active_projects, key=lambda x: x.name):
        tasks = db.query(TaskORM).filter(TaskORM.project_id == p.project_id).all()
        health, pct, done, total, ov = _project_health(tasks, today_str)
        proj_stats.append(dict(name=p.name, health=health, pct=pct, done=done, total=total, overdue=ov))

    date_label = today.strftime("%A, %B %d, %Y")

    # ── header ────────────────────────────────────────────────────────────────
    ov_badge = ""
    if overdue_tasks:
        ov_badge = (f'<td style="padding-right:8px;">'
                    f'<div style="padding:6px 14px;background:rgba(239,68,68,.2);border:1px solid rgba(239,68,68,.35);'
                    f'border-radius:10px;font-size:12.5px;font-weight:700;white-space:nowrap;">'
                    f'<span style="color:#FCA5A5;">{len(overdue_tasks)}</span>'
                    f'<span style="color:rgba(255,255,255,.7);"> overdue</span></div></td>')

    header = f"""
<table width="100%" cellpadding="0" cellspacing="0" role="presentation"
  style="background:linear-gradient(135deg,#312E81 0%,#6366F1 60%,#4338CA 100%);
  border-radius:20px;margin-bottom:16px;overflow:hidden;">
  <tr><td style="padding:30px 28px 26px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
      color:rgba(255,255,255,.5);margin-bottom:8px;">ExecOS · Morning Briefing</div>
    <div style="font-size:27px;font-weight:800;color:#FFFFFF;letter-spacing:-.5px;margin-bottom:14px;">{date_label}</div>
    <table cellpadding="0" cellspacing="0" role="presentation"><tr>
      {ov_badge}
      <td style="padding-right:8px;">
        <div style="padding:6px 14px;background:rgba(255,255,255,.12);border-radius:10px;
          font-size:12.5px;font-weight:700;color:rgba(255,255,255,.8);white-space:nowrap;">
          {len(due_today)} due today</div></td>
      <td>
        <div style="padding:6px 14px;background:rgba(255,255,255,.12);border-radius:10px;
          font-size:12.5px;font-weight:700;color:rgba(255,255,255,.8);white-space:nowrap;">
          {len(carry_forward)} in progress</div></td>
    </tr></table>
  </td></tr>
</table>"""

    # ── overdue section ───────────────────────────────────────────────────────
    if overdue_tasks:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in overdue_tasks[:10]:
            note = _days_overdue(str(t.due_date))
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip(), note, "#EF4444")
        rows += "</table>"
        overdue_section = _card("Overdue — Needs Immediate Attention", "⚠️", rows, "#EF4444")
    else:
        overdue_section = _card("Overdue", "✅", "", empty_msg="No overdue tasks — you're all clear! 🎉")

    # ── today's work ──────────────────────────────────────────────────────────
    if due_today:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in due_today:
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip())
        rows += "</table>"
        today_section = _card("Today's Book of Work", "📋", rows, "#6366F1")
    else:
        today_section = _card("Today's Book of Work", "📋", "", empty_msg="Nothing specifically due today.")

    # ── carry forward ─────────────────────────────────────────────────────────
    carry_section = ""
    if carry_forward:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in carry_forward[:8]:
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip(), "in progress", "#F59E0B")
        rows += "</table>"
        carry_section = _card("Continuing From Yesterday", "⏳", rows, "#F59E0B")

    # ── project status ────────────────────────────────────────────────────────
    proj_section = ""
    if proj_stats:
        inner = ""
        for p in proj_stats:
            ov_warn = (f' &nbsp;<span style="font-size:11px;color:#EF4444;font-weight:700;">⚠ {p["overdue"]} overdue</span>'
                       if p["overdue"] else "")
            inner += f"""
<div style="padding:12px 0;border-bottom:1px solid #F8FAFC;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
    <tr>
      <td>
        <span style="font-size:13.5px;font-weight:700;color:#1E293B;">{p["name"]}</span>
        &nbsp;{_health_badge(p["health"])}{ov_warn}
        <div style="font-size:11.5px;color:#94A3B8;margin-top:3px;">{p["done"]} of {p["total"]} tasks done</div>
        {_progress_bar(p["pct"], p["health"])}
      </td>
      <td width="48" style="text-align:right;vertical-align:top;">
        <span style="font-size:20px;font-weight:800;color:{'#10B981' if p['health']=='green' else '#F59E0B' if p['health']=='yellow' else '#EF4444' if p['health']=='red' else '#94A3B8'};">{p["pct"]}%</span>
      </td>
    </tr>
  </table>
</div>"""
        proj_section = _card("Project Status", "📁", inner, "#0D9488")

    # ── milestones ────────────────────────────────────────────────────────────
    ms_section = ""
    if milestones:
        rows = ""
        for m in milestones:
            overdue_c = "#EF4444" if (m.due_date and str(m.due_date) < today_str) else "#94A3B8"
            rows += f"""
<div style="padding:9px 0;border-bottom:1px solid #F8FAFC;display:flex;justify-content:space-between;">
  <span style="font-size:13px;font-weight:600;color:#1E293B;">{m.title}</span>
  <span style="font-size:12px;font-weight:600;color:{overdue_c};white-space:nowrap;padding-left:12px;">{m.due_date or ""}</span>
</div>"""
        ms_section = _card("Milestones This Week", "🏁", rows, "#7C3AED")

    # ── commitments ───────────────────────────────────────────────────────────
    com_section = ""
    if commitments:
        rows = ""
        for c in commitments[:8]:
            overdue_c = "#EF4444" if (c.due_date and str(c.due_date) < today_str) else "#94A3B8"
            prefix = "⚠ " if (c.due_date and str(c.due_date) < today_str) else ""
            rows += f"""
<div style="padding:9px 0;border-bottom:1px solid #F8FAFC;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td><span style="font-size:13px;font-weight:600;color:#1E293B;">{c.title}</span></td>
    <td width="100" style="text-align:right;white-space:nowrap;">
      <span style="font-size:11.5px;font-weight:600;color:{overdue_c};">{prefix}{c.due_date or "—"}</span>
    </td>
  </tr></table>
</div>"""
        com_section = _card("Open Commitments", "🤝", rows, "#EC4899")

    # ── Jira overdue/due-today section ───────────────────────────────────────
    jira_section = ""
    if jira_issues:
        rows = "".join(
            f'<tr>'
            f'<td style="padding:5px 8px;font-weight:700;color:#6366f1;font-family:monospace;font-size:12px;">'
            f'<a href="{i["web_url"]}" style="color:#6366f1;text-decoration:none;">{_he(i["key"])}</a></td>'
            f'<td style="padding:5px 8px;font-size:13px;">{_he(i["summary"])}</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:#64748b;">{_he(i["status"])}</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:#ef4444;">{_he(i["priority"])}</td>'
            f'</tr>'
            for i in jira_issues[:15]
        )
        jira_section = (
            f'<div style="margin:20px 0;">'
            f'<h3 style="font-size:14px;font-weight:700;color:#1e293b;margin:0 0 8px;">'
            f'Jira — Overdue / Due Today ({len(jira_issues)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;border:1px solid #e2e8f0;">'
            f'<thead><tr style="background:#f8fafc;">'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">KEY</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">SUMMARY</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">STATUS</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">PRIORITY</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    # ── GitLab open MRs section ───────────────────────────────────────────────
    mrs_section = ""
    if open_mrs:
        draft_label = '<span style="color:#94a3b8;font-size:11px;">[Draft]</span>'
        mr_rows = "".join(
            f'<tr>'
            f'<td style="padding:5px 8px;font-size:13px;">'
            f'<a href="{m["web_url"]}" style="color:#6366f1;text-decoration:none;">{_he(m["title"])}</a>'
            f'{"&nbsp;" + draft_label if m["draft"] else ""}'
            f'</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:#64748b;">{_he(m["author"])}</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:#64748b;">{_he(m["project"])}</td>'
            f'</tr>'
            for m in open_mrs[:10]
        )
        mrs_section = (
            f'<div style="margin:20px 0;">'
            f'<h3 style="font-size:14px;font-weight:700;color:#1e293b;margin:0 0 8px;">'
            f'GitLab — Open MRs ({len(open_mrs)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;border:1px solid #e2e8f0;">'
            f'<thead><tr style="background:#f8fafc;">'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">TITLE</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">AUTHOR</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">PROJECT</th>'
            f'</tr></thead><tbody>{mr_rows}</tbody></table></div>'
        )

    # ── reminders section ─────────────────────────────────────────────────────
    reminders_section = _reminders_section(sod_reminders)
    releases_section = _releases_at_risk_section(db)

    body = header + overdue_section + today_section + carry_section + proj_section + ms_section + com_section + jira_section + mrs_section + releases_section + reminders_section
    preheader = f"{len(overdue_tasks)} overdue · {len(due_today)} due today — ExecOS Morning Briefing"
    return _wrap(body, preheader)


# ── EOD email ─────────────────────────────────────────────────────────────────

def build_eod_html(db: Session) -> str:
    today = date.today()
    today_str = today.isoformat()
    today_start = datetime.combine(today, datetime.min.time())

    # ── live Jira done-today data ─────────────────────────────────────────────
    eod_jql = (f'assignee = currentUser() AND status changed to Done '
               f'after "{today.isoformat()}" ORDER BY updated DESC')
    jira_done_today = _fetch_my_jira_issues(db, eod_jql)
    eod_reminders = [r for r in _get_active_reminders(db) if r.include_in_eod]

    proj_names = {p.project_id: p.name for p in db.query(ProjectORM).all()}

    completed = _task_to_app_names((db.query(TaskORM)
                 .filter(TaskORM.status == "done",
                         TaskORM.completed_at >= today_start)
                 .order_by(TaskORM.completed_at.desc()).all()), db)

    missed = _task_to_app_names((db.query(TaskORM)
              .filter(TaskORM.due_date == today_str,
                      TaskORM.status.notin_(["done", "cancelled"])).all()), db)

    still_in_progress = _task_to_app_names((db.query(TaskORM)
                         .filter(TaskORM.status == "in_progress").all()), db)

    all_overdue = _task_to_app_names((db.query(TaskORM)
                   .filter(TaskORM.due_date < today_str,
                           TaskORM.status.notin_(["done", "cancelled"]))
                   .order_by(TaskORM.due_date).all()), db)

    date_label = today.strftime("%A, %B %d, %Y")

    # ── header ────────────────────────────────────────────────────────────────
    missed_badge = ""
    if missed:
        missed_badge = (f'<td style="padding-right:8px;">'
                        f'<div style="padding:6px 14px;background:rgba(239,68,68,.2);'
                        f'border:1px solid rgba(239,68,68,.35);border-radius:10px;'
                        f'font-size:12.5px;font-weight:700;white-space:nowrap;">'
                        f'<span style="color:#FCA5A5;">{len(missed)}</span>'
                        f'<span style="color:rgba(255,255,255,.7);"> missed</span></div></td>')

    header = f"""
<table width="100%" cellpadding="0" cellspacing="0" role="presentation"
  style="background:linear-gradient(135deg,#0F766E 0%,#0D9488 55%,#0891B2 100%);
  border-radius:20px;margin-bottom:16px;overflow:hidden;">
  <tr><td style="padding:30px 28px 26px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
      color:rgba(255,255,255,.5);margin-bottom:8px;">ExecOS · Day Summary</div>
    <div style="font-size:27px;font-weight:800;color:#FFFFFF;letter-spacing:-.5px;margin-bottom:14px;">{date_label}</div>
    <table cellpadding="0" cellspacing="0" role="presentation"><tr>
      <td style="padding-right:8px;">
        <div style="padding:6px 14px;background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.35);
          border-radius:10px;font-size:12.5px;font-weight:700;white-space:nowrap;">
          <span style="color:#6EE7B7;">{len(completed)}</span>
          <span style="color:rgba(255,255,255,.7);"> completed</span></div></td>
      {missed_badge}
      <td>
        <div style="padding:6px 14px;background:rgba(255,255,255,.12);border-radius:10px;
          font-size:12.5px;font-weight:700;color:rgba(255,255,255,.8);white-space:nowrap;">
          {len(still_in_progress)} carrying forward</div></td>
    </tr></table>
  </td></tr>
</table>"""

    # ── completed ─────────────────────────────────────────────────────────────
    if completed:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in completed[:15]:
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip(),
                              check_color="#D1FAE5")
        rows += "</table>"
        completed_section = _card("Completed Today", "✅", rows, "#10B981")
    else:
        completed_section = _card("Completed Today", "📭", "", empty_msg="Nothing marked done today.")

    # ── missed ────────────────────────────────────────────────────────────────
    if missed:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in missed:
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip(),
                              note="was due today", note_color="#EF4444", check_color="#FEE2E2")
        rows += "</table>"
        missed_section = _card("Missed — Due Today, Not Done", "❌", rows, "#EF4444")
    else:
        missed_section = _card("Missed", "🎉", "", empty_msg="Nothing missed today — outstanding work!")

    # ── carry forward ─────────────────────────────────────────────────────────
    carry_section = ""
    if still_in_progress:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in still_in_progress[:8]:
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip(),
                              note="carry forward", note_color="#F59E0B")
        rows += "</table>"
        carry_section = _card("Carrying Forward to Tomorrow", "⏳", rows, "#F59E0B")

    # ── overdue backlog ───────────────────────────────────────────────────────
    ov_section = ""
    if all_overdue:
        rows = '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
        for t in all_overdue[:10]:
            note = _days_overdue(str(t.due_date))
            app_tag = f"[{t._email_app_name}]" if t._email_app_name != "Unassigned" else ""
            rows += _task_row(t.title, t.priority, f"{proj_names.get(t.project_id, '')} {app_tag}".strip(),
                              note=note, note_color="#EF4444")
        rows += "</table>"
        ov_section = _card(f"Overdue Backlog ({len(all_overdue)} items)", "⚠️", rows, "#EF4444")

    # ── Jira done-today section ───────────────────────────────────────────────
    jira_done_section = ""
    if jira_done_today:
        rows = "".join(
            f'<tr>'
            f'<td style="padding:5px 8px;font-weight:700;color:#6366f1;font-family:monospace;font-size:12px;">'
            f'<a href="{i["web_url"]}" style="color:#6366f1;text-decoration:none;">{_he(i["key"])}</a></td>'
            f'<td style="padding:5px 8px;font-size:13px;">{_he(i["summary"])}</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:#64748b;">{_he(i["status"])}</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:#ef4444;">{_he(i["priority"])}</td>'
            f'</tr>'
            for i in jira_done_today[:15]
        )
        jira_done_section = (
            f'<div style="margin:20px 0;">'
            f'<h3 style="font-size:14px;font-weight:700;color:#1e293b;margin:0 0 8px;">'
            f'Jira — Completed Today ({len(jira_done_today)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;border:1px solid #e2e8f0;">'
            f'<thead><tr style="background:#f8fafc;">'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">KEY</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">SUMMARY</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">STATUS</th>'
            f'<th style="padding:5px 8px;text-align:left;font-size:11px;color:#64748b;">PRIORITY</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    # ── reminders section ─────────────────────────────────────────────────────
    reminders_section = _reminders_section(eod_reminders)
    releases_section = _releases_at_risk_section(db)

    body = header + completed_section + missed_section + carry_section + ov_section + jira_done_section + releases_section + reminders_section
    preheader = f"{len(completed)} completed · {len(missed)} missed — ExecOS Day Summary"
    return _wrap(body, preheader)


# ── send ──────────────────────────────────────────────────────────────────────

def send_html_email(subject: str, html_body: str, cfg) -> None:
    if not cfg.recipient_email:
        raise ValueError("Recipient email is required.")
    sender = cfg.smtp_user or f"execos@{cfg.smtp_host}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"ExecOS <{sender}>"
    msg["To"] = cfg.recipient_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    mode = (cfg.smtp_mode or "starttls").lower()
    if mode == "ssl":
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=20, context=ctx) as s:
            if cfg.smtp_user and cfg.smtp_password:
                s.login(cfg.smtp_user, cfg.smtp_password)
            s.sendmail(sender, [cfg.recipient_email], msg.as_string())
    elif mode == "plain":
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as s:
            s.ehlo()
            if cfg.smtp_user and cfg.smtp_password:
                s.login(cfg.smtp_user, cfg.smtp_password)
            s.sendmail(sender, [cfg.recipient_email], msg.as_string())
    else:  # starttls (default)
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as s:
            s.ehlo()
            s.starttls()
            if cfg.smtp_user and cfg.smtp_password:
                s.login(cfg.smtp_user, cfg.smtp_password)
            s.sendmail(sender, [cfg.recipient_email], msg.as_string())


def _get_cfg(db: Session):
    return db.query(EmailConfigORM).filter(EmailConfigORM.id == 1).first()


def send_sod(db: Session) -> None:
    cfg = _get_cfg(db)
    if not cfg or not cfg.sod_enabled:
        return
    html = build_sod_html(db)
    send_html_email(f"📋 Book of Work — {date.today().strftime('%A, %b %d')}", html, cfg)


def send_eod(db: Session) -> None:
    cfg = _get_cfg(db)
    if not cfg or not cfg.eod_enabled:
        return
    html = build_eod_html(db)
    send_html_email(f"🌇 Day Summary — {date.today().strftime('%A, %b %d')}", html, cfg)
