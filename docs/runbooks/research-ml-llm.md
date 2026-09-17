# Investigación Supertrend, ML y observador LLM

Implementación en `codex/research-ml-llm`. Las candidatas rechazadas permanecen
**backtest**. La referencia y su SQLite del VPS no se modifican en esta entrega.
Resultados: `experiments/research-2026-09-17/REPORT.md`.

## Entorno y reproducción

Desde la raíz del repositorio, Python3.12:

```bash
uv sync --frozen --group ml
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

LightGBM en macOS requiere OpenMP: `brew install libomp`. Para Linux se entrega
`Dockerfile.ml` con libgomp1. Entrenamiento y backtests en la Mac, nunca en el VPS
que mantiene el paper. Los artefactos se registran por CLI, con revisión/hashes.

```bash
uv run tradingbot download-data --help
uv run tradingbot data-check -t 1h,4h
uv run tradingbot data-check --data-dir data/research-history -t 4h
uv run tradingbot backtest --config configs/candidates/supertrend-1h-a.yaml
uv run tradingbot walkforward --config configs/candidates/supertrend-1h-a.yaml --fixed --plateau --montecarlo-runs 5000
```

Repetir4h/1h,A/B y `--set execution.slippage_bps=10`/`20`. No cambiar parámetros
tras mirar el resultado. La carpeta de resultados conserva comandos y logs de cada
corrida. Se usaron copias Git aisladas para que cambios posteriores no alteraran
el código mientras corría una evaluación. No se consumió holdout de estas familias.

## Dataset y modelos

`configs/research-ml.yaml` usa historia4h anterior a2019 en un directorio separado.
Los huecos reales de2018 se contrastaron contra klines públicas de Binance. Las
features incluyen solo días UTC completos; huecos pueden producir features no
válidas y períodos sin modelo suficiente. No completar esos períodos como éxito.

```bash
uv run tradingbot research dataset --config configs/research-ml.yaml
uv run tradingbot research train experiments/runs/RES-0001-ml-dataset --kind logistic
uv run tradingbot research train experiments/runs/RES-0001-ml-dataset --kind lightgbm
uv run tradingbot research predict experiments/runs/RES-0001-ml-dataset experiments/runs/RES-0002-ml-train-logistic
```

Los IDs son los de esta entrega; nuevas corridas reciben otros. `dataset.parquet`
contiene etiquetas, `features.parquet` conserva incluso filas inválidas. Cada
modelo JSON conserva pesos, scaler/calibrador, versiones, receta, purga, hash y
fechas. No se carga pickle. `predictions.parquet` guarda probabilidades temporales;
`coverage.parquet` distingue modelo ausente/features inválidas/predicción válida.
Modificar cualquiera rompe el hash. No sustituir archivos de un experimento.

Los YAML `configs/candidates/ml-*.yaml` apuntan a manifests congelados. El umbral
0,55 solo filtra compras, no cambia stop, salida, ranking ni tamaño. `walkforward`
usa receta fija y reentrenamiento mensual, meseta de24 variantes y MonteCarlo5000.

```bash
uv run tradingbot walkforward --config configs/candidates/ml-logistic-a.yaml --fixed --plateau
uv run tradingbot research compare experiments/runs/CONTROL experiments/runs/CANDIDATA
```

La comparación exige mismos días, usa retornos diarios emparejados para Sharpe/CI,
y la curva original por vela para DD. Es un criterio incremental adicional, no una
aprobación por sí solo. Muestra pequeña/cobertura insuficiente impiden promoción.

Para una familia futura que apruebe todas las etapas previas existe una ruta final
explícita `research dataset --final-holdout-family <familia>` con config que habilite
`include_holdout`. Registra el consumo una sola vez; el mismo nombre no puede
volver a consultar. No ejecutar este comando con candidatas rechazadas. El período
ya fue observado por otras familias y no es confirmación totalmente independiente.

## Inferencia local futura

Solo después de gates: entrenar en Mac usando el corte mensual y transferir el
modelo JSON. `research publish <modelo.json> <publicacion.json>` exige vigencia,
verifica hash y añade el momento real de publicación. Paper configura
`prediction.mode: local` y `prediction.publication`; el modelo no puede utilizarse
antes de publicación ni después de vencimiento. Si falta o falla, nuevas compras
se bloquean; las posiciones existentes mantienen stops y salidas. Mantener DB,
logs, STOP/RESUME, configuración e imagen separados por instancia. Nunca usar la
imagen de investigación para reemplazar a la referencia sin su procedimiento de
backup/recuperación (`docs/runbooks/paper-multiestrategia.md`).

## Observador LLM

`advisor observe` tiene feed propio y **ningún broker**. Recolecta todas las rupturas
Donchian, incluso con una posición que ya existiría en otra cartera. El snapshot
no contiene cash/posiciones, para poder reproducir carteras que divergen tras un
veto. BUY es una recomendación guardada, jamás un fill ni una orden de Telegram.

Antes de iniciar una cohorte, elegir modelo exacto, verificar tarifas del proveedor
y poner la clave en entorno/local `.env` sin compartirla. Copiar
`configs/advisor.example.yaml` a `configs/advisor.yaml`. El ejemplo tiene llamadas
pagas deshabilitadas. La DB congela modelo, prompt, tarifas, estrategia, universo,
features y riesgo/costos; cambiar esos elementos exige una nueva cohorte/DB.
La reserva conservadora respeta límites USD1/día y20/mes UTC; una llamada cuyo
resultado se desconoce conserva la reserva y no se repite.

```bash
uv run tradingbot advisor observe --config configs/candidates/donchian-a.yaml --policy configs/advisor.yaml --db db/advisor.db
uv run tradingbot advisor status --policy configs/advisor.yaml --db db/advisor.db
uv run tradingbot advisor replay --policy configs/advisor.yaml --db db/advisor.db --output experiments/advisor-replay-001.json
```

Plazo45s desde cierre exclusivo, cola32, concurrencia2. Respuesta inválida, tardía,
ID incorrecto, timeout, presupuesto agotado o cola llena: sin aceptación. Las
pendientes válidas se retoman antes del warmup al reiniciar; una llamada en vuelo
queda desconocida. Cada respuesta efectiva y su hash se conservan. Un bloqueo de
archivo impide dos procesos observadores sobre la misma DB. Estado y gasto se
consultan por CLI; heartbeat por cierre, healthcheck detecta falta prolongada de ciclos.

Compose opcional, proyecto y volumen propios:

```bash
docker build -t tradingbot-research:<revision> .
RESEARCH_IMAGE=tradingbot-research:<revision> docker compose -f compose.research.yaml --profile observer up -d observer
RESEARCH_IMAGE=tradingbot-research:<revision> docker compose -f compose.research.yaml logs --tail 50 observer
RESEARCH_IMAGE=tradingbot-research:<revision> docker compose -f compose.research.yaml stop observer
```

Reemplazar `<revision>` por el commit probado, nunca por la etiqueta del original.
No desplegado en esta entrega. Sin modelo/API elegidos no se inició una cohorte ni
se generó gasto. Telegram conserva el único receptor original; los papers existentes
mantienen su outbox de operaciones y sus identidades. El observador no simula trades
para producir avisos.

## Condiciones pendientes antes de ejecutar un filtro LLM

El comando `advisor replay` audita respuestas; **no calcula rentabilidad**. Aún no
existe un broker de ejecución diferida activable para LLM. Implementarlo y validarlo
requiere: datos1m, fill posterior a decisión y señal+60s, expiración120s, stops
cronológicos después del fill, cotización fresca paper y control con igual espera.
No usar el open4h anterior a una respuesta para atribuirle una compra.

El protocolo aprobado permite esta fase posterior únicamente con una base elegible,
evidencia prospectiva congelada de al menos12semanas y40cierres por cartera,
comparación incremental con incertidumbre y costos de API. No se puede generar esa
muestra hoy. Ningún resultado de esta entrega autoriza trading real. Si la base no
supera los gates, se conserva la referencia paper y el observador sigue sin broker.
