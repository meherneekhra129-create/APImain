"""
Authentication routes: login, current-user info, and password change.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import Admin
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Accepts a username/password pair, verifies the credentials against the
    database, and returns a signed JWT containing the user's role.
    """
    result = await db.execute(select(Admin).where(Admin.username == body.username))
    user = result.scalars().first()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token({"username": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: Admin = Depends(get_current_user)) -> UserResponse:
    """Return profile information for the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.put("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: Admin = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the current user's password.

    Requires the correct current password before accepting the new one.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters.",
        )

    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    await db.flush()

    return {"message": "Password changed successfully."}
