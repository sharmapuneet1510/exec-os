import os
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_data_dir = pathlib.Path.home() / ".commanddesk"
_data_dir.mkdir(exist_ok=True)

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
