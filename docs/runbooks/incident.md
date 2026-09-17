# Runbook: incidentes

Qué hacer cuando algo se rompe con el paper corriendo (Fase 8; se amplía para live en la Fase 10). Regla general: **primero proteger la posición, después entender**. Todos los comandos se corren en la máquina donde corre el bot (VPS: `ssh root@IP` y `cd ~/trading-bot`; ver [vps.md](vps.md)).

## Cómo me entero

- Telegram: alertas de fills, stops, protecciones, errores del proceso (`error`), velas tardías (`feed`, silenciosas) y el resumen diario. Si el resumen diario **no llega** a la hora configurada, algo está mal: bot caído, Telegram caído o el VPS sin red.
- `/health` desde el celular: edad del último ciclo (tiene que ser menor que el timeframe + minutos), errores de precio, avisos con error.
- Sin Telegram: `paper-status` (SSH → `tradingbot status`), `docker compose --profile paper ps` (`healthy`/`unhealthy`), `docker inspect tradingbot-paper-1 --format '{{.RestartCount}}'`.

## Bot caído con posición abierta

Síntoma: `/health` no responde o el heartbeat está vencido; `docker compose --profile paper ps` muestra el contenedor reiniciando o parado.

1. La posición del paper no corre riesgo real, pero el ejercicio es tratarla como si lo hiciera: el stop vive en el `PaperBroker` (proceso) y en la DB (`positions.stop_price`), así que mientras el proceso esté caído **nadie vigila el stop**. En live (Fase 10) el stop nativo queda en el exchange y esto no aplica.
2. `docker compose --profile paper logs --tail 200 paper`: buscar el último `vela ...`, un traceback, o `watchdog:`.
3. Si el contenedor está en loop de reinicios (`RestartCount` sube): el arranque falla. Causas típicas: `load_markets` con `451` (IP bloqueada por Binance; cambiar de región), `schema_version` distinto (DB de otra versión: no se migra a mano sin leer el ADR-0011), `permission denied` en `logs/` (`chown -R 1000:1000 logs`).
4. Si el proceso está vivo pero sin ciclos (`unhealthy`, heartbeat vencido): esperar el watchdog (sale con 1 a las 2 × timeframe + 5 min y Docker lo levanta) o `docker compose --profile paper restart paper`. Al reanudar procesa las velas perdidas como reposición: ejecuta salidas y stops que hubieran tocado, no abre entradas.
5. Verificar con `/status` o `tradingbot status`: `reanudado desde la DB`, misma posición, `stop_published: true`.
6. Anotar el incidente en `docs/ROADMAP.md` (registro semanal del paper): fecha, duración, velas repuestas, causa.

## Exchange en mantenimiento o sin red

Síntoma: eventos `feed_retry` repetidos en el log (backoff hasta 60 s), `feed_late` por Telegram, `price_errors` sube en `/health`.

- No hacer nada mientras dure: el feed reintenta solo, confirma el cierre con cualquier vela posterior y, si Binance salteó una vela, la saltea con evento y sigue. El watcher de stops no puede ver precios: el stop se evalúa al cierre con el `low` de la vela (regla de gap/toque del broker) cuando vuelve la vela.
- Si dura más de dos cierres: `curl -s -o /dev/null -w "%{http_code}\n" https://api.binance.com/api/v3/time` desde el VPS. `451` = región bloqueada; timeout = red del VPS; `200` = el problema es del bot (logs).
- Después: `/daily` muestra los eventos `feed_*` de las últimas 24 h; anotar en el registro semanal.

## Telegram caído o token revocado

Síntoma: `/health` no responde, el resumen diario no llega, pero `paper-status` por SSH muestra el bot sano. En el log: `telegram: sin conexion (...)` o `telegram: no se pudo enviar`.

- El bot **no depende de Telegram**: la cola de avisos descarta los más viejos cuando se llena (200) y el ciclo de velas sigue. El kill switch por archivo sigue funcionando por SSH: `touch ~/trading-bot/logs/STOP`.
- Token revocado o cambiado (`InvalidToken` en el log): editar el `.env` del VPS (nunca pegar el token en un chat ni en un YAML), `docker compose --profile paper up -d` (reanuda desde la DB) y `docker compose run --rm bot telegram-test` para verificar.
- Telegram caído: esperar; el notificador reintenta la conexión con backoff (30 s → 5 min). Los avisos perdidos quedan en el log y en la DB (`events`).

## Kill switch, flatten y reanudar

- `/pause` (o `/stop`, o `touch logs/STOP`): sin entradas nuevas desde el próximo cierre; la posición abierta sigue con su stop. `/resume` (o borrar el archivo) lo retira.
- `/stop flatten` + `si` (o `echo flatten > logs/STOP`): además vende todo a mercado en el próximo cierre. Irreversible una vez ejecutado; el archivo se puede borrar antes del cierre para cancelarlo.
- Circuit breaker disparado (`drawdown_halted: True`): reanuda solo por plazo (`drawdown_pause_days`); para reanudar antes, `/resume breaker` (o `touch logs/RESUME`). Pensarlo dos veces: el breaker disparó porque el DD superó el límite que validó el walk-forward.

## Stop ejecutado sin que el bot lo viera

Solo aplica a live (Fase 10) con stop nativo en el exchange: el bot arranca, reconcilia órdenes y balances contra la DB, detecta que la posición ya no existe y registra el trade con el fill del exchange. En paper no puede pasar: el stop lo ejecuta el proceso.

## Después de cualquier incidente

1. `tradingbot parity --config configs/paper.yaml --db db/paper.db --from <inicio> --to <fin>` desde la PC con la DB copiada (ver [paper.md](paper.md), "Registro"): un incidente que cambió fills o señales se ve ahí.
2. Registro semanal en `docs/ROADMAP.md`: fecha, qué pasó, cuánto duró, qué hizo el bot al volver.
3. Si el incidente pide un cambio de código en `strategy/`, `risk/`, `engine/` o `execution/`, el reloj del Gate 2 vuelve a cero (`docs/GATES.md`).
