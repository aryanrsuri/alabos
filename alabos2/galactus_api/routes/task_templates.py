"""Task template API routes for alabos."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.connection import get_async_db_session
from ...models.task import (
    TaskTemplate,
    TaskTemplateCreate,
    TaskTemplateResponse,
    TaskTemplateStatus,
    TaskTemplateInput,
    TaskTemplateOutput,
)
from ...events.producer import event_producer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TaskTemplateResponse)
async def create_task_template(
    template_data: TaskTemplateCreate, session: Session = Depends(get_async_db_session)
):
    """Create a new task template."""
    try:
        # Create task template
        template = TaskTemplate(
            name=template_data.name,
            description=template_data.description,
            version="1.0.0",
            status=TaskTemplateStatus.ACTIVE,
            category=template_data.category,
            input_schema=template_data.input_schema,
            output_schema=template_data.output_schema,
            parameter_schema=template_data.parameter_schema,
            required_device_types=template_data.required_device_types,
            preferred_device_types=template_data.preferred_device_types,
            estimated_duration=template_data.estimated_duration,
            max_retries=template_data.max_retries,
            retry_delay=template_data.retry_delay,
            timeout=template_data.timeout,
            requires_user_input=template_data.requires_user_input,
            implementation_class=template_data.implementation_class,
            docker_image=template_data.docker_image,
            metadata=template_data.metadata,
        )

        session.add(template)
        session.commit()
        session.refresh(template)

        # Send event
        event_producer.send_event(
            event_type="created",
            entity_id=template.id,
            entity_type="task_template",
            data={"name": template.name, "category": template.category},
        )

        logger.info(f"Created task template: {template.name}")
        return TaskTemplateResponse.from_orm(template)

    except Exception as e:
        logger.error(f"Error creating task template: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[TaskTemplateResponse])
async def list_task_templates(
    category: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_async_db_session),
):
    """List all task templates with optional filtering."""
    query = session.query(TaskTemplate)

    if category:
        query = query.filter(TaskTemplate.category == category)
    if status:
        query = query.filter(TaskTemplate.status == status)

    templates = query.offset(skip).limit(limit).all()
    return [TaskTemplateResponse.from_orm(t) for t in templates]


@router.get("/{template_id}", response_model=TaskTemplateResponse)
async def get_task_template(
    template_id: UUID, session: Session = Depends(get_async_db_session)
):
    """Get a specific task template."""
    template = (
        session.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")

    return TaskTemplateResponse.from_orm(template)


@router.put("/{template_id}", response_model=TaskTemplateResponse)
async def update_task_template(
    template_id: UUID,
    template_data: TaskTemplateCreate,
    session: Session = Depends(get_async_db_session),
):
    """Update a task template."""
    try:
        template = (
            session.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Task template not found")

        # Update fields
        update_data = template_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(template, field):
                setattr(template, field, value)

        template.updated_at = template.updated_at  # Trigger update
        session.commit()
        session.refresh(template)

        # Send event
        event_producer.send_event(
            event_type="updated",
            entity_id=template.id,
            entity_type="task_template",
            data={"name": template.name},
        )

        logger.info(f"Updated task template: {template.name}")
        return TaskTemplateResponse.from_orm(template)

    except Exception as e:
        logger.error(f"Error updating task template: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}")
async def delete_task_template(
    template_id: UUID, session: Session = Depends(get_async_db_session)
):
    """Delete a task template."""
    try:
        template = (
            session.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Task template not found")

        # Check if template is in use
        if template.tasks:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete template with {len(template.tasks)} associated tasks",
            )

        session.delete(template)
        session.commit()

        # Send event
        event_producer.send_event(
            event_type="deleted",
            entity_id=template_id,
            entity_type="task_template",
            data={"name": template.name},
        )

        logger.info(f"Deleted task template: {template.name}")
        return {"message": "Task template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task template: {e}")
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/validate")
async def validate_task_template(
    template_id: UUID, inputs: dict, session: Session = Depends(get_async_db_session)
):
    """Validate inputs against a task template schema."""
    try:
        template = (
            session.query(TaskTemplate).filter(TaskTemplate.id == template_id).first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Task template not found")

        # Basic validation - in a real implementation, use a proper JSON schema validator
        validation_errors = []

        # Check required inputs
        for input_name, input_config in template.input_schema.items():
            if input_config.get("required", True) and input_name not in inputs:
                validation_errors.append(f"Missing required input: {input_name}")

        # Type validation (simplified)
        for input_name, value in inputs.items():
            if input_name in template.input_schema:
                expected_type = template.input_schema[input_name].get("type", "string")
                if expected_type == "number" and not isinstance(value, (int, float)):
                    validation_errors.append(f"Input {input_name} should be a number")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    validation_errors.append(f"Input {input_name} should be a boolean")

        if validation_errors:
            raise HTTPException(
                status_code=400, detail={"validation_errors": validation_errors}
            )

        return {
            "valid": True,
            "message": "Inputs are valid for this template",
            "template_id": str(template_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating task template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
