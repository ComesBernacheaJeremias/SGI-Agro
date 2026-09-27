from app.core.permissions import define_permission

GROUP = "Usuarios y roles"

USERS_READ = define_permission("users:read", GROUP, "Ver usuarios y roles")
USERS_MANAGE = define_permission("users:manage", GROUP, "Crear y editar usuarios y roles")
AUDIT_READ = define_permission("audit:read", "Historial", "Ver historial general")
