"""
Public license-key validation endpoint (no authentication required).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import LicenseKey
from app.schemas import ValidateRequest, ValidateResponse

router = APIRouter(prefix="/api", tags=["Validation"])


@router.post("/validate", response_model=ValidateResponse)
async def validate_key(
    body: ValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> ValidateResponse:
    """Validate a license key (public — no authentication required).

    Workflow:
    1. Look up the key in the database.
    2. Reject if revoked.
    3. Reject if expired.
    4. If an HWID is provided and the key has no HWID yet, bind it.
    5. If an HWID is provided and the key already has one, verify it matches.
    6. Update ``last_validated`` and increment ``validation_count``.
    7. Return a ``ValidateResponse``.
    """
    result = await db.execute(
        select(LicenseKey).where(LicenseKey.key == body.license_key)
    )
    key_obj = result.scalars().first()

    if key_obj is None:
        return ValidateResponse(
            valid=False,
            message="License key not found.",
            status="invalid",
        )

    # Revoked?
    if key_obj.is_revoked:
        return ValidateResponse(
            valid=False,
            message="This license key has been revoked.",
            expires_at=key_obj.expires_at,
            status="revoked",
        )

    # Expired?
    now = datetime.now(timezone.utc)
    if key_obj.expires_at is not None:
        exp = (
            key_obj.expires_at
            if key_obj.expires_at.tzinfo
            else key_obj.expires_at.replace(tzinfo=timezone.utc)
        )
        if exp < now:
            return ValidateResponse(
                valid=False,
                message="This license key has expired.",
                expires_at=key_obj.expires_at,
                status="expired",
            )

    # HWID check / binding
    if body.hwid:
        if key_obj.hwid is None:
            # First-time binding
            key_obj.hwid = body.hwid
        elif key_obj.hwid != body.hwid:
            return ValidateResponse(
                valid=False,
                message="Hardware ID mismatch. This key is bound to a different device.",
                expires_at=key_obj.expires_at,
                status="hwid_mismatch",
            )

    # Record validation
    key_obj.last_validated = now
    key_obj.validation_count += 1
    db.add(key_obj)
    await db.flush()

    return ValidateResponse(
        valid=True,
        message="License key is valid.",
        expires_at=key_obj.expires_at,
        status="active",
    )
