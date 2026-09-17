# WF-0032 — supertrend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 141.6 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -2.41 % | -0.40 | 7.18 % | 86 | 0.88 | 0 | 44 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -3.44 % | -1.14 | 4.54 % | 21 | 0.50 | 3 (-28.90) | 12 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -8.42 % | -1.40 | 12.32 % | 144 | 0.72 | 0 | 107 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -1.25 % | -0.18 | 6.96 % | 107 | 0.95 | 0 | 66 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +1.95 % | 0.39 | 7.44 % | 134 | 1.08 | 0 | 94 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -12.73 % | -2.63 | 13.47 % | 120 | 0.52 | 0 | 77 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -2.99 % | -0.51 | 11.58 % | 134 | 0.90 | 0 | 99 |

3 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -26.44 % | +175.83 % | +210.90 % | +174.95 % |
| CAGR | -7.39 % | +28.87 % | +32.79 % | +28.77 % |
| Sharpe (diario) | -0.72 | 0.76 | 1.06 | 0.72 |
| Sortino (diario) | -1.14 | 1.12 | 1.72 | 1.03 |
| Calmar | -0.24 | 0.37 | 1.17 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +30.92 % / 1361 d | +77.27 % / 850 d | +28.10 % / 437 d | +81.64 % / 1108 d |
| Profit factor | 0.82 | — | — | — |
| Win rate | +31.37 % | — | — | — |
| Expectancy por trade | -3.75 | — | — | — |
| Trades / duración media | 746 / 24.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +23.90 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 2,278.63 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 7,355.99 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +2.51 %, Sharpe 0.09, max DD +32.47 %, 1104 trades.

## Gate 1 — backtest -> paper: no aprobado (8 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -0.72 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.82 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.27 %) | 30.92 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 1104 | OK |  |
| Trades curva OOS | >= 40 | 746 | OK |  |
| Régimen: retorno 2020 | > 0 | +21.57 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +14.56 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -11.13 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -9.10 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 15.29 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 14.29 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 54.81 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -1.56 % | 5.50 % | 36 | -155.52 |
| 2020 | +21.57 % | 8.14 % | 227 | 2,128.73 |
| 2021 | +14.56 % | 8.64 % | 214 | 1,768.14 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -11.13 % | 14.68 % | 257 | -1,507.01 |
| 2024 | -9.10 % | 15.29 % | 212 | -1,078.10 |
| 2025 (parcial) | -7.44 % | 11.84 % | 158 | -794.85 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 746 trades, semilla 42: max DD p50 +33.65 %, p95 +54.81 %, p99 +63.08 %; retorno p05 -52.28 %, p50 -28.46 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +30.64 %, p95 +45.33 %, p99 +51.02 %; retorno p05 -42.84 %, p50 -25.24 %.

## Meseta ±20 %

14 variantes, pasan +14.29 % (PF > 1.1 y retorno > 0). Informativo: +50.00 % de las variantes tiene Sharpe >= 0.5 x el base (0.09). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| multiplier=3.6 | -14.15 % | 0.94 | -0.17 | 892 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=3.6 | -6.67 % | 0.97 | -0.05 | 873 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | -5.89 % | 0.98 | -0.04 | 949 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | -5.13 % | 0.98 | -0.03 | 948 | no |
| atr_period=8 | -4.95 % | 0.99 | -0.01 | 1105 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=3.6 | -4.54 % | 0.98 | -0.01 | 864 | no |
| stop_atr_mult=2.4 | -4.16 % | 0.99 | -0.01 | 1201 | no |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +0.46 % | 1.01 | 0.07 | 1623 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
