from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, status

from app.core.crud import ListQuery
from app.core.db import DbSession
from app.core.pagination import Page, Pagination
from app.modules.identity.authorization import require
from app.modules.identity.models import User
from app.modules.identity.permissions import USERS_MANAGE, USERS_READ
from app.modules.identity.schemas import ResetPasswordRequest, UserCreate, UserOut, UserUpdate
from app.modules.identity.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])

Reader = Annotated[User, require(USERS_READ)]
Manager = Annotated[User, require(USERS_MANAGE)]


@router.get("")
def list_users(db: DbSession, _: Reader, params: ListQuery, page: Pagination) -> Page[UserOut]:
    items, total = UserService(db).search(params, page)
    return Page(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


@router.get("/{id_}")
def get_user(id_: UUID, db: DbSession, _: Reader) -> UserOut:
    return UserOut.model_validate(UserService(db).get(id_))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: DbSession, actor: Manager) -> UserOut:
    return UserOut.model_validate(UserService(db, actor).create(body))


@router.patch("/{id_}")
def update_user(id_: UUID, body: UserUpdate, db: DbSession, actor: Manager) -> UserOut:
    return UserOut.model_validate(UserService(db, actor).update(id_, body))


@router.post("/{id_}/deactivate")
def deactivate_user(id_: UUID, db: DbSession, actor: Manager) -> UserOut:
    return UserOut.model_validate(UserService(db, actor).set_active(id_, active=False))


@router.post("/{id_}/activate")
def activate_user(id_: UUID, db: DbSession, actor: Manager) -> UserOut:
    return UserOut.model_validate(UserService(db, actor).set_active(id_, active=True))


@router.post("/{id_}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(id_: UUID, body: ResetPasswordRequest, db: DbSession, actor: Manager) -> None:
    UserService(db, actor).reset_password(id_, body.password)
