# WF-0001 — ema_trend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 4d776a274063; activación tardía: LINK/USDT desde 2019-08-04, SOL/USDT desde 2021-02-27
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git 571beeb, params b978b0fa53, datos 4d776a274063, 243.0 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `adx_period` | `14` |
| `adx_threshold` | `20.0` |
| `atr_period` | `14` |
| `cooldown_candles` | `2` |
| `ema_fast` | `20` |
| `ema_regime` | `200` |
| `ema_slow` | `50` |
| `entry_mode` | `cross` |
| `stop_atr_mult` | `2.0` |
| `trailing_atr_mult` | `3.0` |
| `warmup_multiplier` | `6` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +11.29 % | 1.72 | 5.21 % | 18 | 2.42 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +2.29 % | 0.55 | 6.35 % | 12 | 1.17 | 3 (+111.65) |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -8.29 % | -2.38 | 10.86 % | 17 | 0.13 | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.17 % | 0.07 | 5.96 % | 26 | 0.99 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +16.57 % | 1.91 | 8.85 % | 31 | 2.02 | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +3.77 % | 0.69 | 5.85 % | 17 | 1.92 | 1 (-52.68) |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +7.26 % | 1.15 | 6.16 % | 27 | 1.76 | 1 (-8.45) |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -8.71 % | -2.07 | 9.16 % | 15 | 0.12 | 0 |

5 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) |
|---|---|---|
| Retorno total | +23.44 % | +175.83 % |
| CAGR | +5.41 % | +28.87 % |
| Sharpe (diario) | 0.48 | 0.76 |
| Sortino (diario) | 0.82 | 1.12 |
| Calmar | 0.38 | 0.37 |
| Max drawdown / mayor tramo bajo agua | +14.28 % / 452 d | +77.11 % / 852 d |
| Profit factor | 1.31 | — |
| Win rate | +32.52 % | — |
| Expectancy por trade | 14.58 | — |
| Trades / duración media | 163 / 93.0 h | 0 / — h |
| Exposición | +25.74 % | +100.00 % |
| Fees pagados / shortfall medio | 674.67 / 5.4 bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 12,344.06 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +70.21 %, Sharpe 0.72, max DD +15.45 %, 243 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.48 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.31 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 14.28 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 243 | OK |  |
| Trades curva OOS | >= 40 | 163 | OK |  |
| Régimen: retorno 2020 | > 0 | +31.70 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +21.85 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +19.16 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +2.41 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | -7.46 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 12.39 % (2022) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 25.35 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -1.98 % | 6.46 % | 7 | -198.22 |
| 2020 | +31.70 % | 10.73 % | 44 | 2,727.80 |
| 2021 | +21.85 % | 8.32 % | 42 | 3,207.18 |
| 2022 | -7.46 % | 12.39 % | 32 | -1,171.13 |
| 2023 | +19.16 % | 8.85 % | 49 | 2,793.38 |
| 2024 | +2.41 % | 11.75 % | 47 | 424.50 |
| 2025 (parcial) | -4.18 % | 12.32 % | 22 | -739.94 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 163 trades, semilla 42: max DD p50 +11.84 %, p95 +25.35 %, p99 +33.28 %; retorno p05 -11.56 %, p50 +22.32 %.

## Meseta ±20 %

