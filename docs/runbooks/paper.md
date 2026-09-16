# Runbook: paper trading

Proceso de larga duración en Docker (perfil `paper` de compose) que corre el mismo `Engine` del backtest con precios en vivo de Binance y órdenes simuladas (ADR-0011). Lo lanza y lo apaga el usuario, nunca una sesión de Claude.

## Arranque

1. `configs/paper.yaml` = copia de `configs/paper.example.yaml` (hoy `regime_bh` λ 0.5, la config de WF-0008 / EXP-0010). Sin secretos: el paper no necesita claves.
2. Requisitos del host: Docker Desktop iniciado (con "Start Docker Desktop when you sign in"), **suspensión de Windows desactivada** (Configuración → Sistema → Energía: "Nunca" con corriente), Windows Update con horas activas amplias y reinicio automático apagado, y `data/`, `logs/`, `db` (volumen) con permisos.
3. `docker compose build` si cambió el código; después `docker compose --profile paper up -d`.
4. Verificar en el primer minuto: `docker compose --profile paper logs -f paper` debe mostrar `arranque limpio` (o `reanudado desde la DB`), el bootstrap del warmup (1,212 velas de 4h para `regime_bh`) y `status en logs/status.json`. Después `uv run tradingbot status` (o `docker compose exec paper tradingbot status`).

El primer cierre puede tardar hasta 4 h. Hasta entonces `status` muestra la fase `arranque`/`corriendo` con la última vela del bootstrap.

## Qué mirar y cada cuánto

- **Diario:** `tradingbot status` (lee `logs/status.json` del bind mount). Heartbeat < 2 × timeframe + 5 min; si está `VENCIDO`, el healthcheck de compose marca `unhealthy` (no reinicia) y el **watchdog interno** del proceso sale con código 1 para que `restart: unless-stopped` lo levante; revisar `docker compose --profile paper logs paper` si se repite. Equity, posición con `stop_published: true`, últimos eventos. Los round trips viven en la DB del volumen: `docker compose --profile paper exec paper tradingbot trades --db db/paper.db` (o `docker compose cp paper:/app/db/paper.db ./db/paper.db` para `parity` desde el host).
- **Semanal:** `docker compose --profile paper logs --since 168h paper | grep -i "warning\|error"`; eventos `feed_missing_pair`, `feed_retry`, `pending_dropped` en la DB (`events`); `price_errors` en el status. Anotar cualquier reinicio (Docker `RestartCount`).
- **Cada cambio en `strategy/`, `risk/`, `engine/` o `execution/`** reinicia el reloj de las 8 semanas del Gate 2 (`docs/GATES.md`). Mientras el Gate 1 de `regime_bh` no cierre (ROADMAP, Fase 7), las semanas no cuentan: `regime_bh` es carga de prueba.

## Frenar, reanudar, apagar

- **Sin entradas nuevas, proceso vivo:** `uv run tradingbot stop` (crea `logs/STOP`; el contenedor lo ve por el bind mount). Con `--flatten` además vende todo a mercado al próximo cierre. `uv run tradingbot resume` borra el archivo.
- **Circuit breaker por drawdown:** reanuda **por plazo** (`drawdown_pause_days`, 30 d, re-basando el pico: la misma regla que validó el walk-forward) en todos los modos; la reanudación **por nivel** (`drawdown_resume_pct`) solo existe en backtest. Para reanudar antes a mano: `uv run tradingbot resume --breaker` escribe `logs/RESUME`; el proceso lo consume en el próximo cierre, reanuda y re-basa el pico en la equity actual (evento `protection_cleared`). El status muestra `drawdown_halted: True` mientras dure.
- **Apagar ordenado:** `docker compose --profile paper down` (SIGTERM → termina el ciclo en curso, guarda `state` y escribe `status.json` con fase `detenido`; `stop_grace_period` 60 s, el feed despierta cada 10 s). Cada ciclo se confirma en **una sola transacción** SQLite (fills, posiciones, trades, snapshot y `state`): un corte a mitad no deja cash y posiciones inconsistentes. El estado (cash, dust, posiciones con stop, protecciones, última vela) queda en `db/paper.db`; una vela cuyo ciclo explotó a mitad se re-procesa al reiniciar.
- **Reinicio:** el proceso reanuda desde la DB: re-publica los stops de las posiciones abiertas, cancela las órdenes `PENDING` de la sesión anterior (evento `pending_dropped`) y procesa las velas cerradas mientras estuvo caído como **reposición** (`replay`): marca a mercado, sube trailing, ejecuta salidas y stops, pero no abre entradas (`ReasonCode.REPLAY`).

## Problemas conocidos

- **Reloj de la VM de WSL desfasado** (`doctor` marca offset > 1 s, o el feed nunca confirma cierres): `wsl --shutdown` en PowerShell y reiniciar Docker Desktop. El feed usa el reloj del exchange, pero un offset grande retrasa la confirmación.
- **Docker Desktop no arranca (`0x800705aa`)**: cerrar aplicaciones pesadas, `wsl --shutdown`, `%USERPROFILE%\.wslconfig` con `[wsl2] memory=4GB processors=2`, reiniciar Docker Desktop (Aprendizajes, Fase 0).
- **`status --check` VENCIDO con el proceso vivo:** el feed está esperando una vela que Binance no publica (`feed_late` en los eventos) o el exchange está caído (`feed_retry` con backoff hasta 60 s). Si dura más de dos cierres, revisar conectividad y `docker compose --profile paper restart paper`.
- **Posición sin stop publicado (`SIN STOP PUBLICADO` en `status`):** la cantidad no pasa los filtros del exchange (`stop_unpublishable` en `events`). En paper la vende `--flatten`; en live la Fase 10 la cierra a mano.
- **Fill esperando (`pending_orders` no vacío tras un cierre):** el exchange no dio precio en ese instante; el watcher lo reintenta cada 60 s y, si nada funciona, se llena al `open` de la vela siguiente (mismo precio de referencia). Si se repite, mirar `price_errors`.
- **Tras un reinicio con posición abierta la estrategia no emite salida por régimen durante el warmup** (`regime_bh` necesita 202 cierres diarios; el `LiveFeed` los trae en el bootstrap, así que solo pasa si Binance devuelve menos velas). El stop del 20 % protege igual.

## Registro

Cada semana de paper se anota en `docs/ROADMAP.md`: fecha, velas procesadas, fills, eventos raros, reinicios, y el resultado de `tradingbot parity --config configs/paper.yaml --db db/paper.db --from <inicio> --to <fin>` (copiar antes la DB del volumen con `docker compose cp paper:/app/db/paper.db ./db/paper.db`; registra `PAR-NNNN`).
