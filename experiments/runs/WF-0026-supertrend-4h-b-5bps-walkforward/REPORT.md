# WF-0026 — supertrend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 29.5 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +3.31 % | 1.29 | 3.06 % | 23 | 1.84 | 0 | 11 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -1.61 % | -1.85 | 2.52 % | 5 | 0.00 | 0 | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -4.16 % | -1.12 | 6.60 % | 47 | 0.63 | 0 | 22 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +5.88 % | 1.43 | 5.36 % | 31 | 1.72 | 0 | 11 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -0.62 % | -0.19 | 5.01 % | 31 | 0.92 | 0 | 18 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +1.47 % | 0.56 | 3.03 % | 23 | 1.39 | 3 (-20.33) | 16 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +1.60 % | 0.50 | 6.14 % | 27 | 1.36 | 0 | 17 |

3 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +5.68 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | +1.39 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | 0.27 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | 0.42 | 1.12 | 1.74 | 1.03 |
| Calmar | 0.19 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +7.37 % / 727 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 1.16 | — | — | — |
| Win rate | +33.69 % | — | — | — |
| Expectancy por trade | 3.41 | — | — | — |
| Trades / duración media | 187 / 95.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +24.88 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 347.91 / 5.5 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,567.61 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +13.10 %, Sharpe 0.37, max DD +7.37 %, 281 trades.

## Gate 1 — backtest -> paper: no aprobado (4 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.27 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.16 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 7.37 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 4/8 (50 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 281 | OK |  |
| Trades curva OOS | >= 40 | 187 | OK |  |
| Régimen: retorno 2020 | > 0 | +4.16 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +7.98 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +2.58 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -1.14 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 7.20 % (2023) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 14.08 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -1.36 % | 1.36 % | 4 | -136.00 |
| 2020 | +4.16 % | 4.94 % | 51 | 287.52 |
| 2021 | +7.98 % | 4.28 % | 59 | 949.72 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +2.58 % | 7.20 % | 76 | 292.12 |
| 2024 | -1.14 % | 7.08 % | 58 | -120.02 |
| 2025 (parcial) | +0.54 % | 6.12 % | 33 | 66.84 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 187 trades, semilla 42: max DD p50 +6.93 %, p95 +14.08 %, p99 +17.91 %; retorno p05 -8.70 %, p50 +6.12 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +10.27 %, p95 +18.94 %, p99 +23.59 %; retorno p05 -12.75 %, p50 +4.90 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (0.37). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8 | +10.26 % | 1.17 | 0.30 | 276 | sí |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | +12.65 % | 1.24 | 0.37 | 217 | sí |
| stop_atr_mult=2.4 | +13.63 % | 1.20 | 0.37 | 297 | sí |
| atr_period=12 | +15.09 % | 1.25 | 0.40 | 282 | sí |
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | +15.92 % | 1.17 | 0.36 | 404 | sí |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | +18.60 % | 1.34 | 0.50 | 227 | sí |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | +18.73 % | 1.21 | 0.42 | 395 | sí |
| multiplier=2.4 | +18.80 % | 1.24 | 0.43 | 365 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
