"""Registro de los reportes de todos los módulos (se cargan al iniciar la app).

Al crear un módulo con reportes, importar acá su `reports.py`.
"""

from app.modules.assets import reports as assets_reports
from app.modules.commercial import reports as commercial_reports
from app.modules.costs import reports as costs_reports
from app.modules.inventory import reports as inventory_reports

__all__ = ["assets_reports", "commercial_reports", "costs_reports", "inventory_reports"]
