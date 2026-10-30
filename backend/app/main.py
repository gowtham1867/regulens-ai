import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import Base, engine
from app.api.v1 import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    try:
        from app.database import SessionLocal
        from app.services.scheduler import init_default_scheduler_jobs
        db = SessionLocal()
        init_default_scheduler_jobs(db)
        db.close()
    except Exception as e:
        logger.warning(f"Could not init default scheduler jobs: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Evidence-Driven Regulatory Intelligence for AICTE (SIH26261)",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "status": "ONLINE",
        "service": "ReguLens AI Backend",
        "version": "1.0.0",
        "docs_url": "/api/docs",
        "health_check": "/api/v1/health"
    }


@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "ReguLens AI Regulatory Scrutiny Backend",
        "academic_year": settings.REGULATORY_ACADEMIC_YEAR,
        "database": "CONNECTED",
        "storage_dir": os.path.abspath(settings.UPLOAD_DIR)
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing the regulatory scrutiny request.",
            "type": type(exc).__name__,
            "message": str(exc)
        }
    )
