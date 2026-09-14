# ADR-0011: Persistencia SQLite, feed en vivo y paper trading

- Estado: aceptado
- Fecha: 2026-09-14
- Fase: 7

## Contexto

Hasta la Fase 6 el `Engine` corrió solo en backtest: `HistoricalFeed` → `SimulatedBroker` → `InMemoryStore`, con el proceso vivo de punta a punta. Paper (y después testnet/live) es un proceso de larga duración en Docker que se reinicia, pierde red, y tiene que llegar a una vela nueva cada 4 horas sin lookahead y sin decidir cierres con el reloj local. Los puertos de ADR-0002 (`MarketFeed`, `Broker`, `TradeStore`) ya existen; esta ADR fija cómo se implementan para paper y qué se persiste para recuperar el estado. La regla dura 3 manda: mismo `Engine`, misma precedencia intra-vela y mismo modelo de fills y stops; acá no se agrega ningún camino "solo para paper".

## Decisión

### `SqliteStore` (`persistence/sqlite.py`)

- SQLAlchemy 2.0 **Core**, síncrono, `sqlite+pysqlite`, un archivo por modo (`db/paper.db`, `db/testnet.db`, `db/live.db` = `BotConfig.db_path`), volumen nombrado en compose (SQLite sobre bind mount de Windows tiene problemas de locking). PRAGMAs por conexión: `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `foreign_keys=ON`. Un solo proceso escritor; los lectores (`status`, `trades`, `parity`) abren la misma DB en modo lectura.
- Esquema: cada tabla tiene **columnas indexadas para consultar** (par, timestamps, estado, `client_order_id`) y una columna `data` con el **JSON del modelo pydantic** (`model_dump(mode="json")`, `Decimal` como texto: sin pérdida). Tablas `orders` (PK `client_order_id`, la última versión gana), `fills`, `positions` (PK par: abiertas), `trades` (única por `exit_client_order_id`), `equity_snapshots` (PK `ts`), `events`, y `state` (clave/valor JSON) para lo que no es dominio: `schema_version`, última vela procesada, estado de las protecciones, cash y dust. Motivo: fidelidad del `Decimal`, evolución de esquema barata (los campos nuevos viven en el JSON), y las consultas del bot son por par y por tiempo, no relacionales.
- `SqliteStore` implementa el protocolo `TradeStore` sin cambios (el `Engine` no sabe con qué store corre) y agrega `save_state/load_state`, `last_snapshot()` y `close()`. `schema_version` distinto al esperado → error explícito; las migraciones se hacen a mano y quedan documentadas en esta ADR.

### `LiveFeed` (`data/feeds.py`)

- Bootstrap: `fetch_ohlcv` por par con `limit = warmup + 2`, descartando la vela cuyo `open_time + tf_ms > now_exchange` (en formación). `warmup_bars()` devuelve esas velas como `Bar`s (mismo contrato que `HistoricalFeed`: el filtro de mercado se siembra con ellas).
- Cierre de vela: el reloj es el del exchange (`BinanceExchange.now_ms`, offset re-medido cada hora). A `close_time + 3 s` se pide la última vela; el cierre de `t` se confirma **por la aparición de la vela `t+1`** en la respuesta, nunca por el reloj local. Si no aparece, se reintenta cada 2 s hasta 60 s; después, backoff exponencial (2 → 60 s) ante errores de red, con log. Un par que no llega a tiempo sale del `Bar` (hueco tolerado, como en backtest) y se anota un evento.
- Reanudación tras reinicio: el feed arranca desde `state.last_bar_open_time` si existe: las velas cerradas entre esa y ahora se emiten primero como `Bar`s **de reposición** (`bar.replay = True`) y después sigue en vivo.

### `PaperBroker` + `StopWatcher` (`execution/paper.py`)

- `PaperBroker` reutiliza la matemática del `SimulatedBroker` (slippage en contra, tick, fee en el activo recibido, `insufficient_funds`) y cambia solo el precio de referencia: una orden `PENDING` se llena al **`open` de la vela en formación** (`fetch_ohlcv(limit=2)[-1].open`, leído una vez por cierre y compartido por todas las órdenes de ese ciclo) inmediatamente después del cierre, no al `open` de un `Bar` futuro. `ref_price` = ese `open`; `fill_ts` = hora del exchange al llenar.
- `StopWatcher`: tarea asyncio que cada `execution.stop_watch_interval_s` (60 s) lee el último precio de cada par con stop en reposo (`fetch_ticker`) y, si `last ≤ stop`, registra el fill al `last` con slippage, con `fill_ts` = hora observada. Emula la orden nativa de la Fase 10; el `Engine` recibe el evento en el siguiente `on_bar` del broker, con la misma precedencia (fills al open → stops → …). Al cierre de la vela el broker también aplica la regla de gap/toque con el `low` de la vela cerrada por si el watcher no vio el toque (mismo código que el simulado).

### Recuperación tras reinicio

- Al arrancar en paper/live el `Engine` se construye desde la DB: posiciones abiertas (`positions`, con `stop_price` y `highest_close_since_entry`), `cash` y `dust` del `state`, `last_bar_open_time`, y el estado de las protecciones (pico de equity, halt diario, pausa, cooldowns, `undefined_days` del filtro) serializado por `Protections.to_state()/from_state()`.
- Los cierres perdidos durante la caída se procesan como `Bar`s de reposición: **no generan entradas nuevas** (la señal se evalúa pero las `ENTER_LONG` se rechazan con `ReasonCode.REPLAY`), sí marcan a mercado, actualizan trailing y evalúan `low ≤ stop` de las posiciones abiertas con la regla de gap del broker. Los stops en reposo se vuelven a publicar en el broker desde las posiciones cargadas.
- Órdenes `PENDING` al momento de la caída: en paper se descartan con evento `pending_dropped` (no hubo exchange que las llenara); en la Fase 10 el `BinanceBroker` las consulta por `origClientOrderId` antes de decidir.

### Observabilidad y operación

- `observability/status.py` escribe `logs/status.json` (atómico) al final de cada ciclo: `heartbeat_ts`, `mode`, `last_bar`, equity, cash, posiciones con stop, protecciones, últimos errores. El `HEALTHCHECK` de Docker falla si `now − heartbeat_ts > 2 × timeframe + 5 min`. `/paper-status` y `tradingbot status` leen ese archivo, no la DB.
- Logs `structlog` JSON a stdout (Docker los rota) y a `logs/{mode}.jsonl` con rotación por tamaño.
- Shutdown ordenado: `SIGTERM`/`SIGINT` → se termina el `Bar` en curso, se escribe el `status.json` final y se sale con 0; el kill switch por archivo sigue siendo la forma de frenar entradas sin apagar el proceso.
- CLI: `tradingbot paper --config configs/paper.yaml` (perfil `paper` de compose con `restart: unless-stopped`), `tradingbot status`, `tradingbot trades`, `tradingbot parity --db db/paper.db --from --to` (re-ejecuta el backtest sobre el período con la misma config y compara señal a señal y trade a trade por `client_order_id`; registra `PAR-`).

## Alternativas consideradas

- **ORM de SQLAlchemy con tablas normalizadas**: más código, migraciones por cada campo nuevo del dominio, y `Decimal` en SQLite termina como `NUMERIC`/float. El JSON con columnas índice es más simple y exacto.
- **Cierre de vela por reloj local + margen**: es lo que hace freqtrade y es la fuente de velas "cerradas" que después cambian. Confirmar por la aparición de `t+1` cuesta 3–10 s de latencia y elimina el problema.
- **Websockets (`ccxt.pro`)**: menos latencia, más estados de reconexión. Con velas de 4h, REST alcanza; queda en backlog (ADR-0004).
- **Fill del paper al `open` del `Bar` siguiente (idéntico al backtest)**: obligaría a esperar 4 h para llenar una orden decidida al cierre; el `open` de la vela en formación es el mismo precio teórico, disponible al instante, y `parity` mide la diferencia real.
- **Persistir solo posiciones y reconstruir el resto**: el cash y las protecciones no se pueden reconstruir sin el historial completo de fills; el `state` KV es más barato que re-derivarlos.

## Consecuencias

- `Bar` gana el flag `replay` (default `False`); `ReasonCode.REPLAY`; `Protections.to_state/from_state`; `MarketFeed` en vivo necesita el reloj del exchange, así que `BinanceExchange` deja de ser solo de descarga.
- Tests: `SqliteStore` con archivo temporal (reapertura, upsert, orden), `LiveFeed` con exchange falso y reloj simulado (confirmación por `t+1`, reintentos, reposición), `PaperBroker` con precios falsos (fill al open en formación, `StopWatcher` toca, gap al cierre), recuperación con posición abierta (stop re-publicado, sin entradas retroactivas), `status.json`. Nada de esto toca Binance real; `-m network` cubre el bootstrap con velas reales.
- El DoD de la fase (72 h en Docker sin crash) lo corre el usuario con `docker compose --profile paper up -d`; desde ahí `regime_bh` es la carga de prueba del paper hasta que cierre su Gate 1 (ROADMAP, Fase 7).
- Deuda que queda para la Fase 10: quote comprometido en órdenes `PENDING` como campo del snapshot, cuantización del stop al `tickSize`, consulta por `origClientOrderId`.
