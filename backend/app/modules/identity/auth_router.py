from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from app.core.config import get_settings
from app.core.db import DbSession
from app.core.errors import UnauthorizedError
from app.core.security import hash_session_token
from app.modules.identity.auth_service import INVALID_SESSION, AuthResult, AuthService
from app.modules.identity.authorization import effective_permissions
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MeOut,
    TokenResponse,
    UserOut,
)
from app.modules.identity.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SESSION_COOKIE = "sgi_session"
SESSION_COOKIE_PATH = "/api/v1/auth"  # la cookie solo viaja a los endpoints de sesión

SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


def me_out(user: User) -> MeOut:
    return MeOut(
        **UserOut.model_validate(user).model_dump(),
        permissions=sorted(effective_permissions(user.role)),
    )


def _session_response(response: Response, result: AuthResult) -> TokenResponse:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        result.session_token,
        max_age=settings.refresh_token_days * 24 * 3600,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
    )
    return TokenResponse(access_token=result.access_token, user=me_out(result.user))


@router.post("/login")
def login(body: LoginRequest, db: DbSession, request: Request, response: Response) -> TokenResponse:
    result = AuthService(db).login(
        body.username,
        body.password,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return _session_response(response, result)


@router.post("/refresh")
def refresh(
    db: DbSession, response: Response, session_token: SessionCookie = None
) -> TokenResponse:
    if not session_token:
        raise UnauthorizedError(INVALID_SESSION, code="INVALID_SESSION")
    result = AuthService(db).refresh(session_token)
    return _session_response(response, result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: DbSession, response: Response, session_token: SessionCookie = None) -> None:
    if session_token:
        AuthService(db).logout(session_token)
    response.delete_cookie(SESSION_COOKIE, path=SESSION_COOKIE_PATH)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user: CurrentUser, db: DbSession, response: Response) -> None:
    AuthService(db).logout_all(user)
    response.delete_cookie(SESSION_COOKIE, path=SESSION_COOKIE_PATH)


@router.get("/me")
def me(user: CurrentUser) -> MeOut:
    return me_out(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    db: DbSession,
    session_token: SessionCookie = None,
) -> None:
    UserService(db, actor=user).change_own_password(
        user,
        body.current_password,
        body.new_password,
        keep_session_hash=hash_session_token(session_token) if session_token else None,
    )
