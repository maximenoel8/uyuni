#!/bin/bash
set -e

PGUSER=${POSTGRES_USER:-postgres}
PGPORT=${POSTGRES_PORT:-5432}

if ! /usr/bin/diskcheck.sh; then
    exit 1
fi

if ! pg_isready -U "$PGUSER" -h localhost -p "$PGPORT" > /dev/null; then
    echo "Healthcheck failed: PostgreSQL is not ready (user: ${PGUSER}, host: localhost, port: ${PGPORT})."
    exit 1
fi

echo "Healthcheck passed: PostgreSQL is ready."
exit 0
