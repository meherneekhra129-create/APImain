"""
License key CRUD routes: generate, list, revoke, delete, update.
"""

import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import Admin, LicenseKey
from app.schemas import (
    KeyGenerateRequest,
    KeyListResponse,
    KeyResponse,
    KeyUpdateRequest,
)

router = APIRouter(prefix="/api/keys", tags=["License Keys"])

_KEY_CHARS = string.ascii_uppercase + string.digits


def _generate_key(prefix: str) -> str:
    """Generate a single license key in the format ``PREFIX-XXXX-XXXX-XXXX-XXXX``.

    Uses ``secrets`` for cryptographically secure random selection.
    """
    groups = [
        "".join(secrets.choice(_KEY_CHARS) for _ in range(4))
        for _ in range(4)
    ]
    return f"{prefix.upper()}-{'-'.join(groups)}"


@router.post("/generate", response_model=list[KeyResponse], status_code=status.HTTP_201_CREATED)
async def generate_keys(
    body: KeyGenerateRequest,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KeyResponse]:
    """Generate one or more license keys.

    Any authenticated user can generate keys.  Each key is a
    cryptographically-random string in the format
    ``PREFIX-XXXX-XXXX-XXXX-XXXX`` (uppercase alphanumeric).
    """
    prefix = (body.prefix or "LIC").upper()
    created: list[LicenseKey] = []

    for _ in range(body.quantity):
        # Retry until we get a unique key (collision is astronomically unlikely)
        for _attempt in range(10):
            candidate = _generate_key(prefix)
            existing = await db.execute(
                select(LicenseKey).where(LicenseKey.key == candidate)
            )
            if existing.scalars().first() is None:
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate a unique key after multiple attempts.",
            )

        key_obj = LicenseKey(
            key=candidate,
            expires_at=body.expires_at,
            notes=body.notes,
            created_by=current_user.username,
        )
        db.add(key_obj)
        created.append(key_obj)

    await db.flush()
    for k in created:
        await db.refresh(k)

    return [KeyResponse.from_model(k) for k in created]


@router.get("/list", response_model=KeyListResponse)
async def list_keys(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(
        "all",
        alias="status",
        description="Filter: all, active, expired, revoked",
    ),
    search: Optional[str] = Query(None, description="Search in key or notes"),
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KeyListResponse:
    """List license keys with pagination, status filtering, and search.

    The ``status`` query parameter accepts ``all``, ``active``,
    ``expired``, or ``revoked``.  The ``search`` parameter performs a
    case-insensitive substring match against the key value and notes.
    """
    query = select(LicenseKey)
    count_query = select(func.count(LicenseKey.id))

    now = datetime.now(timezone.utc)

    # Status filter
    if status_filter == "active":
        query = query.where(
            LicenseKey.is_revoked == False,  # noqa: E712
            or_(LicenseKey.expires_at.is_(None), LicenseKey.expires_at > now),
        )
        count_query = count_query.where(
            LicenseKey.is_revoked == False,  # noqa: E712
            or_(LicenseKey.expires_at.is_(None), LicenseKey.expires_at > now),
        )
    elif status_filter == "expired":
        query = query.where(
            LicenseKey.is_revoked == False,  # noqa: E712
            LicenseKey.expires_at.isnot(None),
            LicenseKey.expires_at <= now,
        )
        count_query = count_query.where(
            LicenseKey.is_revoked == False,  # noqa: E712
            LicenseKey.expires_at.isnot(None),
            LicenseKey.expires_at <= now,
        )
    elif status_filter == "revoked":
        query = query.where(LicenseKey.is_revoked == True)  # noqa: E712
        count_query = count_query.where(LicenseKey.is_revoked == True)  # noqa: E712

    # Search
    if search:
        like_pattern = f"%{search}%"
        search_filter = or_(
            LicenseKey.key.ilike(like_pattern),
            LicenseKey.notes.ilike(like_pattern),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * per_page
    query = query.order_by(LicenseKey.id.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    keys = result.scalars().all()

    return KeyListResponse(
        keys=[KeyResponse.from_model(k) for k in keys],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.put("/revoke/{key}")
async def revoke_key(
    key: str,
    current_user: Admin = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a license key so it can no longer be validated.

    Requires ``owner`` or ``admin`` role.
    """
    result = await db.execute(select(LicenseKey).where(LicenseKey.key == key))
    license_key = result.scalars().first()
    if license_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License key not found.",
        )

    if license_key.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key is already revoked.",
        )

    license_key.is_revoked = True
    db.add(license_key)
    await db.flush()

    return {"message": f"Key '{key}' has been revoked."}


@router.delete("/delete/{key}", status_code=status.HTTP_200_OK)
async def delete_key(
    key: str,
    current_user: Admin = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Permanently delete a license key.

    Requires ``owner`` role.
    """
    result = await db.execute(select(LicenseKey).where(LicenseKey.key == key))
    license_key = result.scalars().first()
    if license_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License key not found.",
        )

    await db.delete(license_key)
    await db.flush()

    return {"message": f"Key '{key}' has been permanently deleted."}


@router.put("/update/{key}", response_model=KeyResponse)
async def update_key(
    key: str,
    body: KeyUpdateRequest,
    current_user: Admin = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> KeyResponse:
    """Update the expiration date or notes on a license key.

    Requires ``owner`` or ``admin`` role.
    """
    result = await db.execute(select(LicenseKey).where(LicenseKey.key == key))
    license_key = result.scalars().first()
    if license_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License key not found.",
        )

    if body.expires_at is not None:
        license_key.expires_at = body.expires_at
    if body.notes is not None:
        license_key.notes = body.notes

    db.add(license_key)
    await db.flush()
    await db.refresh(license_key)

    return KeyResponse.from_model(license_key)
