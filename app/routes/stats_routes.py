"""
Statistics endpoint — returns aggregate counts about keys and users.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Admin, LicenseKey
from app.schemas import StatsResponse

router = APIRouter(prefix="/api", tags=["Statistics"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """Return high-level statistics about the system.

    Counts total, active, expired, and revoked keys as well as the total
    number of admin users and cumulative validation count.
    """
    now = datetime.now(timezone.utc)

    # Total keys
    total_keys_q = await db.execute(select(func.count(LicenseKey.id)))
    total_keys = total_keys_q.scalar() or 0

    # Revoked keys
    revoked_q = await db.execute(
        select(func.count(LicenseKey.id)).where(LicenseKey.is_revoked == True)  # noqa: E712
    )
    revoked_keys = revoked_q.scalar() or 0

    # Expired keys (not revoked, has expiry in the past)
    expired_q = await db.execute(
        select(func.count(LicenseKey.id)).where(
            LicenseKey.is_revoked == False,  # noqa: E712
            LicenseKey.expires_at.isnot(None),
            LicenseKey.expires_at <= now,
        )
    )
    expired_keys = expired_q.scalar() or 0

    # Active keys (not revoked, not expired)
    active_q = await db.execute(
        select(func.count(LicenseKey.id)).where(
            LicenseKey.is_revoked == False,  # noqa: E712
            or_(LicenseKey.expires_at.is_(None), LicenseKey.expires_at > now),
        )
    )
    active_keys = active_q.scalar() or 0

    # Total users
    users_q = await db.execute(select(func.count(Admin.id)))
    total_users = users_q.scalar() or 0

    # Total validations
    validations_q = await db.execute(
        select(func.coalesce(func.sum(LicenseKey.validation_count), 0))
    )
    total_validations = validations_q.scalar() or 0

    return StatsResponse(
        total_keys=total_keys,
        active_keys=active_keys,
        expired_keys=expired_keys,
        revoked_keys=revoked_keys,
        total_users=total_users,
        total_validations=total_validations,
    )
