> Copia del plan aprobado el 2026-09-07. La version viva con estado por fase es ROADMAP.md; este archivo es la referencia completa de arquitectura, principios, gates e investigacion.

# Plan: trading-bot propio para Binance Spot (Python), incremental

## Contexto

Joaquín quiere construir su propio bot de trading para Binance Spot, por etapas, con calidad y decisiones documentadas, y solo poner dinero real después de validar confiabilidad (backtest → paper trading → testnet → capital mínimo). Los repos de referencia son freqtrade (arquitectura de bot completo) y ccxt (abstracción de exchange). La idea es inspirarse, no copiar: tomar lo que funciona y corregir sus puntos débiles conocidos.

Decisiones ya tomadas con el usuario:

| Tema | Decisión |
|---|---|
| Stack | Python **3.12** gestionado por `uv` (el 3.11 del sistema queda intacto). Motivo: numpy 2.5 exige ≥ 3.12; pandas 3.0 exige ≥ 3.11 |
| Mercado | Binance Spot únicamente, solo long (sin futures ni margin en v1) |
| Estrategia inicial | Trend following con indicadores (EMA + filtro de régimen + ADX, stop por ATR) |
| "Agentes" | (a) módulos internos determinísticos del bot, (b) LLM analista **fuera del loop** de trading, (c) subagentes de Claude Code para el desarrollo |
| Interfaz | CLI + bot de Telegram |
| Deploy | Docker local en esta PC (Windows 10, Docker 29); portable a VPS después |
| Perfil | Python sólido, trading algorítmico nuevo → el plan y el glosario explican los conceptos de trading |

Estado actual: `C:\Users\joaco\Desktop\Projects\trading-bot` vacío, sin git. Disponibles: Python 3.11.2, Node 24, Docker 29.6, git 2.46.

**Modo de ejecución:** al aprobar, se ejecuta **solo la Fase 0**. Cada fase siguiente arranca en una sesión nueva con `/phase-start`, que lee `CLAUDE.md` y `docs/ROADMAP.md` (copia viva de este plan con checkboxes). Es esperable que las fases 3–6 iteren varias veces sobre la estrategia; eso es parte del plan, no un desvío.

---

## 1. Principios de diseño (qué mejoramos respecto a freqtrade)

1. **Un solo camino de código para backtest, paper y live.** El mismo `Engine` (async desde el día 1) consume `Bar`s de un `MarketFeed` (histórico o en vivo) y ejecuta contra un `Broker` (simulado, paper o Binance). freqtrade tiene un motor de backtesting separado del loop live, fuente clásica de discrepancias. Un comando `parity` mide la divergencia paper↔backtest y es parte del gate a live.
2. **Sin lookahead por construcción.** La estrategia recibe una vista truncada en la vela cerrada actual; la señal de la vela `t` se ejecuta al open de `t+1`. Un test automático cubre lookahead y equivalencia backtest/live de los indicadores.
3. **Dinero en `Decimal`, tipos estrictos.** Precios, cantidades y fees en `Decimal` (`Decimal(str(x))` en la frontera, nunca `Decimal(float)`); `float64` solo dentro de indicadores. Config y dominio con pydantic v2.
4. **Realismo de ejecución desde el inicio.** Slippage, fee cobrado en el activo recibido (como hace Binance), redondeo a `stepSize`, `minNotional` también en salidas, gaps a través del stop, dust. freqtrade no modela slippage ni fee en activo base.
5. **Registro de experimentos como ciudadano de primera clase.** Cada corrida deja `config.yaml` congelado, `metrics.json` con metadatos de reproducibilidad y `REPORT.md`; `REGISTRY.md` se regenera desde los artefactos.
6. **Validación anti-overfitting integrada y holdout intocable.** Walk-forward, OOS concatenado, meseta de parámetros, Monte Carlo y 12 meses de holdout que se evalúan una sola vez por familia de estrategia.
7. **Riesgo separado de la estrategia y nunca bloquea salidas.** Sizing, límites y circuit breakers viven en `risk/`; el kill switch significa "sin nuevas entradas".
8. **Superficie chica.** Solo Binance Spot, sin plugins ni multi-exchange. Las abstracciones existen para testear y para el camino único, no por generalidad.
9. **LLM fuera del loop.** Analiza, explica, detecta red flags y propone experimentos. Nunca decide ni ejecuta trades.
10. **Seguridad operativa.** `clientOrderId` determinístico, stop nativo en el exchange, reconciliación exchange↔DB, `live` con triple confirmación y claves fuera del alcance de las sesiones de Claude.

---

## 2. Arquitectura

### 2.1 Módulos internos del bot

```
src/tradingbot/
  domain/         Candle, Bar, Timeframe, Pair, Signal, OrderIntent, Order, Fill, Position, Trade, PortfolioSnapshot, Money
  config/         BotConfig (pydantic-settings): mode, exchange, data, strategy, risk, execution, notify
  data/           ParquetStore, Downloader (incremental), QualityChecker, HistoricalFeed, LiveFeed
  indicators/     ema, sma, rsi, macd, atr, adx, bbands, highest/lowest, cross_above/below (numpy/pandas, con tests)
  strategy/       Protocol Strategy + StrategyContext; strategies/ema_trend.py
  risk/           PositionSizer, RiskManager (límites, circuit breakers, cooldowns, kill switch)
  execution/      Protocol Broker; SimulatedBroker; PaperBroker (+StopWatcher); BinanceBroker; reconciliation
  exchange/       Adapter ccxt: markets/precision/limits, OHLCV paginado, rate limit, mapeo de errores, retry, time offset
  engine/         Engine (async) + PositionManager (niveles de stop/trailing) + Clock
  backtest/       BacktestRunner, metrics, report, benchmark buy&hold
  validation/     equivalence (lookahead), walkforward, optimizer (optuna), montecarlo, regimes, plateau
  persistence/    Protocol TradeStore; InMemoryStore; SqliteStore (SQLAlchemy 2.0); experiments (artefactos)
  notify/         Protocol Notifier; LogNotifier; TelegramNotifier
  analyst/        LLM analista (anthropic SDK)
  cli/            typer: doctor, download-data, data-check, backtest, experiments, walkforward, optimize, paper, parity, status, analyze, live
  observability/  structlog JSON, status.json (heartbeat)
```

