from app.core.permissions import define_permission

GROUP = "Comercial"
CASH_GROUP = "Caja y bancos"

COMMERCIAL_READ = define_permission(
    "commercial:read", GROUP, "Ver compras, ventas y cuentas corrientes"
)
COMMERCIAL_WRITE = define_permission(
    "commercial:write", GROUP, "Cargar y editar compras, ventas, cobros y pagos"
)
COMMERCIAL_CANCEL = define_permission(
    "commercial:cancel", GROUP, "Anular comprobantes, cobros y pagos"
)
CASH_READ = define_permission("cash:read", CASH_GROUP, "Ver cajas, bancos y saldos")
CASH_WRITE = define_permission("cash:write", CASH_GROUP, "Cargar movimientos y configurar cuentas")
