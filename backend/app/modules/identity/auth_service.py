"""Casos de uso de autenticación: login, renovar sesión, logout y cambio de contraseña."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import TooManyRequestsError, UnauthorizedError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_session_token,
    hash_session_token,
    verify_password,
)
from app.modules.identity.models import LoginEvent, LoginResult, SessionToken, User
from app.modules.identity.repository import SessionTokenRepository, UserRepository

INVALID_CREDENTIALS = "Usuario o contraseña incorrectos."
INVALID_SESSION = "La sesión venció o no es válida. Volvé a ingresar."


@dataclass(frozen=True)
class AuthResult:
    user: User
    access_token: str
    session_token: str


class AuthService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.users = UserRepository(session)
        self.tokens = SessionTokenRepository(session)

    # --- Sesión ---

    def login(
        self,
        username: str,
        password: str,
        now: datetime | None = None,
        *,
        ip: str = "",
        user_agent: str = "",
    ) -> AuthResult:
        now = now or datetime.now(UTC)
        attempt = LoginEvent(username=username[:50], ip=ip[:45], user_agent=user_agent[:200])

        if ip and self._ip_blocked(ip, now):
            self._record(attempt, LoginResult.BLOCKED_IP, None)
            raise TooManyRequestsError(
                "Demasiados intentos fallidos desde esta conexión. Esperá unos minutos.",
                code="TOO_MANY_ATTEMPTS",
            )

        user = self.users.get_by_username(username)
        if user is None:
            verify_password(DUMMY_PASSWORD_HASH, password)  # mismo tiempo que un usuario real
            self._record(attempt, LoginResult.FAILED, None)
            raise UnauthorizedError(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

        if user.locked_until and user.locked_until > now:
            minutes = max(1, round((user.locked_until - now).total_seconds() / 60))
            self._record(attempt, LoginResult.LOCKED, user)
            raise UnauthorizedError(
                f"Cuenta bloqueada por intentos fallidos. Probá de nuevo en {minutes} minuto(s).",
                code="ACCOUNT_LOCKED",
            )

        if not verify_password(user.password_hash, password) or not user.is_active:
            self.session.add(self._event(attempt, LoginResult.FAILED, user))
            self._register_failed_attempt(user, now)
            raise UnauthorizedError(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        self.session.add(self._event(attempt, LoginResult.SUCCESS, user))
        return self._start_session(user, now)

    # --- Registro de accesos y tope por IP ---

    @staticmethod
    def _event(attempt: LoginEvent, result: LoginResult, user: User | None) -> LoginEvent:
        attempt.result = result
        attempt.user_id = user.id if user else None
        return attempt

    def _record(self, attempt: LoginEvent, result: LoginResult, user: User | None) -> None:
        """Guarda el intento aunque la operación termine en error."""
        self.session.add(self._event(attempt, result, user))
        self._persist_security_state()

    def _ip_blocked(self, ip: str, now: datetime) -> bool:
        since = now - timedelta(minutes=self.settings.login_ip_window_minutes)
        failures = self.session.scalar(
            select(func.count()).where(
                LoginEvent.ip == ip,
                LoginEvent.created_at >= since,
                LoginEvent.result.in_([LoginResult.FAILED, LoginResult.LOCKED]),
            )
        )
        return (failures or 0) >= self.settings.login_ip_max_attempts

    def refresh(self, session_token: str, now: datetime | None = None) -> AuthResult:
        """Renueva la sesión rotando el token: el usado queda revocado."""
        now = now or datetime.now(UTC)
        stored = self.tokens.get_by_hash(hash_session_token(session_token))
        if stored is None:
            raise UnauthorizedError(INVALID_SESSION, code="INVALID_SESSION")

        if stored.revoked_at is not None:
            # Un token ya usado vuelve a aparecer: posible robo → se cierran todas las sesiones.
            self.tokens.revoke_all_for_user(stored.user_id, now)
            self._persist_security_state()
            raise UnauthorizedError(INVALID_SESSION, code="INVALID_SESSION")

        user = self.users.get(stored.user_id)
        if stored.expires_at <= now or user is None or not user.is_active:
            raise UnauthorizedError(INVALID_SESSION, code="INVALID_SESSION")

        stored.revoked_at = now
        return self._start_session(user, now)

    def logout(self, session_token: str, now: datetime | None = None) -> None:
        stored = self.tokens.get_by_hash(hash_session_token(session_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = now or datetime.now(UTC)

    def logout_all(self, user: User, now: datetime | None = None) -> None:
        self.tokens.revoke_all_for_user(user.id, now or datetime.now(UTC))

    # --- Internos ---

    def _start_session(self, user: User, now: datetime) -> AuthResult:
        token = generate_session_token()
        self.tokens.add(
            SessionToken(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=now + timedelta(days=self.settings.refresh_token_days),
            )
        )
        return AuthResult(
            user=user, access_token=create_access_token(user.id, now), session_token=token
        )

    def _register_failed_attempt(self, user: User, now: datetime) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=self.settings.login_lock_minutes)
            user.failed_login_attempts = 0
        self._persist_security_state()

    def _persist_security_state(self) -> None:
        # Excepción deliberada a "el service no hace commit": los intentos fallidos y las
        # revocaciones deben quedar guardados aunque la operación termine en error (que revierte).
        self.session.commit()
