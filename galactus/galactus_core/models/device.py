"""
Device models for Galactus.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from .base import BaseDBModel, TimestampMixin, Base


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

    # Device identification
    device_type_id = Column(PGUUID(as_uuid=True), ForeignKey('device_types.id'), nullable=False)
    location_id = Column(PGUUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)

    # Physical information
    serial_number = Column(String(100), nullable=True, unique=True)
    model_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)

    # Network and communication
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    port = Column(Integer, nullable=True)
    connection_string = Column(String(500), nullable=True)  # Generic connection string

    # Current state
    status = Column(String(20), nullable=False, default=DeviceStatus.OFFLINE, index=True)
    is_available = Column(Boolean, nullable=False, default=True)
    current_task_id = Column(PGUUID(as_uuid=True), ForeignKey('tasks.id'), nullable=True)

    # Operational data
    last_seen = Column(DateTime(timezone=True), nullable=True)
    uptime_seconds = Column(Integer, nullable=False, default=0)
    total_runtime_seconds = Column(Integer, nullable=False, default=0)

    # Configuration
    config = Column(JSONB, nullable=False, default=dict)  # Device-specific configuration
    calibration_data = Column(JSONB, nullable=True)  # Calibration parameters

    # Sample positions
    sample_positions = Column(JSON, nullable=False, default=list)  # List of available positions

    # Relationships
    device_type = relationship("DeviceType", back_populates="devices")
    location = relationship("Location", back_populates="devices")
    current_task = relationship("Task", back_populates="assigned_device")
    tasks = relationship("Task", back_populates="assigned_device", foreign_keys="Task.assigned_device_id")

    def is_online(self) -> bool:
        """Check if device is online and available."""
        return self.status == DeviceStatus.ONLINE and self.is_available

    def can_execute_task(self, task_template_id: UUID) -> bool:
        """Check if this device can execute a specific task template."""
        if not self.is_online():
            return False

        # Check if device type supports the task template
        return task_template_id in [dt.id for dt in self.device_type.task_templates]

    def get_available_positions(self) -> List[Dict[str, Any]]:
        """Get list of available sample positions."""
        # Implementation would check which positions are currently occupied
        return self.sample_positions


class DeviceType(BaseDBModel):
    """Device type model - defines types of devices that can be used."""
    __tablename__ = "device_types"

    # Type information
    category = Column(String(100), nullable=False, index=True)  # e.g., "furnace", "robot_arm", "sensor"
    subcategory = Column(String(100), nullable=True, index=True)  # e.g., "tube_furnace", "scara_robot"

    # Communication protocol
    protocol = Column(String(50), nullable=False)  # e.g., "modbus", "http", "serial", "tcp"
    protocol_config_schema = Column(JSONB, nullable=False, default=dict)  # Schema for protocol configuration

    # Capabilities and specifications
    capabilities = Column(JSON, nullable=False, default=list)  # List of capability strings
    specifications = Column(JSONB, nullable=False, default=dict)  # Technical specifications
    max_sample_capacity = Column(Integer, nullable=True)  # Maximum number of samples device can handle

    # Performance characteristics
    reliability_score = Column(Float, nullable=True)  # 0.0 to 1.0 reliability score
    avg_setup_time = Column(Integer, nullable=True)  # Average setup time in seconds
    avg_execution_time = Column(Integer, nullable=True)  # Average execution time in seconds

    # Relationships
    devices = relationship("Device", back_populates="device_type")
    task_templates = relationship("TaskTemplate", secondary="task_template_device_types", back_populates="device_types")


class Location(BaseDBModel):
    """Physical location model for devices."""
    __tablename__ = "locations"

    # Location hierarchy
    parent_id = Column(PGUUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)
    location_type = Column(String(50), nullable=False, index=True)  # e.g., "lab", "building", "room", "bench"

    # Physical coordinates
    coordinates = Column(JSONB, nullable=True)  # {"x": 1.0, "y": 2.0, "z": 0.5, "units": "meters"}
    address = Column(Text, nullable=True)  # Human-readable address

    # Environmental conditions
    environmental_conditions = Column(JSONB, nullable=False, default=dict)  # Temperature, humidity, etc.
    safety_requirements = Column(JSON, nullable=False, default=list)  # List of safety requirements

    # Relationships
    parent = relationship("Location", remote_side=[id])
    children = relationship("Location", back_populates="parent")
    devices = relationship("Device", back_populates="location")


# Pydantic models for API
class DeviceCreate(BaseModel):
    """Model for creating a new device."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    device_type_id: UUID = Field(..., description="ID of the device type")
    location_id: Optional[UUID] = None
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    connection_string: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    calibration_data: Optional[Dict[str, Any]] = None
    sample_positions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('ip_address')
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        if v:
            # Basic IP address validation
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
    description: Optional[str]
    device_type_id: UUID
    location_id: Optional[UUID]
    serial_number: Optional[str]
    model_number: Optional[str]
    manufacturer: Optional[str]
    ip_address: Optional[str]
    port: Optional[int]
    connection_string: Optional[str]
    status: str
    is_available: bool
    current_task_id: Optional[UUID]
    last_seen: Optional[datetime]
    uptime_seconds: int
    total_runtime_seconds: int
    config: Dict[str, Any]
    calibration_data: Optional[Dict[str, Any]]
    sample_positions: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class DeviceTypeCreate(BaseModel):
    """Model for creating a new device type."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., description="Device category (e.g., furnace, robot_arm)")
    subcategory: Optional[str] = None
    protocol: str = Field(..., description="Communication protocol")
    protocol_config_schema: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    max_sample_capacity: Optional[int] = None
    reliability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    avg_setup_time: Optional[int] = None
    avg_execution_time: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceTypeResponse(BaseModel):
    """Response model for device type."""
    id: UUID
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    protocol: str
    protocol_config_schema: Dict[str, Any]
    capabilities: List[str]
    specifications: Dict[str, Any]
    max_sample_capacity: Optional[int]
    reliability_score: Optional[float]
    avg_setup_time: Optional[int]
    avg_execution_time: Optional[int]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class LocationCreate(BaseModel):
    """Model for creating a new location."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    location_type: str = Field(..., description="Type of location (lab, building, room, bench)")
    coordinates: Optional[Dict[str, Any]] = None
    address: Optional[str] = None
    environmental_conditions: Dict[str, Any] = Field(default_factory=dict)
    safety_requirements: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LocationResponse(BaseModel):
    """Response model for location."""
    id: UUID
    name: str
    description: Optional[str]
    parent_id: Optional[UUID]
    location_type: str
    coordinates: Optional[Dict[str, Any]]
    address: Optional[str]
    environmental_conditions: Dict[str, Any]
    safety_requirements: List[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True
