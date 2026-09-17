# WF-0029 — supertrend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 133.2 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.37 % | 0.19 | 2.88 % | 63 | 1.07 | 0 | 67 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -0.72 % | -0.56 | 1.67 % | 15 | 0.69 | 2 (-4.03) | 19 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -2.66 % | -0.97 | 4.19 % | 107 | 0.80 | 0 | 144 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -0.35 % | -0.13 | 3.14 % | 81 | 0.97 | 0 | 92 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +3.14 % | 1.05 | 3.52 % | 99 | 1.31 | 0 | 129 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -5.11 % | -2.61 | 5.23 % | 88 | 0.53 | 0 | 109 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -0.71 % | -0.26 | 4.99 % | 99 | 0.96 | 0 | 134 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -6.08 % | +175.83 % | +210.90 % | +174.95 % |
| CAGR | -1.56 % | +28.87 % | +32.79 % | +28.77 % |
| Sharpe (diario) | -0.33 | 0.76 | 1.06 | 0.72 |
| Sortino (diario) | -0.55 | 1.12 | 1.72 | 1.03 |
| Calmar | -0.14 | 0.37 | 1.17 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +10.79 % / 939 d | +77.27 % / 850 d | +28.10 % / 437 d | +81.64 % / 1108 d |
| Profit factor | 0.92 | — | — | — |
| Win rate | +32.07 % | — | — | — |
| Expectancy por trade | -0.94 | — | — | — |
| Trades / duración media | 552 / 24.1 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +22.89 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,005.15 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 9,392.28 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +14.13 %, Sharpe 0.43, max DD +10.73 %, 844 trades.

## Gate 1 — backtest -> paper: no aprobado (6 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -0.33 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.92 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.27 %) | 10.79 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 2/8 (25 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 844 | OK |  |
| Trades curva OOS | >= 40 | 552 | OK |  |
| Régimen: retorno 2020 | > 0 | +12.76 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +8.09 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -2.96 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -0.66 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 6.09 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 35.71 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 20.63 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.11 % | 2.30 % | 28 | 11.17 |
| 2020 | +12.76 % | 3.44 % | 168 | 1,281.47 |
| 2021 | +8.09 % | 3.04 % | 157 | 935.34 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -2.96 % | 5.21 % | 191 | -347.86 |
| 2024 | -0.66 % | 6.09 % | 183 | -51.44 |
| 2025 (parcial) | -2.97 % | 5.13 % | 117 | -324.33 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 552 trades, semilla 42: max DD p50 +11.08 %, p95 +20.63 %, p99 +24.67 %; retorno p05 -18.25 %, p50 -5.37 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +10.85 %, p95 +19.11 %, p99 +22.45 %; retorno p05 -16.48 %, p50 -5.76 %.

## Meseta ±20 %

14 variantes, pasan +35.71 % (PF > 1.1 y retorno > 0). Informativo: +50.00 % de las variantes tiene Sharpe >= 0.5 x el base (0.43). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | -0.87 % | 1.00 | -0.00 | 769 | no |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | -0.19 % | 1.01 | 0.02 | 1211 | no |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | -0.01 % | 1.01 | 0.03 | 1243 | no |
| multiplier=3.6 | +0.10 % | 1.01 | 0.03 | 707 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=3.6 | +2.07 % | 1.04 | 0.10 | 649 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=3.6 | +2.69 % | 1.04 | 0.11 | 643 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +2.92 % | 1.03 | 0.12 | 772 | no |
| atr_period=8 | +7.05 % | 1.07 | 0.24 | 842 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
