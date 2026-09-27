from app.core.permissions import define_permission

GROUP = "Elaboración"

MANUFACTURING_READ = define_permission("manufacturing:read", GROUP, "Ver recetas y preparaciones")
MANUFACTURING_WRITE = define_permission(
    "manufacturing:write", GROUP, "Crear recetas y registrar preparaciones"
)
