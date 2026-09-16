# trading-bot

Bot de trading propio para Binance Spot (solo long, quote USDT). Un solo motor para backtest, paper y live. Dinero real únicamente después de pasar los gates de `docs/GATES.md`. Se construye por fases; cada sesión trabaja sobre la fase activa.

Fase activa, entregables y DoD: @docs/ROADMAP.md
Plan completo (arquitectura, principios, investigación): `docs/PLAN.md`

## Comandos

```bash
uv sync                                   # instala deps (Python 3.12 gestionado por uv)
uv run pytest                             # unit; -m network / -m testnet solo explícitos
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run tradingbot --help
uv run tradingbot doctor                  # Python, env, conexión y reloj vs Binance
uv run tradingbot download-data           # velas cerradas, incremental (8 pares 1h+4h desde 2019)
uv run tradingbot data-info && uv run tradingbot data-check   # datasets y huecos (configs/binance_gaps.json)
uv run tradingbot backtest [--set k=v ...]    # configs/backtest.yaml (ema_trend) o --config configs/regime-bh.yaml; registra EXP-NNNN
uv run tradingbot benchmark --kind bh_btc|equal_weight        # buy & hold registrado como EXP
uv run tradingbot experiments list|show|compare|sync          # REGISTRY.md se regenera con sync
uv run tradingbot stop [--flatten] && uv run tradingbot resume  # kill switch por archivo logs/STOP (paper/live)
uv run tradingbot status [--check] && uv run tradingbot trades --db db/paper.db  # lee logs/status.json (heartbeat) y la DB del paper
uv run tradingbot walkforward [--optimize --trials N] [--plateau]  # IS 24m/OOS 6m + gate 1; registra WF-NNNN (lento: background o terminal del usuario)
uv run tradingbot optimize --to YYYY-MM-DD --trials N          # optuna solo in-sample; registra OPT-NNNN
docker compose --profile paper build       # los servicios tienen perfil: sin --profile no se buildea nada
docker compose run --rm bot doctor        # `run` activa el perfil `tools` del servicio base solo
```

`paper`, `testnet` y `live` corren con `docker compose --profile <modo> up -d`, **lanzado por el usuario** (`tradingbot paper --config configs/paper.yaml [--max-bars N]` es lo que corre el contenedor; runbook en `docs/runbooks/paper.md`). `optimize` y `walkforward` se lanzan en background o desde la terminal del usuario.

## Mapa del código (`src/tradingbot/`)

| Módulo | Responsabilidad |
|---|---|
| `domain/` | Tipos inmutables: Candle, Bar, Timeframe, Signal, OrderIntent, Order, Fill, Position, Trade, Money |
| `config/` | BotConfig (pydantic-settings). Precedencia CLI > env > YAML > defaults |
| `data/` | Parquet store, downloader incremental, quality check, HistoricalFeed / LiveFeed (emiten `Bar`; el live confirma el cierre por la vela t+1) |
| `indicators/` | Indicadores propios vectorizados, semilla y warmup documentados |
| `strategy/` | Protocol `Strategy` + `StrategyContext`; `strategies/ema_trend.py`, `strategies/regime_bh.py` |
| `risk/` | Sizing, límites, circuit breakers, cooldowns, kill switch. Nunca bloquea salidas |
| `execution/` | Protocol `Broker`: SimulatedBroker, PaperBroker (+StopWatcher), BinanceBroker, reconciliación |
| `exchange/` | Adapter ccxt: markets, OHLCV, rate limit, errores, offset de reloj |
| `engine/` | Engine async (+ `EngineState` para reanudar, `Bar.replay`) + PositionManager (niveles de stop) + series precomputadas/rodantes + Clock |
| `backtest/` | Runner, métricas, reporte, benchmark |
| `validation/` | equivalence (lookahead), walkforward, optimizer, plateau, montecarlo, regimes |
| `persistence/` | Protocol `TradeStore`: InMemoryStore, SqliteStore (WAL, JSON + columnas índice, `state` clave/valor); artefactos de experimentos |
| `paper/` | `PaperSession`: LiveFeed → Engine → PaperBroker → SqliteStore, reanudación desde la DB, status.json, shutdown ordenado |
| `observability/` | `logs/status.json` (heartbeat + foto del bot) para Docker, `tradingbot status` y `/paper-status` |
| `notify/` | Notifier: logs, Telegram |
| `analyst/` | LLM analista fuera del loop (anthropic SDK) |
| `cli/` | typer |
| `doctor.py` | Chequeos de entorno |