42 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Trades | Pasa |
|---|---|---|---|---|
| adx_threshold=24.0, ema_fast=16, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +6.70 % | 1.11 | 143 | sí |
| adx_threshold=24.0, ema_fast=16, ema_slow=40, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +14.52 % | 1.28 | 142 | sí |
| adx_threshold=24.0 | +15.42 % | 1.23 | 135 | sí |
| adx_threshold=24.0, ema_fast=24, ema_slow=40, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +17.25 % | 1.33 | 138 | sí |
| adx_threshold=24.0, ema_fast=24, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +24.18 % | 1.39 | 138 | sí |
| adx_threshold=24.0, ema_fast=16, ema_slow=60, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +28.08 % | 1.44 | 149 | sí |
| adx_threshold=16.0, ema_fast=16, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +30.27 % | 1.13 | 407 | sí |
| trailing_atr_mult=2.5 | +31.19 % | 1.26 | 246 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (Gate 1 no aprobado: Sharpe OOS 0.48)
- **Alcance**: los defaults v1 con `cross` en 4h quedan refutados como candidata a paper (Sharpe OOS < 0.8 y < 0.76 del B&H BTC); la familia `ema_trend` sigue con spec v2.
- **Por qué**: curva OOS 2021-08 → 2025-08: +23.44 % / Sharpe 0.48 / DD 14.28 % con 163 trades, contra B&H BTC encadenado +175.8 % / 0.76 / DD 77.1 %. Gana en DD, pierde en Sharpe: cede el 87 % del retorno sin mejorar el retorno por unidad de riesgo. Lo que pasa, pasa justo: PF 1.31 (umbral 1.3); 5/8 ventanas positivas pero dos de ellas +2.29 % y +3.77 %; las dos negativas (−8.29 %, −8.71 %) tienen PF 0.13 y 0.12. Concentración OOS: top 5 = 154 % del PnL, top 10 = 230 % (sin ellos −3,097.07); Monte Carlo p05 −11.6 %. Sharpe con error estándar ≈ 0.50 sobre 4 años: 0.48 no se distingue de 0 ni de 0.76; no hay evidencia de edge OOS y el gate la exige.
- **Qué se aprendió**: (1) El gap 0.72 (muestra completa) → 0.48 (OOS) es el período, no el método: la muestra continua de EXP-0007 restringida a 2021-08 → 2025-08 da +20.43 % / Sharpe 0.43 / DD 13.85 % (corr diaria 0.999 con la curva OOS; los 163 trades son idénticos y ningún cruce se perdió por arrancar en cash). El corte de bordes hasta favorece al WF (≈ +3 pp): las 5 posiciones abiertas al cierre se valuaron en +50.52 y en la continua realizaron −376.49. El edge vive en 2019-08 → 2021-08 (Sharpe 1.24, +41.08 %) y no persiste después (0.43). (2) BTC+ETH solos en el mismo rango (EXP-0003): Sharpe 0.84, +22.38 %, DD 7.07 %; los 6 pares agregados no aportan OOS (ADA −406.52, LTC −1,061.75, XRP −219.92), pero recortar el universo por PnL es snooping: LINK y LTC invierten su signo entre mitades del rango. (3) La meseta al 100 % no informa: el criterio (PF > 1.1, retorno > 0) es laxo y el retorno de las 42 variantes va de +7 % a +277 %; `trailing_atr_mult` 2.5 / 3.0 / 3.5 da medianas +32 % / +74 % / +160 % (pendiente monótona, no meseta). Que 22/42 variantes superen la base dice que los defaults no están sobreajustados, no que la estrategia sea robusta; el retorno depende de cuánto se deja correr al ganador. (4) 52 stops OOS, todos perdedores (−4,599.75), 24 en ≤ 24 h: misma patología que la muestra completa. (5) El PnL de `trades.csv` del WF está a 10,000 por tramo (2,375.97 vs 3,282.19 en la continua): PF y Monte Carlo son comparables, el PnL absoluto no.
- **Siguiente experimento propuesto**: spec v2 de `ema_trend` y como máximo 3 corridas antes de cerrar la familia. (1) WF-0002 (corrido a continuación): modo optimizado (optuna 50 trials por ventana, objetivo `sharpe`, `min_trades` 40) con `cross`: prueba si la sensibilidad a `trailing_atr_mult` sobrevive eligiendo solo en IS; refuta la vía "afinar parámetros" si el Sharpe OOS optimizado ≤ el del modo fijo (0.48). (2) WF-0003 modo fijo con `entry_mode=state`, `cooldown_candles=2`, resto default, 4h, 8 pares, `--plateau`, MC 5,000 (spec v2 antes del código): ataca los 38/76 stops ≤ 24 h y la no re-entrada tras un stop con la tendencia viva. Confirma si Sharpe OOS ≥ 0.8 y ≥ B&H, PF OOS ≥ 1.3, top 10 ≤ 150 % del PnL OOS y costos ≤ 30 % del bruto; refuta `state` en 4h si Sharpe OOS ≤ 0.5 o PF OOS < 1.2. (3) Solo si (1) y (2) fallan: 1h con la misma lógica; si tampoco pasa, `no-go` de la familia sin gastar el holdout y nueva spec de otra familia. No hacer: reducir el universo por PnL, retocar parámetros a mano sobre la muestra completa, ni `--include-holdout` antes de un WF aprobado.
