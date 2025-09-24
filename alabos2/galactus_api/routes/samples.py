"""Sample API routes for alabos."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.connection import get_async_db_session
from ...models.workflow import Sample, SampleResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[SampleResponse])
async def list_samples(
    workflow_id: UUID = None,
    batch_id: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_async_db_session),
):
    """List samples with optional filtering."""
    query = session.query(Sample)

    if workflow_id:
        query = query.filter(Sample.workflow_id == workflow_id)
    if batch_id:
        query = query.filter(Sample.batch_id == batch_id)
    if status:
        query = query.filter(Sample.status == status)

    samples = query.offset(skip).limit(limit).all()
    return [SampleResponse.from_orm(s) for s in samples]


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(sample_id: UUID, session: Session = Depends(get_async_db_session)):
    """Get a specific sample."""
    sample = session.query(Sample).filter(Sample.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    return SampleResponse.from_orm(sample)
