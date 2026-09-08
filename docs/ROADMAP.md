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

## Fase 2 — Adapter de exchange y capa de datos (M) · `cerrada (2026-09-08)`

- [x] `exchange/binance.py` (MarketInfo con tick/step, OHLCV paginado, límites de exchangeInfo, fetch_time, retry selectivo, mapeo de errores) + `markets_snapshot.json`
- [x] `data/`: ParquetStore (parquet `decimal128`, ADR-0005), Downloader incremental (descarta vela en formación, upsert), QualityChecker (+ registro versionado `configs/binance_gaps.json`), HistoricalFeed que emite `Bar`
- [x] CLI `download-data`, `data-info`, `data-check`, `data-markets`; `DataConfig` con universo, timeframes y `since` por defecto
- [x] Fixtures parquet 2023 commiteados: sintéticos (`tests/fixtures/ohlcv/synthetic-*.parquet`) para store/feed/CLI y reales (`BTCUSDT-4h-2023.parquet`, `ETHUSDT-4h-2023.parquet`, generados el 2026-09-08 con `--from-data data`) para los indicadores de la Fase 3
- [x] Tests: 98 nuevos con exchange falso (226 en total), `hypothesis` en el store, `-m network` contra endpoints públicos; mypy strict y ruff limpios
- [x] Revisión del `trading-code-reviewer` aplicada (0 bloqueantes, 6 importantes): klines crudas como string en vez de `fetch_ohlcv` (float), margen de seguridad de 2 s al cierre, serie contigua sin huecos autoinfligidos (continuar desde la última vela, paginado que no se corta por página corta, `--register` verifica contra el exchange), persistencia parcial cada 10 páginas, warmup tolerante a huecos, 418 sin reintento + `Retry-After`. Menores aplicados: retry sobre `OperationFailed`, redacción de query strings, escrituras atómicas de JSON, `DataError` ante parquet ajeno. Deuda en ADR-0005
- [x] DoD verificable sin red: 226 tests, ruff, mypy; descarga incremental idempotente y descarte de la vela en formación probados con exchange falso
- [x] Verificación con red y Docker en la PC del usuario (2026-09-08): `download-data` completo (16 series: ~67k velas 1h y ~16.8k 4h por par; LINK desde 2019-01-16, SOL desde 2020-08-11), segunda corrida idempotente (0 nuevas, 0 actualizadas), `data-check --register` confirmó 178 huecos reales en `configs/binance_gaps.json` y `data-check` sale limpio, `pytest -m network` 4/4, `docker compose build` + `doctor` en contenedor OK
- [x] Fixes de Fase 2 que reveló esa verificación: `Pair` acepta activos de 1 carácter (Binance lista `T/USDT`) y `parse_market` ignora símbolos no representables en vez de tumbar `load_markets`; `markets_snapshot.json` regenerado desde el exchange (`data-markets --refresh --update-snapshot`: BNB tick 0.1→0.01, XRP step 1→0.1, `max_qty` de varios pares, `raw_requests_per_5m` 300000); salida de la CLI en ASCII (`->`, `>=`) y `stdout.reconfigure(errors="replace")` porque la consola cp1252 de Windows crasheaba con `→`

## Fase 3 — Indicadores y contrato de estrategia (M) · `cerrada (2026-09-08)`

- [x] `indicators/core.py`: sma, ema, wilder, rsi, macd, true_range, atr, adx, bbands, highest/lowest, cross_above/below con semillas compatibles con TA-Lib; fixtures `tests/fixtures/indicators/talib-*.parquet` generados con `scripts/gen_indicator_fixtures.py` (TA-Lib 0.7.1); coinciden desde el primer valor válido (error relativo ≤ 2e-10, mismo patrón de NaN)
- [x] `strategy/base.py` (StrategyParams, OhlcvArrays como única frontera Decimal→float, StrategyContext con vistas hasta `index`, Strategy ABC con warmup = multiplicador × período más largo), `registry.py` (`@register`, `build_strategy` desde `StrategyConfig`)
- [x] `docs/strategy/ema-trend-v1.md` escrita antes del código; `strategies/ema_trend.py` (cross/state, régimen que no cierra, cooldown, stop ATR, trailing chandelier, strength = ADX)
- [x] `validation/equivalence.py`: `check_no_lookahead` (señal y trailing en `t` invariantes ante velas futuras, con y sin posición) y `check_window_equivalence` (serie completa vs ventana de warmup, rtol 1e-4; EMA200 con warmup 1200 da 1.4e-6); una estrategia con `shift(-1)` y otra con warmup corto son detectadas en tests
- [x] Agente `strategy-researcher`; skill `/new-strategy`
- [x] DoD: 270 tests (42 nuevos), mypy strict limpio (74 archivos), ruff; `ema_trend` default genera 4 entradas en BTC 2023 y pasa la equivalencia
- [x] Revisión del `trading-code-reviewer` aplicada (0 bloqueantes, 5 importantes): ATR = 0 ya no produce señal con stop = close (stop y trailing en Decimal a partir del close exacto); la equivalencia de ventana compara también **señal y trailing** (paridad 100 % en BTC y ETH 2023) y reporta `signal_match_rate`; `StrategyConfig.warmup_candles` solo puede ampliar el warmup (`effective_warmup`); `bars_since_exit` con semántica fija (0 = vela siguiente al fill de salida) y validado ≥ 0; `longest_period` cuenta doble ADX y ATR (Wilder). Menores: ADX no actualiza con DI⁺+DI⁻ = 0 (como TA-Lib), regex de nombre única, indicadores calculados una vez por slice, tolerancia de precisión en params. Tests: 326 (98 nuevos en la fase), invarianza de prefijo de todos los indicadores