**Loop del `Engine` por cada `Bar` cerrado** (un `Bar` = todas las velas del mismo cierre para todos los pares; pares en orden alfabético fijo). Precedencia idéntica en los tres modos:

1. `Broker.on_bar_open`: fills de órdenes pendientes al `open` (+ slippage).
2. `Broker.on_bar`: stops. Simulado: si `open ≤ stop` → fill al `open` (gap); si no y `low ≤ stop` → fill al `stop`; siempre con slippage. Una posición abierta al open de `t+1` puede stopearse en esa misma vela.
3. Mark-to-market al `close`: equity = USDT libre + Σ qty neta × close. Snapshot de equity.
4. `Strategy.on_candle(ctx)` por par → `Signal` (ENTER_LONG / EXIT_LONG / HOLD + metadata).
5. `RiskManager.evaluate(signals, portfolio)` → `OrderIntent`s o rechazos con `reason_code`. Si hay más entradas que slots: ranking determinístico (default ADX descendente, desempate alfabético). Los topes de notional usan **cash libre**, no PnL no realizado. Las salidas nunca se bloquean.
6. `Broker.submit(intent)` → `Order(PENDING)` (se llena en el paso 1 del próximo `Bar`). `PositionManager` recalcula niveles de stop/trailing y los publica con `Broker.set_stop(position_id, price)`.
7. `TradeStore` persiste; `Notifier` emite eventos.

**El stop lo ejecuta el `Broker`, no el `PositionManager`:**
- `SimulatedBroker` (backtest): reglas del paso 2.
- `PaperBroker`: `StopWatcher` consulta el último precio (`fetch_ticker` o vela 1m) cada 60 s entre cierres y, si `last ≤ stop`, registra el fill al precio observado + slippage. Simula la orden nativa.
- `BinanceBroker`: orden nativa en reposo (`STOP_LOSS` de mercado si el símbolo lo lista en `orderTypes`, si no `STOP_LOSS_LIMIT` con `price = stop × (1 − 0.5%)`), cancelada y repuesta cuando el trailing sube. La orden en reposo bloquea el saldo base: toda salida por señal cancela el stop primero y vende después. El chequeo por software al cierre queda como respaldo (stop-limit no ejecutado por gap).

**Fills:** `SimulatedBroker` llena al `open(t+1)` cuando llega la vela. `PaperBroker` llena inmediatamente al `open` de la vela en formación (`fetch_ohlcv(limit=2)[-1].open`, fijo tras el primer trade del período) + slippage. `BinanceBroker` envía market order; el fill lo informa el exchange. Todo `Fill` guarda `ref_price` (= `open(t+1)`), `fill_price`, `signal_ts`, `decision_ts`, `fill_ts`, `fee_amount`, `fee_asset`; `fill_price − ref_price` es el *implementation shortfall* y se reporta.

**Tiempo:** todo timestamp del dominio es `int` ms epoch UTC; `datetime` solo tz-aware UTC y solo en bordes (CLI, reportes). Vela identificada por `open_time`; `close_time = open_time + tf_ms − 1`. `LiveFeed` usa el reloj del exchange (`fetch_time`, offset cacheado y refrescado cada hora) y confirma el cierre de `t` por la aparición de la vela `t+1`, no por reloj local. "Día" para pérdida diaria y resumen = día UTC; `notify.timezone` (default `America/Argentina/Buenos_Aires`) solo para mostrar horas.

### 2.2 Estrategia v1: `ema_trend` (spec completa en `docs/strategy/ema-trend-v1.md`)

| Elemento | Definición inicial (parametrizable) |
|---|---|
| Timeframe | 4h (1h como alternativa a evaluar) |
| Universo | 8 pares USDT líquidos con historia desde 2019–2020: BTC, ETH, BNB, XRP, ADA, LTC, LINK, SOL. Backtests iniciales con BTC+ETH; el gate se evalúa con ≥ 4 pares |
| Régimen | `close > EMA(200)` habilita entradas. Si el régimen se da vuelta con posición abierta, **no** cierra: sale por stop/trailing/cruce |
| Entrada | `entry_mode: cross \| state`. `cross` = solo en el cruce EMA(20) sobre EMA(50) con ADX(14) > 20. `state` = mientras EMA20 > EMA50, ADX > umbral y régimen alcista, sin posición y con cooldown de N velas tras un stop. Se evalúan ambos en la Fase 6 |
| Sizing | riesgo fijo 1% del equity: `qty = equity × 0.01 / (close(t) − stop_estimado)`; tope 25% del cash libre por posición; máx. 3 posiciones |
| Stop inicial | fijado tras el fill: `fill_price − 2.0 × ATR(14)` |
| Trailing | chandelier: `highest_close_since_entry − 3.0 × ATR(14)` |
| Salida por señal | EMA(20) cruza bajo EMA(50) |
| Costos | fee 0.10% en el activo recibido (0.075% en quote si `pay_with_bnb`), slippage 0.05% |
| Benchmark | buy & hold BTC y cartera equiponderada del universo |
| Rangos para optimizar | EMA rápida 10–30, lenta 40–100, ADX 15–30, mult. ATR stop 1.5–4, trailing 2–5 (paso 0.5; precisión ≤ 0.001 como freqtrade) |

Hipótesis: en cripto las tendencias de 4h persisten lo suficiente para que un seguidor de tendencia con filtro de régimen supere los costos y tenga drawdowns menores que buy & hold en mercados bajistas (2022), cediendo retorno en los alcistas.

### 2.3 Criterios de gate (se formalizan en `docs/GATES.md`, Fase 6)

