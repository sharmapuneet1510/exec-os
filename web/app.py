from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from db.init_db import create_all
from web.routers import tasks, projects, milestones, commitments, alerts, dashboard

app = FastAPI(title="ExecOS", version="1.0.0", description="Personal Execution System")

app.include_router(tasks.router)
app.include_router(projects.router)
app.include_router(milestones.router)
app.include_router(commitments.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)

_static = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.on_event("startup")
def on_startup():
    create_all()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(_static / "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}
