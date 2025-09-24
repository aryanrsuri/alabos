"""Task models for alabos."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseDBModel


class TaskTemplateStatus:
    """Task template statuses."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class TaskTemplateInput(BaseModel):
    """Input schema for a task template."""

    name: str = Field(..., description="Input parameter name")
    type: str = Field(
        ..., description="Input parameter type (str, int, float, bool, dict, list)"
    )
    required: bool = Field(default=True, description="Whether this input is required")
    default: Any = Field(default=None, description="Default value for the input")
    description: str = Field(
        default="", description="Description of the input parameter"
    )
    validation_rules: Dict[str, Any] = Field(
        default_factory=dict, description="Validation rules"
    )


class TaskTemplateOutput(BaseModel):
    """Output schema for a task template."""

    name: str = Field(..., description="Output parameter name")
    type: str = Field(..., description="Output parameter type")
    description: str = Field(
        default="", description="Description of the output parameter"
    )
    required: bool = Field(default=True, description="Whether this output is required")
    is_file: bool = Field(
        default=False, description="Whether this output is a file upload"
    )
    file_config: Optional[Dict[str, Any]] = Field(
        default=None, description="File upload configuration (S3 bucket, etc.)"
    )


class TaskStatus:
    """Task execution statuses."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority:
    """Task priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskInput(BaseModel):
    """Input for a task instance."""

    name: str = Field(..., description="Input parameter name")
    value: Any = Field(..., description="Input parameter value")
    type: str = Field(..., description="Input parameter type")


class TaskOutput(BaseModel):
    """Output from a task instance."""

    name: str = Field(..., description="Output parameter name")
    value: Any = Field(..., description="Output parameter value")
    type: str = Field(..., description="Output parameter type")
    file_url: str | None = Field(
        default=None, description="S3 URL if this output is a file"
    )
    file_metadata: dict[str, Any] | None = Field(
        default=None, description="File metadata (size, content-type, etc.)"
    )


class TaskResult(BaseModel):
    """Result of a task execution."""

    task_id: UUID
    status: str
    outputs: list[TaskOutput] = Field(default_factory=list)
    error_message: str | None = None
    execution_time: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseDBModel):
    """Task instance model."""

    __tablename__ = "tasks"

    task_template_id = Column(
        PGUUID(as_uuid=True), ForeignKey("task_templates.id"), nullable=False
    )
    workflow_id = Column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    job_id = Column(PGUUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)

    status = Column(String(20), nullable=False, default=TaskStatus.PENDING, index=True)
    priority = Column(Integer, nullable=False, default=TaskPriority.NORMAL)
    retry_count = Column(Integer, nullable=False, default=0)

    inputs = Column(JSONB, nullable=False, default=dict)
    outputs = Column(JSONB, nullable=True)
    result_data = Column(JSONB, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Integer, nullable=True)

    assigned_device_id = Column(
        PGUUID(as_uuid=True), ForeignKey("devices.id"), nullable=True
    )

    prev_tasks = Column(JSON, nullable=False, default=list)
    next_tasks = Column(JSON, nullable=False, default=list)

    task_template = relationship("TaskTemplate", back_populates="tasks")
    workflow = relationship("Workflow", back_populates="tasks")
    job = relationship("Job", back_populates="tasks")
    assigned_device = relationship("Device", back_populates="tasks")

    def is_ready(self) -> bool:
        """Check if this task is ready to be executed."""
        return self.status == TaskStatus.READY and all(
            prev_task_id
            in [t.id for t in self.workflow.tasks if t.status == TaskStatus.COMPLETED]
            for prev_task_id in self.prev_tasks
        )

    def can_run_on_device(self, device_id: UUID) -> bool:
        """Check if this task can run on a specific device."""
        device = self.assigned_device or self._get_preferred_device()
        return bool(device and device.id == device_id)

    def _get_preferred_device(self):
        """Get the preferred device for this task based on template requirements."""
        return None


class TaskTemplate(BaseDBModel):
    """Task template model - reusable task definitions with schemas."""

    __tablename__ = "task_templates"

    version = Column(String(50), nullable=False, default="1.0.0")
    category = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)

    input_schema = Column(JSONB, nullable=False, default=dict)
    output_schema = Column(JSONB, nullable=False, default=dict)
    parameter_schema = Column(JSONB, nullable=False, default=dict)

    required_device_types = Column(JSON, nullable=False, default=list)
    preferred_device_types = Column(JSON, nullable=False, default=list)

    estimated_duration = Column(Integer, nullable=True)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_delay = Column(Integer, nullable=False, default=60)
    timeout = Column(Integer, nullable=True)
    requires_user_input = Column(Boolean, nullable=False, default=False)

    implementation_class = Column(String(500), nullable=True)
    docker_image = Column(String(500), nullable=True)

    tasks = relationship("Task", back_populates="task_template")
    device_types = relationship(
        "DeviceType",
        secondary="task_template_device_types",
        back_populates="task_templates",
    )


class TaskTemplateCreate(BaseModel):
    """Model for creating a new task template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(
        ..., description="Task category (e.g., heating, mixing, analysis)"
    )
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    required_device_types: list[UUID] = Field(default_factory=list)
    preferred_device_types: list[UUID] = Field(default_factory=list)
    estimated_duration: int | None = None
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=60, ge=0)
    timeout: int | None = None
    requires_user_input: bool = False
    implementation_class: str | None = None
    docker_image: str | None = None

    @validator("input_schema", "output_schema", "parameter_schema")
    def validate_schema(cls, v):
        """Validate that schema is a proper JSON schema."""
        if not isinstance(v, dict):
            raise ValueError("Schema must be a dictionary")
        return v


class TaskTemplateResponse(BaseModel):
    """Response model for task template."""

    id: UUID
    name: str
    description: str | None
    version: str
    category: str
    status: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    parameter_schema: dict[str, Any]
    required_device_types: list[UUID]
    preferred_device_types: list[UUID]
    estimated_duration: int | None
    max_retries: int
    retry_delay: int
    timeout: int | None
    requires_user_input: bool
    implementation_class: str | None
    docker_image: str | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    class Config:
        from_attributes = True
