#!/bin/sh
# Publica la versión actual del repositorio en el servidor (correr en deploy/).
# 1) trae el código, 2) arma las imágenes, 3) levanta (la API aplica las migraciones sola).
set -eu
cd "$(dirname "$0")"

[ -f .env ] || { echo "Falta deploy/.env (copiar de .env.prod.example y completar)."; exit 1; }
chmod 600 .env  # los secretos solo los lee root

echo "→ Trayendo el código"
git pull --ff-only

VERSION="$(git describe --tags --always)"
echo "→ Versión $VERSION"
sed -i "s/^APP_VERSION=.*/APP_VERSION=$VERSION/" .env || true

echo "→ Armando imágenes"
docker compose -f docker-compose.prod.yml build

echo "→ Levantando"
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker image prune -f >/dev/null

echo "→ Estado"
docker compose -f docker-compose.prod.yml ps
