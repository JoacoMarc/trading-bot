# Registro de experimentos

Índice de todas las corridas registradas. **No se edita a mano**: lo regenera `tradingbot experiments sync` a partir de `runs/*/metrics.json` y de la sección "Notas y veredicto" de cada `REPORT.md`. Prefijos: `EXP-` backtest · `WF-` walk-forward · `OPT-` optimización · `PAR-` paridad paper/backtest.

Holdout reservado: desde 2025-09-01 (ver `docs/GATES.md`). Ninguna corrida lo incluye salvo que la columna "Datos" diga `+holdout`.

| Id | Fecha | Estrategia | Params (hash) | Datos | Pares | TF | Retorno | Sharpe | Max DD | Trades | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-0001 | 2026-09-08 | buy_hold_bh_btc | e67aa67341 | 2019-08-01 → 2025-09-01 | BTC | 4h | +972.2 % | 0.93 | +77.0 % | 0 | go (línea base) |
| EXP-0002 | 2026-09-08 | buy_hold_equal_weight | a7ee9ad771 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +1439.9 % | 0.99 | +79.4 % | 0 | go (línea base) |
| EXP-0003 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | iterar |
