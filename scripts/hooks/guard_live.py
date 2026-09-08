#!/usr/bin/env python3
"""Hook PreToolUse (Bash|PowerShell) de Claude Code.

Segunda barrera detrás de `permissions.deny` en `.claude/settings.json`:
- bloquea cualquier comando que lance el modo live del bot;
- bloquea lecturas o copias de archivos `.env*` con secretos (`.env.example` está permitido).

Contrato de Claude Code: lee el JSON del evento por stdin; código de salida 2 bloquea la
herramienta y muestra stderr como motivo; 0 deja pasar. Debe correr con el Python del sistema,
sin dependencias.
"""

from __future__ import annotations

import json
import re
import sys

LIVE_PATTERNS = (
    r"\btradingbot\s+live\b",
    r"\btradingbot\.cli\S*\s+live\b",
    r"--confirm-live\b",
    r"\bTRADINGBOT_LIVE_ACK\b",
    r"--profile[\s=]+live\b",
)

# `.env`, `.env.live`, `.env.paper`, `.env.testnet`... pero no `.env.example` ni `.envrc`.
SECRET_FILE_PATTERN = r"(?<![\w.-])\.env(?:\.(?!example\b)[\w-]+)?(?![\w.-])"

LIVE_MESSAGE = (
    "guard_live: bloqueado. El modo live no se lanza desde Claude; lo ejecuta el usuario con "
    "`docker compose --profile live up -d` (ver CLAUDE.md, regla 4)."
)
SECRET_MESSAGE = (
    "guard_live: bloqueado. No se leen ni copian archivos .env* con secretos desde Claude. "
    "Usá .env.example como plantilla (ver CLAUDE.md, regla 5)."
)


def decide(command: str) -> str | None:
    """Devuelve el motivo del bloqueo o None si el comando puede ejecutarse."""
    for pattern in LIVE_PATTERNS:
        if re.search(pattern, command):
            return LIVE_MESSAGE
    if re.search(SECRET_FILE_PATTERN, command):
        return SECRET_MESSAGE
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command", ""))
    reason = decide(command)
    if reason is None:
        return 0
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
