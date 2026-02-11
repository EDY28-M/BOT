
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from app.core.config import DATABASE_URL

# Engine con soporte para SQLite WAL (Write-Ahead Logging) para mejor concurrencia
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionFactory = sessionmaker(bind=engine)
ScopedSession = scoped_session(SessionFactory)

Base = declarative_base()

def init_db():
    from app.db import models
    Base.metadata.create_all(engine)
