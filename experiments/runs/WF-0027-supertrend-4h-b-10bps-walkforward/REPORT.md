# WF-0027 — supertrend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 29.7 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +3.17 % | 1.24 | 3.10 % | 23 | 1.79 | 0 | 11 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -1.64 % | -1.87 | 2.54 % | 5 | 0.00 | 0 | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -4.52 % | -1.22 | 6.79 % | 47 | 0.60 | 0 | 22 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +5.59 % | 1.36 | 5.44 % | 31 | 1.67 | 0 | 11 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -0.88 % | -0.28 | 5.18 % | 31 | 0.88 | 0 | 18 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +1.29 % | 0.49 | 3.10 % | 23 | 1.34 | 3 (-21.66) | 16 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +1.32 % | 0.41 | 6.30 % | 27 | 1.29 | 0 | 17 |

3 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +4.07 % | +174.73 % | +203.24 % | +173.86 % |
| CAGR | +1.00 % | +28.74 % | +31.96 % | +28.64 % |
| Sharpe (diario) | 0.20 | 0.76 | 1.04 | 0.72 |
| Sortino (diario) | 0.31 | 1.11 | 1.69 | 1.03 |
| Calmar | 0.13 | 0.37 | 1.16 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +7.78 % / 728 d | +77.14 % / 852 d | +27.48 % / 438 d | +81.55 % / 1108 d |
| Profit factor | 1.12 | — | — | — |
| Win rate | +33.16 % | — | — | — |
| Expectancy por trade | 2.59 | — | — | — |
| Trades / duración media | 187 / 95.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +24.88 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 347.48 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,407.07 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +10.76 %, Sharpe 0.31, max DD +7.78 %, 281 trades.

## Gate 1 — backtest -> paper: no aprobado (4 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.20 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.12 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.14 %) | 7.78 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 4/8 (50 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 281 | OK |  |
| Trades curva OOS | >= 40 | 187 | OK |  |
| Régimen: retorno 2020 | > 0 | +3.76 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +7.68 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +1.93 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -1.59 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 7.59 % (2023) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 15.03 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -1.38 % | 1.38 % | 4 | -138.25 |
| 2020 | +3.76 % | 5.16 % | 51 | 249.45 |
| 2021 | +7.68 % | 4.33 % | 59 | 914.71 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +1.93 % | 7.59 % | 76 | 218.35 |
| 2024 | -1.59 % | 7.31 % | 58 | -168.35 |
| 2025 (parcial) | +0.21 % | 6.28 % | 33 | 29.95 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 187 trades, semilla 42: max DD p50 +7.41 %, p95 +15.03 %, p99 +18.91 %; retorno p05 -10.18 %, p50 +4.58 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +10.80 %, p95 +19.87 %, p99 +24.69 %; retorno p05 -14.08 %, p50 +3.23 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (0.31). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8 | +7.96 % | 1.13 | 0.24 | 276 | sí |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | +10.36 % | 1.20 | 0.31 | 217 | sí |
| stop_atr_mult=2.4 | +10.53 % | 1.16 | 0.29 | 297 | sí |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +10.67 % | 1.12 | 0.26 | 404 | sí |
| atr_period=12 | +12.68 % | 1.21 | 0.35 | 282 | sí |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | +14.44 % | 1.16 | 0.33 | 396 | sí |
| multiplier=2.4 | +15.60 % | 1.20 | 0.36 | 365 | sí |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +16.06 % | 1.29 | 0.44 | 227 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
