from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.schemas import AssistResponse
from src.api.routes import router
from src.core.config import get_settings

import logging

# Basic console logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)-20s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    settings = get_settings()

    # Using attribute access + fallback
    env = getattr(settings, "ENVIRONMENT", "unknown")

    logger.info(
        "Starting | env=%s | model=%s | ollama=%s | mcp=%s:%d",
        env,
        settings.OLLAMA_MODEL.value,
        settings.OLLAMA_BASE_URL,
        settings.MCP_HOST,
        settings.MCP_PORT,
    )

    try:
        yield
    finally:
        logger.info("Shutting down")


# Create app with conditional docs
settings = get_settings()

app = FastAPI(
    title="AI Assistant API",
    description="Workflow-based AI assistance endpoint",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if getattr(settings, "ENVIRONMENT",
                                "development") != "production" else None,
    redoc_url=None,
)

app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown",
        }
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=AssistResponse(error="Internal server error").model_dump(),
    )


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "healthy"}
