"""
School Result Analysis System - Application Entrypoint

Creates and configures the FastAPI application instance.
Mounts routers, exception handlers, and static files.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api.v1.api_router import api_router

# ============================================
# Logging Configuration
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================
# Application Lifespan (Startup / Shutdown)
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("=" * 50)
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"API prefix: {settings.API_V1_STR}")
    logger.info(f"Storage provider: {settings.STORAGE_PROVIDER}")
    logger.info("=" * 50)
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


# ============================================
# Application Factory
# ============================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Exception Handlers ---
register_exception_handlers(app)

# --- API Routes ---
app.include_router(api_router, prefix=settings.API_V1_STR)


# --- Health Check Endpoint ---
@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint.
    Returns application status for uptime monitoring and deployment validation.
    """
    return {
        "status": "healthy",
        "application": settings.PROJECT_NAME,
    }


# --- Static File Mounting (Frontend) ---
# Mount the frontend directory to serve HTML/CSS/JS files.
# This must be the LAST mount to avoid intercepting API routes.
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
