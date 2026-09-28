"""Comandos de administración.

Uso (desde la raíz del proyecto, en PowerShell o CMD):
    docker compose exec api python -m app.cli create-user
    docker compose exec api python -m app.cli seed-demo    (datos de ejemplo, base vacía)
En producción, desde deploy/: docker compose -f docker-compose.prod.yml exec api python -m app.cli …
Usuarios: create-user · list-users · reset-password · deactivate-user · activate-user ·
revoke-sessions. Los usuarios no se borran: se desactivan (el historial conserva quién hizo qué).
"""

import argparse
import getpass
import sys
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import demo
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.modules.identity.models import User
from app.modules.identity.repository import RoleRepository, UserRepository
from app.modules.identity.schemas import UserCreate
from app.modules.identity.user_service import UserService

has_data = demo.has_data


def create_user() -> int:
    with SessionLocal() as session:
        roles = {role.code: role for role in RoleRepository(session).list_all()}
        print("Roles: " + ", ".join(f"{code} ({role.name})" for code, role in roles.items()))
        role = roles.get(input("Rol: ").strip())
        if role is None:
            print("Ese rol no existe.", file=sys.stderr)
            return 1
        username = input("Usuario: ").strip()
        full_name = input("Nombre completo: ").strip()
        password = getpass.getpass("Contraseña (mínimo 10 caracteres): ")
        if password != getpass.getpass("Repetir contraseña: "):
            print("Las contraseñas no coinciden.", file=sys.stderr)
            return 1
        try:
            data = UserCreate(
                username=username, full_name=full_name, role_id=role.id, password=password
            )
            user = UserService(session).create(data)
            session.commit()
        except AppError as error:
            print(error.message, file=sys.stderr)
            return 1
        except ValueError as error:  # validación de datos (campos vacíos, largos)
            print(f"Datos inválidos: {error}", file=sys.stderr)
            return 1
        print(f"Usuario '{user.username}' creado con rol {role.name}.")
    return 0


def seed_demo() -> int:
    """Datos de ejemplo para mostrar el sistema (solo en una base vacía, nunca en producción)."""
    if get_settings().is_production:
        print("No se cargan datos de ejemplo en producción.", file=sys.stderr)
        return 1
    with SessionLocal() as session:
        if has_data(session):
            print(
                "La base ya tiene datos: los datos de ejemplo van en una base vacía.",
                file=sys.stderr,
            )
            return 1
        demo.seed_demo(session)
        session.commit()
    print("Datos de ejemplo cargados. Creá un usuario con: python -m app.cli create-user")
    return 0


def _find_user(session: Session) -> User | None:
    username = input("Usuario: ").strip()
    user = UserRepository(session).get_by_username(username)
    if user is None:
        print(f"No existe el usuario '{username}'.", file=sys.stderr)
    return user


def list_users() -> int:
    with SessionLocal() as session:
        users = session.scalars(select(User).order_by(User.username)).all()
        tz = get_settings().tzinfo
        print(f"{'USUARIO':<20} {'NOMBRE':<28} {'ROL':<14} {'ESTADO':<10} ÚLTIMO INGRESO")
        for u in users:
            state = "activo" if u.is_active else "inactivo"
            if u.locked_until and u.locked_until > datetime.now(UTC):
                state = "bloqueado"
            last = (
                u.last_login_at.astimezone(tz).strftime("%d/%m/%Y %H:%M")
                if u.last_login_at
                else "-"
            )
            print(f"{u.username:<20} {u.full_name[:27]:<28} {u.role.name:<14} {state:<10} {last}")
    return 0


def reset_password() -> int:
    """Contraseña nueva para un usuario (también lo desbloquea y cierra sus sesiones)."""
    with SessionLocal() as session:
        user = _find_user(session)
        if user is None:
            return 1
        password = getpass.getpass("Contraseña nueva (mínimo 10 caracteres): ")
        if password != getpass.getpass("Repetir contraseña: "):
            print("Las contraseñas no coinciden.", file=sys.stderr)
            return 1
        try:
            UserService(session).reset_password(user.id, password)
            session.commit()
        except AppError as error:
            print(error.message, file=sys.stderr)
            return 1
        print(f"Contraseña de '{user.username}' cambiada; se cerraron sus sesiones.")
    return 0


def _set_active(active: bool) -> int:
    with SessionLocal() as session:
        user = _find_user(session)
        if user is None:
            return 1
        UserService(session).set_active(user.id, active)
        session.commit()
        print(f"Usuario '{user.username}' {'reactivado' if active else 'desactivado'}.")
    return 0


def revoke_sessions() -> int:
    with SessionLocal() as session:
        user = _find_user(session)
        if user is None:
            return 1
        UserService(session).revoke_sessions(user.id)
        session.commit()
        print(f"Se cerraron todas las sesiones de '{user.username}'.")
    return 0


COMMANDS = {
    "create-user": create_user,
    "list-users": list_users,
    "reset-password": reset_password,
    "deactivate-user": lambda: _set_active(False),
    "activate-user": lambda: _set_active(True),
    "revoke-sessions": revoke_sessions,
    "seed-demo": seed_demo,
}


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=COMMANDS)
    return COMMANDS[parser.parse_args().command]()


if __name__ == "__main__":
    sys.exit(main())
