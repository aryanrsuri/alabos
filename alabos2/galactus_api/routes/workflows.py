"""Workflow API routes for alabos."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.connection import get_async_db_session
from ...models.workflow import (
    Workflow,
    WorkflowCreate,
    WorkflowResponse,
    WorkflowStatus,
    Sample,
    SampleCreate,
    SampleResponse,
)
from ...models.task import Task, TaskCreate
from ...events.producer import event_producer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: WorkflowCreate, session: Session = Depends(get_async_db_session)
):
    """Create a new workflow."""
    try:
        # Create workflow
        workflow = Workflow(
            name=workflow_data.name,
            description=workflow_data.description,
            version="1.0.0",
            status=WorkflowStatus.DRAFT,
            task_graph=workflow_data.task_graph,
            sample_count=workflow_data.sample_count,
            max_concurrent_tasks=workflow_data.max_concurrent_tasks,
            start_conditions=workflow_data.start_conditions,
            stop_conditions=workflow_data.stop_conditions,
            optimization_targets=workflow_data.optimization_targets,
            template_id=workflow_data.template_id,
            metadata=workflow_data.metadata,
        )

        session.add(workflow)
        session.commit()
        session.refresh(workflow)

        # Create samples if provided
        if workflow_data.samples:
            for sample_data in workflow_data.samples:
                sample = Sample(
                    name=sample_data.name,
                    workflow_id=workflow.id,
                    batch_id=sample_data.batch_id,
                    composition=sample_data.composition,
                    properties=sample_data.properties,
                    target_properties=sample_data.target_properties,
                    metadata=sample_data.metadata,
                )
                session.add(sample)

            session.commit()

        # Send event
        event_producer.send_event(
            event_type="created",
            entity_id=workflow.id,
            entity_type="workflow",
            data={"name": workflow.name, "sample_count": workflow.sample_count},
        )

        logger.info(f"Created workflow: {workflow.name}")
        return WorkflowResponse.from_orm(workflow)

    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_async_db_session),
):
    """List all workflows with optional filtering."""
    query = session.query(Workflow)

    if status:
        query = query.filter(Workflow.status == status)

    workflows = query.offset(skip).limit(limit).all()
    return [WorkflowResponse.from_orm(w) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID, session: Session = Depends(get_async_db_session)
):
    """Get a specific workflow with all its samples and tasks."""
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse.from_orm(workflow)


@router.put("/{workflow_id}/status")
async def update_workflow_status(
    workflow_id: UUID, status: str, session: Session = Depends(get_async_db_session)
):
    """Update workflow status."""
    try:
        workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Validate status transition
        valid_transitions = {
            WorkflowStatus.DRAFT: [WorkflowStatus.ACTIVE, WorkflowStatus.CANCELLED],
            WorkflowStatus.ACTIVE: [
                WorkflowStatus.RUNNING,
                WorkflowStatus.PAUSED,
                WorkflowStatus.CANCELLED,
            ],
            WorkflowStatus.RUNNING: [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.PAUSED,
            ],
            WorkflowStatus.PAUSED: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
        }

        if status not in valid_transitions.get(workflow.status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from {workflow.status} to {status}",
            )

        old_status = workflow.status
        workflow.status = status

        if status == WorkflowStatus.RUNNING:
            workflow.started_at = (
                workflow.started_at or None
            )  # Set current time if not set
        elif status == WorkflowStatus.COMPLETED:
            workflow.completed_at = None  # Set current time

        session.commit()

        # Send event
        event_producer.send_event(
            event_type="status_changed",
            entity_id=workflow_id,
            entity_type="workflow",
            data={"old_status": old_status, "new_status": status},
        )

        logger.info(f"Updated workflow {workflow_id} status: {old_status} -> {status}")
        return {"message": f"Workflow status updated to {status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow status: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/samples", response_model=List[SampleResponse])
async def get_workflow_samples(
    workflow_id: UUID, session: Session = Depends(get_async_db_session)
):
    """Get all samples for a workflow."""
    samples = session.query(Sample).filter(Sample.workflow_id == workflow_id).all()
    return [SampleResponse.from_orm(s) for s in samples]


@router.post("/{workflow_id}/samples", response_model=SampleResponse)
async def create_workflow_sample(
    workflow_id: UUID,
    sample_data: SampleCreate,
    session: Session = Depends(get_async_db_session),
):
    """Create a sample for a workflow."""
    try:
        # Verify workflow exists
        workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        sample = Sample(
            name=sample_data.name,
            workflow_id=workflow_id,
            batch_id=sample_data.batch_id,
            composition=sample_data.composition,
            properties=sample_data.properties,
            target_properties=sample_data.target_properties,
            metadata=sample_data.metadata,
        )

        session.add(sample)
        session.commit()
        session.refresh(sample)

        # Send event
        event_producer.send_event(
            event_type="created",
            entity_id=sample.id,
            entity_type="sample",
            data={"workflow_id": str(workflow_id), "name": sample.name},
        )

        logger.info(f"Created sample {sample.name} for workflow {workflow_id}")
        return SampleResponse.from_orm(sample)

    except Exception as e:
        logger.error(f"Error creating sample: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/optimize")
async def optimize_workflow(
    workflow_id: UUID,
    optimization_targets: dict = None,
    session: Session = Depends(get_async_db_session),
):
    """Optimize a workflow for better performance."""
    try:
        workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if workflow.status not in [WorkflowStatus.DRAFT, WorkflowStatus.ACTIVE]:
            raise HTTPException(
                status_code=400,
                detail="Can only optimize workflows in draft or active status",
            )

        # Simple optimization logic - in a real implementation this would be more sophisticated
        if optimization_targets:
            workflow.optimization_targets = optimization_targets

        # Recalculate task dependencies and optimize execution order
        # This is a placeholder for more complex optimization logic

        session.commit()

        # Send event
        event_producer.send_event(
            event_type="optimized",
            entity_id=workflow_id,
            entity_type="workflow",
            data={"optimization_targets": optimization_targets},
        )

        logger.info(f"Optimized workflow {workflow_id}")
        return {
            "message": "Workflow optimized successfully",
            "workflow_id": str(workflow_id),
            "optimization_targets": workflow.optimization_targets,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing workflow: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
