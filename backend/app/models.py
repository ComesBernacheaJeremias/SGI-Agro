"""Registro de todos los modelos para Alembic.

Al crear un módulo con tablas, importar acá sus modelos para que las migraciones los detecten.
"""

from app.core.audit import AuditLog
from app.core.models import Base
from app.core.sequences import DocumentSequence
from app.modules.assets.models import (
    Asset,
    Maintenance,
    MaintenancePart,
    MaintenancePlan,
    MeterReading,
)
from app.modules.commercial.models import (
    Allocation,
    CashAccount,
    CashMovement,
    CommercialDocument,
    CommercialLine,
    ExpenseCategory,
    Payment,
    PaymentLine,
)
from app.modules.identity.models import Role, RolePermission, SessionToken, User
from app.modules.inventory.models import StockDocument, StockDocumentLine, StockMove
from app.modules.manufacturing.models import (
    ProductionOrder,
    ProductionOrderLine,
    Recipe,
    RecipeComponent,
)
from app.modules.masterdata.models import (
    Party,
    Product,
    ProductCategory,
    ProductUnitConversion,
    Unit,
    Warehouse,
)
from app.modules.production.models import (
    Batch,
    Crop,
    CropCycle,
    Farm,
    FieldOperation,
    FieldOperationAsset,
    FieldOperationCycle,
    FieldOperationInput,
    OperationType,
    Plot,
    Season,
)

__all__ = [
    "Allocation",
    "Asset",
    "AuditLog",
    "Base",
    "Batch",
    "CashAccount",
    "CashMovement",
    "CommercialDocument",
    "CommercialLine",
    "Crop",
    "CropCycle",
    "DocumentSequence",
    "ExpenseCategory",
    "Farm",
    "FieldOperation",
    "FieldOperationAsset",
    "FieldOperationCycle",
    "FieldOperationInput",
    "Maintenance",
    "MaintenancePart",
    "MaintenancePlan",
    "MeterReading",
    "OperationType",
    "Party",
    "Payment",
    "PaymentLine",
    "Plot",
    "Product",
    "ProductCategory",
    "ProductUnitConversion",
    "ProductionOrder",
    "ProductionOrderLine",
    "Recipe",
    "RecipeComponent",
    "Role",
    "RolePermission",
    "Season",
    "SessionToken",
    "StockDocument",
    "StockDocumentLine",
    "StockMove",
    "Unit",
    "User",
    "Warehouse",
]
