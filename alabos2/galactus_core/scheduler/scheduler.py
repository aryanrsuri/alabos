"""Core scheduler for alabos - manages task execution and resource allocation."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from ..database.connection import get_db_session_sync
from ..events.producer import event_producer
from ..models.device import Device, DeviceStatus
from ..models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class ResourceAllocation:
    """Represents a resource allocation for a task."""

    def __init__(self, device_id: UUID, sample_positions: list[str]):
        self.device_id = device_id
        self.sample_positions = sample_positions
        self.allocated_at = datetime.utcnow()

    def conflicts_with(self, other: "ResourceAllocation") -> bool:
        """Check if this allocation conflicts with another."""
        return self.device_id == other.device_id or any(
            pos in other.sample_positions for pos in self.sample_positions
        )


class SchedulingDecision:
    """Result of a scheduling decision."""

    def __init__(
        self,
        task_id: UUID,
        can_run: bool,
        reason: str,
        estimated_start: datetime | None = None,
    ):
        self.task_id = task_id
        self.can_run = can_run
        self.reason = reason
        self.estimated_start = estimated_start


class ResourceScheduler:
    """Core scheduler for managing resource allocation and task execution."""

    def __init__(self):
        self.active_allocations: dict[UUID, ResourceAllocation] = {}
        self.device_availability: dict[UUID, datetime] = {}
        self.pending_tasks: list[UUID] = []
        self.task_dependencies: dict[UUID, set[UUID]] = defaultdict(set)
        self.running = False
        self.scheduler_loop_task: asyncio.Task | None = None

    def add_task_dependency(self, task_id: UUID, depends_on: UUID):
        """Add a dependency relationship between tasks."""
        self.task_dependencies[task_id].add(depends_on)

    def can_task_run(self, task_id: UUID, session: Session) -> SchedulingDecision:
        """Check if a task can run given current resource availability."""
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return SchedulingDecision(task_id, False, "Task not found")

            
            if task.status not in [TaskStatus.PENDING, TaskStatus.READY]:
                return SchedulingDecision(
                    task_id, False, f"Task in invalid state: {task.status}"
                )

            
            if not self._check_dependencies_satisfied(task, session):
                return SchedulingDecision(task_id, False, "Dependencies not satisfied")

            
            resource_available = self._check_resource_availability(task, session)
            if not resource_available[0]:
                return SchedulingDecision(task_id, False, resource_available[1])

            
            estimated_start = self._estimate_start_time(task, session)

            return SchedulingDecision(task_id, True, "Ready to run", estimated_start)

        except Exception as e:
            logger.error(f"Error checking if task {task_id} can run: {e}")
            return SchedulingDecision(task_id, False, f"Error: {e!s}")

    def _check_dependencies_satisfied(self, task: Task, session: Session) -> bool:
        """Check if all task dependencies are satisfied."""
        if not task.prev_tasks:
            return True

        for prev_task_id in task.prev_tasks:
            prev_task = session.query(Task).filter(Task.id == prev_task_id).first()
            if not prev_task or prev_task.status != TaskStatus.COMPLETED:
                return False

        return True

    def _check_resource_availability(
        self, task: Task, session: Session
    ) -> tuple[bool, str]:
        """Check if required resources are available for the task."""
        try:
            
            template = task.task_template
            if not template:
                return False, "Task template not found"

            
            required_device_types = template.required_device_types
            if required_device_types:
                available_devices = (
                    session.query(Device)
                    .filter(
                        Device.device_type_id.in_(required_device_types),
                        Device.status == DeviceStatus.ONLINE,
                        Device.is_available == True,
                    )
                    .all()
                )

                if len(available_devices) < len(required_device_types):
                    return (
                        False,
                        f"Insufficient devices available: need {len(required_device_types)}, have {len(available_devices)}",
                    )

            
            if task.assigned_device_id:
                device = (
                    session.query(Device)
                    .filter(Device.id == task.assigned_device_id)
                    .first()
                )
                if not device or not device.is_online():
                    return (
                        False,
                        f"Assigned device {task.assigned_device_id} is not available",
                    )

                
                if device.id in self.active_allocations:
                    return False, f"Device {device.id} is already allocated"

            return True, "Resources available"

        except Exception as e:
            return False, f"Error checking resource availability: {e!s}"

    def _estimate_start_time(self, task: Task, session: Session) -> datetime | None:
        """Estimate when a task can start based on dependencies and resource availability."""
        try:
            
            estimated_start = datetime.utcnow()

            
            if task.assigned_device_id:
                device = (
                    session.query(Device)
                    .filter(Device.id == task.assigned_device_id)
                    .first()
                )
                if device and device.current_task_id:
                    current_task = (
                        session.query(Task)
                        .filter(Task.id == device.current_task_id)
                        .first()
                    )
                    if current_task and current_task.status in [
                        TaskStatus.RUNNING,
                        TaskStatus.READY,
                    ]:
                        
                        if (
                            current_task.task_template
                            and current_task.task_template.estimated_duration
                        ):
                            estimated_completion = current_task.started_at + timedelta(
                                minutes=current_task.task_template.estimated_duration
                            )
                            estimated_start = max(estimated_start, estimated_completion)
                        else:
                            
                            estimated_start += timedelta(minutes=30)

            return estimated_start

        except Exception as e:
            logger.error(f"Error estimating start time for task {task.id}: {e}")
            return datetime.utcnow()

    def allocate_resources(self, task_id: UUID, session: Session) -> bool:
        """Allocate resources for a task."""
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            
            if task.assigned_device_id:
                device = (
                    session.query(Device)
                    .filter(Device.id == task.assigned_device_id)
                    .first()
                )
                if device:
                    
                    allocation = ResourceAllocation(
                        device_id=device.id,
                        sample_positions=[],  
                    )
                    self.active_allocations[device.id] = allocation

                    
                    device.status = DeviceStatus.BUSY
                    device.current_task_id = task_id

                    
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.utcnow()

                    
                    event_producer.send_task_event(
                        task_id=task_id,
                        event_type="started",
                        data={"device_id": str(device.id)},
                    )

                    logger.info(f"Allocated device {device.id} to task {task_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error allocating resources for task {task_id}: {e}")
            return False

    def release_resources(self, task_id: UUID, session: Session) -> bool:
        """Release resources allocated to a completed task."""
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            
            if task.assigned_device_id:
                device = (
                    session.query(Device)
                    .filter(Device.id == task.assigned_device_id)
                    .first()
                )
                if device and device.id in self.active_allocations:
                    
                    del self.active_allocations[device.id]

                    
                    device.status = DeviceStatus.ONLINE
                    device.current_task_id = None

                    logger.info(f"Released device {device.id} from task {task_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error releasing resources for task {task_id}: {e}")
            return False

    async def run_scheduler_loop(self):
        """Main scheduler loop that continuously checks for ready tasks."""
        logger.info("Starting scheduler loop")

        while self.running:
            try:
                with get_db_session_sync() as session:
                    
                    tasks = (
                        session.query(Task)
                        .filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.READY]))
                        .all()
                    )

                    for task in tasks:
                        decision = self.can_task_run(task.id, session)

                        if decision.can_run:
                            logger.info(f"Task {task.id} is ready to run")
                            
                            if self.allocate_resources(task.id, session):
                                logger.info(f"Started task {task.id}")
                            else:
                                logger.warning(
                                    f"Failed to allocate resources for task {task.id}"
                                )

                
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(10)  

        logger.info("Scheduler loop stopped")

    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        self.scheduler_loop_task = asyncio.create_task(self.run_scheduler_loop())
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping scheduler...")
        self.running = False

        if self.scheduler_loop_task:
            self.scheduler_loop_task.cancel()

        logger.info("Scheduler stopped")

    def get_queue_status(self, session: Session) -> dict[str, int]:
        """Get current queue status."""
        try:
            pending = (
                session.query(Task).filter(Task.status == TaskStatus.PENDING).count()
            )
            ready = session.query(Task).filter(Task.status == TaskStatus.READY).count()
            running = (
                session.query(Task).filter(Task.status == TaskStatus.RUNNING).count()
            )

            return {
                "pending": pending,
                "ready": ready,
                "running": running,
                "total_queued": pending + ready + running,
            }
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {"error": str(e)}



scheduler = ResourceScheduler()
