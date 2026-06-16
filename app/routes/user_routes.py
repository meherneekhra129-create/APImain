"""
User management routes — restricted to the ``owner`` role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, hash_password, require_role
from app.database import get_db
from app.models import Admin
from app.schemas import UserCreateRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["User Management"])


@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    current_user: Admin = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new admin or moderator account.

    Only users with the ``owner`` role may create new accounts.
    The ``owner`` role itself cannot be assigned via this endpoint.
    """
    # Check for duplicate username
    result = await db.execute(select(Admin).where(Admin.username == body.username))
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' is already taken.",
        )

    new_user = Admin(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        created_by=current_user.username,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.get("/list", response_model=list[UserResponse])
async def list_users(
    current_user: Admin = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List every admin/moderator account in the system."""
    result = await db.execute(select(Admin).order_by(Admin.id))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.delete("/delete/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    current_user: Admin = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an admin/moderator account by ID.

    Restrictions:
    - Cannot delete your own account.
    - Cannot delete another ``owner``.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    result = await db.execute(select(Admin).where(Admin.id == user_id))
    target = result.scalars().first()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if target.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another owner account.",
        )

    await db.delete(target)
    await db.flush()

    return {"message": f"User '{target.username}' deleted successfully."}


@router.put("/update/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    current_user: Admin = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update an admin/moderator's role or reset their password.

    Restrictions:
    - Cannot change your own role.
    - Cannot modify another ``owner``.
    """
    result = await db.execute(select(Admin).where(Admin.id == user_id))
    target = result.scalars().first()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if target.role == "owner" and target.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another owner account.",
        )

    if body.role is not None:
        if target.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role.",
            )
        target.role = body.role

    if body.password is not None:
        target.hashed_password = hash_password(body.password)

    db.add(target)
    await db.flush()
    await db.refresh(target)

    return UserResponse.model_validate(target)
