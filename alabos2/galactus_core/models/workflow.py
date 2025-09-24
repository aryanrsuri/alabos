"""Workflow models for alabos."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseDBModel


class WorkflowStatus:
    """Workflow execution statuses."""

    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Sample(BaseDBModel):
    """Sample model for workflow samples."""

    __tablename__ = "samples"

    workflow_id = Column(
        PGUUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    batch_id = Column(String(100), nullable=True, index=True)

    composition = Column(JSONB, nullable=False, default=dict)
    properties = Column(JSONB, nullable=False, default=dict)
    target_properties = Column(JSONB, nullable=True)

    current_task_id = Column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    position = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default="initialized", index=True)

    workflow = relationship("Workflow", back_populates="samples")
    current_task = relationship("Task", back_populates="current_samples")


class Workflow(BaseDBModel):
    """Workflow model - represents a complete experiment/workflow with samples and tasks."""

    __tablename__ = "workflows"

    version = Column(String(50), nullable=False, default="1.0.0")
    status = Column(
        String(20), nullable=False, default=WorkflowStatus.DRAFT, index=True
    )

    task_graph = Column(JSONB, nullable=False, default=dict)
    sample_count = Column(Integer, nullable=False, default=1)
    max_concurrent_tasks = Column(Integer, nullable=False, default=5)

    start_conditions = Column(JSONB, nullable=False, default=dict)
    stop_conditions = Column(JSONB, nullable=False, default=dict)
    optimization_targets = Column(JSONB, nullable=True)

    progress_percentage = Column(Integer, nullable=False, default=0)
    current_task_count = Column(Integer, nullable=False, default=0)
    completed_task_count = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)

    samples = relationship(
        "Sample", back_populates="workflow", cascade="all, delete-orphan"
    )
    tasks = relationship(
        "Task", back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowTemplate(BaseDBModel):
    """Workflow template model - reusable workflow definitions."""

    __tablename__ = "workflow_templates"

    version = Column(String(50), nullable=False, default="1.0.0")
    category = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)

    task_graph_template = Column(JSONB, nullable=False, default=dict)
    default_sample_count = Column(Integer, nullable=False, default=1)
    max_sample_count = Column(Integer, nullable=False, default=100)
    variable_parameters = Column(JSONB, nullable=False, default=list)

    default_max_concurrent_tasks = Column(Integer, nullable=False, default=5)
    optimization_enabled = Column(Boolean, nullable=False, default=False)
    optimization_targets = Column(JSONB, nullable=True)

    implementation_class = Column(String(500), nullable=True)

    workflows = relationship("Workflow", back_populates="template")


class SampleCreate(BaseModel):
    """Model for creating a new sample."""

    name: str = Field(..., min_length=1, max_length=255)
    batch_id: str | None = None
    composition: dict[str, Any] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    target_properties: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SampleResponse(BaseModel):
    """Response model for sample."""

    id: UUID
    name: str
    workflow_id: UUID
    batch_id: str | None
    composition: dict[str, Any]
    properties: dict[str, Any]
    target_properties: dict[str, Any] | None
    current_task_id: UUID | None
    position: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    class Config:
        from_attributes = True


class WorkflowCreate(BaseModel):
    """Model for creating a new workflow."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    template_id: UUID | None = None
    task_graph: dict[str, Any] = Field(default_factory=dict)
    sample_count: int = Field(default=1, ge=1, le=1000)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=50)
    start_conditions: dict[str, Any] = Field(default_factory=dict)
    stop_conditions: dict[str, Any] = Field(default_factory=dict)
    optimization_targets: dict[str, Any] | None = None
    samples: list[SampleCreate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @validator("samples")
    def validate_sample_count(cls, v, values):
        """Validate that sample count matches provided samples if not using template."""
        if "sample_count" in values and len(v) != values["sample_count"]:
            raise ValueError("Number of samples must match sample_count")
        return v


class WorkflowResponse(BaseModel):
    """Response model for workflow."""

    id: UUID
    name: str
    description: str | None
    version: str
    status: str
    task_graph: dict[str, Any]
    sample_count: int
    max_concurrent_tasks: int
    start_conditions: dict[str, Any]
    stop_conditions: dict[str, Any]
    optimization_targets: dict[str, Any] | None
    progress_percentage: int
    current_task_count: int
    completed_task_count: int
    started_at: datetime | None
    completed_at: datetime | None
    estimated_completion: datetime | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
    template_id: UUID | None

    class Config:
        from_attributes = True


class WorkflowTemplateCreate(BaseModel):
    """Model for creating a new workflow template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(
        ..., description="Workflow category (e.g., synthesis, characterization)"
    )
    task_graph_template: dict[str, Any] = Field(default_factory=dict)
    default_sample_count: int = Field(default=1, ge=1, le=1000)
    max_sample_count: int = Field(default=100, ge=1, le=1000)
    variable_parameters: list[str] = Field(default_factory=list)
    default_max_concurrent_tasks: int = Field(default=5, ge=1, le=50)
    optimization_enabled: bool = False
    optimization_targets: dict[str, Any] | None = None
    implementation_class: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowTemplateResponse(BaseModel):
    """Response model for workflow template."""

    id: UUID
    name: str
    description: str | None
    version: str
    category: str
    status: str
    task_graph_template: dict[str, Any]
    default_sample_count: int
    max_sample_count: int
    variable_parameters: list[str]
    default_max_concurrent_tasks: int
    optimization_enabled: bool
    optimization_targets: dict[str, Any] | None
    implementation_class: str | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    class Config:
        from_attributes = True