**Holdout:** los últimos 12 meses de datos (desde 2025-09-01) quedan reservados. Ningún backtest ni optimización los usa (`--to` por defecto los excluye; `--include-holdout` solo para la corrida final). Se evalúan **una sola vez** por familia de estrategia.

**Backtest → Paper** (con el universo final de ≥ 4 pares y la config de riesgo completa, al cierre de la Fase 6):
- Walk-forward rodante IS 24 m / OOS 6 m (≈ 9 ventanas desde 2019). Las ventanas OOS se **concatenan** en una sola curva; sobre ella: Sharpe (retornos diarios, rf = 0, √365) ≥ 0.8 **y** ≥ Sharpe de buy & hold BTC del mismo período; profit factor ≥ 1.3; max DD ≤ 25% **y** ≤ 50% del DD de buy & hold. Secundario: ≥ 60% de ventanas OOS positivas.
- ≥ 100 trades en la muestra completa **y** ≥ 40 en la curva OOS concatenada.
- Regímenes por año: positivo en 2020–21 y 2023–24; pérdida ≤ 8% en 2022; ningún año con DD > 25%.
- Meseta: cada parámetro ±20% (uno a la vez) y los vértices del hipercubo ±20% mantienen PF > 1.1 y retorno > 0 en ≥ 80% de los casos.
- Monte Carlo (remuestreo de trades, 5000 corridas): DD del percentil 95 ≤ 35%.
- Holdout: PF > 1.1 y DD ≤ 25%. Test de equivalencia/lookahead en verde.

**Paper → Live:** ≥ 8 semanas de paper contadas desde el último cambio en `strategy/`, `risk/`, `engine/` o `execution/`; `parity` ≥ 95% de señales coincidentes y desvío medio de fill ≤ 15 bps; 0 excepciones no manejadas en las últimas 4 semanas; reconciliación limpia; kill switch probado; ciclo completo en testnet. El capital inicial lo decide el usuario y se recomienda pequeño.

### 2.4 Registro de experimentos

```
experiments/
  REGISTRY.md              regenerado por `experiments sync` desde runs/*/metrics.json + veredicto de cada REPORT.md
  TEMPLATE_REPORT.md
  runs/EXP-0007-ema-trend-4h/
    config.yaml            congelado (nunca se edita)
    metrics.json           bloque `metrics` (comparable, rtol 1e-9) + bloque `meta` (git sha, data hash, host, duración, semillas)
    trades.csv  equity.csv  equity.png
    REPORT.md              autogenerado + sección "Notas y veredicto" (humano o backtest-analyst)
    analysis.md            (opcional) análisis del LLM
```

Prefijos: `EXP-` backtest, `WF-` walk-forward, `OPT-` optimización, `PAR-` paridad paper/backtest. Sin base SQLite para experimentos en v1 (backlog).

### 2.5 Workspace de Claude Code

**`CLAUDE.md`** (≤ 200 líneas, español): propósito y fase actual (`@docs/ROADMAP.md`), comandos, mapa de módulos, reglas duras, convenciones, flujo para agregar una estrategia, punteros a `docs/decisions/`, `experiments/REGISTRY.md`, `docs/GATES.md`, `docs/glossary.md`. `CLAUDE.local.md` (gitignored) para notas de esta máquina.

Reglas duras:
- Dinero, cantidades y fees en `Decimal`; frontera con `Decimal(str(x))`.
- Las estrategias solo ven velas cerradas. Cambios en `strategy/` o `indicators/` corren el test de equivalencia.
- `paper`, `testnet` y `live` corren con `docker compose up -d` lanzado por el usuario, nunca en foreground desde Claude. `optimize` y `walkforward` se lanzan en background o desde la terminal del usuario.
- Nunca ejecutar `live` desde una sesión de Claude (deny + hook). Live requiere `mode: live` + `--confirm-live` + env `TRADINGBOT_LIVE_ACK=yes`; claves solo en `.env.live`, cargado únicamente por el perfil `live` de compose.
- Secretos solo en `.env*` (gitignored); los YAML de `configs/` no contienen claves. `.env` de desarrollo nunca tiene claves con permiso de trading.
- Todo backtest se corre por CLI para que quede registrado. No se edita `config.yaml` de una corrida registrada.
- El `RiskManager` nunca bloquea salidas.
- Decisiones de arquitectura → ADR. Cambios de estrategia → spec en `docs/strategy/` antes del código.
- Tests: `addopts = -m "not network and not testnet"`; los marcados solo explícitos.
- La sesión principal es la única que escribe archivos; los subagentes devuelven texto.

**Subagentes (`.claude/agents/`)** — todos read-only, devuelven texto que la sesión principal aplica:

| Agente | Rol | `tools` | Se crea en |
|---|---|---|---|
| `trading-code-reviewer` | Revisa diffs: lookahead, off-by-one de velas, float en dinero, fees/slippage, errores del exchange, idempotencia, bloqueo de salidas | Read, Grep, Glob | Fase 0 |
| `strategy-researcher` | Diseña/investiga estrategias y redacta la spec (hipótesis, reglas, params, rangos, comportamiento por régimen) | Read, Grep, Glob, WebSearch, WebFetch | Fase 3 |
| `backtest-analyst` | Corre backtests/walk-forward por CLI, compara con corridas previas, detecta overfitting, redacta el veredicto | Read, Grep, Glob, Bash | Fase 4 |
| `risk-auditor` | Audita config de riesgo y corre la checklist de go-live | Read, Grep, Glob, Bash | Fase 5 |

Formato: frontmatter `name`, `description`, `tools` (allowlist), `permissionMode: plan` en los de solo lectura, `model: inherit`.

**Skills (`.claude/skills/<n>/SKILL.md`)**

