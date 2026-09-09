# Registro de experimentos

Índice de todas las corridas registradas. **No se edita a mano**: lo regenera `tradingbot experiments sync` a partir de `runs/*/metrics.json` y de la sección "Notas y veredicto" de cada `REPORT.md`. Prefijos: `EXP-` backtest · `WF-` walk-forward · `OPT-` optimización · `PAR-` paridad paper/backtest.

Holdout reservado: desde 2025-09-01 (ver `docs/GATES.md`). Ninguna corrida lo incluye salvo que la columna "Datos" diga `+holdout`.

| Id | Fecha | Estrategia | Params (hash) | Datos | Pares | TF | Retorno | Sharpe | Max DD | Trades | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-0001 | 2026-09-08 | buy_hold_bh_btc | e67aa67341 | 2019-08-01 → 2025-09-01 | BTC | 4h | +972.2 % | 0.93 | +77.0 % | 0 | go (línea base) |
| EXP-0002 | 2026-09-08 | buy_hold_equal_weight | a7ee9ad771 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +1439.9 % | 0.99 | +79.4 % | 0 | go (línea base) |
| EXP-0003 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | iterar |
| EXP-0004 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | go (control: reproducibilidad) |
| EXP-0005 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | go (control: defaults sin costo) |
| EXP-0006 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +65.4 % | 1.14 | +7.7 % | 76 | no-go (niveles agresivos en BTC+ETH; la mecánica del ADR-0007 queda validada) |
| EXP-0007 | 2026-09-09 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +76.9 % | 0.75 | +15.5 % | 248 | no-go (defaults v1 `cross` en 8 pares: top 10 > 100 % del PnL) |
| WF-0001 | 2026-09-09 | ema_trend | b978b0fa53 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +23.4 % | 0.48 | +14.3 % | 163 | no-go (Gate 1 no aprobado: Sharpe OOS 0.48) |
| WF-0002 | 2026-09-09 | ema_trend | b978b0fa53 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +77.5 % | 1.03 | +15.5 % | 140 | no-go (afinar parámetros refutada: 2 trades = 102 % del PnL) |
