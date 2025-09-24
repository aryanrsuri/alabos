"""Job models for alabos - manages workflow execution.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseDBModel


class JobStatus:
    """Job execution statuses."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority:
    """Job priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class Job(BaseDBModel):
    """Job model - represents the execution of a workflow."""

    __tablename__ = "jobs"

    workflow_id = Column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    submitted_by = Column(String(255), nullable=True)

    status = Column(String(20), nullable=False, default=JobStatus.CREATED, index=True)
    priority = Column(Integer, nullable=False, default=JobPriority.NORMAL)
    max_retries = Column(Integer, nullable=False, default=1)

    max_concurrent_tasks = Column(Integer, nullable=False, default=5)
    resource_requirements = Column(JSONB, nullable=False, default=dict)
    allocated_resources = Column(JSONB, nullable=True)

    progress_percentage = Column(Integer, nullable=False, default=0)
    total_tasks = Column(Integer, nullable=False, default=0)
    completed_tasks = Column(Integer, nullable=False, default=0)
    failed_tasks = Column(Integer, nullable=False, default=0)
    cancelled_tasks = Column(Integer, nullable=False, default=0)

    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    actual_duration = Column(Integer, nullable=True)

    execution_mode = Column(String(50), nullable=False, default="normal")
    execution_config = Column(JSONB, nullable=False, default=dict)

    results = Column(JSONB, nullable=True)
    artifacts = Column(JSON, nullable=False, default=list)
    logs = Column(JSON, nullable=False, default=list)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("Workflow", back_populates="jobs")
    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan")

    def is_active(self) -> bool:
        """Check if job is currently active (running or queued)."""
        return self.status in [JobStatus.QUEUED, JobStatus.RUNNING]

    def is_completed(self) -> bool:
        """Check if job execution is complete."""
        return self.status in [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]

    def can_transition_to(self, new_status: str) -> bool:
        """Check if job can transition to a new status."""
        valid_transitions = {
            JobStatus.CREATED: [JobStatus.QUEUED, JobStatus.CANCELLED],
            JobStatus.QUEUED: [
                JobStatus.RUNNING,
                JobStatus.CANCELLED,
                JobStatus.FAILED,
            ],
            JobStatus.RUNNING: [
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.PAUSED,
            ],
            JobStatus.PAUSED: [
                JobStatus.RUNNING,
                JobStatus.CANCELLED,
                JobStatus.FAILED,
            ],
            JobStatus.COMPLETED: [],
            JobStatus.FAILED: [JobStatus.QUEUED],
            JobStatus.CANCELLED: [],
        }
        return new_status in valid_transitions.get(self.status, [])

    def calculate_progress(self) -> int:
        """Calculate job progress percentage."""
        if self.total_tasks == 0:
            return 100 if self.is_completed() else 0

        completed_progress = self.completed_tasks * 100
        failed_progress = self.failed_tasks * 50
        cancelled_progress = self.cancelled_tasks * 25

        total_progress = completed_progress + failed_progress + cancelled_progress
        return min(100, total_progress // self.total_tasks)


class JobQueue:
    """Job queue model for managing job execution order."""

    __tablename__ = "job_queues"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(
        PGUUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, unique=True
    )

    queue_name = Column(String(100), nullable=False, index=True, default="default")
    priority = Column(Integer, nullable=False, default=JobPriority.NORMAL)
    position = Column(Integer, nullable=False)

    queued_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    estimated_start = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)

    resource_reservation = Column(JSONB, nullable=True)

    job = relationship("Job", back_populates="queue_entries")

    __table_args__ = (
        Index("idx_queue_priority_time", "queue_name", "priority", "queued_at"),
    )


class JobCreate(BaseModel):
    """Model for creating a new job."""

    workflow_id: UUID = Field(..., description="ID of the workflow to execute")
    submitted_by: str | None = None
    priority: int = Field(default=JobPriority.NORMAL, ge=1, le=4)
    max_retries: int = Field(default=1, ge=0, le=5)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=50)
    resource_requirements: dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = Field(
        default="normal", description="Execution mode (normal, optimized, debug)"
    )
    execution_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v):
        """Validate execution mode."""
        valid_modes = ["normal", "optimized", "debug", "simulation"]
        if v not in valid_modes:
            raise ValueError(f"Execution mode must be one of: {valid_modes}")
        return v


class JobResponse(BaseModel):
    """Response model for job."""

    id: UUID
    workflow_id: UUID
    submitted_by: str | None
    status: str
    priority: int
    max_retries: int
    max_concurrent_tasks: int
    resource_requirements: dict[str, Any]
    allocated_resources: dict[str, Any] | None
    progress_percentage: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    execution_mode: str
    execution_config: dict[str, Any]
    results: dict[str, Any] | None
    error_message: str | None
    retry_count: int
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    estimated_completion: datetime | None
    actual_duration: int | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    model_config = {"from_attributes": True}


class JobQueueResponse(BaseModel):
    """Response model for job queue entry."""

    id: UUID
    job_id: UUID
    queue_name: str
    priority: int
    position: int
    queued_at: datetime
    estimated_start: datetime | None
    actual_start: datetime | None
    resource_reservation: dict[str, Any] | None

    model_config = {"from_attributes": True}