| Skill | Qué hace | Fase |
|---|---|---|
| `/phase-start` | Lee ROADMAP, muestra fase actual, DoD y archivos clave | 0 |
| `/phase-close` | Verifica DoD (tests, ruff, mypy, docs), actualiza ROADMAP y memoria, propone commit | 0 |
| `/adr <título>` | Crea ADR desde plantilla | 0 |
| `/new-strategy <nombre>` | Scaffold de estrategia + test + spec | 3 |
| `/backtest <estrategia> [opciones]` | Corre backtest, registra, resume vs benchmark y última corrida | 4 |
| `/experiment-review <id>` | Lee artefactos y escribe veredicto | 4 |
| `/walkforward <estrategia>` | Walk-forward + optimización IS, reporta OOS/IS y meseta | 6 |
| `/paper-status` | Lee `logs/status.json` y logs: posiciones, PnL, errores | 7 |
| `/analyze <exp-id>` | Invoca al analista LLM | 9 |
| `/live-checklist` | Checklist de go-live con `risk-auditor` | 10 |

`disable-model-invocation: true` en `/backtest`, `/walkforward`, `/live-checklist`; `argument-hint` y `$ARGUMENTS`; scripts auxiliares vía `${CLAUDE_SKILL_DIR}`.

**Permisos y hooks (`.claude/settings.json`)**
- `permissions.deny`: `Read(./.env)`, `Read(./.env.*)`, `Bash(tradingbot live*)`, `Bash(uv run tradingbot live*)`, `Bash(docker compose --profile live*)`.
- `permissions.allow`: `Bash(uv run pytest*)`, `Bash(uv run ruff*)`, `Bash(uv run mypy*)`, `Bash(uv run tradingbot backtest*)`, `Bash(uv run tradingbot experiments*)`, `Bash(uv run tradingbot data-*)`.
- `PreToolUse` `matcher: "Bash"` → `python ${CLAUDE_PROJECT_DIR}/scripts/hooks/guard_live.py` (lee `tool_input.command`, exit 2 si contiene `live`, `--confirm-live` o `TRADINGBOT_LIVE_ACK`). Segunda capa detrás del deny.
- `PostToolUse` `matcher: "Edit|Write"` → `python ${CLAUDE_PROJECT_DIR}/scripts/hooks/format_py.py` (si `.py`: `uv run --no-sync ruff format` + `ruff check --fix`).

**Memoria de Claude** (`~/.claude/projects/.../memory/`): al cerrar la Fase 0 se guardan las decisiones de este plan, el perfil del usuario y el feedback "incremental, no copiar freqtrade". `/phase-close` agrega estado y aprendizajes no derivables del repo.

**Docs:** `docs/ROADMAP.md`, `docs/decisions/ADR-*.md`, `docs/strategy/`, `docs/GATES.md`, `docs/runbooks/{paper,live,incident}.md`, `docs/glossary.md` (arranca con 10 términos: vela, timeframe, lookahead, slippage, fee, drawdown, Sharpe, walk-forward, overfitting, régimen; crece por fase).

---

## 3. Stack y dependencias

Versiones verificadas en PyPI el 2026-09-07 (se fijan en `uv.lock` en la Fase 0):

| Área | Elección | Versión | Nota |
|---|---|---|---|
| Runtime | Python 3.12 (`.python-version`, `requires-python = ">=3.12"`), imagen `python:3.12-slim` | — | 3.11 capa numpy en 2.4.x |
| Paquetes | `uv` + `pyproject.toml` + `uv.lock` | 0.12.10 | grupos: `dev`, `fixtures` (TA-Lib) |
| Calidad | `ruff`, `mypy --strict` (+ `pandas-stubs`, `ignore_missing_imports` para `ccxt.*`, `optuna.*`, `telegram.*`, `talib.*`), `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`), `hypothesis`, `pre-commit` | ruff 0.16, pytest-asyncio 1.4, hypothesis 6.167 | |
| Exchange | `ccxt` (sync para descarga; `ccxt.async_support` para live; `ccxt.pro` en backlog) | 4.5.78 | pinea deps transitivas exactas: no pinear aiohttp |
| Datos | `pandas` 3.x + `numpy` 2.x, `pyarrow` | pandas `>=3.0,<3.1`, numpy 2.5, pyarrow 25 | pandas 3: Copy-on-Write y strings PyArrow |
| Indicadores | propios (`ewm`/`rolling`), semilla documentada | — | pandas-ta excluido (repo borrado, licencia incierta); TA-Lib 0.7.1 solo en grupo `fixtures` |
| Config | `pydantic` v2 + `pydantic-settings`, YAML | 2.13 / 2.15 | |
| Persistencia | SQLite (WAL) + `SQLAlchemy` 2.0 **sync** | 2.0.52 | un solo proceso escritor |
| Optimización | `optuna` | 5.0 | |
| CLI | `typer` | 0.27 | |
| Logs | `structlog` | 26.1 | |
| Telegram | `python-telegram-bot[job-queue,rate-limiter]` | 22.8 | asyncio puro, mismo event loop del engine |
| LLM | `anthropic`; `claude-opus-5`, thinking adaptativo, streaming, `client.messages.parse()`, fallback de refusal | 1.4 | cargar skill `claude-api` en la Fase 9 |
| Gráficos | `matplotlib` | — | |
| Contenedores | `Dockerfile` multi-stage (`uv sync --frozen --no-dev`), `compose.yaml` con perfiles `paper`, `testnet`, `live` | Docker 29 | |

Descartados: vectorbt (OSS recortado vs PRO, solo vectorizado), backtrader (sin mantenimiento, GPL), nautilus_trader (excelente pero enorme; contradice el objetivo de construir y entender el motor), polars (opción futura).

---

## 4. Fases

Tamaño en sesiones de Claude Code: S = 1, M = 1–2, L = 2–4. Cada fase termina con `/phase-close`.

### Fase 0 — Fundación del repo y workspace de Claude (S) ← se ejecuta al aprobar

