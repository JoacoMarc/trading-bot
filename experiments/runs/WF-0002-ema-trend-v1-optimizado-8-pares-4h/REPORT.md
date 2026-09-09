# WF-0002 — ema_trend 4h walk-forward IS 24 m / OOS 6 m (optimizado)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 4d776a274063
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo optimizado: optuna TPE, 50 trials por ventana, semilla 42, objetivo `sharpe`, min_trades 40
- Reproducibilidad: git 571beeb, params b978b0fa53, datos 4d776a274063, 764.7 s en PC-Joaco

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
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | adx_threshold=15.0, ema_fast=29, ema_slow=60, stop_atr_mult=3.5, trailing_atr_mult=4.0 | +6.81 % | 1.37 | 7.18 % | 21 | 1.88 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | adx_threshold=15.0, ema_fast=21, ema_slow=80, stop_atr_mult=2.5, trailing_atr_mult=4.0 | -0.72 % | -0.07 | 8.42 % | 17 | 0.68 | 3 (+254.76) |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | adx_threshold=15.0, ema_fast=27, ema_slow=60, stop_atr_mult=3.5, trailing_atr_mult=4.5 | +8.30 % | 1.12 | 9.10 % | 21 | 0.74 | 2 (+1,120.92) |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | adx_threshold=22.0, ema_fast=26, ema_slow=65, stop_atr_mult=3.5, trailing_atr_mult=4.5 | -2.72 % | -0.47 | 4.97 % | 20 | 0.76 | 1 (-53.49) |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | adx_threshold=22.0, ema_fast=18, ema_slow=80, stop_atr_mult=1.5, trailing_atr_mult=4.5 | +36.58 % | 2.49 | 10.39 % | 23 | 3.52 | 2 (+59.08) |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | adx_threshold=24.0, ema_fast=15, ema_slow=45, stop_atr_mult=2.5 | +1.34 % | 0.45 | 2.76 % | 10 | 1.44 | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | adx_threshold=26.0, ema_fast=24, ema_slow=55, trailing_atr_mult=4.0 | +24.88 % | 2.23 | 8.03 % | 14 | 5.68 | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | adx_threshold=22.0, ema_fast=18, ema_slow=80, stop_atr_mult=4.0, trailing_atr_mult=4.5 | -8.06 % | -2.79 | 8.26 % | 14 | 0.01 | 0 |

8 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) |
|---|---|---|
| Retorno total | +77.53 % | +175.83 % |
| CAGR | +15.43 % | +28.87 % |
| Sharpe (diario) | 1.03 | 0.76 |
| Sortino (diario) | 1.88 | 1.12 |
| Calmar | 0.99 | 0.37 |
| Max drawdown / mayor tramo bajo agua | +15.54 % / 436 d | +77.11 % / 852 d |
| Profit factor | 1.77 | — |
| Win rate | +32.86 % | — |
| Expectancy por trade | 37.79 | — |
| Trades / duración media | 140 / 135.7 h | 0 / — h |
| Exposición | +33.05 % | +100.00 % |
| Fees pagados / shortfall medio | 468.28 / 5.5 bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 17,752.96 USDT.