## Fase 4 — Motor async, broker simulado, backtesting y registro (L) · `cerrada (2026-09-08)`

- [x] `engine/engine.py` async (loop de §2.1: fills al open → stops → mark-to-market → señales → salidas → entradas → trailing), `position_manager.py` (stop re-anclado al fill, trailing solo sube, `bars_since_exit`), `series.py` (`PrecomputedSeries`); `persistence/store.py` (`TradeStore` + `InMemoryStore`)
- [x] `risk/sizing.py` (fixed-fractional por distancia al stop, tope sobre cash libre × `cost_factor`, `minQty`/`minNotional`) + `RiskManager` mínimo (ranking por strength, slots con pendientes, exposición, `ReasonCode`; `exit_intent` nunca bloquea salvo filtros del exchange → `STUCK`)
- [x] `execution/broker.py` (`Broker`, `StopOrder`) y `simulated.py` (fill al open t+1 con slippage y tick, gap-through vs toque, fee en activo recibido o quote con BNB, sin fills parciales)
- [x] `backtest/`: métricas sobre retornos diarios (Sharpe, Sortino, Calmar, CAGR, max DD y duración, PF, expectancy, exposición, fees, shortfall), benchmarks buy & hold aparte del Engine, reporte (REPORT.md, equity.png, trades.csv, equity.csv), `runner.py`; `persistence/experiments.py` (ids por tipo, `metrics.json` con `meta` reproducible, `REGISTRY.md` regenerado); CLI `backtest`, `benchmark`, `experiments list|show|compare|sync`; `configs/backtest.yaml`
- [x] ADR-0006 registro de experimentos (el 0005 lo usó la Fase 2); agente `backtest-analyst`; skills `/backtest`, `/experiment-review`
- [x] Tests: 379 en total (53 nuevos): fill al open t+1 con slippage/fee/stop re-anclado, salida por señal y `bars_since_exit`, gap-through y toque, trailing solo sube, STUCK, ranking/`max_positions`, hueco de par, fee BNB, invariantes con hypothesis (cash ≥ 0, ≤ 1 posición por par, trades = ventas), métricas a mano, benchmark exacto, registro y CLI sobre store temporal, reproducibilidad (`metrics` idéntico entre dos corridas)
- [x] Revisión del `trading-code-reviewer` aplicada (2 bloqueantes, 6 importantes): una compra cuyo costo al open supera el cash libre se **rechaza** (`insufficient_funds`, como `-2010`) en vez de dejar cash negativo; el benchmark arranca su curva en `initial_cash` antes de pagar costos (comparable con la estrategia); los pares con salida pendiente no ocupan un segundo slot; un trailing en o sobre el close vende a mercado al open siguiente (Binance rechaza stops sobre el último precio); los stops que no pasan `minQty`/`minNotional` no se publican (`stop_unpublishable`, par sin protección); las salidas `STUCK` se reintentan cada vela; `config.yaml` congela el rango efectivo (`start`/`end`) para que recargarlo reproduzca la corrida; `longest_underwater_days` renombrado y drawdown anual contra el pico corriente. Menores: fee cuantizada a 8 decimales, `fill_ts` del toque de stop al close, `*` en el REGISTRY para corridas con árbol sucio, reintento de id al registrar, CLI captura `ValidationError`, spec detectada por versión. Deuda anotada abajo
- [x] DoD: EXP-0001 (B&H BTC) y EXP-0002 (equiponderado) `go (línea base)`; EXP-0003 (`ema_trend` default BTC+ETH 4h: +69.9 %, Sharpe 1.17, DD 7.2 %, PF 2.60, 79 trades) `iterar`. Veredictos del `backtest-analyst` en cada `REPORT.md`; EXP-0004..0006 (8 pares, `entry_mode=state`, `stop_atr_mult=3.0`) propuestos ahí

Deuda registrada (menores del revisor de la Fase 4): rendimiento para optuna (Fase 6: `Signal.hold` y `PortfolioSnapshot` pydantic por par y vela, `Bar`s reconstruidos por par en el runner, parquet completo releído por trial; cachear `OhlcvArrays` entre trials); `data_hash` sobre el parquet completo en vez del rango usado; `minNotional` de la salida evaluado al close de `t` y no al open de `t+1`; `bars_since_exit` cuenta `Bar`s globales (documentado); una salida por señal con hueco del par en `t+1` deja la posición sin stop hasta que el par reaparece; `REPORT.md` se genera desde una plantilla en código y no desde `experiments/TEMPLATE_REPORT.md` (ADR-0006 lo aclara); `MarketFeed.warmup_bars` sin consumidor hasta la Fase 7. Del análisis de EXP-0003: `Trade.pnl` no descuenta el costo de entrada del dust (Σpnl de `trades.csv` − Δequity = 12.96 USDT) y el `REPORT.md` no muestra el ledger de dust; falta un benchmark B&H escalado a la volatilidad de la estrategia; el criterio "ningún año con DD > 25 %" del gate debe fijar si el DD anual se mide contra el pico histórico (como hoy) o intra-año (Fase 6).