Entregables:
- `git init`; `uv python install 3.12` + `.python-version`; `uv init` con `src/tradingbot/`; `pyproject.toml` (deps de §3; `[tool.pytest.ini_options]` con `markers = ["network", "testnet"]`, `addopts`, `asyncio_mode`; `[tool.mypy]` strict con overrides; `[tool.ruff]` con `line-ending = "lf"`); `uv.lock`; `.pre-commit-config.yaml`.
- `.gitignore` (`.env*`, `!.env.example`, `data/`, `db/`, `logs/`, `*.db`, `CLAUDE.local.md`); `.gitattributes` (`* text=auto eol=lf`, `*.parquet binary`); `.editorconfig`; `.dockerignore` (`data/ db/ logs/ experiments/runs/ .venv/ .git/ tests/ .claude/`); `.env.example`.
- `Dockerfile` multi-stage sobre `python:3.12-slim`; `compose.yaml` con servicio `bot`, perfiles y volúmenes (`db/` en volumen nombrado `tradingbot-db`; `data/`, `logs/`, `experiments/` bind mounts).
- CLI stub: `tradingbot --version`, `tradingbot doctor` (Python, env, conectividad pública a Binance, offset de reloj local vs `fetch_time`; falla si > 1000 ms).
- `CLAUDE.md`, `.claude/agents/trading-code-reviewer.md`, `.claude/skills/{phase-start,phase-close,adr}/SKILL.md`, `.claude/settings.json` (permisos + hooks), `scripts/hooks/guard_live.py`, `scripts/hooks/format_py.py`.
- `docs/ROADMAP.md` (este plan con checkboxes), `docs/glossary.md` (10 términos), `docs/GATES.md` (puntero a §2.3; se redacta en Fase 6), `docs/strategy/README.md`, `docs/decisions/`:
  - ADR-0001 stack: Python 3.12 + uv + ccxt + pandas 3
  - ADR-0002 un solo camino backtest/paper/live: ports `MarketFeed`/`Broker`/`TradeStore`/`Notifier`, `Bar` multi-par, precedencia intra-vela, modelo de fills y de stops (§2.1)
  - ADR-0003 Decimal para dinero, float64 solo en indicadores
  - ADR-0004 alcance v1: Binance Spot, solo long, quote USDT
- `experiments/REGISTRY.md` (vacío) y `experiments/TEMPLATE_REPORT.md`.
- Memoria de Claude; primer commit.

DoD: `uv run pytest` verde (smoke), `ruff` y `mypy` limpios, `docker compose build` ok, `docker compose run --rm bot tradingbot doctor` corre.

### Fase 1 — Dominio y configuración (S/M)

Entregables:
- `domain/`: `Timeframe` (`to_ms()`, `floor(ts)`, `next_close(ts)`, `is_closed(open_time, now)`), `Candle`, `Bar(close_time, candles: dict[Pair, Candle])`, `Pair` (quote debe ser USDT), `Side`, `OrderType`, `OrderStatus`, `Signal`, `OrderIntent` (con `client_order_id` determinístico `tb-{strategy[:8]}-{BASEQUOTE}-{open_time_s}-{B|S}`, ≤ 36 chars, regex de Binance `^[\.A-Z\:/a-z0-9_-]{1,36}$`), `Order`, `Fill` (`price`, `qty`, `fee_amount`, `fee_asset`, `ref_price`, timestamps), `Position` (`qty` **neta** tras fee, `entry_time`, `stop_price`, `highest_close_since_entry`, `client_order_id`), `Trade` cerrado, `PortfolioSnapshot` (cash, posiciones, dust, equity), `Money` (`quantize_price`, `quantize_qty` con `ROUND_DOWN`), excepciones de dominio.
- `config/`: `Mode = backtest | paper | testnet | live` (los dos últimos exigen claves, los otros las ignoran); sub-configs; carga YAML + env con precedencia CLI > env > YAML > defaults; validaciones cruzadas.
- `engine/clock.py`: `Clock` (`SimClock`, `RealClock`).
- `configs/backtest.example.yaml`, `configs/paper.example.yaml`.

Verificación: unit + `hypothesis` (cuantización, redondeo, ids). DoD: cobertura de `domain/` y `config/` ≥ 90%; `mypy --strict` limpio.

### Fase 2 — Adapter de exchange y capa de datos (M)

Entregables:
- `exchange/binance.py`: `load_markets` → `MarketInfo` (en Binance `precision.price/amount` son **tick/step sizes**; `limits.amount.min` = LOT_SIZE minQty; `limits.cost.min` = NOTIONAL, hoy 5 USDT), `fetch_ohlcv` paginado (máx. 1000/req o `params={'paginate': True}`), lectura de límites reales desde `exchangeInfo` (hoy 6000 weight/min, 100 órdenes/10 s), `fetch_time` con offset cacheado, retry con backoff solo para `NetworkError`/`OperationFailed` (incluye `RateLimitExceeded`, `DDoSProtection`, `ExchangeNotAvailable`), nunca para `InvalidOrder`/`InsufficientFunds`/`AuthenticationError`; mapeo a excepciones de dominio. `exchange/markets_snapshot.json` para tests y backtests sin red.
- `data/store.py` (parquet por `exchange/pair/timeframe`, esquema fijo, `open_time` UTC ms), `data/downloader.py` (descarta la vela en formación si `open_time + tf_ms > exchange_time`; incremental re-pide desde la última vela **inclusive** y hace upsert por `open_time`), `data/quality.py` (huecos, duplicados, espaciado; los huecos reales de Binance se registran en `data/binance/gaps.json`), `data/feeds.py` → `HistoricalFeed(from, to, warmup)` que emite `Bar`s, precarga `warmup` velas antes de `from` y falla con `InsufficientWarmup` si no alcanzan; tolera pares faltantes en un `Bar`.
- CLI: `download-data --pairs ... --timeframes 1h 4h --since 2019-01-01`, `data-info`, `data-check`.
- Fixtures commiteados: `tests/fixtures/ohlcv/BTCUSDT-4h-2023.parquet` y `ETHUSDT-4h-2023.parquet` (~2000 velas c/u). Toda la suite unitaria usa fixtures o series sintéticas; `data/` está gitignored.

