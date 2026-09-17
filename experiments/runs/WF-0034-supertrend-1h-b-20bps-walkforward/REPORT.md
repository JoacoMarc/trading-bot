# WF-0034 — supertrend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 124.0 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -6.75 % | -1.21 | 9.04 % | 88 | 0.69 | 0 | 42 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -4.57 % | -1.50 | 5.26 % | 22 | 0.39 | 2 (-12.25) | 12 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -13.46 % | -2.14 | 17.94 % | 149 | 0.61 | 0 | 102 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -5.69 % | -1.03 | 10.98 % | 107 | 0.78 | 0 | 66 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -3.66 % | -0.56 | 11.39 % | 134 | 0.88 | 0 | 94 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -17.30 % | -3.54 | 17.85 % | 122 | 0.41 | 0 | 75 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -7.82 % | -1.32 | 14.32 % | 136 | 0.75 | 0 | 97 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -46.65 % | +172.55 % | +178.66 % | +171.69 % |
| CAGR | -14.54 % | +28.49 % | +29.20 % | +28.39 % |
| Sharpe (diario) | -1.46 | 0.75 | 0.97 | 0.72 |
| Sortino (diario) | -2.19 | 1.11 | 1.58 | 1.02 |
| Calmar | -0.30 | 0.37 | 0.98 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +49.28 % / 1446 d | +77.34 % / 851 d | +29.70 % / 437 d | +81.69 % / 1108 d |
| Profit factor | 0.67 | — | — | — |
| Win rate | +28.63 % | — | — | — |
| Expectancy por trade | -7.66 | — | — | — |
| Trades / duración media | 758 / 23.9 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +23.84 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 2,249.14 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 5,334.65 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -30.82 %, Sharpe -0.44, max DD +47.69 %, 1046 trades.

## Gate 1 — backtest -> paper: no aprobado (8 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | -1.46 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.67 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.34 %) | 49.28 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 0/8 (0 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 1046 | OK |  |
| Trades curva OOS | >= 40 | 758 | OK |  |
| Régimen: retorno 2020 | > 0 | +10.50 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +5.26 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -17.39 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -17.58 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 21.85 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 83.07 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -2.87 % | 6.12 % | 36 | -286.71 |
| 2020 | +10.50 % | 9.28 % | 227 | 1,025.20 |
| 2021 | +5.26 % | 11.43 % | 217 | 592.37 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -17.39 % | 18.47 % | 227 | -1,948.99 |
| 2024 | -17.58 % | 21.85 % | 207 | -1,611.70 |
| 2025 (parcial) | -10.05 % | 14.73 % | 132 | -747.80 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 758 trades, semilla 42: max DD p50 +60.52 %, p95 +83.07 %, p99 +92.87 %; retorno p05 -81.87 %, p50 -58.34 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +47.82 %, p95 +61.14 %, p99 +65.67 %; retorno p05 -59.62 %, p50 -45.42 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | -53.39 % | 0.82 | -0.96 | 1476 | no |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | -51.68 % | 0.83 | -0.88 | 1573 | no |
| multiplier=2.4 | -47.62 % | 0.83 | -0.76 | 1321 | no |
| stop_atr_mult=2.4 | -46.37 % | 0.82 | -0.88 | 1204 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | -42.93 % | 0.79 | -0.88 | 919 | no |
| multiplier=3.6 | -40.86 % | 0.79 | -0.72 | 887 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | -38.23 % | 0.81 | -0.73 | 906 | no |
| atr_period=8 | -34.29 % | 0.86 | -0.52 | 1050 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
