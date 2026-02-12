
from sqlalchemy import create_engine, event, text, inspect
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
    
    # Auto-migración: agregar session_id si no existe en tablas existentes
    _auto_migrate()


def _auto_migrate():
    """Agrega columnas session_id a tablas existentes si faltan."""
    inspector = inspect(engine)
    
    for table_name in ["registros", "lotes"]:
        if table_name in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns(table_name)]
            if "session_id" not in columns:
                with engine.connect() as conn:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN session_id VARCHAR(36) DEFAULT 'legacy'"
                    ))
                    conn.execute(text(
                        f"UPDATE {table_name} SET session_id = 'legacy' WHERE session_id IS NULL OR session_id = ''"
                    ))
                    conn.commit()

