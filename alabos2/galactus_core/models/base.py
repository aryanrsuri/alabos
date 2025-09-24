"""Base models and common database structures for alabos.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BaseDBModel(TimestampMixin, Base):
    """Base database model with common fields."""

    __abstract__ = True

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)


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
    entity_type: str = Field(
        ..., description="Type of the entity (task, workflow, device, etc.)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict, description="Event payload data")


class KafkaEvent(BaseDBModel):
    """Database model for storing Kafka events in TimescaleDB."""

    __tablename__ = "kafka_events"

    event_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_events_time_type", "created_at", "event_type"),
        Index("idx_events_entity", "entity_id", "entity_type"),
    )


class DeviceType(BaseDBModel):
    """Device type model - defines types of devices that can be used."""

    __tablename__ = "device_types"

    category = Column(String(100), nullable=False, index=True)
    protocol = Column(String(50), nullable=False)
    protocol_config = Column(JSON, nullable=False, default=dict)
    capabilities = Column(JSON, nullable=False, default=list)

    task_templates = relationship(
        "TaskTemplate",
        secondary="task_template_device_types",
        back_populates="device_types_rel",
    )


class TaskTemplateDeviceType(BaseDBModel):
    """Association table for TaskTemplate to DeviceType relationship."""

    __tablename__ = "task_template_device_types"

    task_template_id = Column(
        PGUUID(as_uuid=True), ForeignKey("task_templates.id"), nullable=False
    )
    device_type_id = Column(
        PGUUID(as_uuid=True), ForeignKey("device_types.id"), nullable=False
    )
