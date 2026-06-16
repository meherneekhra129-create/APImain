"""
Authentication utilities: password hashing, JWT token management,
and FastAPI dependencies for role-based access control.
"""

from datetime import datetime, timedelta, timezone
from typing import Callable, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Admin

# ── Password hashing ───────────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return _pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a bcrypt hash."""
    return _pwd_ctx.verify(plain, hashed)


# ── JWT tokens ──────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"

_bearer_scheme = HTTPBearer()


def create_access_token(data: dict) -> str:
    """Create a signed JWT containing *data* plus an expiration claim.

    The token includes ``username``, ``role``, and ``exp`` claims.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT, returning its payload.

    Raises ``HTTPException 401`` if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependencies ────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """Decode the Bearer token and return the matching ``Admin`` row.

    Raises ``HTTPException 401`` when the token is missing, invalid,
    or the referenced user no longer exists.
    """
    payload = decode_access_token(credentials.credentials)
    username: str | None = payload.get("username")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'username' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(Admin).where(Admin.username == username))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str) -> Callable:
    """Return a FastAPI dependency that enforces role-based access.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_role("owner", "admin"))])
        async def admin_only():
            ...

    Or inject the user directly::

        @router.get("/admin-only")
        async def admin_only(user: Admin = Depends(require_role("owner"))):
            ...
    """

    async def _role_checker(
        current_user: Admin = Depends(get_current_user),
    ) -> Admin:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(roles)}. "
                       f"Your role is '{current_user.role}'.",
            )
        return current_user

    return _role_checker
