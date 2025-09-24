"""
Workflow models for Galactus.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from .base import BaseDBModel, TimestampMixin, Base


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

    # Sample identification
    workflow_id = Column(PGUUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False)
    batch_id = Column(String(100), nullable=True, index=True)  # For grouping samples in a batch

    # Physical properties
    composition = Column(JSONB, nullable=False, default=dict)  # Chemical composition/formula
    properties = Column(JSONB, nullable=False, default=dict)  # Physical/chemical properties
    target_properties = Column(JSONB, nullable=True)  # Target properties for optimization

    # Current state
    current_task_id = Column(PGUUID(as_uuid=True), ForeignKey('tasks.id'), nullable=True)
    position = Column(String(500), nullable=True)  # Current physical position/location
    status = Column(String(50), nullable=False, default="initialized", index=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="samples")
    current_task = relationship("Task", back_populates="current_samples")


class Workflow(BaseDBModel):
    """Workflow model - represents a complete experiment/workflow with samples and tasks."""
    __tablename__ = "workflows"

    # Workflow metadata
    version = Column(String(50), nullable=False, default="1.0.0")
    status = Column(String(20), nullable=False, default=WorkflowStatus.DRAFT, index=True)

    # Workflow configuration
    task_graph = Column(JSONB, nullable=False, default=dict)  # DAG representation of tasks
    sample_count = Column(Integer, nullable=False, default=1)
    max_concurrent_tasks = Column(Integer, nullable=False, default=5)

    # Execution control
    start_conditions = Column(JSONB, nullable=False, default=dict)  # Conditions to start workflow
    stop_conditions = Column(JSONB, nullable=False, default=dict)   # Conditions to stop workflow
    optimization_targets = Column(JSONB, nullable=True)  # What to optimize (e.g., {"yield": "maximize"})

    # Progress tracking
    progress_percentage = Column(Integer, nullable=False, default=0)  # 0-100
    current_task_count = Column(Integer, nullable=False, default=0)
    completed_task_count = Column(Integer, nullable=False, default=0)

    # Execution metadata
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    samples = relationship("Sample", back_populates="workflow", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowTemplate(BaseDBModel):
    """Workflow template model - reusable workflow definitions."""
    __tablename__ = "workflow_templates"

    # Template metadata
    version = Column(String(50), nullable=False, default="1.0.0")
    category = Column(String(100), nullable=False, index=True)  # e.g., "synthesis", "characterization"
    status = Column(String(20), nullable=False, default="active", index=True)

    # Template configuration
    task_graph_template = Column(JSONB, nullable=False, default=dict)  # Template for task graph
    default_sample_count = Column(Integer, nullable=False, default=1)
    max_sample_count = Column(Integer, nullable=False, default=100)
    variable_parameters = Column(JSONB, nullable=False, default=list)  # Parameters that can vary per sample

    # Execution settings
    default_max_concurrent_tasks = Column(Integer, nullable=False, default=5)
    optimization_enabled = Column(Boolean, nullable=False, default=False)
    optimization_targets = Column(JSONB, nullable=True)  # Default optimization targets

    # Implementation reference
    implementation_class = Column(String(500), nullable=True)  # Python class for workflow logic

    # Relationships
    workflows = relationship("Workflow", back_populates="template")


# Pydantic models for API
class SampleCreate(BaseModel):
    """Model for creating a new sample."""
    name: str = Field(..., min_length=1, max_length=255)
    batch_id: Optional[str] = None
    composition: Dict[str, Any] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)
    target_properties: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SampleResponse(BaseModel):
    """Response model for sample."""
    id: UUID
    name: str
    workflow_id: UUID
    batch_id: Optional[str]
    composition: Dict[str, Any]
    properties: Dict[str, Any]
    target_properties: Optional[Dict[str, Any]]
    current_task_id: Optional[UUID]
    position: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class WorkflowCreate(BaseModel):
    """Model for creating a new workflow."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    task_graph: Dict[str, Any] = Field(default_factory=dict)
    sample_count: int = Field(default=1, ge=1, le=1000)
    max_concurrent_tasks: int = Field(default=5, ge=1, le=50)
    start_conditions: Dict[str, Any] = Field(default_factory=dict)
    stop_conditions: Dict[str, Any] = Field(default_factory=dict)
    optimization_targets: Optional[Dict[str, Any]] = None
    samples: List[SampleCreate] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('samples')
    def validate_sample_count(cls, v, values):
        """Validate that sample count matches provided samples if not using template."""
        if 'sample_count' in values and len(v) != values['sample_count']:
            raise ValueError("Number of samples must match sample_count")
        return v


class WorkflowResponse(BaseModel):
    """Response model for workflow."""
    id: UUID
    name: str
    description: Optional[str]
    version: str
    status: str
    task_graph: Dict[str, Any]
    sample_count: int
    max_concurrent_tasks: int
    start_conditions: Dict[str, Any]
    stop_conditions: Dict[str, Any]
    optimization_targets: Optional[Dict[str, Any]]
    progress_percentage: int
    current_task_count: int
    completed_task_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    template_id: Optional[UUID]

    class Config:
        from_attributes = True


class WorkflowTemplateCreate(BaseModel):
    """Model for creating a new workflow template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., description="Workflow category (e.g., synthesis, characterization)")
    task_graph_template: Dict[str, Any] = Field(default_factory=dict)
    default_sample_count: int = Field(default=1, ge=1, le=1000)
    max_sample_count: int = Field(default=100, ge=1, le=1000)
    variable_parameters: List[str] = Field(default_factory=list)
    default_max_concurrent_tasks: int = Field(default=5, ge=1, le=50)
    optimization_enabled: bool = False
    optimization_targets: Optional[Dict[str, Any]] = None
    implementation_class: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowTemplateResponse(BaseModel):
    """Response model for workflow template."""
    id: UUID
    name: str
    description: Optional[str]
    version: str
    category: str
    status: str
    task_graph_template: Dict[str, Any]
    default_sample_count: int
    max_sample_count: int
    variable_parameters: List[str]
    default_max_concurrent_tasks: int
    optimization_enabled: bool
    optimization_targets: Optional[Dict[str, Any]]
    implementation_class: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True
