from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from db.init_db import create_all
from web.routers import tasks, projects, milestones, commitments, alerts, dashboard, estimation
from web.routers import email_routes

app = FastAPI(title="ExecOS", version="1.0.0", description="Personal Execution System")

app.include_router(tasks.router)
app.include_router(projects.router)
app.include_router(milestones.router)
app.include_router(commitments.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(estimation.router)
app.include_router(email_routes.router)

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
