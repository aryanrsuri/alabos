"""Device API routes for alabos."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.connection import get_async_db_session
from ...models.device import Device, DeviceCreate, DeviceResponse, DeviceStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    status: str = None,
    device_type_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_async_db_session),
):
    """List devices with optional filtering."""
    query = session.query(Device)

    if status:
        query = query.filter(Device.status == status)
    if device_type_id:
        query = query.filter(Device.device_type_id == device_type_id)

    devices = query.offset(skip).limit(limit).all()
    return [DeviceResponse.from_orm(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: UUID, session: Session = Depends(get_async_db_session)):
    """Get a specific device."""
    device = session.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return DeviceResponse.from_orm(device)