## Reglas duras

1. **Dinero en `Decimal`.** Precios, cantidades y fees en `Decimal`; frontera con `Decimal(str(x))`, nunca `Decimal(float)`. `float64` solo dentro de `indicators/`.
2. **Sin lookahead.** Las estrategias solo ven velas cerradas. Señal en `t` → fill al open de `t+1`. Todo cambio en `strategy/` o `indicators/` corre el test de equivalencia (`validation/equivalence.py`).
3. **Un solo camino.** Backtest, paper y live comparten `Engine`, precedencia intra-vela y modelo de fills/stops (ADR-0002). No se agregan atajos "solo para backtest".
4. **Live nunca desde Claude.** `permissions.deny` + hook `scripts/hooks/guard_live.py` bloquean `tradingbot live`, `--confirm-live` y `TRADINGBOT_LIVE_ACK`. Live exige `mode: live` + `--confirm-live` + env `TRADINGBOT_LIVE_ACK=yes`, y sus claves viven solo en `.env.live` (perfil `live` de compose).
5. **Secretos.** Solo en `.env*` (gitignored, no se leen desde Claude; `.env.example` es la plantilla). Los YAML de `configs/` no contienen claves. `.env` de desarrollo nunca tiene claves con permiso de trading.
6. **Experimentos por CLI.** Todo backtest/walk-forward/optimización se corre con `tradingbot ...` para que quede registrado en `experiments/runs/`. No se edita el `config.yaml` de una corrida registrada. `REGISTRY.md` se regenera con `tradingbot experiments sync`.
7. **Riesgo nunca bloquea salidas.** Kill switch = sin nuevas entradas (+ `--flatten` opcional).
8. **Tiempo.** Timestamps del dominio en `int` ms epoch UTC. `datetime` solo tz-aware UTC y solo en bordes. El cierre de vela lo define el reloj del exchange, no el local.
9. **Decisiones documentadas.** Arquitectura → ADR (`/adr`). Estrategia → spec en `docs/strategy/` antes del código. Sin código de fases futuras "porque ya estamos".
10. **Un solo escritor.** La sesión principal escribe archivos; los subagentes (`.claude/agents/`) son read-only y devuelven texto.

## Convenciones

- Python 3.12, `mypy --strict`, ruff (lint + format, LF). Identificadores en inglés; docstrings, comentarios, docs y mensajes de CLI en español.
- Tests en `tests/` espejando `src/`. Unit rápidos por defecto (`addopts` excluye `network` y `testnet`). Fixtures de mercado en `tests/fixtures/` (parquet chico commiteado o series sintéticas); `data/` está gitignored y ningún test depende de él.
- `hypothesis` para invariantes (cuantización, cash ≥ 0, exposición ≤ límite).
- Commits: Conventional Commits en español (`feat(engine): ...`, `fix(data): ...`, `docs: ...`, `test: ...`, `chore: ...`). Commit solo cuando el usuario lo pide o al cerrar fase con `/phase-close`.
- Dependencias con `uv add` (grupo `dev` para tooling, `fixtures` solo para TA-Lib). No pinear aiohttp: ccxt lo pinea.
- Windows: archivos LF (`.gitattributes`), rutas con `pathlib`, nada de `os.system`.

## Flujo de trabajo

- Sesión: `/phase-start` → trabajar la fase activa → `/phase-close` (verifica DoD, actualiza ROADMAP y memoria, propone commit).
- Nueva estrategia: `/new-strategy <nombre>` → spec → implementación → tests → equivalencia → `/backtest` → `/experiment-review`.
- Antes de cerrar una fase que toque `strategy/`, `engine/`, `execution/` o `risk/`: pedir revisión al agente `trading-code-reviewer`.
- Conceptos de trading que aparezcan por primera vez → entrada en `docs/glossary.md`.

## Referencias

- `docs/PLAN.md` · `docs/ROADMAP.md` · `docs/GATES.md` · `docs/glossary.md`
- `docs/decisions/` (ADRs) · `docs/strategy/` (specs) · `docs/runbooks/`
- `experiments/REGISTRY.md` · `experiments/TEMPLATE_REPORT.md`
- Referencias externas estudiadas: freqtrade (arquitectura, protecciones, Telegram) y ccxt (Binance). Inspiran, no se copian.
