#!/usr/bin/env python3
"""ExecOS start script - runs the web server from the correct directory."""

import subprocess
import sys
import os
import pathlib

# Set root to this script's directory
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# Load .env if it exists
_env_file = pathlib.Path(ROOT) / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file, override=False)
    except ImportError:
        pass

def main():
    print("🚀 ExecOS - Command Center")
    print("=" * 50)
    print(f"📁 Running from: {ROOT}")

    # Install dependencies if needed
    try:
        import fastapi
    except ImportError:
        print("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

    # Start the server
    print("\n🔄 Starting server on http://localhost:8080...")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "web.app:app",
        "--host", "0.0.0.0",
        "--port", "8080",
        "--reload"
    ])

if __name__ == "__main__":
    main()