Verificación: unit con exchange falso; `-m network` contra endpoints públicos. DoD: los 8 pares del universo en 1h y 4h desde 2019 (o desde su listado) en `data/`; `data-check` sin hallazgos fuera de los huecos registrados; descarga incremental idempotente.

### Fase 3 — Indicadores y contrato de estrategia (M)

Entregables:
- `indicators/`: `sma`, `ema`, `rsi`, `macd`, `atr`, `adx`, `bbands`, `highest/lowest`, `cross_above/cross_below`. Cada indicador documenta su semilla y warmup/NaN. Tests contra fixtures TA-Lib (`scripts/gen_indicator_fixtures.py`, grupo `fixtures`) **tras burn-in de 5 × período** con `rtol 1e-6`; primeros valores contra fixtures propios.
- `strategy/base.py`: `Strategy` protocol (`name`, `Params` pydantic, `warmup_candles` ≥ 5 × período más largo → 1000 velas para EMA200, `compute_indicators(df, params) -> df`, `on_candle(ctx) -> Signal`), `StrategyContext` (fila actual y ventana como arrays numpy precomputados, sin copiar el DataFrame por vela; posición abierta; equity; cash), registro de estrategias.
- `strategy/strategies/ema_trend.py` + `docs/strategy/ema-trend-v1.md` (§2.2 completa).
- `validation/equivalence.py`: para `t` aleatorios, `compute_indicators(data[:t])` vs `compute_indicators(data[t−warmup:t])` con `rtol 1e-4`, y señal de `data[:t]` vs señal de `data[:t+k]` truncada en `t` idéntica. Un solo test cubre lookahead y paridad backtest/live (en backtest los indicadores se precomputan vectorizados por par; en live se recomputan sobre la ventana).
- Agente `strategy-researcher`; skill `/new-strategy`.

DoD: tests de indicadores y equivalencia en verde; `ema_trend` genera señales sobre los fixtures.

### Fase 4 — Motor async, broker simulado, backtesting y registro (L)

Entregables:
- `engine/engine.py` **async** desde el día 1 (`MarketFeed` es `AsyncIterator[Bar]`; `BacktestRunner` usa `asyncio.run`), loop de §2.1; `engine/position_manager.py` (niveles de stop/trailing → `Broker.set_stop`).
- `persistence/store.py`: `TradeStore` protocol (`save_order/save_fill/save_position/snapshot_equity/load_open_positions`) + `InMemoryStore`.
- `risk/sizing.py` (fixed-fractional por distancia al stop, topes sobre cash libre) + `RiskManager` mínimo: máx. posiciones, exposición máx. por par/total, `min_notional` en entradas y salidas, ranking de señales. Nunca bloquea salidas.
- `execution/simulated.py`: órdenes `PENDING` llenadas al `open` siguiente; stops con gap-through (§2.1); slippage en bps; fee 0.10% descontado del **activo recibido** (base en compras, quote en ventas) o 0.075% en quote con `pay_with_bnb`; venta = `quantize_qty(qty_neta, step, ROUND_DOWN)`, resto a ledger `dust` (fuera del equity operativo, reportado aparte); salida con notional < `min_notional` → rechazo con `reason_code` y posición `STUCK` (alerta).
- `backtest/metrics.py`: retorno total, CAGR, Sharpe y Sortino sobre retornos **diarios** (equity remuestreada a 1D, rf = 0, √365), Calmar, max DD y duración (equity mark-to-market por `Bar`), win rate, PF, expectancy, duración media, exposición, fees, shortfall medio, n trades. `backtest/report.py` (REPORT.md, equity.png con DD, trades.csv, equity.csv); benchmark buy & hold.
- `persistence/experiments.py`: escribe artefactos; `experiments list|show|compare|sync` leen `runs/*/metrics.json` y regeneran `REGISTRY.md`.
- CLI `backtest --config configs/backtest.yaml [--strategy --pairs --from --to --set k=v]` (`--to` excluye el holdout por defecto).
- ADR-0005 registro de experimentos. Agente `backtest-analyst`; skills `/backtest`, `/experiment-review`.

Verificación: (a) serie sintética donde una señal al cierre `t` produce exactamente un fill en `open(t+1)`; (b) tendencia perfecta → N trades esperados; rango → sin entradas; (c) matemática de fees en base/quote, slippage, gap-through, dust; (d) `hypothesis` sobre series aleatorias: cash ≥ 0, qty ≥ 0, equity sin NaN, nunca dos posiciones del mismo par; (e) reproducibilidad: mismo config → bloque `metrics` idéntico (`rtol 1e-9`); (f) métricas contra valores a mano.
DoD: `EXP-0001` buy & hold BTC, `EXP-0002` equiponderado, `EXP-0003` `ema_trend` default BTC+ETH 4h 2019 → inicio del holdout, con veredicto.

### Fase 5 — Riesgo y protecciones (M)

Entregables:
- `risk/manager.py` completo: pérdida diaria máxima (día UTC) → sin entradas hasta el día siguiente; circuit breaker por DD desde el pico → sin entradas hasta intervención manual; cooldown tras N pérdidas seguidas y tras stop por par; kill switch (archivo `STOP` o comando) = sin nuevas entradas, `--flatten` opcional para cerrar todo. Toda decisión → `reason_code` logueado.
- Backtests de la Fase 4 re-ejecutados con protecciones para medir costo/beneficio (registrados). Agente `risk-auditor`.

Verificación: unit + `hypothesis` sobre invariantes (exposición ≤ límite, nunca orden < `min_notional`, nunca una salida bloqueada). DoD: invariantes probadas; experimento con/sin protecciones registrado.

### Fase 6 — Validación, optimización y gate (L, iterativa)

