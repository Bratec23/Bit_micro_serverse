from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Лёгкие миграции: добавление новых колонок (SQLite/PostgreSQL)."""
    from sqlalchemy import inspect, text

    new_columns = {
        "kp_documents": [
            ("is_shared", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("owner_name", "VARCHAR(255) NOT NULL DEFAULT ''"),
        ],
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in new_columns.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
