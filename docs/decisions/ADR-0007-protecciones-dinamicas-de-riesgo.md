# ADR-0007: Protecciones dinámicas del RiskManager

- Estado: aceptado
- Fecha: 2026-09-08
- Fase: 5

## Contexto

La Fase 4 dejó un `RiskManager` estático: slots, exposición, sizing y filtros del exchange. `RiskConfig` declaraba desde la Fase 1 `daily_loss_limit_pct`, `max_drawdown_pct`, `cooldown_candles_after_stop` y `pause_after_consecutive_losses` sin que nadie los aplicara: EXP-0003 corrió con 3 % / 20 % declarados y no aplicados. El plan pide protecciones que acoten el riesgo de cola, con `reason_code` en cada decisión, que nunca bloqueen una salida (regla dura 7) y que se comporten igual en backtest, paper y live (ADR-0002). Pregunta que el plan no cubría: qué hace el circuit breaker por drawdown en un backtest, donde no existe la "intervención manual".

## Decisión

- Las protecciones viven en `risk/protections.py` (`Protections`), compuestas por el `RiskManager`, y **solo bloquean entradas**. `exit_intent` no las consulta.
- **Pérdida diaria** (día UTC = `ts // 86_400_000`): base = equity del último snapshot del día anterior (el primer día usa la primera equity observada). Al alcanzar `daily_loss_limit_pct` no hay entradas hasta el primer `Bar` del día UTC siguiente.
- **Circuit breaker por drawdown** desde el pico de equity de la corrida (o del proceso): al alcanzar `max_drawdown_pct` no hay entradas. En backtest reanuda solo (`auto_resume=True`) cuando el DD vuelve por debajo de `drawdown_resume_pct` (por defecto la mitad del umbral) **o** tras `drawdown_pause_days` días frenado (default 30), y en ese caso el pico se re-basa en la equity actual: un bot long-only frenado queda en cash, su DD no puede recuperarse solo y sin plazo el halt sería permanente (la primera corrida agresiva lo mostró: 9 trades y 70 rechazos por `drawdown_halt`). En paper/live nada reanuda solo: `resume()` (comando manual; transporte en las Fases 7–8) reanuda de inmediato y re-basa el pico.
- **Pausa tras N pérdidas seguidas** (`pause_after_consecutive_losses`): `pause_candles_after_losses` `Bar`s sin entradas; el contador se reinicia al pausar, al vencer la pausa y con cada ganancia. Cuenta pérdidas globales, no por par.
- **Cooldown por par tras una salida perdedora por stop o trailing** (`cooldown_candles_after_stop`): `Bar`s sin entradas en ese par, con la misma semántica que `bars_since_exit` (el bar del fill de salida cuenta como 0). Un trailing que devuelve hasta perder es el mismo ruido que un stop; un trailing ganador no enfría. Es independiente del `cooldown_candles` de la estrategia, que solo afecta a `entry_mode=state`.
- **Kill switch**: archivo `risk.kill_switch_file` (por defecto `logs/STOP`: `logs/` es bind mount en compose, así que el host lo escribe y el contenedor lo ve) o comandos `tradingbot stop [--flatten]` / `tradingbot resume`, que leen solo el bloque `risk` del YAML sin construir `BotConfig` (un YAML live sin claves en el entorno también tiene que poder frenar). Si el archivo existe no hay entradas; si contiene `flatten`, el `Engine` vende todas las posiciones a mercado al open siguiente (`ExitReason.FLATTEN`). Si el archivo no se puede consultar (`OSError`), el poll responde `active=True` sin flatten (fail-safe). El `Engine` lo consulta una vez por `Bar` en paper/live; en backtest no se inyecta.
- Prioridad cuando coinciden varias: `kill_switch` > `drawdown_halt` > `daily_loss_limit` > `consecutive_losses`; `pair_cooldown` se evalúa por par después.
- Cada transición genera un evento `protection_triggered` / `protection_cleared` en el `TradeStore`, con `reason` y detalle, visible en `REPORT.md` y, desde la Fase 7, en `status.json`. Los `entry_rejected` se registran una vez por par mientras el motivo no cambie (las `stats` cuentan todos); con `entry_mode=state` un halt largo no llena el store.
- El estado vive en memoria por proceso. Su persistencia para reinicios llega con `SqliteStore` (Fase 7).

## Alternativas consideradas

- **Halt hasta el final de la corrida**: fiel al live, pero un disparo temprano deja el backtest plano y no mide el costo real de la protección.
- **Reanudar solo por nivel de DD**: elegante, pero en cash el DD no se mueve y el halt se vuelve permanente; por eso el plazo en días es el respaldo.
- **Reanudar solo tras N días fijos**: desacoplado de si la equity se recuperó; queda como respaldo, no como regla principal.
- **Protecciones dentro de la estrategia**: mezcla señal con riesgo y no sirve para varias estrategias.
- **Cancelar compras `PENDING` al activar el kill switch**: exige soporte del broker (cancelación en el exchange, Fase 10); hoy la compra de la vela anterior se llena igual al open y queda protegida por su stop.

## Consecuencias

- Cambia el resultado de cualquier config con protecciones activas: EXP-0003 no se reproduce recargando su `config.yaml` (anotado en sus Notas); EXP-0004, con las protecciones en `null`, es la prueba de reproducibilidad.
- Regla dura 7 verificada por `hypothesis`: `exit_intent` no depende del estado de las protecciones.
- Deuda: persistencia del estado (Fase 7: al reiniciar se pierden pico, halt diario, pausa y cooldowns; solo el archivo STOP sobrevive, anotar en el runbook de paper), comando remoto de `resume` (Fase 8), cancelación de pendientes (Fase 10), pausa por pérdidas por par.
