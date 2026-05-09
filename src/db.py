from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st  # type: ignore

        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    raise RuntimeError(
        "DATABASE_URL not set. Define it as env var or in .streamlit/secrets.toml."
    )


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = _resolve_database_url()
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    sm = get_sessionmaker()
    s = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def list_tables() -> list[str]:
    from src.models import Base

    return sorted(Base.metadata.tables.keys())


def get_table(name: str):
    from src.models import Base

    return Base.metadata.tables.get(name)


def get_orm_class(table_name: str):
    from src.models import Base

    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if cls.__tablename__ == table_name:
            return cls
    return None
