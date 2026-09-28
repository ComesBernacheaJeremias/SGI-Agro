from app.core.permissions import define_permission

GROUP = "Producción"

PRODUCTION_READ = define_permission("production:read", GROUP, "Ver")
PRODUCTION_WRITE = define_permission(
    "production:write", GROUP, "Cargar labores, cosechas y cultivos"
)
PRODUCTION_CONFIG = define_permission(
    "production:config",
    GROUP,
    "Configurar establecimientos, lotes, tipos de cultivo y tipos de labor",
)
PRODUCTION_REOPEN = define_permission(
    "production:reopen_cycle", GROUP, "Reabrir cultivos finalizados", support_only=True
)
