"""Device models for alabos."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseDBModel


class DeviceStatus:
    """Device status values."""

    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    UNKNOWN = "unknown"


class DeviceCapability:
    """Device capability types."""

    TEMPERATURE_CONTROL = "temperature_control"
    PRESSURE_CONTROL = "pressure_control"
    ATMOSPHERE_CONTROL = "atmosphere_control"
    MIXING = "mixing"
    DOSING = "dosing"
    MEASUREMENT = "measurement"
    MOVEMENT = "movement"
    STORAGE = "storage"
    CLEANING = "cleaning"


class Device(BaseDBModel):
    """Physical device model."""

    __tablename__ = "devices"

    device_type_id = Column(
        PGUUID(as_uuid=True), ForeignKey("device_types.id"), nullable=False
    )
    location_id = Column(
        PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )

    serial_number = Column(String(100), nullable=True, unique=True)
    model_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)

    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    connection_string = Column(String(500), nullable=True)

    status = Column(
        String(20), nullable=False, default=DeviceStatus.OFFLINE, index=True
    )
    is_available = Column(Boolean, nullable=False, default=True)
    current_task_id = Column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )

    last_seen = Column(DateTime(timezone=True), nullable=True)
    uptime_seconds = Column(Integer, nullable=False, default=0)
    total_runtime_seconds = Column(Integer, nullable=False, default=0)

    config = Column(JSONB, nullable=False, default=dict)
    calibration_data = Column(JSONB, nullable=True)

    sample_positions = Column(JSON, nullable=False, default=list)

    device_type = relationship("DeviceType", back_populates="devices")
    location = relationship("Location", back_populates="devices")
    current_task = relationship("Task", back_populates="assigned_device")
    tasks = relationship(
        "Task", back_populates="assigned_device", foreign_keys="Task.assigned_device_id"
    )

    def is_online(self) -> bool:
        """Check if device is online and available."""
        return self.status == DeviceStatus.ONLINE and self.is_available

    def can_execute_task(self, task_template_id: UUID) -> bool:
        """Check if this device can execute a specific task template."""
        if not self.is_online():
            return False

        return task_template_id in [dt.id for dt in self.device_type.task_templates]

    def get_available_positions(self) -> list[dict[str, Any]]:
        """Get list of available sample positions."""
        return self.sample_positions


class DeviceType(BaseDBModel):
    """Device type model - defines types of devices that can be used."""

    __tablename__ = "device_types"

    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)

    protocol = Column(String(50), nullable=False)
    protocol_config_schema = Column(JSONB, nullable=False, default=dict)

    capabilities = Column(JSON, nullable=False, default=list)
    specifications = Column(JSONB, nullable=False, default=dict)
    max_sample_capacity = Column(Integer, nullable=True)

    reliability_score = Column(Float, nullable=True)
    avg_setup_time = Column(Integer, nullable=True)
    avg_execution_time = Column(Integer, nullable=True)

    devices = relationship("Device", back_populates="device_type")
    task_templates = relationship(
        "TaskTemplate",
        secondary="task_template_device_types",
        back_populates="device_types",
    )


class Location(BaseDBModel):
    """Physical location model for devices."""

    __tablename__ = "locations"

    parent_id = Column(PGUUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    location_type = Column(String(50), nullable=False, index=True)

    coordinates = Column(JSONB, nullable=True)
    address = Column(Text, nullable=True)

    environmental_conditions = Column(JSONB, nullable=False, default=dict)
    safety_requirements = Column(JSON, nullable=False, default=list)

    parent = relationship("Location", remote_side=[id])
    children = relationship("Location", back_populates="parent")
    devices = relationship("Device", back_populates="location")


class DeviceCreate(BaseModel):
    """Model for creating a new device."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    device_type_id: UUID = Field(..., description="ID of the device type")
    location_id: UUID | None = None
    serial_number: str | None = None
    model_number: str | None = None
    manufacturer: str | None = None
    ip_address: str | None = None
    port: int | None = None
    connection_string: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    calibration_data: dict[str, Any] | None = None
    sample_positions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @validator("ip_address")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        if v:
            import ipaddress

            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError("Invalid IP address format")
        return v


class DeviceResponse(BaseModel):
    """Response model for device."""

    id: UUID
    name: str
    description: str | None
    device_type_id: UUID
    location_id: UUID | None
    serial_number: str | None
    model_number: str | None
    manufacturer: str | None
    ip_address: str | None
    port: int | None
    connection_string: str | None
    status: str
    is_available: bool
    current_task_id: UUID | None
    last_seen: datetime | None
    uptime_seconds: int
    total_runtime_seconds: int
    config: dict[str, Any]
    calibration_data: dict[str, Any] | None
    sample_positions: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    class Config:
        from_attributes = True


class DeviceTypeCreate(BaseModel):
    """Model for creating a new device type."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(..., description="Device category (e.g., furnace, robot_arm)")
    subcategory: str | None = None
    protocol: str = Field(..., description="Communication protocol")
    protocol_config_schema: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)
    specifications: dict[str, Any] = Field(default_factory=dict)
    max_sample_capacity: int | None = None
    reliability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    avg_setup_time: int | None = None
    avg_execution_time: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceTypeResponse(BaseModel):
    """Response model for device type."""

    id: UUID
    name: str
    description: str | None
    category: str
    subcategory: str | None
    protocol: str
    protocol_config_schema: dict[str, Any]
    capabilities: list[str]
    specifications: dict[str, Any]
    max_sample_capacity: int | None
    reliability_score: float | None
    avg_setup_time: int | None
    avg_execution_time: int | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    class Config:
        from_attributes = True


class LocationCreate(BaseModel):
    """Model for creating a new location."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    parent_id: UUID | None = None
    location_type: str = Field(
        ..., description="Type of location (lab, building, room, bench)"
    )
    coordinates: dict[str, Any] | None = None
    address: str | None = None
    environmental_conditions: dict[str, Any] = Field(default_factory=dict)
    safety_requirements: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LocationResponse(BaseModel):
    """Response model for location."""

    id: UUID
    name: str
    description: str | None
    parent_id: UUID | None
    location_type: str
    coordinates: dict[str, Any] | None
    address: str | None
    environmental_conditions: dict[str, Any]
    safety_requirements: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    class Config:
        from_attributes = True
