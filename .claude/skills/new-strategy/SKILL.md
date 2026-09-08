---
name: new-strategy
description: Scaffold de una estrategia nueva del trading-bot siguiendo el flujo obligatorio: spec en docs/strategy/ antes del código, módulo en strategy/strategies/, registro por nombre, tests y test de equivalencia (lookahead). Usar cuando el usuario quiera agregar una estrategia o una versión nueva de una existente.
argument-hint: "<nombre_snake_case> [versión]"
---

Flujo (regla dura 9 de `CLAUDE.md`: spec antes del código).

1. Nombre: `$ARGUMENTS` → `<nombre>` en snake_case, ≤ 12 caracteres (límite de `StrategyConfig.name`, por el `client_order_id`), y versión (default `v1`). Si ya existe `docs/strategy/<nombre>-<versión>.md`, preguntá si es una versión nueva.
2. **Spec.** Invocá al agente `strategy-researcher` con la idea del usuario y guardá su salida en `docs/strategy/<nombre>-<versión>.md`. Si el usuario ya trajo la spec, validala contra la plantilla de `docs/strategy/README.md` (hipótesis, reglas con stop y salida, parámetros con rangos, regímenes, riesgos). Agregá la fila a la tabla de `docs/strategy/README.md`.
3. **Indicadores.** Si la spec necesita un indicador que no está en `src/tradingbot/indicators/core.py`, agregalo ahí con semilla documentada, regenerá los fixtures con `uv run python scripts/gen_indicator_fixtures.py` (grupo `fixtures`, TA-Lib) y su test en `tests/indicators/`.
4. **Estrategia.** Creá `src/tradingbot/strategy/strategies/<nombre>.py` tomando `ema_trend.py` como patrón: `Params(StrategyParams)` con validadores y rangos, clase con `name = "<nombre>"`, `longest_period`, `compute_indicators`, `on_candle`, `trailing_stop`, decorada con `@register`. Importala en `strategy/strategies/__init__.py`.
5. **Tests.** `tests/strategy/test_<nombre>.py`: señales sobre series sintéticas con resultado conocido, `ENTER_LONG` siempre con `stop_price < close`, `HOLD` sin posición y sin cruce, y el test de equivalencia:
   `check_window_equivalence` y `check_no_lookahead` de `tradingbot.validation.equivalence` sobre los fixtures reales de `tests/fixtures/ohlcv/`.
6. **Config.** Ejemplo de `params` en `configs/*.example.yaml` si difiere del default.
7. Corré `uv run pytest tests/strategy tests/indicators`, `uv run ruff check .`, `uv run mypy`. Pedí revisión al `trading-code-reviewer` antes de correr el primer backtest (`/backtest`, Fase 4).

Nunca escribas la estrategia antes de la spec ni una spec sin comportamiento esperado por régimen.
