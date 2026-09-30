#!/usr/bin/env bash
# Entorno local: levanta db, api y web y muestra los logs. Ctrl+C (o cerrar la terminal) lo apaga;
# los datos quedan en el volumen.
# Uso: ./dev.sh           levantar
#      ./dev.sh --build   reconstruir las imágenes antes (tras cambiar dependencias del backend o del frontend)
set -euo pipefail
cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker no está corriendo. Inicialo y volvé a probar." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Se creó .env a partir de .env.example (revisá los valores)."
fi
set -a; source .env; set +a

up_args=(-d)
case "${1:-}" in
  "") ;;
  --build) up_args+=(--build --renew-anon-volumes) ;;  # -V renueva el node_modules del contenedor web
  *) echo "Opción desconocida: $1 (usar --build o nada)" >&2; exit 1 ;;
esac

docker compose up "${up_args[@]}"

logs_pid=""
stop() {
  trap - INT TERM HUP
  echo
  echo "Apagando el sistema..."
  [[ -n "$logs_pid" ]] && kill "$logs_pid" 2>/dev/null || true
  docker compose stop
  exit 0
}
trap stop INT TERM
# Terminal cerrada: también apaga (sin terminal donde escribir, la salida va a /dev/null)
trap 'exec >/dev/null 2>&1; stop' HUP

cat <<EOF

  Sistema:  http://localhost:${WEB_HOST_PORT:-5173}
  Swagger:  http://localhost:${API_HOST_PORT:-8000}/api/docs
  Base:     localhost:${DB_HOST_PORT:-5433}

  Ctrl+C para apagar.

EOF

# En segundo plano para que Ctrl+C llegue al trap sin esperar a que termine
docker compose logs -f --tail 20 api web &
logs_pid=$!
wait "$logs_pid" || true
stop
