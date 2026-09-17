# WF-0028 — supertrend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 29.6 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +2.89 % | 1.13 | 3.18 % | 23 | 1.69 | 0 | 11 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -1.70 % | -1.92 | 2.58 % | 5 | 0.00 | 0 | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -5.26 % | -1.41 | 7.19 % | 47 | 0.55 | 0 | 22 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +5.04 % | 1.22 | 5.61 % | 31 | 1.59 | 0 | 11 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -1.39 % | -0.46 | 5.54 % | 31 | 0.82 | 0 | 18 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.93 % | 0.36 | 3.23 % | 23 | 1.26 | 3 (-24.29) | 16 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +0.76 % | 0.25 | 6.62 % | 27 | 1.16 | 0 | 17 |

3 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +0.94 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | +0.23 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | 0.07 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | 0.11 | 1.11 | 1.59 | 1.02 |
| Calmar | 0.03 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +8.61 % / 778 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 1.04 | — | — | — |
| Win rate | +31.55 % | — | — | — |
| Expectancy por trade | 0.97 | — | — | — |
| Trades / duración media | 187 / 95.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +24.87 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 346.65 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,094.13 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +6.13 %, Sharpe 0.19, max DD +8.60 %, 281 trades.

## Gate 1 — backtest -> paper: no aprobado (5 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | 0.07 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.04 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 8.61 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 4/8 (50 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 281 | OK |  |
| Trades curva OOS | >= 40 | 187 | OK |  |
| Régimen: retorno 2020 | > 0 | +2.90 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +7.08 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +0.65 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -2.49 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 8.37 % (2023) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 64.29 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 17.18 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -1.44 % | 1.44 % | 4 | -143.57 |
| 2020 | +2.90 % | 5.67 % | 51 | 166.75 |
| 2021 | +7.08 % | 4.43 % | 59 | 845.00 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +0.65 % | 8.37 % | 76 | 75.98 |
| 2024 | -2.49 % | 7.77 % | 58 | -260.42 |
| 2025 (parcial) | -0.43 % | 6.61 % | 33 | -39.49 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 187 trades, semilla 42: max DD p50 +8.51 %, p95 +17.18 %, p99 +21.33 %; retorno p05 -13.12 %, p50 +1.57 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +11.89 %, p95 +21.79 %, p99 +26.84 %; retorno p05 -16.75 %, p50 +0.14 %.

## Meseta ±20 %

14 variantes, pasan +64.29 % (PF > 1.1 y retorno > 0). Informativo: +92.86 % de las variantes tiene Sharpe >= 0.5 x el base (0.19). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +1.97 % | 1.02 | 0.08 | 406 | no |
| atr_period=8 | +3.52 % | 1.06 | 0.13 | 276 | no |
| stop_atr_mult=2.4 | +3.99 % | 1.06 | 0.13 | 298 | no |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | +5.48 % | 1.06 | 0.15 | 398 | no |
| multiplier=2.4 | +7.85 % | 1.10 | 0.21 | 366 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | +5.91 % | 1.11 | 0.19 | 217 | sí |
| atr_period=12 | +7.96 % | 1.13 | 0.23 | 282 | sí |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +11.15 % | 1.20 | 0.32 | 227 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
