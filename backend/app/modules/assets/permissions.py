from app.core.permissions import define_permission

GROUP = "Activos"

ASSETS_READ = define_permission("assets:read", GROUP, "Ver")
ASSETS_WRITE = define_permission("assets:write", GROUP, "Crear y editar")
ASSETS_DEACTIVATE = define_permission("assets:deactivate", GROUP, "Desactivar y reactivar")
