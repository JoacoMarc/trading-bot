---
name: paper-status
description: Lee el estado del paper trading del trading-bot (logs/status.json y la DB de paper) y resume equity, posiciones, stops, protecciones, eventos recientes y salud del proceso. Usar cuando el usuario pregunte "cómo va el paper", "está corriendo el bot", "qué posiciones tiene" o antes de tocar código que reinicie el reloj del Gate 2.
argument-hint: "[--file logs/status.json] [--db db/paper.db]"
---

El paper corre en Docker lanzado por el usuario; esta skill **solo lee**. Nunca arranca, para ni reinicia el proceso (eso es `docker compose --profile paper ...` desde la terminal del usuario) y nunca escribe `logs/STOP` sin que el usuario lo pida explícitamente.

Pasos:

1. `uv run tradingbot status` (o `--file <ruta>` si se pasó). Si sale `sin status`, el proceso nunca arrancó o el bind mount de `logs/` no está: decirlo y parar acá.
2. Leé: fase (`arranque`, `corriendo`, `detenido`), heartbeat (si dice `VENCIDO`, el proceso no procesa cierres: mirar `docker compose --profile paper ps` y `logs`), última vela y próximo cierre, equity y cash, posiciones (cada una debe decir stop publicado; `SIN STOP PUBLICADO` es una alerta), órdenes pendientes (deberían estar vacías salvo justo después de un cierre), protecciones activas (`drawdown_halted` en paper no reanuda solo), kill switch, rechazos y `price_errors`, últimos eventos.
3. `uv run tradingbot trades --db db/paper.db --last 10` para los round trips cerrados y las posiciones abiertas de la DB (tiene que coincidir con el status).
4. Si hay algo raro (heartbeat vencido, stop sin publicar, `feed_missing_pair` repetido, `pending_dropped`, reinicios), buscá la sección correspondiente en `docs/runbooks/paper.md` y proponé el paso del runbook; no lo ejecutes.
5. Resumen al usuario en ≤ 12 líneas: salud, posición y PnL no realizado, qué protecciones están activas, eventos que merecen atención, y si el reloj del Gate 2 está corriendo (solo cuando el Gate 1 de la estrategia esté cerrado; ver ROADMAP Fase 7).
