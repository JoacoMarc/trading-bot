# ADR-0002: Un solo camino para backtest, paper y live

- Estado: aceptado
- Fecha: 2026-09-07
- Fase: 0

## Contexto

freqtrade tiene dos motores: el loop live (event-driven, cada ~5 s) y el backtesting (indicadores vectorizados + replay por vela) con distinta cadencia de callbacks. Esa dualidad es la raíz de las discrepancias backtest-vs-real y de la necesidad de herramientas aparte para detectar lookahead. Queremos que el resultado de un backtest sea una predicción verificable de lo que el bot hace en paper y live, y poder medir la desviación.

## Decisión

Un único `Engine` **async** consume `Bar`s de un `MarketFeed` y ejecuta contra un `Broker`; los tres modos solo cambian las implementaciones de los puertos.

**Puertos** (Protocols): `MarketFeed` (`AsyncIterator[Bar]`), `Broker`, `TradeStore`, `Notifier`, `Clock`.

**`Bar` multi-par**: todas las velas del mismo cierre para todos los pares (tolera pares faltantes). Los pares se procesan en orden alfabético fijo. Equity = USDT libre + Σ qty neta × close del `Bar`.

**Precedencia intra-vela**, idéntica en los tres modos:

1. Fills de órdenes pendientes al `open` (+ slippage).
2. Stops: si `open ≤ stop` → fill al `open` (gap); si no y `low ≤ stop` → fill al `stop`; siempre con slippage. Supuesto conservador: si stop y objetivo caen en la misma vela, se asume que tocó el stop.
3. Mark-to-market al `close` y snapshot de equity.
4. `Strategy.on_candle` por par → `Signal`.
5. `RiskManager.evaluate` → `OrderIntent`s o rechazos con `reason_code`; ranking determinístico si hay más entradas que slots; topes sobre cash libre; las salidas nunca se bloquean.
6. `Broker.submit(intent)` → `Order(PENDING)` que se llena en el paso 1 del `Bar` siguiente. `PositionManager` publica niveles de stop con `Broker.set_stop`.
7. Persistencia y notificaciones.

**Fills**: señal en `t` → fill al `open(t+1)`. `SimulatedBroker` lo hace al llegar la vela; `PaperBroker` inmediatamente al `open` de la vela en formación; `BinanceBroker` envía market order. Todo `Fill` guarda `ref_price`, `fill_price`, `signal_ts`, `decision_ts`, `fill_ts`, `fee_amount`, `fee_asset`.

**Stops**: los ejecuta el `Broker`, no el `PositionManager`. Simulado: regla del paso 2. Paper: `StopWatcher` cada 60 s contra el último precio. Live: orden nativa en reposo en el exchange (`STOP_LOSS` o `STOP_LOSS_LIMIT` con precio 0.5 % bajo el stop), cancelada y repuesta cuando el trailing sube; el chequeo por software al cierre es respaldo.

**Paridad medible**: `tradingbot parity` re-ejecuta el backtest sobre el período de paper y compara señal a señal y trade a trade por `client_order_id`. Es criterio del gate Paper → Live.

## Alternativas consideradas

- **Backtest vectorizado separado** (como freqtrade): más rápido, pero duplica la lógica de ejecución y garantiza divergencias.
- **Engine síncrono en backtest y async en live**: obliga a reescribir el núcleo probado justo antes del paper. El overhead de asyncio sobre ~140k eventos es despreciable.
- **Stops evaluados solo al cierre de vela en paper/live**: el fill real puede quedar 3–8 % debajo del stop en 4h; rompe la paridad con el backtest y expone a pérdidas mayores. Por eso el stop nativo es primario.
- **Velas sueltas por par en orden temporal**: hace que el equity se marque con precios de distinto instante y que "máx. N posiciones" dependa del orden de llegada.

## Consecuencias

- Backtest y live comparten estrategia, riesgo, sizing, contabilidad de fees y dust; un bug se arregla en un solo lugar.
- El backtest paga el costo de simular bar a bar (no vectorizado): aceptable para 8 pares × 4h; optuna se mantiene barato con `StrategyContext` sobre arrays precomputados.
- Reglas duras: sin atajos "solo para backtest"; el `RiskManager` nunca bloquea salidas; señal en `t` nunca usa `close(t)` como precio de fill.
- La paridad tiene una métrica y un umbral (≥ 95 % de señales, ≤ 15 bps de desvío) en `docs/GATES.md`.
