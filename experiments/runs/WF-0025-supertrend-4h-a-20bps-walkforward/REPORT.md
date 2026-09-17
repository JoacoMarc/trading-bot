# WF-0025 — supertrend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 29.3 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +1.52 % | 1.33 | 1.32 % | 17 | 2.03 | 0 | 17 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -0.67 % | -1.91 | 1.02 % | 4 | 0.00 | 0 | 1 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.56 % | -0.38 | 2.11 % | 34 | 0.85 | 0 | 35 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +2.49 % | 1.48 | 2.26 % | 22 | 1.94 | 0 | 20 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.05 % | 0.05 | 2.03 % | 23 | 1.04 | 0 | 26 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.77 % | 0.71 | 1.23 % | 17 | 1.49 | 2 (-5.04) | 23 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +1.06 % | 0.73 | 2.22 % | 20 | 1.70 | 0 | 24 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +4.70 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | +1.16 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | 0.48 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | 0.77 | 1.11 | 1.59 | 1.02 |
| Calmar | 0.39 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +2.97 % / 526 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 1.34 | — | — | — |
| Win rate | +36.50 % | — | — | — |
| Expectancy por trade | 3.55 | — | — | — |
| Trades / duración media | 137 / 98.3 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +23.88 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 127.53 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,470.15 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +3.91 %, Sharpe 0.27, max DD +2.97 %, 213 trades.

## Gate 1 — backtest -> paper: no aprobado (2 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | 0.48 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.34 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 2.97 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 213 | OK |  |
| Trades curva OOS | >= 40 | 137 | OK |  |
| Régimen: retorno 2020 | > 0 | +0.83 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +0.79 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +2.13 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +0.25 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 2.97 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 71.43 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 4.91 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.72 % | 0.72 % | 4 | -71.97 |
| 2020 | +0.83 % | 2.30 % | 40 | 65.65 |
| 2021 | +0.79 % | 2.04 % | 47 | 102.27 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +2.13 % | 2.26 % | 55 | 219.21 |
| 2024 | +0.25 % | 2.97 % | 42 | 32.54 |
| 2025 (parcial) | +0.58 % | 2.23 % | 25 | 64.02 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 137 trades, semilla 42: max DD p50 +2.52 %, p95 +4.91 %, p99 +6.48 %; retorno p05 -1.66 %, p50 +4.83 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +3.67 %, p95 +6.85 %, p99 +8.67 %; retorno p05 -3.15 %, p50 +4.35 %.

## Meseta ±20 %

14 variantes, pasan +71.43 % (PF > 1.1 y retorno > 0). Informativo: +78.57 % de las variantes tiene Sharpe >= 0.5 x el base (0.27). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8 | +0.87 % | 1.05 | 0.07 | 209 | no |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +2.00 % | 1.06 | 0.12 | 303 | no |
| multiplier=2.4 | +2.06 % | 1.08 | 0.13 | 270 | no |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | +2.95 % | 1.10 | 0.18 | 296 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +2.47 % | 1.13 | 0.18 | 180 | sí |
| stop_atr_mult=2.4 | +3.80 % | 1.16 | 0.26 | 230 | sí |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | +4.68 % | 1.24 | 0.33 | 170 | sí |
| atr_period=12 | +5.51 % | 1.26 | 0.37 | 212 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
