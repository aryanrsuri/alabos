"""Task execution engine for alabos."""

import asyncio
import importlib
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from alabos.alabos_core.models.device import Device

from ..database.connection import get_db_session_sync
from ..events.producer import event_producer
from ..models.job import Job, JobStatus
from ..models.task import Task, TaskStatus
from ..utils.file_handler import FileHandler

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks based on their templates and implementations."""

    def __init__(self):
        self.file_handler = FileHandler()
        self.active_executions: dict[UUID, asyncio.Task] = {}

    async def execute_task(self, task_id: UUID) -> bool:
        """Execute a single task."""
        try:
            logger.info(f"Starting execution of task {task_id}")

            with get_db_session_sync() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return False

                
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                session.commit()

                
                event_producer.send_task_event(
                    task_id=task_id,
                    event_type="started",
                    data={"workflow_id": str(task.workflow_id)},
                )

            
            result = await self._run_task_implementation(task_id)

            
            success = await self._process_task_result(task_id, result)

            if success:
                logger.info(f"Task {task_id} completed successfully")
                
                await self._release_task_resources(task_id)
            else:
                logger.error(f"Task {task_id} failed")

            return success

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            await self._handle_task_error(task_id, str(e))
            return False

    async def _run_task_implementation(self, task_id: UUID) -> dict[str, Any]:
        """Run the actual task implementation."""
        with get_db_session_sync() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task or not task.task_template:
                raise ValueError(f"Invalid task or template: {task_id}")

            template = task.task_template

            
            if template.implementation_class:
                try:
                    
                    module_name, class_name = template.implementation_class.rsplit(
                        ".", 1
                    )
                    module = importlib.import_module(module_name)
                    impl_class = getattr(module, class_name)

                    
                    impl_instance = impl_class(
                        task_id=task_id, inputs=task.inputs, session=session
                    )

                    result = await impl_instance.run()
                    return result

                except Exception as e:
                    logger.error(
                        f"Error running custom implementation for task {task_id}: {e}"
                    )
                    

            
            return await self._default_task_execution(task, template)

    async def _default_task_execution(self, task: Task, template) -> dict[str, Any]:
        """Default task execution for tasks without custom implementations."""
        logger.info(f"Running default execution for task {task.id}")

        
        execution_time = template.estimated_duration or 60
        await asyncio.sleep(min(execution_time / 10, 30))  

        outputs = {}
        for output_name, output_config in template.output_schema.items():
            if output_config.get("type") == "file":
                file_path = f"/tmp/task_{task.id}_{output_name}.txt"
                with open(file_path, "w") as f:
                    f.write(f"Mock output for {output_name} from task {task.id}")

                file_url = await self.file_handler.upload_file(
                    file_path, f"task_outputs/{task.id}/{output_name}"
                )
                outputs[output_name] = {
                    "value": f"Mock result for {output_name}",
                    "file_url": file_url,
                    "file_metadata": {"size": 100, "type": "text/plain"},
                }
            else:
                outputs[output_name] = {
                    "value": f"Mock result for {output_name}",
                    "type": output_config.get("type", "string"),
                }

        return {
            "task_id": str(task.id),
            "status": "completed",
            "outputs": outputs,
            "execution_time": execution_time,
            "metadata": {"execution_mode": "default"},
        }

    async def _process_task_result(self, task_id: UUID, result: dict[str, Any]) -> bool:
        """Process and store task results."""
        try:
            with get_db_session_sync() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return False

                
                task.status = (
                    TaskStatus.COMPLETED
                    if result.get("status") == "completed"
                    else TaskStatus.FAILED
                )
                task.completed_at = datetime.utcnow()
                task.outputs = result.get("outputs", {})
                task.execution_time = result.get("execution_time")
                task.result_data = result

                if result.get("status") != "completed":
                    task.error_message = result.get("error_message", "Task failed")

                session.commit()

                
                job = session.query(Job).filter(Job.id == task.job_id).first()
                if job:
                    
                    total_tasks = (
                        session.query(Task).filter(Task.job_id == job.id).count()
                    )
                    completed_tasks = (
                        session.query(Task)
                        .filter(
                            Task.job_id == job.id, Task.status == TaskStatus.COMPLETED
                        )
                        .count()
                    )

                    job.completed_tasks = completed_tasks
                    job.progress_percentage = (
                        int((completed_tasks / total_tasks) * 100)
                        if total_tasks > 0
                        else 100
                    )

                    
                    if completed_tasks == total_tasks:
                        job.status = JobStatus.COMPLETED
                        job.completed_at = datetime.utcnow()

                    session.commit()

                
                event_producer.send_task_event(
                    task_id=task_id,
                    event_type="completed"
                    if task.status == TaskStatus.COMPLETED
                    else "failed",
                    data={
                        "job_id": str(task.job_id),
                        "execution_time": task.execution_time,
                        "outputs_count": len(task.outputs) if task.outputs else 0,
                    },
                )

            return True

        except Exception as e:
            logger.error(f"Error processing task result for {task_id}: {e}")
            return False

    async def _handle_task_error(self, task_id: UUID, error_message: str):
        """Handle task execution errors."""
        try:
            with get_db_session_sync() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return

                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                task.error_message = error_message

                session.commit()

                
                job = session.query(Job).filter(Job.id == task.job_id).first()
                if job:
                    job.failed_tasks += 1
                    job.progress_percentage = job.calculate_progress()
                    session.commit()

                
                event_producer.send_task_event(
                    task_id=task_id,
                    event_type="failed",
                    data={"job_id": str(task.job_id), "error_message": error_message},
                )

                
                await self._release_task_resources(task_id)

        except Exception as e:
            logger.error(f"Error handling task error for {task_id}: {e}")

    async def _release_task_resources(self, task_id: UUID):
        """Release resources allocated to a task."""
        try:
            with get_db_session_sync() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task or not task.assigned_device_id:
                    return

                device = (
                    session.query(Device)
                    .filter(Device.id == task.assigned_device_id)
                    .first()
                )
                if device:
                    device.status = "online"
                    device.current_task_id = None
                    device.total_runtime_seconds += int(task.execution_time or 0)
                    session.commit()

        except Exception as e:
            logger.error(f"Error releasing resources for task {task_id}: {e}")

    def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a running task."""
        try:
            with get_db_session_sync() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return False

                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.utcnow()

                    
                    asyncio.create_task(self._release_task_resources(task_id))

                    session.commit()

                    
                    event_producer.send_task_event(
                        task_id=task_id,
                        event_type="cancelled",
                        data={"reason": "Manual cancellation"},
                    )

                    logger.info(f"Cancelled task {task_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False



task_executor = TaskExecutor()
