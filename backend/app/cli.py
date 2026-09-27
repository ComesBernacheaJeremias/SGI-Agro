"""Comandos de administración.

Uso (desde la raíz del proyecto, en PowerShell o CMD):
    docker compose exec api python -m app.cli create-user
    docker compose exec api python -m app.cli seed-demo    (datos de ejemplo, base vacía)
"""

import argparse
import getpass
import sys

from app import demo
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.modules.identity.repository import RoleRepository
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


COMMANDS = {"create-user": create_user, "seed-demo": seed_demo}


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=COMMANDS)
    return COMMANDS[parser.parse_args().command]()


if __name__ == "__main__":
    sys.exit(main())
