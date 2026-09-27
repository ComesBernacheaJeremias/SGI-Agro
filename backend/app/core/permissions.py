"""Registro de permisos del sistema.

Cada módulo declara sus permisos en su `permissions.py` con `define_permission(...)` y los usa
como constantes en sus routers (así un typo es un error de Python, no un permiso inexistente).
Formato del código: `modulo:accion` (ej. `masterdata:create`).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Permission:
    code: str
    group: str  # nombre del módulo para mostrar ("Maestros")
    label: str  # acción para mostrar ("Crear")
    support_only: bool = False  # solo el rol soporte (ej. reabrir ciclos)

    @property
    def is_read(self) -> bool:
        return self.code.endswith(":read")


_registry: dict[str, Permission] = {}


def define_permission(
    code: str, group: str, label: str, *, support_only: bool = False
) -> Permission:
    if code in _registry:
        raise ValueError(f"Permiso duplicado: {code}")
    permission = Permission(code, group, label, support_only)
    _registry[code] = permission
    return permission


def all_permissions() -> list[Permission]:
    return list(_registry.values())


def is_defined(code: str) -> bool:
    return code in _registry
