---
name: walkforward
description: Corre el walk-forward del trading-bot por CLI (IS 24 m / OOS 6 m, curva OOS concatenada, Monte Carlo, meseta y Gate 1) en modo fijo u optimizado con optuna, y deja el WF-NNNN listo para el veredicto. Usar cuando el usuario pida validar una estrategia o config, "correr el walk-forward", "ver si pasa el gate" u optimizar parámetros.
argument-hint: "[--config ruta] [--pairs ...] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--optimize --trials N] [--plateau] [--set clave=valor ...]"
disable-model-invocation: true
---

Regla dura 6: walk-forward y optimización se corren **solo** con la CLI para que queden registrados como `WF-` / `OPT-`. El IS nunca se reporta como evidencia; la evidencia es la curva OOS concatenada (ADR-0008).

Pasos:

1. Confirmá qué se valida: la config base (`configs/backtest.yaml` u otra), el universo y el rango. Con `--set` se cambian parámetros sin tocar el YAML. Recordá que `--to` excluye el holdout (desde 2025-09-01) salvo `--include-holdout`, que **no** se usa acá.
2. Elegí el modo:
   - **fijo** (default): mismos parámetros en todas las ventanas + muestra completa, regímenes por año y, con `--plateau`, la meseta ±20 %. Tarda ~1 min con 8 pares (la meseta suma ~40 backtests).
   - **optimizado** (`--optimize --trials N --seed S --objective sharpe|calmar|profit_factor --min-trades 40`): optuna elige parámetros en cada IS y se evalúan en su OOS. Tarda `ventanas × trials × 2–4 s`: con más de ~20 trials lanzalo con `run_in_background` o pedile al usuario que lo corra en su terminal.
3. Corré `uv run tradingbot walkforward [opciones] --label "<estrategia> <qué cambia>"`. Para un IS explícito sin ventanas: `uv run tradingbot optimize --to YYYY-MM-DD --trials N`.
4. Leé la salida: tabla de ventanas, OOS concatenado vs B&H BTC OOS vs muestra completa, Monte Carlo, meseta y la tabla del Gate 1 (`OK` / `FALLA` / `n/a`). `n/a` no cuenta como aprobado.
5. Pedí el análisis al agente `backtest-analyst` con el id del `WF-` (y el `EXP-` de rango completo comparable) y escribí el veredicto con `/experiment-review <id>`. Si algún criterio falla, el veredicto es `iterar` o `no-go`, nunca `go`.
6. Si el usuario quiere probar otra variante de la estrategia (universo, `entry_mode`, timeframe), primero la spec nueva en `docs/strategy/` (`/new-strategy` o versión vN+1), después la corrida.

No toques el holdout: se usa una sola vez por familia de estrategia, al final de la Fase 6, con `tradingbot backtest --include-holdout`.
