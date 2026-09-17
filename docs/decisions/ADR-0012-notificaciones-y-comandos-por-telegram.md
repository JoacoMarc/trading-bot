# ADR-0012: Notificaciones y comandos por Telegram

- Estado: aceptado
- Fecha: 2026-09-16
- Fase: 8

## Contexto

El paper corre en un VPS (ROADMAP, Fase 8) y hasta ahora la única forma de saber qué hizo es entrar por SSH y leer `status.json`. La Fase 8 agrega el puerto `Notifier` de ADR-0002 con dos implementaciones (log y Telegram) y comandos desde el celular. Restricciones reales:

- El `Engine` es el único que sabe cuándo se abre una posición, se cierra un trade, se rechaza una entrada o dispara una protección; hoy lo escribe todo en el `TradeStore` y nadie más se entera hasta leer la DB. No se agrega un segundo camino "solo para paper" (regla dura 3): el backtest tiene que seguir corriendo sin notificador.
- Cada ciclo del paper va en **una transacción SQLite** (ADR-0011, I1). Un aviso que sale antes del commit puede describir algo que después se deshace.
- `python-telegram-bot` es asyncio puro y no thread-safe: tiene que vivir en el mismo event loop que `PaperSession`, y un Telegram caído (red, 429, token revocado) no puede frenar ni retrasar el ciclo de velas.
- El token y el `chat_id` son secretos (`SecretStr`, solo por `.env`, regla dura 5). Desde un celular, un toque accidental no puede liquidar la posición.
- Los comandos de control ya existen como archivos (`logs/STOP`, `logs/RESUME`, ADR-0007/0011) y el `Engine` los consume una vez por `Bar`.

## Decisión

### Gancho de eventos en el `Engine`

`Engine` acepta un `listener: EngineListener | None` (Protocol en `engine/engine.py`) con tres métodos: `on_event(EventRecord)` (lo mismo que va a `store.record_event`: rechazos, `exit_stuck`, protecciones disparadas y liberadas, fills huérfanos), `on_position_opened(Position, Fill)` y `on_trade_closed(Trade, Fill)`. Todo `record_event` del motor pasa por `Engine._record`, que persiste y después avisa al listener. Sin listener (backtest) no cambia nada.

### Puerto `Notifier` (`notify/base.py`)

`Notification(ts, category, text, pair, level)` ya renderizada en texto plano; `Notifier` con `notify(Notification)` **síncrono, que nunca bloquea ni lanza**, más el ciclo de vida `run()`/`stop()` para correr como tarea auxiliar de la sesión (mismo patrón que `StopWatcher` y el watchdog: si muere, `_task_done` pide la parada ordenada). `LogNotifier` escribe al log (default en toda sesión). Las categorías y su nivel por defecto viven en `NotifyConfig.events` (`on` avisa con sonido, `silent` avisa sin sonido, `off` no avisa): `entry`, `exit`, `stop`, `stuck`, `protection`, `error`, `lifecycle`, `daily` en `on`; `rejection` y `feed` en `silent`.

### Buffer y commit

`PaperSession` implementa `EngineListener` y **acumula** las notificaciones del ciclo en una lista; las entrega al `Notifier` recién después de que la transacción del ciclo (o del lote del watcher) confirmó, y las **descarta si la transacción falla** (rollback → sin aviso; la vela se re-procesa al reiniciar y avisa entonces). Lo que se notifica es lo que quedó en la DB. Los hooks del listener corren dentro de la transacción con el estado ya mutado, así que el `Engine` los envuelve: una excepción del listener se loguea y el ciclo sigue (el listener es observacional). Las notas llevan el `ts` del fill o del evento; los hooks no salen a la red.

### `TelegramNotifier` (`notify/telegram.py`)

