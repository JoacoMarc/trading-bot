"""Escritura atómica: archivo temporal en el mismo directorio + `os.replace`.

Un corte a mitad de escritura nunca deja un archivo truncado; el lector ve la versión anterior
o la nueva, completa.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))
