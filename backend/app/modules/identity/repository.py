from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.crud import CrudRepository
from app.core.repository import BaseRepository
from app.modules.identity.models import Role, SessionToken, User


class UserRepository(CrudRepository[User]):
    model = User
    search_fields = ("username", "full_name")
    default_sort = "full_name"

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(
            select(User).where(func.lower(User.username) == username.strip().lower())
        )

    def count_by_role(self, role_id: UUID) -> int:
        return self.session.scalar(select(func.count()).where(User.role_id == role_id)) or 0


class RoleRepository(CrudRepository[Role]):
    model = Role
    search_fields = ("name",)

    def get_by_code(self, code: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.code == code))

    def list_all(self) -> list[Role]:
        return list(self.session.scalars(select(Role).order_by(Role.name)))


class SessionTokenRepository(BaseRepository[SessionToken]):
    model = SessionToken

    def get_by_hash(self, token_hash: str) -> SessionToken | None:
        return self.session.scalar(
            select(SessionToken).where(SessionToken.token_hash == token_hash)
        )

    def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        self.session.execute(
            update(SessionToken)
            .where(SessionToken.user_id == user_id, SessionToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
