# WF-0024 — supertrend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 29.1 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +1.62 % | 1.42 | 1.27 % | 17 | 2.14 | 0 | 17 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -0.65 % | -1.85 | 1.00 % | 4 | 0.00 | 0 | 1 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.29 % | -0.20 | 1.99 % | 34 | 0.93 | 0 | 35 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +2.69 % | 1.61 | 2.19 % | 22 | 2.05 | 0 | 20 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.25 % | 0.21 | 1.90 % | 23 | 1.13 | 0 | 26 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.91 % | 0.85 | 1.18 % | 17 | 1.59 | 2 (-4.23) | 23 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +1.27 % | 0.88 | 2.10 % | 20 | 1.91 | 0 | 24 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +5.91 % | +174.73 % | +203.24 % | +173.86 % |
| CAGR | +1.45 % | +28.74 % | +31.96 % | +28.64 % |
| Sharpe (diario) | 0.61 | 0.76 | 1.04 | 0.72 |
| Sortino (diario) | 0.98 | 1.11 | 1.69 | 1.03 |
| Calmar | 0.52 | 0.37 | 1.16 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +2.78 % / 523 d | +77.14 % / 852 d | +27.48 % / 438 d | +81.55 % / 1108 d |
| Profit factor | 1.44 | — | — | — |
| Win rate | +37.96 % | — | — | — |
| Expectancy por trade | 4.39 | — | — | — |
| Trades / duración media | 137 / 98.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +23.89 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 127.64 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,591.05 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +5.62 %, Sharpe 0.38, max DD +2.78 %, 213 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.61 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.44 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.14 %) | 2.78 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 213 | OK |  |
| Trades curva OOS | >= 40 | 137 | OK |  |
| Régimen: retorno 2020 | > 0 | +1.16 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +1.01 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +2.60 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +0.61 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 2.78 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 4.38 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.69 % | 0.69 % | 4 | -69.29 |
| 2020 | +1.16 % | 2.14 % | 40 | 97.94 |
| 2021 | +1.01 % | 1.96 % | 47 | 124.83 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +2.60 % | 2.19 % | 55 | 267.35 |
| 2024 | +0.61 % | 2.78 % | 42 | 69.67 |
| 2025 (parcial) | +0.84 % | 2.10 % | 25 | 91.80 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 137 trades, semilla 42: max DD p50 +2.26 %, p95 +4.38 %, p99 +5.86 %; retorno p05 -0.56 %, p50 +5.98 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +3.39 %, p95 +6.24 %, p99 +7.95 %; retorno p05 -1.92 %, p50 +5.54 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +92.86 % de las variantes tiene Sharpe >= 0.5 x el base (0.38). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8 | +2.51 % | 1.13 | 0.19 | 209 | sí |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +4.30 % | 1.22 | 0.31 | 180 | sí |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +5.25 % | 1.16 | 0.29 | 301 | sí |
| multiplier=2.4 | +5.26 % | 1.20 | 0.31 | 269 | sí |
| stop_atr_mult=2.4 | +6.24 % | 1.27 | 0.41 | 229 | sí |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | +6.25 % | 1.20 | 0.35 | 294 | sí |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | +6.46 % | 1.34 | 0.45 | 170 | sí |
| atr_period=12 | +7.22 % | 1.34 | 0.47 | 212 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
