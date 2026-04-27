import os
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env from the project root (two levels up from this file)
try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

_data_dir = pathlib.Path.home() / ".commanddesk"
_data_dir.mkdir(exist_ok=True)

# DB_PATH lets you set just the SQLite file path without the full URL scheme
_db_path = os.getenv("DB_PATH")
if _db_path:
    DATABASE_URL = f"sqlite:///{_db_path}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_data_dir}/execos.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
