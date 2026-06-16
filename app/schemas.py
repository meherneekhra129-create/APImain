"""
Pydantic schemas for request / response validation and serialisation.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ── Authentication ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Credentials submitted by a user to obtain a JWT token."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class ChangePasswordRequest(BaseModel):
    """Payload for changing the current user's password."""

    current_password: str
    new_password: str


# ── License Keys ────────────────────────────────────────────────────────────


class KeyGenerateRequest(BaseModel):
    """Parameters for batch-generating license keys."""

    quantity: int = Field(default=1, ge=1, le=100)
    expires_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    prefix: Optional[str] = Field(default="LIC", max_length=10)


class KeyResponse(BaseModel):
    """Serialised representation of a single license key."""

    id: int
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_revoked: bool
    hwid: Optional[str] = None
    notes: Optional[str] = None
    last_validated: Optional[datetime] = None
    validation_count: int
    created_by: Optional[str] = None
    status: str  # active | expired | revoked

    model_config = {"from_attributes": True}

    @staticmethod
    def compute_status(
        is_revoked: bool,
        expires_at: Optional[datetime],
    ) -> str:
        """Derive the human-readable status string for a key."""
        if is_revoked:
            return "revoked"
        if expires_at is not None:
            # Make both datetimes offset-aware for safe comparison
            now = datetime.now(timezone.utc)
            exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            if exp < now:
                return "expired"
        return "active"

    @classmethod
    def from_model(cls, model: object) -> "KeyResponse":
        """Build a KeyResponse from an ORM LicenseKey instance."""
        return cls(
            id=model.id,  # type: ignore[attr-defined]
            key=model.key,  # type: ignore[attr-defined]
            created_at=model.created_at,  # type: ignore[attr-defined]
            expires_at=model.expires_at,  # type: ignore[attr-defined]
            is_revoked=model.is_revoked,  # type: ignore[attr-defined]
            hwid=model.hwid,  # type: ignore[attr-defined]
            notes=model.notes,  # type: ignore[attr-defined]
            last_validated=model.last_validated,  # type: ignore[attr-defined]
            validation_count=model.validation_count,  # type: ignore[attr-defined]
            created_by=model.created_by,  # type: ignore[attr-defined]
            status=cls.compute_status(
                model.is_revoked,  # type: ignore[attr-defined]
                model.expires_at,  # type: ignore[attr-defined]
            ),
        )


class KeyListResponse(BaseModel):
    """Paginated list of license keys."""

    keys: list[KeyResponse]
    total: int
    page: int
    per_page: int


class KeyUpdateRequest(BaseModel):
    """Mutable fields on a license key."""

    expires_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=500)


# ── Validation (public) ────────────────────────────────────────────────────


class ValidateRequest(BaseModel):
    """Payload sent by a client application to validate a license key."""

    license_key: str
    hwid: Optional[str] = None


class ValidateResponse(BaseModel):
    """Result of a license key validation attempt."""

    valid: bool
    message: str
    expires_at: Optional[datetime] = None
    status: str


# ── User management ────────────────────────────────────────────────────────


class UserCreateRequest(BaseModel):
    """Payload for creating a new admin / moderator account."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    role: str = Field(pattern=r"^(admin|moderator)$")


class UserResponse(BaseModel):
    """Serialised admin user (no password hash)."""

    id: int
    username: str
    role: str
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Mutable fields on an admin user."""

    role: Optional[str] = Field(default=None, pattern=r"^(admin|moderator)$")
    password: Optional[str] = Field(default=None, min_length=6)


# ── Stats ───────────────────────────────────────────────────────────────────


class StatsResponse(BaseModel):
    """High-level statistics about the system."""

    total_keys: int
    active_keys: int
    expired_keys: int
    revoked_keys: int
    total_users: int
    total_validations: int
