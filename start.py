#!/usr/bin/env python3
"""
ExecOS — single-script startup.
Installs dependencies, initialises the SQLite database, and starts the web server.
Open http://localhost:8080 after running.
"""

import subprocess
import sys
import os
import pathlib

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# Load .env before anything else so DATABASE_URL / DB_PATH are available
_env_file = pathlib.Path(ROOT) / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file, override=False)
    except ImportError:
        # dotenv not yet installed — parse manually for the two critical keys
        for line in _env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() in ("DATABASE_URL", "DB_PATH", "PORT") and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()


def _pip(*packages):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", *packages],
        stdout=subprocess.DEVNULL,
    )


def ensure_deps():
    req = os.path.join(ROOT, "requirements.txt")
    try:
        import fastapi, uvicorn, sqlalchemy  # noqa: F401
    except ImportError:
        print("Installing dependencies…")
        _pip("-r", req)


def init_db():
    sys.path.insert(0, ROOT)
    from db.init_db import create_all
    create_all()


def start():
    ensure_deps()
    init_db()

    port = int(os.getenv("PORT", "8080"))
    print(f"\nExecOS running → http://localhost:{port}\n")

    try:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass

    import uvicorn
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[ROOT],
    )


if __name__ == "__main__":
    start()
