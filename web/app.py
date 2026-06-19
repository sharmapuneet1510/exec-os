from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import pathlib
import json
import time

from db.init_db import create_all
from web.routers.tasks import router as tasks_router
from web.routers.projects import router as projects_router
from web.routers.milestones import router as milestones_router
from web.routers.commitments import router as commitments_router
from web.routers.alerts import router as alerts_router
from web.routers.dashboard import router as dashboard_router
from web.routers.estimation import router as estimation_router
from web.routers.email_routes import router as email_router
from web.routers.jira_routes import router as jira_router
from web.routers.gitlab_routes import router as gitlab_router
from web.routers.planner_routes import router as planner_router
from web.routers.team_routes import router as team_router
from web.routers.sprint_routes import router as sprint_router
from web.routers.proj_estimate_routes import router as proj_estimate_router
from web.routers.delivery_routes import router as delivery_router
from web.routers.application_routes import router as application_router
from web.routers.app_integration_routes import router as app_integration_router
from web.routers.workload_routes import router as workload_router
from web.routers.outlook_calendar_routes import router as outlook_router
from web.routers.activity_log_routes import router as activity_log_router
from web.routers.releases import router as releases_router
from web.routers.resource_allocation_routes import router as resource_allocation_router
from web.routers import reminders
from web.routers.admin import router as admin_router
from web.routers.my_work_routes import router as my_work_router
from web.routers.members import router as members_router
from web.routers.jira_sync_routes import router as jira_sync_router
from web.routers.settings import router as settings_router
from web.routers.issue_comments import router as issue_comments_router
from web.routers.setup_routes import router as setup_router

from services.reminder_scheduler import create_scheduler_job
from services.backup_scheduler import start_backup_scheduler, shutdown_backup_scheduler

app = FastAPI(title="ExecOS", version="1.0.0", description="Personal Execution System")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        body = b""
        if request.method in ("POST", "PATCH", "PUT"):
            body = await request.body()
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive

        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        if request.url.path.startswith("/api/"):
            try:
                from db.base import SessionLocal
                db = SessionLocal()
                from db.models import ActivityLogORM
                log = ActivityLogORM(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    request_headers=dict(request.headers),
                    request_body=body.decode() if body else None,
                    response_headers=dict(response.headers),
                    duration_ms=int(duration_ms),
                )
                db.add(log)
                db.commit()
                db.close()
            except Exception:
                pass

        return response


app.add_middleware(LoggingMiddleware)

app.include_router(tasks_router)
app.include_router(projects_router)
app.include_router(milestones_router)
app.include_router(commitments_router)
app.include_router(alerts_router)
app.include_router(dashboard_router)
app.include_router(estimation_router)
app.include_router(email_router)
app.include_router(jira_router)
app.include_router(gitlab_router)
app.include_router(planner_router)
app.include_router(team_router)
app.include_router(sprint_router)
app.include_router(proj_estimate_router)
app.include_router(delivery_router)
app.include_router(application_router)
app.include_router(app_integration_router)
app.include_router(workload_router)
app.include_router(outlook_router)
app.include_router(activity_log_router)
app.include_router(releases_router)
app.include_router(resource_allocation_router)
app.include_router(admin_router)
app.include_router(my_work_router)
app.include_router(members_router)
app.include_router(jira_sync_router)
app.include_router(settings_router)
app.include_router(issue_comments_router)
app.include_router(setup_router)

_static = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.on_event("startup")
def on_startup():
    create_all()
    _start_scheduler()
    start_backup_scheduler()


def _start_scheduler():
    try:
        from db.base import SessionLocal
        from db.models import EmailConfigORM
        from web import scheduler
        db = SessionLocal()
        try:
            cfg = db.query(EmailConfigORM).filter(EmailConfigORM.id == 1).first()
            sod = cfg.sod_time if cfg and cfg.sod_time else "08:00"
            eod = cfg.eod_time if cfg and cfg.eod_time else "18:00"
        finally:
            db.close()
        scheduler.start(sod, eod)
    except Exception:
        pass


@app.on_event("shutdown")
def on_shutdown():
    shutdown_backup_scheduler()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(_static / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/system/info")
def system_info():
    from db.base import DATABASE_URL
    import os
    url = DATABASE_URL
    # Mask password in postgres URLs
    if "@" in url:
        scheme, rest = url.split("://", 1)
        userinfo, hostpart = rest.split("@", 1)
        if ":" in userinfo:
            user = userinfo.split(":")[0]
            userinfo = f"{user}:••••"
        url = f"{scheme}://{userinfo}@{hostpart}"
    db_type = "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql" if DATABASE_URL.startswith("postgres") else "other"
    db_path = None
    if db_type == "sqlite":
        raw = DATABASE_URL.replace("sqlite:///", "")
        db_path = os.path.abspath(raw) if raw else None
    return {
        "db_type": db_type,
        "db_path": db_path,
        "database_url_masked": url,
        "env_file": str(pathlib.Path(__file__).parent.parent / ".env"),
    }
