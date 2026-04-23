from .base import engine
from . import models  # noqa: F401 — ensures all ORM classes are registered


def create_all():
    models.Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    create_all()
