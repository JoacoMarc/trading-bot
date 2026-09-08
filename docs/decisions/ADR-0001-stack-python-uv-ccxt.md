# ADR-0001: Stack — Python 3.12, uv, ccxt, pandas 3, indicadores propios

- Estado: aceptado
- Fecha: 2026-09-07
- Fase: 0

## Contexto

Bot personal para Binance Spot que debe correr en Docker sobre una PC Windows 10 y ser fácil de razonar, testear y mantener por una sola persona con Python sólido. Las referencias (freqtrade, ccxt) son Python. El sistema tiene Python 3.11, pero numpy 2.5 exige ≥ 3.12 y pandas 3.0 exige ≥ 3.11.

## Decisión

- **Python 3.12** gestionado por `uv` (`.python-version`); el 3.11 del sistema no se toca. Imagen `python:3.12-slim`.
- **uv** para paquetes y lockfile; grupos `dev` (tooling) y `fixtures` (TA-Lib, solo para generar fixtures de indicadores).
- **ccxt** como adapter de exchange (sync para descarga de datos, `async_support` para live; `ccxt.pro` en backlog).
- **pandas 3.x + numpy 2.x + pyarrow** para datos; parquet como formato de OHLCV.
- **Indicadores propios** vectorizados con `ewm`/`rolling`, testeados contra TA-Lib tras burn-in.
- pydantic v2 (config y dominio), SQLAlchemy 2.0 sync + SQLite, optuna, typer, structlog, python-telegram-bot 22, anthropic SDK 1.x, matplotlib.
- Calidad: ruff (lint + format, LF), `mypy --strict`, pytest + pytest-asyncio + hypothesis, pre-commit.

## Alternativas consideradas

- **TypeScript/Node**: ccxt existe en TS pero el ecosistema cuantitativo (pandas, optuna, indicadores) es mucho más pobre.
- **Python 3.11 (el del sistema)**: capa numpy en 2.4.x y excluye libs actuales; uv instala 3.12 sin fricción.
- **pandas-ta**: repositorio eliminado, releases pagos anunciados, licencia incierta. Descartado.
- **TA-Lib como dependencia de runtime**: ya tiene wheels para Windows, pero es una dependencia C más en la imagen y no queremos depender de su semántica de semillas. Solo dev/fixtures.
- **Motores de backtesting existentes** (vectorbt, backtrader, nautilus_trader): vectorbt OSS recortado vs PRO y solo vectorizado; backtrader sin mantenimiento y GPL; nautilus excelente pero un framework enorme que contradice el objetivo de construir y entender el motor. Ver ADR-0002.
- **polars**: opción futura para la capa de datos si pandas queda lento.

## Consecuencias

- Reproducibilidad total vía `uv.lock`; Docker instala con `uv sync --frozen --no-dev`.
- pandas 3 trae Copy-on-Write obligatorio y strings PyArrow: el código se escribe con esa semántica desde el inicio.
- ccxt pinea muchas dependencias transitivas exactas (aiohttp, etc.): no pinear esas libs por nuestra cuenta.
- Regla dura: `uv add` para dependencias; `pip` no se usa dentro del proyecto.