- `Application` de `python-telegram-bot` con ciclo de vida manual (`initialize` → `start_polling` → `start`; al parar, el orden inverso) dentro del loop de la sesión. `AIORateLimiter` activo.
- Envío por **cola acotada** (200 mensajes): `notify()` encola sin esperar; si la cola está llena se descarta el más viejo con un log. Una tarea drena la cola con timeout por mensaje y reintento acotado; los errores de Telegram se loguean y se cuentan (`status.json` → `notify.errors`), nunca se propagan al ciclo.
- **Whitelist**: solo se atienden mensajes nuevos con texto (`UpdateType.MESSAGE`: un mensaje editado no re-ejecuta un `/pause` viejo) del `chat_id` configurado; el resto se ignora (un log por chat desconocido, sin el id). Los loggers `httpx`/`httpcore` quedan en WARNING porque imprimen la URL con el token a INFO.
- **Polling**: PTB reintenta el `getUpdates` solo; sus errores se cuentan (`polling_errors`) y, si el `Updater` dejó de correr con el proceso vivo, el notificador se reconecta (`reconnects`). Ambos salen en `status.json`.
- **Aviso urgente**: `Notifier.send_now()` manda sin cola y acotado; lo usa el watchdog antes de salir con 1 (la cola no llegaría a drenarse).
- Comandos: `/status`, `/balance`, `/positions`, `/trades [n]`, `/profit`, `/daily`, `/health`, `/help` leen del `status_payload` y de la DB (`notify/commands.py`, funciones puras sobre un `CommandBackend` que `PaperSession` implementa: testeables sin Telegram). Los de control usan **los mismos archivos que la CLI**: `/pause` y `/stop` = `tradingbot stop` (sin entradas nuevas; reversible), `/resume` = `tradingbot resume`, `/resume breaker` = `--breaker`. `/stop flatten` **exige confirmación**: el bot pregunta y solo si el mismo chat responde `si` dentro de `notify.confirm_window_s` (60 s) escribe `flatten`. El `Engine` los consume en el próximo `Bar` (o antes: el watcher no lee el kill switch, así que un flatten tarda hasta un cierre, igual que desde la CLI).
- **Resumen diario** a `notify.daily_summary_hour` en `notify.timezone`, una vez por día local (un reinicio no lo repite): equity y su variación en las **últimas 24 h** (base = último snapshot anterior a 24 h; recién arrancado, el primero, y el texto lo dice), drawdown desde el pico del breaker, trades cerrados, fees y shortfall medio de los fills de 24 h, eventos raros por tipo. Se eligió 24 h rodantes y no el día UTC porque la hora del resumen es local y un "día UTC" a las 09:00 de Buenos Aires tendría 12 h. `/daily` lo pide a demanda.
- `tradingbot telegram-test --config` envía un mensaje de prueba y espera un comando durante N segundos: valida token y `chat_id` en el VPS antes de reiniciar el paper.

### Qué no hace

Telegram no decide ni ejecuta órdenes directamente, no puede cambiar la config ni reiniciar el proceso, y no reemplaza al kill switch por archivo (que sigue funcionando sin Telegram). El LLM analista (Fase 9) tampoco entra por acá.

## Alternativas consideradas

- **Decorar el `TradeStore`** (`NotifyingStore` que intercepta `save_fill`/`save_trade`/`record_event`): cero cambios en el motor, pero mezcla notificación con persistencia, obliga a inferir "apertura" desde `save_position` (que también se llama al marcar y al subir el trailing) y sigue avisando antes del commit. El listener explícito dice lo que pasó.
- **`PaperSession` infiere los eventos comparando el estado antes y después de cada vela**: frágil (dos fills en la misma vela, fills del watcher fuera del ciclo) y duplica lógica del motor.
- **Enviar dentro de la transacción / `await` en el ciclo**: un Telegram lento retrasa el cierre de la vela y un 429 puede tumbar el ciclo. La cola con descarte protege el loop de velas; perder un aviso es aceptable, perder un cierre no.
- **Comandos que llaman al `Engine` directamente** (`engine.flatten()` desde el handler): un segundo camino de control que el backtest no tiene y que corre fuera de la transacción del ciclo. Los archivos ya están validados y el `Engine` los consume en el punto correcto de la precedencia intra-vela.
- **`/stop flatten` sin confirmación** (como el `--flatten` de la CLI): en la CLI el operador está en la máquina; en el celular un toque equivocado vende todo.
- **`JobQueue` de PTB para el resumen diario**: agrega APScheduler al loop y no se testea con reloj falso; una tarea propia con `sleep` inyectable sigue el patrón del watchdog.
- **Webhook** en vez de polling: exige puerto abierto y TLS en el VPS (`ufw` solo deja SSH); polling con un chat alcanza.

## Consecuencias

- `Engine` gana `listener` y `_record`; `EventRecord` no cambia. Los tests del motor siguen iguales (sin listener).
- `NotifyConfig` gana `events` (niveles por categoría) y `confirm_window_s`; `telegram_enabled: true` sigue exigiendo `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env` (el compose del paper ya lo carga con `required: false`).
- `status.json` gana `notify` (`backend`, `queued`, `sent`, `errors`, `dropped`); `tradingbot status` lo muestra.
- Operación: el `.env` del VPS lleva el token; cambiarlo o rotarlo es editar el archivo y `docker compose --profile paper up -d` (reanuda desde la DB). Runbook `docs/runbooks/incident.md` para los casos de la Fase 8 (bot caído con posición abierta, exchange en mantenimiento, token revocado, Telegram caído).
- Deuda: un solo `chat_id`; sin botones inline (texto plano, sin `parse_mode`, para que un símbolo raro no rompa el envío); los comandos de control tardan hasta un cierre en aplicarse (el watcher no lee el kill switch); `/trades` y `/profit` leen toda la tabla (suficiente para ≤ 15 trades/año).
- Regla operativa nueva para `CLAUDE.md`: el token de Telegram nunca pasa por el chat ni por YAML; se pega en `.env` (PC) o `.env` del VPS, y `telegram-test` lo valida.
