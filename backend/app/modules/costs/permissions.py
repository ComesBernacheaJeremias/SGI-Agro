from app.core.permissions import define_permission

COSTS_READ = define_permission(
    "costs:read", "Costos y rentabilidad", "Ver costos, rentabilidad y resultado de gestión"
)
