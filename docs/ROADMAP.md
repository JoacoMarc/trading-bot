# ROADMAP

Copia viva del plan (detalle completo en [PLAN.md](PLAN.md)). Estados: `pendiente` · `en curso` · `cerrada (fecha)`. Cada fase se trabaja en sesiones propias con `/phase-start` y se cierra con `/phase-close`. Tamaño en sesiones: S = 1, M = 1–2, L = 2–4.

## Fase 0 — Fundación del repo y workspace de Claude (S) · `cerrada (2026-09-07)`

- [x] git, uv + Python 3.12, `pyproject.toml`, `uv.lock`, ruff/mypy/pytest configurados
- [x] `.gitignore`, `.gitattributes` (LF), `.editorconfig`, `.dockerignore`, `.env.example`
- [x] `Dockerfile` multi-stage + `compose.yaml` (volumen nombrado para `db/`)
- [x] CLI: `tradingbot --version`, `tradingbot doctor`
- [x] `CLAUDE.md`, agente `trading-code-reviewer`, skills `/phase-start` `/phase-close` `/adr`, `settings.json` (deny + hooks), `scripts/hooks/`
- [x] `docs/`: ROADMAP, PLAN, glossary, GATES (puntero), strategy/README, runbooks/README, ADR-0001..0004
- [x] `experiments/REGISTRY.md` + `TEMPLATE_REPORT.md`
- [x] Memoria de Claude con decisiones y perfil
- [x] DoD: pytest verde (30 tests), ruff y mypy limpios, `tradingbot doctor` OK contra Binance real
- [x] DoD: `docker compose build` (imagen `tradingbot:local`, ~1 GB) y `docker compose run --rm bot doctor` OK (offset -435 ms)
- [x] Primer commit

## Fase 1 — Dominio y configuración (S/M) · `cerrada (2026-09-07)`

- [x] `domain/`: Timeframe, Candle, Bar, Pair (quote USDT), Signal, OrderIntent (`client_order_id` determinístico), Order, Fill (fee_asset, ref_price, shortfall), Position (qty neta, stop, highest_close), Trade, PortfolioSnapshot, money, errores
- [x] `config/`: Mode backtest|paper|testnet|live, sub-configs, YAML + env + `.env`, precedencia CLI > env > YAML > defaults, secretos solo por env (rechazados en YAML), `parse_set` para `--set a.b=c`
- [x] `engine/clock.py` (`Clock`, `RealClock`, `SimClock`); `configs/backtest.example.yaml`, `configs/paper.example.yaml`
- [x] DoD: cobertura domain+config+engine 99 %, mypy strict limpio (35 archivos), hypothesis en cuantización, timeframes y client_order_id, 128 tests
- [x] Revisión del `trading-code-reviewer` aplicada: 2 bloqueantes (stop de `Position` por encima de la entrada; `Order.with_fill` sin validar) y 9 importantes (np.float64, precisión de `quantize`, `fee_quote` para fees en BNB, propósito en el `client_order_id`, `OrderIntent` BUY con stop obligatorio, `Bar` sin pares duplicados, `public_dump` recargable, `.env` con claves desconocidas, secretos por `--set`)

Deuda registrada (menores del revisor, para fases siguientes): quote comprometido en órdenes `PENDING` en `PortfolioSnapshot` (Fase 7); `Signal.ref_close` para paridad (Fase 3); `pnl_pct` sobre notional bruta; `Bar.candles` como mapping inmutable; separar `trigger_price` de `stop_price` en `OrderIntent` para órdenes `STOP_LOSS*` (Fase 10).

## Fase 2 — Adapter de exchange y capa de datos (M) · `en curso`

- [ ] `exchange/binance.py` (MarketInfo con tick/step, OHLCV paginado, límites de exchangeInfo, fetch_time, retry selectivo, mapeo de errores) + `markets_snapshot.json`
- [ ] `data/`: ParquetStore, Downloader incremental (descarta vela en formación, upsert), QualityChecker (+ `gaps.json`), HistoricalFeed que emite `Bar`
- [ ] CLI `download-data`, `data-info`, `data-check`; fixtures parquet 2023 commiteados
- [ ] DoD: 8 pares 1h+4h desde 2019 en `data/`, `data-check` limpio fuera de huecos registrados, incremental idempotente

## Fase 3 — Indicadores y contrato de estrategia (M) · `pendiente`

- [ ] `indicators/` con semilla documentada y tests vs fixtures TA-Lib tras burn-in
- [ ] `strategy/base.py` (Strategy, StrategyContext con arrays numpy, warmup ≥ 5× período), `strategies/ema_trend.py`, `docs/strategy/ema-trend-v1.md`
- [ ] `validation/equivalence.py` (lookahead + paridad de ventana)
- [ ] Agente `strategy-researcher`; skill `/new-strategy`

## Fase 4 — Motor async, broker simulado, backtesting y registro (L) · `pendiente`

