# Papers independientes — operación y validación

Rama de implementación: `codex/paper-multiestrategia`. ADR-0013. Solo spot simulado.
La referencia conserva su DB/estrategia. Candidatas: `pullback` y `donchian`, perfil A.
Perfil B solo histórico. Ninguna candidata queda aprobada por tener código o Compose.

## Validación local

Instalar uv y sincronizar Python 3.12 con `uv sync --python 3.12`. Luego:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run tradingbot download-data --timeframes 4h --until 2025-09-01
uv run tradingbot data-check --timeframes 4h
uv run python scripts/compare_candidates.py --dry-run
uv run python scripts/compare_candidates.py
```

El último comando requiere revisión git limpia; correr en background y conservar su salida.
Registra 4 backtests base, 4 WF fijos (24m/6m, meseta, Monte Carlo) y 8 pruebas de costos.
Evaluar todos los criterios de GATES.md, no elegir el mejor de A/B mirando holdout.
Solo A que apruebe pre-holdout puede evaluarse una vez desde 2025-09-01 hasta el último
día UTC cerrado, con `backtest --include-holdout --from ... --to ...`, registrando el corte.
Ese período ya fue visto en otras familias: declarar esa exposición previa. Solo tras pasar
también el holdout se habilita la instancia; si falla, mantener el servicio sin arrancar.

## Imágenes y secretos

Construir una imagen por revisión limpia (`tradingbot:<sha>`), sin pisar `tradingbot:local`.
`REFERENCE_IMAGE` y `CANDIDATE_IMAGE` designan revisiones verificadas. No usar `latest`.
El Compose de candidatas se ejecuta desde un checkout de esa misma revisión en el VPS.
Solo interpola `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` desde el entorno privado existente;
no importa otros overrides de la referencia. No imprimir `docker compose config` con secretos:
usar `config --quiet`. Nunca copiar tokens a YAML, git, informes o mensajes.

Cada candidata tiene volumen `paper.db` propio; los logs del host van en
`logs/candidates/pullback` y `logs/candidates/donchian`. Crear ambos con dueño UID 1000
antes del primer arranque. Dentro de cada contenedor las rutas siguen siendo `/app/db`
y `/app/logs`: los healthchecks y controles existentes apuntan al montaje de esa instancia.

## Respaldo y actualización de la referencia

Antes del cambio, guardar fuera del repo el ID exacto de imagen, configuración pública,
status y una copia consistente usando SQLite `Connection.backup`; no copiar solo el `.db`
de una base WAL abierta. Confirmar `PRAGMA integrity_check` sobre la copia.

Construir la imagen nueva en un checkout separado. Probar la recuperación contra una copia
de la DB con exchange falso y Telegram deshabilitado; comparar posición, cash, stop y estado
de protecciones. El nuevo outbox es una tabla aditiva compatible con schema v1; no altera
fills/trades ni genera avisos de operaciones antiguas.

Actualizar exclusivamente el servicio original desde su directorio operativo:

```bash
docker compose -f compose.yaml -f compose.reference.yaml --profile paper up -d --no-build --no-deps paper
docker compose --profile paper exec paper tradingbot status --check
docker compose --profile paper exec paper tradingbot status
docker compose --profile paper exec paper tradingbot telegram-test --config configs/paper.yaml --send-only
```

Comprobar estado recuperado y ausencia de compras duplicadas. No correr `down -v` ni eliminar
volúmenes. Para rollback, usar la imagen anterior con el mismo volumen; no restaurar una copia
vieja sobre una DB que ya recibió nuevos fills. La imagen anterior ignora el outbox: los avisos
pendientes se conservan, pero no se envían hasta volver a una versión compatible.

## Arranque de candidatas aprobadas

Solo ejecutar el comando de la candidata cuyo Gate 1 completo esté aprobado y registrado:

```bash
docker compose -f compose.candidates.yaml --profile pullback up -d --no-build pullback
docker compose -f compose.candidates.yaml --profile donchian up -d --no-build donchian
```

Para cada instancia, reemplazar `pullback` y el nombre del YAML si corresponde:

```bash
docker compose -f compose.candidates.yaml exec pullback tradingbot status
docker compose -f compose.candidates.yaml exec pullback tradingbot telegram-test --config configs/candidates/paper-pullback_rsi.yaml --send-only
docker compose -f compose.candidates.yaml exec pullback tradingbot stop --config configs/candidates/paper-pullback_rsi.yaml
docker compose -f compose.candidates.yaml exec pullback tradingbot resume --config configs/candidates/paper-pullback_rsi.yaml
docker compose -f compose.candidates.yaml stop pullback
```

`stop` de la CLI frena compras; `stop --flatten` solicita vender lo abierto. El `stop` de Docker
apaga el proceso. No confundirlos. Antes de editar reglas, frenar esa instancia y guardar su
config y resultados como un experimento terminado; no reiniciar un experimento distinto sobre
su estado. No reutilizar una DB de otra estrategia ni renombrar instancias durante una corrida.

## Telegram y seguimiento

Todos envían al chat actual; solo referencia escucha comandos. Las candidatas nunca ejecutan
getUpdates ni descartan mensajes pendientes. Usar siempre `telegram-test --send-only` mientras
el receptor original esté activo. La prueba no escribe operaciones ficticias en la DB.

Los avisos dicen `[PAPER | nombre]`, y detallan compra, venta o límite de pérdida, cantidades,
precio, hora local y resultado neto. Cada operación confirmada genera una fila durable; al
volver la red o reiniciar se reintenta. `notify.durable_pending` en status indica el atraso.
Después de un resultado HTTP incierto puede verse un duplicado; no se promete exactly-once.
Alertas importantes y resúmenes diarios también identifican instancia. Comandos del chat
afectan solo a la referencia; los candidatos se administran por CLI.

Verificar salud y consumo después del arranque y al completar el primer cierre de 4h.
Comparar curvas desde la misma fecha, normalizando referencia a 100 y declarando su posición
heredada. Cada candidata empieza con 10000 USDT propios. No sumar retornos/capitales de esas
cuentas como si constituyeran una sola cartera. El Gate 2 requiere su período completo y
paridad; aprobar Gate 1 no autoriza dinero real.
