---
tags: [desarrollo, calidad]
actualizado: 2026-09-27
---

# Definition of Done

Una historia de usuario está **terminada** cuando:

- [ ] Cumple sus criterios de aceptación (nota del módulo).
- [ ] Tiene tests de sus reglas de negocio y de sus endpoints, en verde.
- [ ] Pasa formato, lint y tipos.
- [ ] Incluye su migración (si cambia la base).
- [ ] Endpoints con permisos; entidades nuevas con historial.
- [ ] Sin código duplicado: lo común se movió a `core/` o `shared/`.
- [ ] UI en español; usable en celular si es pantalla de carga de campo.
- [ ] Nota del módulo actualizada (sección "Implementación"); ADR si hubo una decisión relevante.
- [ ] `.env.example` y README actualizados si cambió la configuración.
- [ ] Probado en local por el desarrollador.
- [ ] Comandos de git entregados al desarrollador; bitácora actualizada.