- [ ] `engine/engine.py` async + `position_manager.py`; `TradeStore` + `InMemoryStore`
- [ ] `risk/sizing.py` + RiskManager mínimo (máx. posiciones, exposición, minNotional, ranking; nunca bloquea salidas)
- [ ] `execution/simulated.py` (fill open t+1, gap-through, fee en activo recibido, dust, STUCK)
- [ ] `backtest/` métricas diarias, reporte, benchmark; `persistence/experiments.py`; CLI `backtest`, `experiments list|show|compare|sync`
- [ ] ADR-0005 experimentos; agente `backtest-analyst`; skills `/backtest`, `/experiment-review`
- [ ] DoD: EXP-0001 (B&H BTC), EXP-0002 (equiponderado), EXP-0003 (`ema_trend` default) registrados con veredicto

## Fase 5 — Riesgo y protecciones (M) · `pendiente`

- [ ] `risk/manager.py`: pérdida diaria, circuit breaker por DD, cooldowns, kill switch (+ `--flatten`), reason codes
- [ ] Backtests con/sin protecciones registrados; agente `risk-auditor`

## Fase 6 — Validación, optimización y gate (L, iterativa) · `pendiente`

- [ ] `validation/`: walkforward (IS 24m / OOS 6m, OOS concatenado), optimizer (optuna, solo IS), plateau, montecarlo, regimes
- [ ] `docs/GATES.md` final; skill `/walkforward`
- [ ] Iteraciones de estrategia (≥ 4 pares, cross vs state, 1h vs 4h) con specs y veredictos; holdout una sola vez
- [ ] DoD: decisión go / no-go / iterar en REGISTRY

## Fase 7 — Persistencia SQLite, feed en vivo y paper trading (L) · `pendiente`

- [ ] `SqliteStore` (WAL, un escritor), `LiveFeed` (bootstrap, cierre por reloj del exchange), `PaperBroker` + `StopWatcher`
- [ ] Recuperación tras reinicio; `logs/status.json`; shutdown ordenado; perfil `paper` en compose
- [ ] CLI `paper`, `parity`; runbook paper; skill `/paper-status`
- [ ] DoD: 72 h en Docker sin crash; luego ≥ 8 semanas de paper

## Fase 8 — Telegram y observabilidad (M) · `pendiente`

- [ ] `notify/telegram.py` (comandos, alertas, resumen diario, whitelist); runbook de incidentes

## Fase 9 — Analista LLM (M) · `pendiente`

- [ ] `analyst/` con anthropic SDK (`claude-opus-5`, salida estructurada), CLI `analyze`, ADR-0006, skill `/analyze`

## Fase 10 — Broker real, testnet y preparación para live (L) · `pendiente`

- [ ] `BinanceBroker` (clientOrderId, stop nativo primario, fills parciales, errores), `reconciliation.py`
- [ ] Perfil `testnet`, tests `-m testnet`; seguridad de claves; runbook live; checklist go-live; skill `/live-checklist`

## Fase 11 — Live con capital mínimo y operación (ongoing) · `pendiente`

- [ ] Arranque con capital pequeño; revisión semanal (parity, shortfall) y mensual (analista); backlog

## Aprendizajes

- Fase 0: `uv` instalado vía `pip install uv`; `Python311\Scripts` agregado al PATH de usuario para que `uv` resuelva en shells nuevas (en esta sesión se usó `python -m uv`). Los hooks de `.claude/settings.json` se activan de inmediato y funcionan en Windows con `python "${CLAUDE_PROJECT_DIR}/..."`; el hook `guard_live` inspecciona el comando completo, así que sus casos de prueba viven en `tests/test_hooks.py` y no en la línea de comandos.
- Fase 0: Docker Desktop falló una vez al arrancar con `Wsl/Service/CreateInstance/CreateVm/HCS/0x800705aa` ("recursos insuficientes") con 16 GB de RAM y ~5 GB libres; el usuario lo levantó después y la build pasó. Si se repite antes del paper (Fase 7): cerrar apps pesadas, `wsl --shutdown`, crear `%USERPROFILE%\.wslconfig` con `[wsl2]` `memory=4GB` `processors=2`, reiniciar Docker Desktop. La imagen pesa ~1 GB (pandas, pyarrow, matplotlib, optuna); adelgazarla queda en backlog.
- Fase 0: `pre-commit run --all-files` no revisa nada si los archivos no están trackeados; hacer `git add` antes.
- Fase 1: `model_copy(update=...)` de pydantic **no revalida**; toda transición de estado que deba respetar invariantes (fills, status) reconstruye el modelo con `model_validate`. La fuente `.env` estándar de pydantic-settings agrega claves desconocidas al payload y con `extra="forbid"` rompe el arranque filtrando el valor: se reemplazó por una fuente que solo entrega campos conocidos. `np.float32` no es subclase de `float`; `to_decimal` acepta cualquier escalar con `__float__`. Binance solo exige `clientOrderId` único entre órdenes abiertas: el broker (Fase 10) debe consultar por `origClientOrderId` antes de reintentar.
