"""FastAPI main application for alabos."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..database.connection import get_async_db_session
from ..events.consumer import EventConsumer
from ..events.producer import event_producer
from ..scheduler.scheduler import scheduler
from .routes import task_templates, workflows, jobs, tasks, devices, samples

logger = logging.getLogger(__name__)

# Global event consumer
event_consumer = EventConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting alabos API server...")

    # Start event consumer
    event_consumer.subscribe_to_entity_events(
        "task", ["created", "started", "completed", "failed"]
    )
    event_consumer.subscribe_to_entity_events(
        "workflow", ["created", "started", "completed", "failed"]
    )
    event_consumer.subscribe_to_entity_events(
        "job", ["created", "started", "completed", "failed"]
    )
    event_consumer.subscribe_to_entity_events("device", ["status_changed"])
    event_consumer.start()

    # Start scheduler
    scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down alabos API server...")
    event_consumer.stop()
    scheduler.stop()


# Create FastAPI application
app = FastAPI(
    title="alabos API",
    description="Semi-Autonomous Laboratory Management System API",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    task_templates.router, prefix="/api/v1/task-templates", tags=["task-templates"]
)
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(samples.router, prefix="/api/v1/samples", tags=["samples"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "services": {
            "scheduler": scheduler.running,
            "event_consumer": event_consumer.health_check(),
        },
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to alabos API", "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