## Fase 5 — Riesgo y protecciones (M) · `en curso`

- [x] `risk/protections.py` + `RiskManager` (ADR-0007): pérdida diaria (día UTC, base = cierre del día anterior), circuit breaker por DD con reanudación configurable (`drawdown_resume_pct` o `drawdown_pause_days` con pico re-basado, automática en backtest; manual en paper/live), pausa tras N pérdidas seguidas, cooldown por par tras salida perdedora (stop o trailing), kill switch por archivo `logs/STOP` (`tradingbot stop [--flatten]` / `resume`) con `flatten` en el Engine; `ReasonCode` nuevos, eventos `protection_triggered/cleared`, `--set k=null` para apagar protecciones; agente `risk-auditor`; glosario (circuit breaker, kill switch, pérdida diaria, cooldown)
- [ ] Backtests con/sin protecciones registrados con veredicto: EXP-0004 sin protecciones (reproduce EXP-0003), EXP-0005 defaults, EXP-0006 agresivas

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
- Fase 2: la sesión remota de Claude Code no tiene salida a `api.binance.com` ni a `data.binance.vision` (403 del proxy): todo lo que toque Binance real (descarga, fixtures reales, `-m network`) se corre desde la máquina del usuario. En ccxt para Binance, `market["precision"]` son tick/step sizes (`precisionMode = TICK_SIZE`) y llegan como `float`; los valores exactos se leen como string desde `market["info"]["filters"]`. `itertuples` de pandas-stubs tipa cada atributo como una unión enorme que rompe `mypy --strict`: iterar columnas con tipos concretos (`iter_rows`). pyarrow no trae stubs (`ignore_missing_imports`). El `rateLimits` real no lo guarda ccxt tras `load_markets`: se pide `exchangeInfo` aparte (peso 20) y se cachea. Nunca pegar claves de API en el chat: quedan en la transcripción; las claves van a `.env*` y las de testnet/live solo las carga el usuario. El patrón `data/` sin anclar en `.gitignore`/`.dockerignore` ignoraba también el paquete `src/tradingbot/data/` (git no lo veía y Docker no lo copiaba): los directorios de estado se anclan a la raíz (`/data/`, `/db/`, `/logs/`).
- Fase 2 (verificación real): un snapshot de mercados escrito sin acceso al exchange es una suposición, no un dato; regenerarlo siempre con `data-markets --refresh --update-snapshot` y dejar que `pytest -m network` lo compare. Binance tiene activos de una sola letra (`T`). La consola de Windows usa cp1252: nada de `→`/`≥`/`✓` en la salida de la CLI. El hook `format_py.py` corre `ruff --fix` tras cada edición y borra imports que todavía no se usan: agregar el import y su uso en la misma edición. El reloj de la VM de WSL deriva (doctor en contenedor marcó -995 ms): `wsl --shutdown` + reinicio de Docker Desktop lo corrige.
- Fase 3: las semillas de TA-Lib (SMA para EMA, Wilder para RSI/ATR/ADX, ambas EMAs del MACD sembradas en `slow-1`) se reproducen exactas; el ADX exige un loop Python fiel a `ta_ADX.c`. Un warmup de 6x el período más largo deja la EMA200 a 1e-6 de la serie completa; con 5x llega a ~3e-4 y roza el rtol. La paridad hay que medirla sobre señales, no solo sobre indicadores: un cruce es discontinuo. Herramientas: `ruff --fix` en el hook borra imports que aún no se usan (agregar import y uso en la misma edición); los comandos Bash con heredocs largos fallan al parsear, usar Write para contenido extenso.
- Fase 4: el flujo limpio es commit del código → corridas → commit de artefactos; `git_dirty` marca con `*` toda corrida hecha con cambios trackeados sin commitear y esas corridas no son citables, y regenerar el REGISTRY no debe ensuciar el árbol (`git_info` excluye `experiments/` y archivos sin trackear). El broker simulado rechaza compras con `insufficient_funds` cuando el fill al open sale más caro que el cash disponible (gap alcista); sin eso el cash quedaba negativo. La equity de los benchmarks arranca en `initial_cash` antes de costos para que el retorno incluya la fee de entrada. Con BTC+ETH y `ema_trend` default salen ~13 trades/año, lejos de los 100 del gate: el universo de ≥ 4 pares es obligatorio antes de sacar conclusiones. Nunca `git add -A`: aparecieron claves reales en la plantilla de entorno y en un archivo suelto; stagear siempre por rutas explícitas y rotar las claves expuestas.
