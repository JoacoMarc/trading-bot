# WF-0031 — supertrend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 124.7 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -1.32 % | -0.56 | 3.24 % | 65 | 0.85 | 0 | 65 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -1.06 % | -0.81 | 1.90 % | 15 | 0.58 | 2 (-6.31) | 19 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -5.68 % | -1.98 | 6.86 % | 110 | 0.63 | 0 | 141 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -2.35 % | -0.99 | 5.00 % | 81 | 0.80 | 0 | 92 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.63 % | 0.24 | 4.03 % | 99 | 1.06 | 0 | 129 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -7.22 % | -3.54 | 7.31 % | 90 | 0.41 | 0 | 107 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -3.70 % | -1.33 | 6.95 % | 101 | 0.75 | 0 | 132 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -19.16 % | +172.55 % | +178.66 % | +171.69 % |
| CAGR | -5.18 % | +28.49 % | +29.20 % | +28.39 % |
| Sharpe (diario) | -1.12 | 0.75 | 0.97 | 0.72 |
| Sortino (diario) | -1.76 | 1.11 | 1.58 | 1.02 |
| Calmar | -0.24 | 0.37 | 0.98 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +21.29 % / 1425 d | +77.34 % / 851 d | +29.70 % / 437 d | +81.69 % / 1108 d |
| Profit factor | 0.73 | — | — | — |
| Win rate | +28.88 % | — | — | — |
| Expectancy por trade | -3.53 | — | — | — |
| Trades / duración media | 561 / 23.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +22.70 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,007.19 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 8,084.46 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -9.28 %, Sharpe -0.27, max DD +21.54 %, 833 trades.

## Gate 1 — backtest -> paper: no aprobado (6 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | -1.12 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.73 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.34 %) | 21.29 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 833 | OK |  |
| Trades curva OOS | >= 40 | 561 | OK |  |
| Régimen: retorno 2020 | > 0 | +8.50 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +4.58 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -7.87 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -5.06 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 8.53 % (2023) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 34.16 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.45 % | 2.48 % | 28 | -44.14 |
| 2020 | +8.50 % | 3.97 % | 168 | 849.77 |
| 2021 | +4.58 % | 3.27 % | 161 | 517.43 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -7.87 % | 8.53 % | 194 | -876.50 |
| 2024 | -5.06 % | 8.31 % | 184 | -499.51 |
| 2025 (parcial) | -8.18 % | 8.34 % | 98 | -786.12 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 561 trades, semilla 42: max DD p50 +22.66 %, p95 +34.16 %, p99 +38.56 %; retorno p05 -32.74 %, p50 -20.23 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +20.49 %, p95 +29.71 %, p99 +33.48 %; retorno p05 -28.33 %, p50 -18.44 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | -32.92 % | 0.78 | -1.12 | 1182 | no |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | -29.43 % | 0.81 | -0.93 | 1189 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | -20.53 % | 0.82 | -0.74 | 752 | no |
| stop_atr_mult=2.4 | -18.58 % | 0.86 | -0.60 | 925 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | -17.00 % | 0.85 | -0.57 | 761 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=3.6 | -14.64 % | 0.83 | -0.58 | 652 | no |
| multiplier=3.6 | -14.24 % | 0.85 | -0.47 | 687 | no |
| atr_period=8 | -13.44 % | 0.89 | -0.41 | 840 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
