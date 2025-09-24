"""
Base models and common database structures for Galactus.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BaseDBModel(TimestampMixin, Base):
    """Base database model with common fields."""
    __abstract__ = True

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)


# Event models for Kafka
class EventType:
    """Event types for the system."""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    DEVICE_STATUS_CHANGED = "device_status_changed"
    SAMPLE_CREATED = "sample_created"
    SAMPLE_POSITION_CHANGED = "sample_position_changed"
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"


class EventBase(BaseModel):
    """Base event model."""
    event_type: str = Field(..., description="Type of the event")
    entity_id: UUID = Field(..., description="ID of the entity this event relates to")
    entity_type: str = Field(..., description="Type of the entity (task, workflow, device, etc.)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")


class KafkaEvent(BaseDBModel):
    """Database model for storing Kafka events in TimescaleDB."""
    __tablename__ = "kafka_events"

    event_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)

    # TimescaleDB specific - partitioning by time
    __table_args__ = (
        Index('idx_events_time_type', 'created_at', 'event_type'),
        Index('idx_events_entity', 'entity_id', 'entity_type'),
    )


# Task template models
class TaskTemplateStatus:
    """Task template statuses."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class TaskTemplateInput(BaseModel):
    """Input schema for a task template."""
    name: str = Field(..., description="Input parameter name")
    type: str = Field(..., description="Input parameter type (str, int, float, bool, dict, list)")
    required: bool = Field(default=True, description="Whether this input is required")
    default: Any = Field(default=None, description="Default value for the input")
    description: str = Field(default="", description="Description of the input parameter")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")


class TaskTemplateOutput(BaseModel):
    """Output schema for a task template."""
    name: str = Field(..., description="Output parameter name")
    type: str = Field(..., description="Output parameter type")
    description: str = Field(default="", description="Description of the output parameter")
    required: bool = Field(default=True, description="Whether this output is required")
    is_file: bool = Field(default=False, description="Whether this output is a file upload")
    file_config: Optional[Dict[str, Any]] = Field(default=None, description="File upload configuration (S3 bucket, etc.)")


class TaskTemplate(BaseDBModel):
    """Task template model - reusable task definitions with schemas."""
    __tablename__ = "task_templates"

    version = Column(String(50), nullable=False, default="1.0.0")
    status = Column(String(20), nullable=False, default=TaskTemplateStatus.DRAFT)
    input_schema = Column(JSON, nullable=False, default=list)
    output_schema = Column(JSON, nullable=False, default=list)
    device_types = Column(JSON, nullable=False, default=list)
    estimated_duration = Column(Integer, nullable=True)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_delay = Column(Integer, nullable=False, default=60)
    code_reference = Column(String(500), nullable=True)

    device_types_rel = relationship("DeviceType", secondary="task_template_device_types", back_populates="task_templates")


class DeviceType(BaseDBModel):
    """Device type model - defines types of devices that can be used."""
    __tablename__ = "device_types"

    category = Column(String(100), nullable=False, index=True)
    protocol = Column(String(50), nullable=False)
    protocol_config = Column(JSON, nullable=False, default=dict)
    capabilities = Column(JSON, nullable=False, default=list)

    task_templates = relationship("TaskTemplate", secondary="task_template_device_types", back_populates="device_types_rel")


class TaskTemplateDeviceType(BaseDBModel):
    """Association table for TaskTemplate to DeviceType relationship."""
    __tablename__ = "task_template_device_types"

    task_template_id = Column(PGUUID(as_uuid=True), ForeignKey('task_templates.id'), nullable=False)
    device_type_id = Column(PGUUID(as_uuid=True), ForeignKey('device_types.id'), nullable=False)