Entregables:
- `validation/walkforward.py` (IS 24 m / OOS 6 m rodante, anclado opcional; OOS concatenado), `validation/optimizer.py` (optuna TPE, solo IS, objetivo configurable: Sharpe/Calmar/PF con penalización por pocos trades, semilla registrada), `validation/plateau.py` (±20% uno a la vez + vértices), `validation/montecarlo.py`, `validation/regimes.py` (por año).
- `docs/GATES.md` final con §2.3; skill `/walkforward`.
- Iteración de la estrategia: universo ≥ 4 pares, `entry_mode` cross vs state, 1h vs 4h. Cada iteración = spec nueva (`ema-trend-v2.md`), experimentos registrados, veredicto. Presupuesto: 3–4 iteraciones antes de replantear la familia. El holdout se toca **una vez**, al final, con `--include-holdout`.

DoD: `WF-`/`OPT-` registrados; decisión go / no-go / iterar en `REGISTRY.md`. **No se pasa a paper sin cumplir el gate.**

### Fase 7 — Persistencia SQLite, feed en vivo y paper trading (L)

Entregables:
- `persistence/sqlite.py`: `SqliteStore` (misma interfaz que `InMemoryStore`), tablas `orders`, `trades`, `positions`, `equity_snapshots`, `events`; `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`; SQLAlchemy sync; un único proceso escritor; DBs separadas `paper.db`, `testnet.db`, `live.db`.
- `data/feeds.py` → `LiveFeed`: bootstrap con `fetch_ohlcv(limit=warmup+2)` por par descartando la vela en formación; poll a `close + 3 s`, reintentos cada 2 s hasta ver la vela `t+1`; reconexión con backoff; emite `Bar`s.
- `execution/paper.py`: `PaperBroker` (fill al `open` de la vela en formación + slippage) + `StopWatcher` cada 60 s.
- Recuperación al reiniciar: posiciones desde DB con `stop_price` y `highest_close_since_entry` persistidos; los cierres perdidos **no** generan entradas retroactivas pero sí evalúan sus `low` contra stops abiertos.
- `observability/status.py`: `logs/status.json` (equity, posiciones, último `Bar`, errores recientes, `heartbeat_ts`) por ciclo; `HEALTHCHECK` de Docker y `/paper-status` leen ese archivo, no la DB. Consultas históricas vía `docker compose exec bot tradingbot status|trades`.
- `engine` con shutdown ordenado (SIGTERM); `compose.yaml` perfil `paper` con `restart: unless-stopped`; logs JSON rotados.
- CLI `paper`, `parity --db db/paper.db --from --to` (re-ejecuta el backtest sobre el período y compara señal a señal y trade a trade por `client_order_id`; reporta % de coincidencia y bps de desvío; registra `PAR-`).
- `docs/runbooks/paper.md`: desactivar suspensión de Windows, Docker Desktop al inicio, deriva de reloj (`wsl --shutdown` + reinicio de Docker Desktop), Windows Update. Skill `/paper-status`.

Verificación: integración con feed simulado acelerado; reinicio con posición abierta; `parity` sobre 1 semana. DoD: 72 h en Docker sin crash con estado persistido y recuperado. Desde acá el paper corre en segundo plano ≥ 8 semanas; cada cambio en `strategy/`, `risk/`, `engine/` o `execution/` reinicia el reloj.

### Fase 8 — Telegram y observabilidad (M)

Entregables:
- `notify/telegram.py` (mismo event loop del engine): comandos `/status /balance /positions /trades /profit /daily /pause /resume /stop /health`; alertas de entrada, salida, stop, circuit breaker, error, reconexión, `STUCK`; resumen diario (PnL, equity, DD, shortfall, errores) a hora configurable en `notify.timezone`; whitelist por `chat_id`; niveles `on/silent/off` por evento.
- `docs/runbooks/incident.md` (bot caído con posición abierta, exchange en mantenimiento, clave revocada, stop nativo ejecutado sin que el bot lo viera).

DoD: alertas y comandos funcionando en el celular contra paper.

### Fase 9 — Analista LLM (M)

Entregables:
- `analyst/context.py`: contexto compacto de una corrida (métricas, regímenes, peores/mejores trades, params, comparación con corridas previas). `analyst/client.py`: `anthropic` SDK, `claude-opus-5`, thinking adaptativo, streaming, `client.messages.parse()` → `AnalysisReport` (resumen, red flags de overfitting, hipótesis, experimentos sugeridos con params), sistema estable cacheado, tokens/costo registrados. Sin herramientas: solo lee artefactos y escribe markdown. Antes de codear: skill `claude-api` + `python/claude-api/README.md`.
- CLI `analyze experiment <id>`, `analyze paper --days 7`, `analyze compare <id> <id>`; ADR-0006 LLM fuera del loop; skill `/analyze`.

DoD: 3 análisis revisados por el usuario y considerados útiles; costo por análisis registrado.

### Fase 10 — Broker real, testnet y preparación para live (L)

Entregables:
- `execution/binance_live.py`: `BinanceBroker` (ccxt async): market/limit con `params={'clientOrderId': ...}` (mismo id en reintentos; `fetch_order` por `clientOrderId` para confirmar), fills parciales y timeouts, `amount_to_precision` (trunca) / `price_to_precision`, **stop nativo primario** (§2.1) + chequeo por software de respaldo, cancelar stop antes de vender por señal, `options.adjustForTimeDifference=True`, `recvWindow=10000`, mapeo de errores (`-1013` filtros, `-2010` rechazo, `-1021` timestamp, `-1003` rate limit, `-2015` permisos/IP, `-2008` clave de otro entorno).
- `execution/reconciliation.py`: al arrancar y cada N minutos compara órdenes abiertas, stops en reposo y balances con la DB; discrepancia → alerta y pausa de entradas.
- **Binance Spot Testnet** (`set_sandbox_mode(True)` → `testnet.binance.vision`, claves con login de GitHub): perfil `testnet` de compose, `testnet.db`, tests `-m testnet` del ciclo entrada → stop nativo → salida. Limitaciones: solo `/api`, reset mensual, pocos símbolos. Alternativa: Demo Trading (`enable_demo_trading(True)`, claves propias, excluyente con sandbox).
- Seguridad: API key con *Reading* + *Spot Trading*, sin retiros, IP whitelisted (sin IP se borra a los 90 días); `.env.live` solo en perfil `live`; triple confirmación.
- `docs/runbooks/live.md`, checklist de go-live en `docs/GATES.md`; skill `/live-checklist`.

