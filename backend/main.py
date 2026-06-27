import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from config import get_settings
from core.logging import setup_logging
from core.exceptions import AppError
from database.db import engine, Base
from routers import ai
from schemas.schema import HealthResponse

settings = get_settings()
setup_logging(settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.media_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.media_dir, "snapshots"), exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    yield
    await engine.dispose()
    logger.info("Database connection pool disposed")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade AI product image search — Google Shopping style",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
app.include_router(ai.router, prefix="/api/v1/ai", tags=["Product Search"])


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health():
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
        logger.exception("Health check database failure")

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.app_version,
        database=db_status,
    )


@app.get("/", tags=["Monitoring"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
