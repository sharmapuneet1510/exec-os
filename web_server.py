#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from web.app import app  # noqa: F401

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=["."],
    )
