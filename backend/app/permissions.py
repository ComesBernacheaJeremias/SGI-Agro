"""Registro de los permisos de todos los módulos (se cargan al iniciar la app).

Al crear un módulo con permisos, importar acá su `permissions.py`.
"""

from app.modules.assets import permissions as assets_permissions
from app.modules.commercial import permissions as commercial_permissions
from app.modules.costs import permissions as costs_permissions
from app.modules.identity import permissions as identity_permissions
from app.modules.inventory import permissions as inventory_permissions
from app.modules.manufacturing import permissions as manufacturing_permissions
from app.modules.masterdata import permissions as masterdata_permissions
from app.modules.production import permissions as production_permissions

__all__ = [
    "assets_permissions",
    "commercial_permissions",
    "costs_permissions",
    "identity_permissions",
    "inventory_permissions",
    "manufacturing_permissions",
    "masterdata_permissions",
    "production_permissions",
]