DoD: ciclo completo en testnet; checklist en verde por `risk-auditor`; `parity` de paper dentro de umbral; el usuario define capital inicial.

### Fase 11 — Live con capital mínimo y operación (ongoing)

- Arranque con capital pequeño. Semanal: live vs paper vs backtest del mismo período (`parity`, shortfall). Mensual: revisión con el analista. Aumento de capital solo tras N semanas dentro de banda.
- Backlog: websockets (`ccxt.pro`), datos 1m/5m para stops más fieles en backtest, multi-timeframe, segunda estrategia (mean reversion para rangos) y portfolio de estrategias, SQLite de experimentos, dashboard web, polars, abstracción para futures.

---

## 5. Verificación end-to-end

- Fase 0: `uv run pytest`, `uv run ruff check .`, `uv run mypy src`, `docker compose build`, `docker compose run --rm bot tradingbot doctor`.
- Fases 2–6: CLI sobre datos reales; cada corrida deja artefactos en `experiments/runs/` y una fila en `REGISTRY.md` vía `experiments sync`.
- Fase 7+: `docker compose --profile paper up -d`, `/paper-status`, `tradingbot parity`, comandos de Telegram.
- Fase 10: suite `-m testnet`.
- Siempre: test de equivalencia y suite unitaria antes de `/phase-close`.

---

## 6. Notas de investigación (2026-09-07)

### 6.1 freqtrade (docs stable)

Adoptado (adaptado): orden del loop live (trades abiertos → pairlist → OHLCV → indicadores/señales → órdenes abiertas → salidas → entradas), disparado acá por `Bar` cerrado y no por tick de 5 s; contrato indicadores/señales + `startup_candle_count` → `compute_indicators` + `on_candle` + `warmup_candles`; precedencia explícita de salidas (freqtrade: señal → stop → ROI → trailing asumiendo high antes que low; nosotros: stop con supuesto conservador); protecciones `StoplossGuard`, `MaxDrawdown`, `CooldownPeriod`, `LowProfitPairs` → base del `RiskManager`; dry-run con wallet simulada y DB por modo; Telegram con niveles por evento y `authorized_users`; `--timeframe-detail` → backlog; Optuna con precisión limitada a 0.001.

Corregido: dos motores con distinta cadencia (raíz de discrepancias) → un engine; dataframe completo que facilita lookahead + dos comandos para detectarlo después → vista truncada + test de equivalencia; backtest sin slippage ni fills parciales ("all orders are filled at the requested price") → modelo de fill realista; límites de precisión históricos no disponibles → mismo supuesto, documentado; optimización sin walk-forward ni OOS y params no usables en indicadores → walk-forward integrado y params como entrada de `compute_indicators`; config JSON sin tipos pisada por atributos de estrategia → pydantic con precedencia explícita; riesgo delgado → `risk/` con presupuesto de portfolio; TA-Lib obligatorio → indicadores propios.

### 6.2 ccxt y Binance Spot

- ccxt 4.5.78 (MIT, Python ≥ 3.10): `ccxt`, `ccxt.async_support`, `ccxt.pro` en un paquete. Binance pro soporta `watch_ohlcv(_for_symbols)`, `watch_orders`, `watch_balance`; el user-data stream no se des-suscribe, se cierra con `await exchange.close()`.
- `fetch_ohlcv`: default 500, máx. 1000 en spot; `params['until']`; `params={'paginate': True}`. Klines pesan 2.
- Rate limit: `enableRateLimit=True` por defecto (`rateLimit=50` ms con costos por endpoint). Respetar `X-MBX-USED-WEIGHT-1M`, 429 y 418 (ban 2 min a 3 días). Límites hoy: 6000 weight/min, 100 órdenes/10 s, 200k/día. BTC/USDT: tickSize 0.01, stepSize 0.00001, minNotional 5 USDT, PERCENT_PRICE_BY_SIDE.
- Órdenes: `create_order(symbol, type, side, amount, price, params)`; `clientOrderId`; `STOP_LOSS`/`STOP_LOSS_LIMIT` con `stopPrice`/`triggerPrice`; `params={'test': True}` valida sin colocar; **sin OCO unificado** (el OCO lo gestiona el bot).
- Excepciones: `RateLimitExceeded`, `DDoSProtection`, `ExchangeNotAvailable`, `RequestTimeout` descienden de `NetworkError` (reintentable); `InvalidOrder`, `InsufficientFunds`, `AuthenticationError`, `BadSymbol` de `ExchangeError` (no reintentar).
- Fees VIP0: 0.10% maker/taker; 0.075% con BNB. Binance cobra la fee en el activo recibido salvo con BNB.
- Entornos de prueba: testnet (`testnet.binance.vision`, sandbox) y Demo Trading (`demo-api.binance.com`); claves no intercambiables (`-2008`).

### 6.3 Ecosistema Python (PyPI)

- pandas 3.0 (Copy-on-Write, strings PyArrow) → `>=3.0,<3.1`. numpy 2.5 exige ≥ 3.12 → Python 3.12.
- pandas-ta: repo eliminado, releases pagos anunciados, licencia incierta → excluido. `ta` (MIT) congelado desde 2023. TA-Lib 0.7.1 con wheels `win_amd64` → grupo `fixtures`.
- python-telegram-bot 22.8 asyncio puro, no thread-safe. optuna 5.0. anthropic SDK 1.4 (`httpx2`).
- Semillas: TA-Lib siembra EMA/ATR/ADX con SMA de las primeras N velas; pandas `ewm(adjust=False)` con la primera vela. Por eso los tests comparan tras burn-in.
