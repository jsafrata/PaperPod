import os
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import text as sa_text
from supabase import create_client, Client

from config import settings

# --- Database ---

_db_url = settings.database_url
_is_sqlite = False

# Fallback to local SQLite if no DATABASE_URL
if not _db_url:
    _db_path = os.path.join(os.path.dirname(__file__), "local.db")
    _db_url = f"sqlite:///{_db_path}"
    _is_sqlite = True
    print(f"INFO: No DATABASE_URL set, using local SQLite: {_db_path}")

engine = create_engine(
    _db_url,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

# Enable WAL mode for SQLite — allows concurrent reads during writes
if _is_sqlite:
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def init_db():
    """Create tables and enable pgvector extension (skipped for SQLite)."""
    if not _is_sqlite:
        try:
            with engine.begin() as conn:
                conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"WARNING: Could not enable pgvector: {e}")

    SQLModel.metadata.create_all(engine)
    print("INFO: Database tables created")


def get_db():
    """FastAPI dependency for DB sessions."""
    with Session(engine) as session:
        yield session


# --- Supabase Storage ---

_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase not configured")
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase_client
