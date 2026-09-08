from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import MemberCreateRequest, UserRead


router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: MemberCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> User:
    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can create members",
        )

    if payload.role == UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create another owner through this endpoint",
        )

    existing_user = await db.scalar(
        select(User).where(User.email == payload.email.lower())
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    member = User(
        organization_id=current_user.organization_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )

    db.add(member)
    await db.commit()
    await db.refresh(member)

    return member