from app.core.permissions import define_permission

GROUP = "Inventario"

INVENTORY_READ = define_permission("inventory:read", GROUP, "Ver stock y movimientos")
INVENTORY_WRITE = define_permission(
    "inventory:write", GROUP, "Cargar y editar ingresos, egresos y transferencias"
)
INVENTORY_CANCEL = define_permission("inventory:cancel", GROUP, "Anular comprobantes")
INVENTORY_ADJUST = define_permission("inventory:adjust", GROUP, "Hacer ajustes de inventario")
