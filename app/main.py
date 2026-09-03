"""FastAPI application main entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
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
