#!/bin/sh
# Backup de la base: pg_dump comprimido (formato custom) en /backups, 7 días locales, y copia a
# DigitalOcean Spaces (30 días) si están las variables SPACES_*.
#   backup.sh loop   → corre todos los días a la hora BACKUP_HOUR (por defecto 03)
#   backup.sh now    → un backup ahora (con un nombre opcional: backup.sh now antes-de-restaurar)
set -eu

BACKUP_HOUR="${BACKUP_HOUR:-03}"
LOCAL_DAYS=7
REMOTE_DAYS=30

spaces_configured() {
	[ -n "${SPACES_KEY:-}" ] && [ -n "${SPACES_SECRET:-}" ] && [ -n "${SPACES_BUCKET:-}" ]
}

# rclone se configura por variables de entorno (sin archivo)
export RCLONE_CONFIG_SPACES_TYPE=s3
export RCLONE_CONFIG_SPACES_PROVIDER=DigitalOcean
export RCLONE_CONFIG_SPACES_ACCESS_KEY_ID="${SPACES_KEY:-}"
export RCLONE_CONFIG_SPACES_SECRET_ACCESS_KEY="${SPACES_SECRET:-}"
export RCLONE_CONFIG_SPACES_ENDPOINT="${SPACES_REGION:-nyc3}.digitaloceanspaces.com"
export RCLONE_CONFIG_SPACES_ACL=private

run_backup() {
	label="${1:+$1-}"
	file="/backups/sgi-${label}$(date +%Y-%m-%d_%H%M%S).dump"
	echo "[backup] $(date '+%d/%m/%Y %H:%M') → $file"
	pg_dump --format=custom --compress=9 --no-owner --file="$file.tmp"
	mv "$file.tmp" "$file"
	find /backups -name 'sgi-*.dump' -mtime +"$LOCAL_DAYS" -delete
	if spaces_configured; then
		rclone copy "$file" "spaces:$SPACES_BUCKET/sgi-backups/"
		rclone delete --min-age "${REMOTE_DAYS}d" "spaces:$SPACES_BUCKET/sgi-backups/"
		echo "[backup] copiado a Spaces"
	else
		echo "[backup] ATENCIÓN: Spaces no configurado, el backup queda solo en el servidor"
	fi
	date +%F > /backups/.last
}

case "${1:-loop}" in
now)
	run_backup "${2:-}"
	;;
loop)
	echo "[backup] programado todos los días a las ${BACKUP_HOUR} h"
	while true; do
		if [ "$(date +%H)" = "$BACKUP_HOUR" ] && [ "$(cat /backups/.last 2>/dev/null)" != "$(date +%F)" ]; then
			run_backup || echo "[backup] ERROR: falló el backup"
		fi
		sleep 300
	done
	;;
*)
	echo "Uso: backup.sh [loop|now]" >&2
	exit 1
	;;
esac
