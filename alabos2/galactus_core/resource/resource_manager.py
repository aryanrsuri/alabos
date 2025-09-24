"""Resource manager for alabos - handles device and sample position allocation."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.connection import get_db_session_sync
from ..models.device import Device, DeviceStatus

logger = logging.getLogger(__name__)


class ResourceRequest:
    """Represents a request for resources."""

    def __init__(
        self, task_id: UUID, required_device_types: list[UUID], sample_count: int = 0
    ):
        self.task_id = task_id
        self.required_device_types = required_device_types
        self.sample_count = sample_count
        self.requested_at = datetime.utcnow()


class ResourceAllocation:
    """Represents an allocated resource."""

    def __init__(self, device_id: UUID, task_id: UUID, sample_positions: list[str]):
        self.device_id = device_id
        self.task_id = task_id
        self.sample_positions = sample_positions
        self.allocated_at = datetime.utcnow()


class ResourceConflict(Exception):
    """Raised when there's a resource conflict."""

    pass


class ResourceManager:
    """Manages device and sample position allocation with conflict resolution."""

    def __init__(self):
        self.active_allocations: dict[UUID, ResourceAllocation] = {}
        self.device_availability: dict[UUID, datetime] = {}
        self.sample_position_availability: dict[str, datetime] = {}
        self.pending_requests: list[ResourceRequest] = []

    def request_resources(
        self, request: ResourceRequest, session: Session
    ) -> ResourceAllocation | None:
        """Request resources for a task."""
        try:
            # Check if resources are available
            allocation = self._find_available_resources(request, session)
            if allocation:
                # Allocate the resources
                self._allocate_resources(allocation)
                logger.info(f"Allocated resources for task {request.task_id}")
                return allocation
            else:
                # Add to pending queue
                self.pending_requests.append(request)
                logger.info(f"Queued resource request for task {request.task_id}")
                return None

        except ResourceConflict as e:
            logger.warning(f"Resource conflict for task {request.task_id}: {e}")
            self.pending_requests.append(request)
            return None
        except Exception as e:
            logger.error(f"Error requesting resources for task {request.task_id}: {e}")
            return None

    def _find_available_resources(
        self, request: ResourceRequest, session: Session
    ) -> ResourceAllocation | None:
        """Find available resources that match the request."""
        try:
            # Get available devices of required types
            available_devices = self._get_available_devices(
                request.required_device_types, session
            )
            if not available_devices:
                return None

            # Check for conflicts
            conflicting_devices = set()
            for device_id, device in available_devices.items():
                if device_id in self.active_allocations:
                    conflicting_devices.add(device_id)

            if conflicting_devices:
                # Try to find non-conflicting devices
                available_non_conflicting = {
                    device_id: device
                    for device_id, device in available_devices.items()
                    if device_id not in conflicting_devices
                }
                if not available_non_conflicting:
                    raise ResourceConflict(
                        f"All available devices are allocated: {conflicting_devices}"
                    )

                selected_devices = list(available_non_conflicting.values())[
                    : len(request.required_device_types)
                ]
            else:
                selected_devices = list(available_devices.values())[
                    : len(request.required_device_types)
                ]

            # Create allocation
            device_allocations = []
            for device in selected_devices:
                # Get available sample positions for this device
                available_positions = self._get_available_sample_positions(
                    device, request.sample_count, session
                )
                if len(available_positions) < request.sample_count:
                    raise ResourceConflict(
                        f"Insufficient sample positions on device {device.id}"
                    )

                device_allocations.append(
                    (device.id, available_positions[: request.sample_count])
                )

            # Create resource allocation
            primary_device_id = device_allocations[0][0]
            all_sample_positions = []
            for device_id, positions in device_allocations:
                all_sample_positions.extend(positions)

            return ResourceAllocation(
                primary_device_id, request.task_id, all_sample_positions
            )

        except Exception as e:
            logger.error(f"Error finding available resources: {e}")
            return None

    def _get_available_devices(
        self, required_device_types: list[UUID], session: Session
    ) -> dict[UUID, Device]:
        """Get available devices of specified types."""
        try:
            devices = (
                session.query(Device)
                .filter(
                    Device.device_type_id.in_(required_device_types),
                    Device.status == DeviceStatus.ONLINE,
                    Device.is_available == True,
                )
                .all()
            )

            return {device.id: device for device in devices}

        except Exception as e:
            logger.error(f"Error getting available devices: {e}")
            return {}

    def _get_available_sample_positions(
        self, device: Device, count: int, session: Session
    ) -> list[str]:
        """Get available sample positions on a device."""
        try:
            if not device.sample_positions:
                return []

            available_positions = []
            for position in device.sample_positions:
                position_name = position.get("name", "")
                if position_name not in self.sample_position_availability:
                    available_positions.append(position_name)

            return available_positions[:count]

        except Exception as e:
            logger.error(f"Error getting available sample positions: {e}")
            return []

    def _allocate_resources(self, allocation: ResourceAllocation):
        """Allocate the specified resources."""
        try:
            self.active_allocations[allocation.device_id] = allocation

            # Mark sample positions as unavailable
            for position in allocation.sample_positions:
                self.sample_position_availability[position] = (
                    datetime.utcnow() + timedelta(hours=1)
                )  # Default lock duration

            logger.info(
                f"Allocated device {allocation.device_id} and {len(allocation.sample_positions)} sample positions"
            )

        except Exception as e:
            logger.error(f"Error allocating resources: {e}")

    def release_resources(self, device_id: UUID):
        """Release resources allocated to a device."""
        try:
            if device_id in self.active_allocations:
                allocation = self.active_allocations[device_id]

                # Release sample positions
                for position in allocation.sample_positions:
                    if position in self.sample_position_availability:
                        del self.sample_position_availability[position]

                # Remove allocation
                del self.active_allocations[device_id]

                logger.info(f"Released resources for device {device_id}")

                # Check if any pending requests can now be fulfilled
                self._process_pending_requests()

        except Exception as e:
            logger.error(f"Error releasing resources for device {device_id}: {e}")

    def _process_pending_requests(self):
        """Process pending resource requests."""
        try:
            remaining_requests = []

            for request in self.pending_requests:
                allocation = self._find_available_resources(
                    request, get_db_session_sync()
                )
                if allocation:
                    self._allocate_resources(allocation)
                    logger.info(f"Fulfilled pending request for task {request.task_id}")
                else:
                    remaining_requests.append(request)

            self.pending_requests = remaining_requests

        except Exception as e:
            logger.error(f"Error processing pending requests: {e}")

    def get_resource_status(self, session: Session) -> dict[str, Any]:
        """Get current resource status."""
        try:
            # Get all devices
            all_devices = session.query(Device).all()

            # Get active allocations
            active_allocations = len(self.active_allocations)

            # Get pending requests
            pending_requests = len(self.pending_requests)

            # Device status breakdown
            device_status = {
                DeviceStatus.ONLINE: 0,
                DeviceStatus.OFFLINE: 0,
                DeviceStatus.BUSY: 0,
                DeviceStatus.MAINTENANCE: 0,
                DeviceStatus.ERROR: 0,
            }

            for device in all_devices:
                device_status[device.status] += 1

            # Available vs allocated sample positions
            total_positions = sum(
                len(device.sample_positions) for device in all_devices
            )
            allocated_positions = sum(
                len(allocation.sample_positions)
                for allocation in self.active_allocations.values()
            )

            return {
                "total_devices": len(all_devices),
                "device_status": device_status,
                "active_allocations": active_allocations,
                "pending_requests": pending_requests,
                "total_sample_positions": total_positions,
                "allocated_sample_positions": allocated_positions,
                "available_sample_positions": total_positions - allocated_positions,
            }

        except Exception as e:
            logger.error(f"Error getting resource status: {e}")
            return {"error": str(e)}

    def optimize_allocation(self, session: Session) -> dict[str, Any]:
        """Optimize current resource allocation."""
        try:
            # This is a placeholder for more sophisticated optimization logic
            # For now, just process pending requests
            initial_pending = len(self.pending_requests)
            self._process_pending_requests()
            fulfilled = initial_pending - len(self.pending_requests)

            return {
                "optimization_type": "pending_request_processing",
                "initial_pending_requests": initial_pending,
                "fulfilled_requests": fulfilled,
                "remaining_pending_requests": len(self.pending_requests),
            }

        except Exception as e:
            logger.error(f"Error optimizing allocation: {e}")
            return {"error": str(e)}


# Global resource manager instance
resource_manager = ResourceManager()
