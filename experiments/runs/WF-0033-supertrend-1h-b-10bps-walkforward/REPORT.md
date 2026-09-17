# WF-0033 — supertrend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 126.6 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -4.33 % | -0.76 | 8.00 % | 87 | 0.79 | 0 | 43 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -3.72 % | -1.24 | 4.73 % | 21 | 0.47 | 3 (-31.07) | 12 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -10.05 % | -1.67 | 13.48 % | 145 | 0.68 | 0 | 106 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -2.88 % | -0.49 | 8.43 % | 107 | 0.89 | 0 | 66 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.02 % | 0.06 | 8.77 % | 134 | 1.01 | 0 | 94 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -14.41 % | -2.95 | 15.07 % | 121 | 0.48 | 0 | 76 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -4.94 % | -0.89 | 12.29 % | 134 | 0.83 | 0 | 99 |

3 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -34.53 % | +174.73 % | +199.75 % | +173.86 % |
| CAGR | -10.05 % | +28.74 % | +31.58 % | +28.64 % |
| Sharpe (diario) | -1.00 | 0.76 | 1.03 | 0.72 |
| Sortino (diario) | -1.55 | 1.11 | 1.68 | 1.03 |
| Calmar | -0.27 | 0.37 | 1.10 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +37.65 % / 1446 d | +77.29 % / 850 d | +28.64 % / 437 d | +81.65 % / 1108 d |
| Profit factor | 0.76 | — | — | — |
| Win rate | +30.44 % | — | — | — |
| Expectancy por trade | -5.20 | — | — | — |
| Trades / duración media | 749 / 24.2 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +23.86 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 2,263.80 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 6,547.38 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -11.79 %, Sharpe -0.11, max DD +38.76 %, 1084 trades.

## Gate 1 — backtest -> paper: no aprobado (8 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -1.00 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.76 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.29 %) | 37.65 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 1084 | OK |  |
| Trades curva OOS | >= 40 | 749 | OK |  |
| Régimen: retorno 2020 | > 0 | +17.77 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +11.09 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -14.35 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -12.30 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 17.79 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 64.13 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -1.94 % | 5.68 % | 36 | -193.15 |
| 2020 | +17.77 % | 8.52 % | 227 | 1,748.06 |
| 2021 | +11.09 % | 10.08 % | 215 | 1,307.05 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -14.35 % | 15.21 % | 227 | -1,825.80 |
| 2024 | -12.30 % | 17.79 % | 249 | -1,312.39 |
| 2025 (parcial) | -8.46 % | 12.30 % | 130 | -789.66 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 749 trades, semilla 42: max DD p50 +42.96 %, p95 +64.13 %, p99 +73.93 %; retorno p05 -62.38 %, p50 -39.16 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +37.16 %, p95 +51.34 %, p99 +56.65 %; retorno p05 -49.47 %, p50 -33.55 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | -27.46 % | 0.92 | -0.37 | 1498 | no |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | -25.18 % | 0.94 | -0.30 | 1578 | no |
| multiplier=3.6 | -22.92 % | 0.89 | -0.32 | 901 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | -22.18 % | 0.90 | -0.35 | 942 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | -20.37 % | 0.91 | -0.32 | 947 | no |
| stop_atr_mult=2.4 | -20.26 % | 0.93 | -0.29 | 1217 | no |
| multiplier=2.4 | -17.91 % | 0.95 | -0.19 | 1339 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=3.6 | -17.41 % | 0.91 | -0.23 | 837 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
