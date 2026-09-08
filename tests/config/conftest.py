import os

import pytest

from tradingbot.config import SECRET_FIELDS


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla los tests del entorno real: sin TRADINGBOT_* ni secretos heredados."""
    for name in list(os.environ):
        if name.upper().startswith("TRADINGBOT_") or name.lower() in SECRET_FIELDS:
            monkeypatch.delenv(name, raising=False)
