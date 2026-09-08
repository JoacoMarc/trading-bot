---
name: backtest
description: Corre un backtest del trading-bot por CLI (para que quede registrado en experiments/), muestra las métricas contra los benchmarks y la última corrida comparable, y deja el REPORT.md listo para el veredicto. Usar cuando el usuario pida correr, repetir o comparar un backtest.
argument-hint: "[--config ruta] [--strategy nombre] [--pairs BTC/USDT,ETH/USDT] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--set clave=valor ...]"
disable-model-invocation: true
---

Regla dura 6: los backtests se corren **solo** con la CLI para que queden registrados. Nunca llames al runner desde Python suelto para "probar rápido".

Pasos:

1. Verificá que haya datos: `uv run tradingbot data-info`. Si faltan pares o el rango, `uv run tradingbot download-data` (la descarga real la corre el usuario si esta sesión no tiene red).
2. Elegí la config: `configs/backtest.yaml` por defecto; `$ARGUMENTS` puede traer `--config`, `--strategy`, `--pairs`, `--from`, `--to`, `--set clave=valor`. No uses `--include-holdout` salvo pedido explícito del usuario y solo en la corrida final de una familia (docs/GATES.md).
3. Corré: `uv run tradingbot backtest $ARGUMENTS`. Si tarda más de un par de minutos (8 pares desde 2019), lanzalo con `run_in_background` y esperá la notificación.
4. Leé el id registrado (`EXP-NNNN`) y mostrá al usuario la tabla estrategia vs benchmarks que imprimió la CLI.
5. Compará con la corrida previa más parecida (misma estrategia, mismo timeframe): `uv run tradingbot experiments compare EXP-anterior EXP-nuevo`. Si el `data_hash` difiere, avisá que la comparación no es limpia.
6. Invocá al agente `backtest-analyst` con el id de la corrida para que proponga el veredicto. Pegá su texto en la sección **Notas y veredicto** del `REPORT.md` de la corrida (es lo único editable) solo si el usuario está de acuerdo; después `uv run tradingbot experiments sync`.
7. Si la corrida sugiere cambiar la estrategia (parámetros fuera del rango de la spec o reglas nuevas), no toques el código: proponé una spec `vN+1` con `/new-strategy`.

No edites `config.yaml` de una corrida registrada ni borres carpetas de `experiments/runs/`.
