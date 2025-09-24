"""Job API routes for alabos."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.connection import get_async_db_session
from ...models.job import (
    Job,
    JobCreate,
    JobResponse,
    JobStatus,
    JobQueue,
    JobQueueResponse,
)
from ...models.workflow import Workflow
from ...events.producer import event_producer
from ...scheduler.scheduler import scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=JobResponse)
async def create_job(
    job_data: JobCreate, session: Session = Depends(get_async_db_session)
):
    """Create a new job."""
    try:
        # Verify workflow exists
        workflow = (
            session.query(Workflow).filter(Workflow.id == job_data.workflow_id).first()
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Create job
        job = Job(
            name=workflow.name,  # Use workflow name as job name
            workflow_id=job_data.workflow_id,
            submitted_by=job_data.submitted_by,
            priority=job_data.priority,
            max_retries=job_data.max_retries,
            max_concurrent_tasks=job_data.max_concurrent_tasks,
            resource_requirements=job_data.resource_requirements,
            execution_mode=job_data.execution_mode,
            execution_config=job_data.execution_config,
            metadata=job_data.metadata,
        )

        session.add(job)
        session.commit()
        session.refresh(job)

        # Create job queue entry
        queue_entry = JobQueue(
            job_id=job.id,
            priority=job_data.priority,
            position=0,  # Will be updated by scheduler
        )
        session.add(queue_entry)
        session.commit()

        # Update workflow status to active if it's still a draft
        if workflow.status == "draft":
            workflow.status = "active"
            session.commit()

        # Send event
        event_producer.send_event(
            event_type="created",
            entity_id=job.id,
            entity_type="job",
            data={
                "workflow_id": str(job_data.workflow_id),
                "priority": job_data.priority,
                "execution_mode": job_data.execution_mode,
            },
        )

        logger.info(f"Created job {job.id} for workflow {job_data.workflow_id}")
        return JobResponse.from_orm(job)

    except Exception as e:
        logger.error(f"Error creating job: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: str = None,
    priority: int = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_async_db_session),
):
    """List all jobs with optional filtering."""
    query = session.query(Job)

    if status:
        query = query.filter(Job.status == status)
    if priority is not None:
        query = query.filter(Job.priority == priority)

    jobs = query.offset(skip).limit(limit).all()
    return [JobResponse.from_orm(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, session: Session = Depends(get_async_db_session)):
    """Get a specific job."""
    job = session.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse.from_orm(job)


@router.put("/{job_id}/status")
async def update_job_status(
    job_id: UUID, status: str, session: Session = Depends(get_async_db_session)
):
    """Update job status."""
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Validate status transition
        if not job.can_transition_to(status):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from {job.status} to {status}",
            )

        old_status = job.status
        job.status = status

        if status == JobStatus.RUNNING:
            job.started_at = job.started_at or None  # Set current time if not set
            job.queued_at = job.queued_at or None
        elif status == JobStatus.COMPLETED:
            job.completed_at = None  # Set current time

        session.commit()

        # Send event
        event_producer.send_event(
            event_type="status_changed",
            entity_id=job_id,
            entity_type="job",
            data={"old_status": old_status, "new_status": status},
        )

        logger.info(f"Updated job {job_id} status: {old_status} -> {status}")
        return {"message": f"Job status updated to {status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{job_id}/queue")
async def queue_job(job_id: UUID, session: Session = Depends(get_async_db_session)):
    """Queue a job for execution."""
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.CREATED:
            raise HTTPException(
                status_code=400,
                detail=f"Job must be in 'created' status to be queued, current status: {job.status}",
            )

        # Update job status
        job.status = JobStatus.QUEUED
        job.queued_at = None  # Set current time

        # Update queue position
        queue_entry = session.query(JobQueue).filter(JobQueue.job_id == job_id).first()
        if queue_entry:
            # Simple queue positioning based on priority and creation time
            higher_priority_jobs = (
                session.query(JobQueue).filter(JobQueue.priority > job.priority).count()
            )
            queue_entry.position = higher_priority_jobs

        session.commit()

        # Send event
        event_producer.send_event(
            event_type="queued",
            entity_id=job_id,
            entity_type="job",
            data={"queue_position": queue_entry.position if queue_entry else 0},
        )

        logger.info(
            f"Queued job {job_id} at position {queue_entry.position if queue_entry else 0}"
        )
        return {
            "message": "Job queued successfully",
            "queue_position": queue_entry.position if queue_entry else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing job: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{job_id}/queue", response_model=JobQueueResponse)
async def get_job_queue_status(
    job_id: UUID, session: Session = Depends(get_async_db_session)
):
    """Get job queue status."""
    queue_entry = session.query(JobQueue).filter(JobQueue.job_id == job_id).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Job queue entry not found")

    return JobQueueResponse.from_orm(queue_entry)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: UUID, session: Session = Depends(get_async_db_session)):
    """Cancel a job."""
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=400, detail=f"Cannot cancel job in status: {job.status}"
            )

        # Update job status
        old_status = job.status
        job.status = JobStatus.CANCELLED
        job.completed_at = None  # Set current time

        session.commit()

        # Send event
        event_producer.send_event(
            event_type="cancelled",
            entity_id=job_id,
            entity_type="job",
            data={"reason": "User requested cancellation"},
        )

        logger.info(f"Cancelled job {job_id} from status {old_status}")
        return {"message": "Job cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/queue/status")
async def get_queue_status(session: Session = Depends(get_async_db_session)):
    """Get overall queue status."""
    try:
        # Get scheduler queue status
        scheduler_status = scheduler.get_queue_status(session)

        # Get job queue statistics
        queue_stats = (
            session.query(JobQueue.queue_name, Job.status, Job.priority).join(Job).all()
        )

        # Aggregate statistics
        stats = {
            "total_queued": len(queue_stats),
            "by_status": {},
            "by_priority": {},
            "by_queue": {},
        }

        for queue_name, status, priority in queue_stats:
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
            stats["by_queue"][queue_name] = stats["by_queue"].get(queue_name, 0) + 1

        return {**scheduler_status, **stats}

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