## Gate 1 — backtest -> paper: incompleto (8 criterios sin evaluar)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 1.03 | OK |  |
| Profit factor OOS | >= 1.3 | 1.77 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 15.54 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | - | n/a | solo en modo fijo |
| Trades curva OOS | >= 40 | 140 | OK |  |
| Régimen: retorno 2020 | > 0 | sin datos | n/a | curva OOS concatenada (informativo: n/a en modo optimizado) |
| Régimen: retorno 2021 | > 0 | parcial (+6.13 %) | n/a | curva OOS concatenada (informativo: n/a en modo optimizado) |
| Régimen: retorno 2023 | > 0 | +55.29 % | n/a | curva OOS concatenada (informativo: n/a en modo optimizado) |
| Régimen: retorno 2024 | > 0 | +18.04 % | n/a | curva OOS concatenada (informativo: n/a en modo optimizado) |
| Régimen: retorno 2022 | >= -8 % | -2.98 % | n/a | curva OOS concatenada (informativo: n/a en modo optimizado) |
| Régimen: max DD intra-año | <= 25 % | 12.27 % (2025) | n/a | curva OOS concatenada (informativo: n/a en modo optimizado) |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | - | n/a | correr con --plateau |
| Monte Carlo DD p95 | <= 35 % | 24.67 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (curva OOS concatenada (informativo: n/a en modo optimizado))

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2021 (parcial) | +6.13 % | 7.18 % | 20 | 617.39 |
| 2022 | -2.98 % | 11.84 % | 39 | -539.82 |
| 2023 | +55.29 % | 8.82 % | 36 | 3,397.04 |
| 2024 | +18.04 % | 7.78 % | 26 | 2,337.20 |
| 2025 (parcial) | -5.94 % | 12.27 % | 19 | -521.01 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 140 trades, semilla 42: max DD p50 +11.16 %, p95 +24.67 %, p99 +33.49 %; retorno p05 -8.91 %, p50 +49.94 %.

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (afinar parámetros refutada: 2 trades = 102 % del PnL)
- **Por qué**: el Sharpe OOS 1.03 (≥ 0.8 y ≥ 0.76 del B&H) cumple la letra del criterio fijado en WF-0001, pero no por el mecanismo que se quería probar. Los 5,290.81 USDT de PnL OOS son dos trades (SOL 2023-10-16 → 11-21 +3,410.97, ADA 2024-11-07 → 26 +2,001.44 = 102 % del neto); sin ellos PnL −121.60 y PF 0.98 en 138 trades; top 10 = 162 % (falla el ≤ 150 % que WF-0001 fijó para la familia). Optimizar en IS no predice el OOS: correlación `is_score` vs retorno OOS −0.64 (Spearman −0.62); las 3 ventanas con mejor IS dieron +6.81 / −0.72 / −8.06 % y las 3 peores +36.58 / +1.34 / +24.88 %. Los parámetros saltan entre ventanas que comparten 18 de 24 meses de IS (`stop_atr_mult` 1.5 → 4.0, `ema_slow` 45–80, `adx_threshold` en el borde 15 en w1–w3). La mejora vs modo fijo (1.03 vs 0.48) es ≈ 1.1 SE (SE ≈ 0.50; t pareado diario 1.39): indistinguible de ruido. 1,381.27 USDT (18 % del Δequity) son posiciones abiertas valuadas a mercado sin fee; por trades cerrados las ventanas positivas son 4/8 y w3 pasa de +8.30 % a PF 0.74. Gate incompleto por diseño (8 n/a): no puede ser go.
- **Qué se aprendió**: (1) 50 trials sobre 24 meses con ~40–60 trades seleccionan ruido: Sharpe IS medio 1.74 → OOS 0.54 y correlación de signo invertido; la vía "afinar parámetros" de v1 `cross` queda cerrada, por ventana y sobre la muestra completa. (2) Lo único estable que eligió optuna es `trailing_atr_mult` ≥ 4.0 (7/8 ventanas), la misma pendiente monótona de la meseta de WF-0001: un trailing ancho convierte la estrategia en una apuesta a 1–2 parabólicas de altcoins por año (win rate 33 %, payoff 3.6); eso se mide con top-N y PF sin los 2 mejores, no con Sharpe. (3) La diferencia con el fijo no está en EMA/ADX sino en cuánto se deja correr (SOL vendida el 10-09 con +180.50 por trailing 3.0) y en no re-entrar tras stop (ADA: 2 stops en oct-2024, sin cruce en nov): confirma el diagnóstico de la spec v2. (4) En modo optimizado las abiertas al cierre inflan el retorno por ventana (w3 +1,120.92 sin fee): leer PF por trades cerrados. (5) La patología de entrada persiste con cualquier parámetro: 42 stops todos perdedores (−3,963.59, 23 en ≤ 24 h) y 19 salidas por señal todas perdedoras (−963.26). Costos irrelevantes (fees 3.9 % del bruto, shortfall 5.5 bps).
- **Siguiente experimento propuesto**: no volver a optimizar parámetros de v1 `cross` ni adoptar `trailing_atr_mult` 4.5 a mano (sería elegirlo mirando este OOS). Sigue el plan de WF-0001: spec v2 y WF-0003 en modo fijo con `entry_mode=state`, `cooldown_candles=2`, resto default (trailing 3.0), 8 pares 4h, IS 24 / OOS 6, `--plateau`, MC 5,000, semilla 42. Confirma si Sharpe OOS ≥ 0.8 y ≥ B&H, PF OOS ≥ 1.3, top 10 ≤ 150 % y top 2 ≤ 50 % del PnL OOS, PF sin los 2 mejores ≥ 1.1, ≥ 5/8 ventanas positivas por trades cerrados, costos ≤ 30 % del bruto; refuta `state` en 4h si Sharpe OOS ≤ 0.5 o PF OOS < 1.2. Lo que refutaría esta lectura de WF-0002 (opcional, ~13 min cada una, no recomendado): semillas 43 y 44 con Sharpe OOS ≥ 0.8 y top 2 ≤ 50 % del PnL en ambas; si se dispersan, el 1.03 fue suerte de dos trades.
