#!/bin/sh
# Restaura un backup en la base de producción (correr en deploy/). REEMPLAZA TODOS LOS DATOS.
#   ./restore.sh                         → lista los backups disponibles
#   ./restore.sh sgi-2026-10-01_030000.dump → restaura ese archivo (de /backups o de Spaces)
set -eu
cd "$(dirname "$0")"
COMPOSE="docker compose -f docker-compose.prod.yml"

if [ $# -eq 0 ]; then
	echo "Backups en el servidor:"
	$COMPOSE exec -T backup sh -c 'ls -1t /backups/*.dump 2>/dev/null | xargs -n1 basename'
	echo "Backups en Spaces:"
	$COMPOSE exec -T backup sh -c 'rclone lsf "spaces:$SPACES_BUCKET/sgi-backups/" 2>/dev/null || echo "(Spaces no configurado)"'
	exit 0
fi

FILE="$1"
echo "Se va a REEMPLAZAR la base actual por el backup $FILE."
printf "Escribí RESTAURAR para continuar: "
read -r answer
[ "$answer" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }

# Si no está en el servidor, se baja de Spaces
$COMPOSE exec -T backup sh -c "[ -f /backups/$FILE ] || rclone copy \"spaces:\$SPACES_BUCKET/sgi-backups/$FILE\" /backups/"

echo "→ Deteniendo la API"
$COMPOSE stop api

echo "→ Backup de seguridad del estado actual"
$COMPOSE exec -T backup backup.sh now antes-de-restaurar

echo "→ Restaurando"
$COMPOSE exec -T backup sh -c "
	psql -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '\$PGDATABASE' AND pid <> pg_backend_pid();\" >/dev/null
	dropdb \"\$PGDATABASE\" && createdb \"\$PGDATABASE\" &&
	pg_restore --no-owner --dbname=\"\$PGDATABASE\" /backups/$FILE"

echo "→ Levantando la API"
$COMPOSE start api
echo "Listo."
