from app.core.permissions import define_permission

GROUP = "Maestros"

MASTERDATA_READ = define_permission("masterdata:read", GROUP, "Ver")
MASTERDATA_WRITE = define_permission("masterdata:write", GROUP, "Crear y editar")
MASTERDATA_DEACTIVATE = define_permission("masterdata:deactivate", GROUP, "Desactivar y reactivar")
