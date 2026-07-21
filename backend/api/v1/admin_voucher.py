from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging
import csv
import io
import json

from database import get_db
from repositories.voucher_repository import VoucherRepository
from services.voucher_service import VoucherService
from utils.auth import get_current_admin
from utils.api_response import success, error
from utils.time_utils import get_utc_now, parse_iso_datetime
from models.voucher import Voucher, VoucherStatus

router = APIRouter(prefix="/api/admin/vouchers", tags=["Admin - Vouchers"])

logger = logging.getLogger(__name__)


def get_voucher_service(db: Session = Depends(get_db)):
    repo = VoucherRepository(db)
    return VoucherService(repository=repo)


class CreateVoucherSchema(BaseModel):
    minutes: int = Field(..., gt=0, le=525600, description="Duration in minutes (max 1 year)")
    expires_at: str | None = Field(None, description="Optional ISO 8601 expiration date")
    notes: str | None = Field(None, description="Optional administrative notes")


class CreateVouchersBulkSchema(BaseModel):
    count: int = Field(..., gt=0, le=10000, description="Number of vouchers to create")
    minutes: int = Field(..., gt=0, le=525600, description="Duration in minutes per voucher (max 1 year)")
    expires_at: str | None = Field(None, description="Optional ISO 8601 expiration date")
    notes: str | None = Field(None, description="Optional administrative notes")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_voucher(
    payload: CreateVoucherSchema | None = None,
    minutes: int | None = Query(None),
    expires_at: str | None = Query(None),
    notes: str | None = Query(None),
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Create a single voucher (supports JSON body or Query parameters)."""
    req_minutes = payload.minutes if payload else minutes
    req_expires_at = payload.expires_at if payload else expires_at
    req_notes = payload.notes if payload else notes

    if req_minutes is None or req_minutes <= 0:
        raise HTTPException(status_code=400, detail="Minutes must be positive")
    
    parsed_expires = None
    if req_expires_at:
        try:
            parsed_expires = parse_iso_datetime(req_expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO 8601 (e.g., 2026-12-31T23:59:59)")
    
    voucher = service.create_voucher(
        minutes=req_minutes,
        expires_at=parsed_expires,
        created_by=current_admin,
        notes=req_notes,
    )
    
    return success(data={
        "id": voucher.id,
        "code": voucher.code,
        "minutes": voucher.minutes,
        "status": voucher.status.value,
        "expires_at": voucher.expires_at.isoformat() if voucher.expires_at else None,
        "created_by": voucher.created_by,
        "notes": voucher.notes,
        "created_at": voucher.created_at.isoformat(),
    }, message="Voucher created successfully")


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_vouchers_bulk(
    payload: CreateVouchersBulkSchema | None = None,
    count: int | None = Query(None),
    minutes: int | None = Query(None),
    expires_at: str | None = Query(None),
    notes: str | None = Query(None),
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Create multiple vouchers in bulk (supports JSON body or Query parameters)."""
    req_count = payload.count if payload else count
    req_minutes = payload.minutes if payload else minutes
    req_expires_at = payload.expires_at if payload else expires_at
    req_notes = payload.notes if payload else notes

    if req_count is None or req_count <= 0:
        raise HTTPException(status_code=400, detail="Count must be positive")
    if req_count > 10000:
        raise HTTPException(status_code=400, detail="Maximum 10,000 vouchers per bulk operation")
    if req_minutes is None or req_minutes <= 0:
        raise HTTPException(status_code=400, detail="Minutes must be positive")
    
    parsed_expires = None
    if req_expires_at:
        try:
            parsed_expires = parse_iso_datetime(req_expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO 8601")
    
    vouchers = service.create_vouchers_bulk(
        count=req_count,
        minutes=req_minutes,
        expires_at=parsed_expires,
        created_by=current_admin,
        notes=req_notes,
    )
    
    return success(data={
        "created": len(vouchers),
        "requested": req_count,
        "vouchers": [
            {
                "id": v.id,
                "code": v.code,
                "minutes": v.minutes,
                "status": v.status.value,
                "expires_at": v.expires_at.isoformat() if v.expires_at else None,
                "created_by": v.created_by,
                "notes": v.notes,
                "created_at": v.created_at.isoformat(),
            }
            for v in vouchers
        ],
    }, message=f"{len(vouchers)} vouchers created successfully")


@router.get("")
def list_vouchers(
    status_filter: VoucherStatus | None = Query(None, description="Filter by voucher status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_at", pattern="^(id|code|minutes|status|expires_at|created_at|used_at)$"),
    order_desc: bool = Query(True),
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """List vouchers with pagination and filtering."""
    vouchers = service.list_vouchers(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_desc=order_desc,
    )
    
    total = service.count_vouchers(status_filter=status_filter)
    
    return success(data={
        "vouchers": [
            {
                "id": v.id,
                "code": v.code,
                "minutes": v.minutes,
                "status": v.status.value,
                "expires_at": v.expires_at.isoformat() if v.expires_at else None,
                "used_at": v.used_at.isoformat() if v.used_at else None,
                "used_by_client_id": v.used_by_client_id,
                "used_by_client_mac": v.used_by_client.mac_address if v.used_by_client else None,
                "created_by": v.created_by,
                "notes": v.notes,
                "created_at": v.created_at.isoformat(),
                "updated_at": v.updated_at.isoformat(),
            }
            for v in vouchers
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        },
    })


@router.get("/stats")
def get_voucher_stats(
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Get voucher statistics."""
    total = service.count_vouchers()
    unused = service.count_vouchers(VoucherStatus.UNUSED)
    used = service.count_vouchers(VoucherStatus.USED)
    expired = service.count_vouchers(VoucherStatus.EXPIRED)
    
    return success(data={
        "total": total,
        "unused": unused,
        "used": used,
        "expired": expired,
    })


@router.get("/export")
def export_vouchers(
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format: csv or json"),
    status_filter: VoucherStatus | None = Query(None, description="Filter by voucher status"),
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Export vouchers to CSV or JSON."""
    vouchers = service.list_vouchers(
        status_filter=status_filter,
        limit=10000,
        offset=0,
        order_by="created_at",
        order_desc=True,
    )
    
    now_str = get_utc_now().strftime('%Y%m%d_%H%M%S')
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "ID", "Code", "Minutes", "Status", 
            "Expires At", "Used At", "Used By Client ID", "Used By Client MAC",
            "Created By", "Notes", "Created At", "Updated At"
        ])
        
        for v in vouchers:
            writer.writerow([
                v.id,
                v.code,
                v.minutes,
                v.status.value,
                v.expires_at.isoformat() if v.expires_at else "",
                v.used_at.isoformat() if v.used_at else "",
                v.used_by_client_id or "",
                v.used_by_client.mac_address if v.used_by_client else "",
                v.created_by or "",
                v.notes or "",
                v.created_at.isoformat(),
                v.updated_at.isoformat(),
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        filename = f"vouchers_{now_str}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:  # JSON
        data = {
            "exported_at": get_utc_now().isoformat(),
            "exported_by": current_admin,
            "total": len(vouchers),
            "vouchers": [
                {
                    "id": v.id,
                    "code": v.code,
                    "minutes": v.minutes,
                    "status": v.status.value,
                    "expires_at": v.expires_at.isoformat() if v.expires_at else None,
                    "used_at": v.used_at.isoformat() if v.used_at else None,
                    "used_by_client_id": v.used_by_client_id,
                    "used_by_client_mac": v.used_by_client.mac_address if v.used_by_client else None,
                    "created_by": v.created_by,
                    "notes": v.notes,
                    "created_at": v.created_at.isoformat(),
                    "updated_at": v.updated_at.isoformat(),
                }
                for v in vouchers
            ]
        }
        
        filename = f"vouchers_{now_str}.json"
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/{voucher_id}")
def get_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Get a single voucher by ID."""
    voucher = service.get_voucher(voucher_id)
    
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    return success(data={
        "id": voucher.id,
        "code": voucher.code,
        "minutes": voucher.minutes,
        "status": voucher.status.value,
        "expires_at": voucher.expires_at.isoformat() if voucher.expires_at else None,
        "used_at": voucher.used_at.isoformat() if voucher.used_at else None,
        "used_by_client_id": voucher.used_by_client_id,
        "used_by_client_mac": voucher.used_by_client.mac_address if voucher.used_by_client else None,
        "created_by": voucher.created_by,
        "notes": voucher.notes,
        "created_at": voucher.created_at.isoformat(),
        "updated_at": voucher.updated_at.isoformat(),
    })


@router.delete("/{voucher_id}")
def delete_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Delete an unused voucher."""
    voucher = service.get_voucher(voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    if voucher.status == VoucherStatus.USED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a used voucher. Deletion is restricted to preserve financial audit history."
        )
    
    service.delete_voucher(voucher_id)
    logger.info("Voucher %d deleted by admin %s", voucher_id, current_admin)
    return success(message="Voucher deleted successfully")



@router.post("/{voucher_id}/expire")
def expire_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
    service: VoucherService = Depends(get_voucher_service),
):
    """Manually mark a voucher as expired."""
    voucher = service.get_voucher(voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    
    if voucher.status == VoucherStatus.USED:
        raise HTTPException(status_code=400, detail="Cannot expire an already used voucher")
    
    voucher.status = VoucherStatus.EXPIRED
    db.commit()
    logger.info("Voucher %d marked EXPIRED by admin %s", voucher_id, current_admin)
    return success(message="Voucher marked as expired")