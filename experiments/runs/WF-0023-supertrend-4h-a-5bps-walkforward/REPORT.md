# WF-0023 — supertrend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 28.5 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +1.67 % | 1.47 | 1.25 % | 17 | 2.20 | 0 | 17 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -0.64 % | -1.83 | 0.99 % | 4 | 0.00 | 0 | 1 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.15 % | -0.12 | 1.92 % | 34 | 0.96 | 0 | 35 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +2.79 % | 1.67 | 2.16 % | 22 | 2.11 | 0 | 20 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.35 % | 0.29 | 1.84 % | 23 | 1.18 | 0 | 26 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.98 % | 0.91 | 1.15 % | 17 | 1.65 | 2 (-3.83) | 23 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +1.38 % | 0.96 | 2.04 % | 20 | 2.02 | 0 | 24 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +6.53 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | +1.59 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | 0.67 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | 1.09 | 1.12 | 1.74 | 1.03 |
| Calmar | 0.59 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +2.70 % / 523 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 1.50 | — | — | — |
| Win rate | +37.96 % | — | — | — |
| Expectancy por trade | 4.82 | — | — | — |
| Trades / duración media | 137 / 98.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +23.89 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 127.70 / 5.5 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,652.72 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +6.47 %, Sharpe 0.44, max DD +2.70 %, 213 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.67 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.50 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 2.70 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 213 | OK |  |
| Trades curva OOS | >= 40 | 137 | OK |  |
| Régimen: retorno 2020 | > 0 | +1.31 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +1.12 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +2.83 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +0.78 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 2.70 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 4.12 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.68 % | 0.68 % | 4 | -68.16 |
| 2020 | +1.31 % | 2.07 % | 40 | 112.40 |
| 2021 | +1.12 % | 1.92 % | 47 | 136.04 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +2.83 % | 2.16 % | 55 | 292.12 |
| 2024 | +0.78 % | 2.70 % | 42 | 88.61 |
| 2025 (parcial) | +0.97 % | 2.04 % | 25 | 105.99 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 137 trades, semilla 42: max DD p50 +2.15 %, p95 +4.12 %, p99 +5.52 %; retorno p05 +0.01 %, p50 +6.56 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +3.26 %, p95 +5.97 %, p99 +7.62 %; retorno p05 -1.37 %, p50 +6.16 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (0.44). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8 | +3.33 % | 1.17 | 0.25 | 209 | sí |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +5.21 % | 1.28 | 0.37 | 180 | sí |
| multiplier=2.4 | +6.31 % | 1.24 | 0.37 | 269 | sí |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +6.85 % | 1.21 | 0.38 | 301 | sí |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | +7.35 % | 1.39 | 0.51 | 170 | sí |
| stop_atr_mult=2.4 | +7.44 % | 1.32 | 0.49 | 229 | sí |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | +7.77 % | 1.26 | 0.43 | 294 | sí |
| atr_period=12 | +8.08 % | 1.39 | 0.53 | 212 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
