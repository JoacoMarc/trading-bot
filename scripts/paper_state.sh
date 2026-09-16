#!/usr/bin/env bash
# Exporta o importa el volumen de la DB del paper (SQLite en `tradingbot-db`) como un .tgz, para
# mover el estado entre máquinas o hacer backups (docs/runbooks/vps.md).
#
#   bash scripts/paper_state.sh export paper-state.tgz   # con el paper parado (compose down)
#   bash scripts/paper_state.sh import paper-state.tgz   # antes del primer `up` en el destino
#
# El nombre del volumen depende del nombre del proyecto de compose (`name: tradingbot` en
# compose.yaml => `tradingbot_tradingbot-db`); se puede pisar con PAPER_DB_VOLUME.
set -euo pipefail

action="${1:-}"
archive="${2:-paper-state.tgz}"
volume="${PAPER_DB_VOLUME:-tradingbot_tradingbot-db}"

if [[ "$action" != "export" && "$action" != "import" ]]; then
  echo "uso: $0 export|import [archivo.tgz]" >&2
  exit 2
fi

if docker ps --filter "name=paper" --filter "status=running" --format '{{.Names}}' | grep -q paper; then
  echo "el paper esta corriendo; pararlo primero: docker compose --profile paper down" >&2
  exit 1
fi

if ! docker volume inspect "$volume" >/dev/null 2>&1; then
  if [[ "$action" == "export" ]]; then
    echo "no existe el volumen $volume (PAPER_DB_VOLUME para cambiarlo)" >&2
    exit 1
  fi
  docker volume create "$volume" >/dev/null
fi

archive_dir="$(cd "$(dirname "$archive")" && pwd)"
archive_name="$(basename "$archive")"
mkdir -p "$archive_dir"

if [[ "$action" == "export" ]]; then
  docker run --rm -v "$volume:/db:ro" -v "$archive_dir:/backup" alpine \
    tar czf "/backup/$archive_name" -C /db .
  echo "estado exportado a $archive ($(du -h "$archive" | cut -f1))"
else
  if [[ ! -f "$archive" ]]; then
    echo "no existe $archive" >&2
    exit 1
  fi
  docker run --rm -v "$volume:/db" -v "$archive_dir:/backup:ro" alpine \
    sh -c "rm -rf /db/* && tar xzf /backup/$archive_name -C /db && chown -R 1000:1000 /db"
  echo "estado importado en el volumen $volume:"
  docker run --rm -v "$volume:/db:ro" alpine ls -la /db
fi
