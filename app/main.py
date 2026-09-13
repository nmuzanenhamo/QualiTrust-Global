"""FastAPI application main entry point."""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.middleware import MetricsMiddleware
from app.models import Qualification, User, UserRole
from app.services.auth_service import AuthService
from app.services.blockchain_service import BlockchainService


DEFAULT_ADMIN_EMAIL = "admin@qvs.com"
DEFAULT_ADMIN_PASSWORD = "Admin1234!"


def _seed_default_admin():
    """Create a default admin account if no admin exists."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not existing:
            AuthService.create_user(
                db,
                email=DEFAULT_ADMIN_EMAIL,
                full_name="System Administrator",
                password=DEFAULT_ADMIN_PASSWORD,
                role=UserRole.ADMIN,
            )
            print(f"Default admin created: {DEFAULT_ADMIN_EMAIL}")
    except Exception:
        pass
    finally:
        db.close()


def _backfill_credential_hashes():
    """Assign blockchain hashes to existing qualifications that lack one."""
    db = SessionLocal()
    try:
        unhashed = (
            db.query(Qualification).filter(Qualification.credential_hash.is_(None)).order_by(Qualification.id).all()
        )
        if unhashed:
            for qual in unhashed:
                BlockchainService.assign_hash(db, qual)
            print(f"Backfilled credential hashes for {len(unhashed)} qualification(s)")
    except Exception:
        pass
    finally:
        db.close()


def _migrate_add_document_path():
    """Add document_path column to qualifications table if it doesn't exist."""
    from sqlalchemy import text, inspect

    try:
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("qualifications")]
        if "document_path" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE qualifications ADD COLUMN document_path VARCHAR(500)"))
                conn.commit()
            print("Added document_path column to qualifications table")
    except Exception:
        pass


def _migrate_qualification_type_values():
    """Update old qualification_type enum names to the new schema.

    SQLAlchemy Enum columns store the enum *name* (e.g. 'DEGREE'), not the
    value (e.g. 'degree'), so we update by name here.
    """
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE qualifications SET qualification_type = 'UNDERGRADUATE_DEGREE' "
                    "WHERE qualification_type = 'DEGREE'"
                )
            )
            conn.commit()
    except Exception:
        pass


def _migrate_clear_soft_deleted_serials():
    """Clear serial_number on soft-deleted records to free up the UNIQUE constraint."""
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE qualifications SET serial_number = NULL WHERE is_deleted = 1 AND serial_number IS NOT NULL"
                )
            )
            conn.commit()
    except Exception:
        pass


def _migrate_add_grade_column():
    """Add grade column to qualifications table if it doesn't exist."""
    from sqlalchemy import text, inspect

    try:
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("qualifications")]
        if "grade" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE qualifications ADD COLUMN grade VARCHAR(200)"))
                conn.commit()
            print("Added grade column to qualifications table")
    except Exception:
        pass


def _migrate_pending_to_registered():
    """Update existing 'pending' qualifications to 'registered' status."""
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(text("UPDATE qualifications SET status = 'registered' WHERE status = 'pending'"))
            conn.commit()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables, seed admin, and backfill hashes on startup."""
    Base.metadata.create_all(bind=engine)
    _migrate_add_document_path()
    _migrate_add_grade_column()
    _migrate_pending_to_registered()
    _migrate_qualification_type_values()
    _migrate_clear_soft_deleted_serials()
    _seed_default_admin()
    _backfill_credential_hashes()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A DevOps-enabled Qualification Verification System with "
        "blockchain verification, AI fraud detection, and real-time monitoring."
    ),
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Serve static frontend files
_static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/css", StaticFiles(directory=_static_dir / "css"), name="css")
app.mount("/js", StaticFiles(directory=_static_dir / "js"), name="js")

# Serve uploaded certificate documents
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")


@app.get("/")
async def root():
    """Serve the modern web UI."""
    return FileResponse(_static_dir / "index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
    }


# Routers
from app.api.routers import ai, audit, auth, qualifications, verification

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(qualifications.router, prefix="/api/v1/qualifications", tags=["qualifications"])
app.include_router(verification.router, prefix="/api/v1/qualifications", tags=["verification"])
app.include_router(audit.router, prefix="/api/v1/audit-logs", tags=["audit"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
