"""Task API routes for alabos."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.connection import get_async_db_session
from ...models.task import Task, TaskStatus, TaskCreate, TaskResponse
from ...events.producer import event_producer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: str = None,
    job_id: UUID = None,
    workflow_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_async_db_session),
):
    """List tasks with optional filtering."""
    query = session.query(Task)

    if status:
        query = query.filter(Task.status == status)
    if job_id:
        query = query.filter(Task.job_id == job_id)
    if workflow_id:
        query = query.filter(Task.workflow_id == workflow_id)

    tasks = query.offset(skip).limit(limit).all()
    return [TaskResponse.from_orm(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, session: Session = Depends(get_async_db_session)):
    """Get a specific task."""
    task = session.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse.from_orm(task)


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: UUID, session: Session = Depends(get_async_db_session)):
    """Cancel a running task."""
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status not in [
            TaskStatus.PENDING,
            TaskStatus.READY,
            TaskStatus.RUNNING,
        ]:
            raise HTTPException(
                status_code=400, detail=f"Cannot cancel task in status: {task.status}"
            )

        # Update task status
        old_status = task.status
        task.status = TaskStatus.CANCELLED
        task.completed_at = None  # Set current time

        session.commit()

        # Send event
        event_producer.send_event(
            event_type="cancelled",
            entity_id=task_id,
            entity_type="task",
            data={"reason": "User requested cancellation"},
        )

        logger.info(f"Cancelled task {task_id} from status {old_status}")
        return {"message": "Task cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
