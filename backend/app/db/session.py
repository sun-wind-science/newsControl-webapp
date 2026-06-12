from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().sqlalchemy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_local_schema() -> None:
    # 本地 MVP 使用 create_all 启动，已有 SQLite 表需要少量兼容字段。
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "resources" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("resources")}
    with engine.begin() as connection:
        if "project_id" not in columns:
            connection.execute(text("ALTER TABLE resources ADD COLUMN project_id CHAR(32)"))
    if "review_items" in inspector.get_table_names():
        review_columns = {column["name"] for column in inspector.get_columns("review_items")}
        with engine.begin() as connection:
            if "project_id" not in review_columns:
                connection.execute(text("ALTER TABLE review_items ADD COLUMN project_id CHAR(32)"))
