from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import pathlib
import json
import time

from db.init_db import create_all
from web.routers import tasks, projects, milestones, commitments, alerts, dashboard, estimation
from web.routers import email_routes
from web.routers import jira_routes
from web.routers import gitlab_routes
from web.routers import planner_routes
from web.routers import team_routes
from web.routers import sprint_routes
from web.routers import proj_estimate_routes
from web.routers import delivery_routes
from web.routers import application_routes
from web.routers import app_integration_routes
from web.routers import workload_routes
from web.routers import outlook_calendar_routes
from web.routers import activity_log_routes

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

app.include_router(tasks.router)
app.include_router(projects.router)
app.include_router(milestones.router)
app.include_router(commitments.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(estimation.router)
app.include_router(email_routes.router)
app.include_router(jira_routes.router)
app.include_router(gitlab_routes.router)
app.include_router(planner_routes.router)
app.include_router(team_routes.router)
app.include_router(sprint_routes.router)
app.include_router(proj_estimate_routes.router)
app.include_router(delivery_routes.router)
app.include_router(application_routes.router)
app.include_router(app_integration_routes.router)
app.include_router(workload_routes.router)
app.include_router(outlook_calendar_routes.router)
app.include_router(activity_log_routes.router)

_static = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.on_event("startup")
def on_startup():
    create_all()
    _start_scheduler()


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
