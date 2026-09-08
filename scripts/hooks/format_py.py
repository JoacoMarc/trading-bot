#!/usr/bin/env python3
"""Hook PostToolUse (Edit|Write) de Claude Code: formatea el .py editado con ruff.

Corre `ruff format` y `ruff check --fix` sobre el archivo recién escrito, solo si está dentro
del proyecto. Nunca bloquea (PostToolUse no puede) y siempre sale con 0.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def uv_command() -> list[str]:
    uv = shutil.which("uv")
    return [uv] if uv else [sys.executable, "-m", "uv"]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not file_path or not str(file_path).endswith(".py"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or "."
    project = Path(project_dir).resolve()
    target = Path(file_path).resolve()
    if not target.exists() or project not in target.parents:
        return 0

    ruff = [*uv_command(), "run", "--no-sync", "ruff"]
    for args in (["format", str(target)], ["check", "--fix", "--quiet", str(target)]):
        try:
            subprocess.run(
                [*ruff, *args],
                cwd=project,
                check=False,
                timeout=50,
                capture_output=True,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"format_py: ruff no disponible ({exc})", file=sys.stderr)
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
