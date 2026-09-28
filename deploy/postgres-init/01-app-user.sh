#!/bin/sh
# Primera inicialización de la base (solo corre con el volumen vacío): usuario de la aplicación
# SIN superusuario, dueño de su propia base. Las migraciones y la extensión unaccent (que es
# "trusted") funcionan con ese usuario; nada más de PostgreSQL queda a su alcance.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<EOSQL
CREATE ROLE "$APP_DB_USER" LOGIN PASSWORD '$APP_DB_PASSWORD'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE DATABASE "$APP_DB_NAME" OWNER "$APP_DB_USER";
REVOKE ALL ON DATABASE "$APP_DB_NAME" FROM PUBLIC;
EOSQL
