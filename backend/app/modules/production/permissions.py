from app.core.permissions import define_permission

GROUP = "Producción"

PRODUCTION_READ = define_permission("production:read", GROUP, "Ver")
PRODUCTION_WRITE = define_permission("production:write", GROUP, "Cargar labores, cosechas y ciclos")
PRODUCTION_CONFIG = define_permission(
    "production:config", GROUP, "Configurar establecimientos, lotes, cultivos y tipos de labor"
)
PRODUCTION_REOPEN = define_permission(
    "production:reopen_cycle", GROUP, "Reabrir ciclos finalizados", support_only=True
)
