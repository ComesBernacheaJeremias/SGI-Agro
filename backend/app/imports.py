"""Registro de las importaciones desde Excel de todos los módulos (se cargan al iniciar).

Al sumar una importación, importar acá el `imports.py` de su módulo.
"""

from app.modules.commercial import imports as commercial_imports
from app.modules.inventory import imports as inventory_imports
from app.modules.masterdata import imports as masterdata_imports

__all__ = ["commercial_imports", "inventory_imports", "masterdata_imports"]
