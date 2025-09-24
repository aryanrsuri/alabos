"""
Task models for Galactus.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from .base import BaseDBModel, TimestampMixin, Base


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
    file_url: Optional[str] = Field(default=None, description="S3 URL if this output is a file")
    file_metadata: Optional[Dict[str, Any]] = Field(default=None, description="File metadata (size, content-type, etc.)")


class TaskResult(BaseModel):
    """Result of a task execution."""
    task_id: UUID
    status: str
    outputs: List[TaskOutput] = Field(default_factory=list)
    error_message: Optional[str] = None
    execution_time: Optional[float] = None  # in seconds
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseDBModel):
    """Task instance model."""
    __tablename__ = "tasks"

    # Core task information
    task_template_id = Column(PGUUID(as_uuid=True), ForeignKey('task_templates.id'), nullable=False)
    workflow_id = Column(PGUUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False)

    # Execution information
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING, index=True)
    priority = Column(Integer, nullable=False, default=TaskPriority.NORMAL)
    retry_count = Column(Integer, nullable=False, default=0)

    # Input/Output data
    inputs = Column(JSONB, nullable=False, default=dict)  # Dict of input parameter values
    outputs = Column(JSONB, nullable=True)  # Dict of output parameter values
    result_data = Column(JSONB, nullable=True)  # Full result object as JSON

    # Execution metadata
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Integer, nullable=True)  # Duration in seconds

    # Device assignment
    assigned_device_id = Column(PGUUID(as_uuid=True), ForeignKey('devices.id'), nullable=True)

    # Dependencies and relationships
    prev_tasks = Column(JSON, nullable=False, default=list)  # List of task IDs that must complete first
    next_tasks = Column(JSON, nullable=False, default=list)  # List of task IDs that depend on this task

    # Relationships
    task_template = relationship("TaskTemplate", back_populates="tasks")
    workflow = relationship("Workflow", back_populates="tasks")
    job = relationship("Job", back_populates="tasks")
    assigned_device = relationship("Device", back_populates="tasks")

    def is_ready(self) -> bool:
        """Check if this task is ready to be executed."""
        return (
            self.status == TaskStatus.READY and
            all(prev_task_id in [t.id for t in self.workflow.tasks if t.status == TaskStatus.COMPLETED]
                for prev_task_id in self.prev_tasks)
        )

    def can_run_on_device(self, device_id: UUID) -> bool:
        """Check if this task can run on a specific device."""
        device = self.assigned_device or self._get_preferred_device()
        return device and device.id == device_id

    def _get_preferred_device(self):
        """Get the preferred device for this task based on template requirements."""
        # Implementation would check device availability and compatibility
        return None


class TaskTemplate(BaseDBModel):
    """Task template model - reusable task definitions with schemas."""
    __tablename__ = "task_templates"

    # Template metadata
    version = Column(String(50), nullable=False, default="1.0.0")
    category = Column(String(100), nullable=False, index=True)  # e.g., "heating", "mixing", "analysis"
    status = Column(String(20), nullable=False, default="active", index=True)

    # Schema definitions
    input_schema = Column(JSONB, nullable=False, default=dict)  # Dict defining input parameters
    output_schema = Column(JSONB, nullable=False, default=dict)  # Dict defining output parameters
    parameter_schema = Column(JSONB, nullable=False, default=dict)  # Dict for parameter validation

    # Device requirements
    required_device_types = Column(JSON, nullable=False, default=list)  # List of required device type IDs
    preferred_device_types = Column(JSON, nullable=False, default=list)  # List of preferred device type IDs

    # Execution configuration
    estimated_duration = Column(Integer, nullable=True)  # Estimated duration in seconds
    max_retries = Column(Integer, nullable=False, default=3)
    retry_delay = Column(Integer, nullable=False, default=60)  # Delay between retries in seconds
    timeout = Column(Integer, nullable=True)  # Task timeout in seconds
    requires_user_input = Column(Boolean, nullable=False, default=False)

    # Implementation reference
    implementation_class = Column(String(500), nullable=True)  # Python class path for task implementation
    docker_image = Column(String(500), nullable=True)  # Docker image for task execution

    # Relationships
    tasks = relationship("Task", back_populates="task_template")
    device_types = relationship("DeviceType", secondary="task_template_device_types", back_populates="task_templates")


# Pydantic models for API
class TaskTemplateCreate(BaseModel):
    """Model for creating a new task template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., description="Task category (e.g., heating, mixing, analysis)")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    parameter_schema: Dict[str, Any] = Field(default_factory=dict)
    required_device_types: List[UUID] = Field(default_factory=list)
    preferred_device_types: List[UUID] = Field(default_factory=list)
    estimated_duration: Optional[int] = None
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=60, ge=0)
    timeout: Optional[int] = None
    requires_user_input: bool = False
    implementation_class: Optional[str] = None
    docker_image: Optional[str] = None

    @validator('input_schema', 'output_schema', 'parameter_schema')
    def validate_schema(cls, v):
        """Validate that schema is a proper JSON schema."""
        if not isinstance(v, dict):
            raise ValueError("Schema must be a dictionary")
        return v


class TaskTemplateResponse(BaseModel):
    """Response model for task template."""
    id: UUID
    name: str
    description: Optional[str]
    version: str
    category: str
    status: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    parameter_schema: Dict[str, Any]
    required_device_types: List[UUID]
    preferred_device_types: List[UUID]
    estimated_duration: Optional[int]
    max_retries: int
    retry_delay: int
    timeout: Optional[int]
    requires_user_input: bool
    implementation_class: Optional[str]
    docker_image: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True
