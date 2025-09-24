"""
Job models for Galactus - manages workflow execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from .base import BaseDBModel, TimestampMixin, Base


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

    # Job identification
    workflow_id = Column(PGUUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False)
    submitted_by = Column(String(255), nullable=True)  # User or system that submitted the job

    # Execution control
    status = Column(String(20), nullable=False, default=JobStatus.CREATED, index=True)
    priority = Column(Integer, nullable=False, default=JobPriority.NORMAL)
    max_retries = Column(Integer, nullable=False, default=1)  # Job-level retry count

    # Resource allocation
    max_concurrent_tasks = Column(Integer, nullable=False, default=5)
    resource_requirements = Column(JSONB, nullable=False, default=dict)  # Resource requirements for the job
    allocated_resources = Column(JSONB, nullable=True)  # Actually allocated resources

    # Progress tracking
    progress_percentage = Column(Integer, nullable=False, default=0)  # 0-100
    total_tasks = Column(Integer, nullable=False, default=0)
    completed_tasks = Column(Integer, nullable=False, default=0)
    failed_tasks = Column(Integer, nullable=False, default=0)
    cancelled_tasks = Column(Integer, nullable=False, default=0)

    # Timing information
    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    actual_duration = Column(Integer, nullable=True)  # Duration in seconds

    # Execution configuration
    execution_mode = Column(String(50), nullable=False, default="normal")  # normal, optimized, debug
    execution_config = Column(JSONB, nullable=False, default=dict)  # Additional execution parameters

    # Results and artifacts
    results = Column(JSONB, nullable=True)  # Final job results
    artifacts = Column(JSON, nullable=False, default=list)  # List of artifact references
    logs = Column(JSON, nullable=False, default=list)  # List of log file references

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="jobs")
    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan")

    def is_active(self) -> bool:
        """Check if job is currently active (running or queued)."""
        return self.status in [JobStatus.QUEUED, JobStatus.RUNNING]

    def is_completed(self) -> bool:
        """Check if job execution is complete."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]

    def can_transition_to(self, new_status: str) -> bool:
        """Check if job can transition to a new status."""
        valid_transitions = {
            JobStatus.CREATED: [JobStatus.QUEUED, JobStatus.CANCELLED],
            JobStatus.QUEUED: [JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED],
            JobStatus.RUNNING: [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PAUSED],
            JobStatus.PAUSED: [JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED],
            JobStatus.COMPLETED: [],  # Terminal state
            JobStatus.FAILED: [JobStatus.QUEUED],  # Allow retry
            JobStatus.CANCELLED: []   # Terminal state
        }
        return new_status in valid_transitions.get(self.status, [])

    def calculate_progress(self) -> int:
        """Calculate job progress percentage."""
        if self.total_tasks == 0:
            return 100 if self.is_completed() else 0

        completed_progress = self.completed_tasks * 100
        failed_progress = self.failed_tasks * 50  # Failed tasks count as 50% progress
        cancelled_progress = self.cancelled_tasks * 25  # Cancelled tasks count as 25% progress

        total_progress = completed_progress + failed_progress + cancelled_progress
        return min(100, total_progress // self.total_tasks)


class JobQueue:
    """Job queue model for managing job execution order."""
    __tablename__ = "job_queues"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False, unique=True)

    # Queue information
    queue_name = Column(String(100), nullable=False, index=True, default="default")
    priority = Column(Integer, nullable=False, default=JobPriority.NORMAL)
    position = Column(Integer, nullable=False)  # Position in queue

    # Timing
    queued_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    estimated_start = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)

    # Resource allocation
    resource_reservation = Column(JSONB, nullable=True)  # Reserved resources for this job

    # Relationships
    job = relationship("Job", back_populates="queue_entries")

    __table_args__ = (
        # Index for efficient queue ordering
        Index('idx_queue_priority_time', 'queue_name', 'priority', 'queued_at'),
    )


# Pydantic models for API
class JobCreate(BaseModel):
    """Model for creating a new job."""
    workflow_id: UUID = Field(..., description="ID of the workflow to execute")
    submitted_by: Optional[str] = None
    priority: int = Field(default=JobPriority.NORMAL, ge=1, le=4)
    max_retries: int = Field(default=1, ge=0, le=5)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=50)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = Field(default="normal", description="Execution mode (normal, optimized, debug)")
    execution_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('execution_mode')
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
    submitted_by: Optional[str]
    status: str
    priority: int
    max_retries: int
    max_concurrent_tasks: int
    resource_requirements: Dict[str, Any]
    allocated_resources: Optional[Dict[str, Any]]
    progress_percentage: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    execution_mode: str
    execution_config: Dict[str, Any]
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    actual_duration: Optional[int]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class JobQueueResponse(BaseModel):
    """Response model for job queue entry."""
    id: UUID
    job_id: UUID
    queue_name: str
    priority: int
    position: int
    queued_at: datetime
    estimated_start: Optional[datetime]
    actual_start: Optional[datetime]
    resource_reservation: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
