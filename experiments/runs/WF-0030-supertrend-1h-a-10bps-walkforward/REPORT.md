# WF-0030 — supertrend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 123.7 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -0.43 % | -0.17 | 2.94 % | 64 | 0.96 | 0 | 66 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -0.83 % | -0.64 | 1.75 % | 15 | 0.65 | 2 (-4.82) | 19 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -3.43 % | -1.24 | 4.78 % | 108 | 0.76 | 0 | 143 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -1.03 % | -0.43 | 3.77 % | 81 | 0.91 | 0 | 92 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +2.29 % | 0.78 | 3.70 % | 99 | 1.22 | 0 | 129 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -5.88 % | -2.94 | 5.99 % | 89 | 0.48 | 0 | 108 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -1.67 % | -0.64 | 5.49 % | 99 | 0.88 | 0 | 134 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -10.67 % | +174.73 % | +199.75 % | +173.86 % |
| CAGR | -2.78 % | +28.74 % | +31.58 % | +28.64 % |
| Sharpe (diario) | -0.60 | 0.76 | 1.03 | 0.72 |
| Sortino (diario) | -0.99 | 1.11 | 1.68 | 1.03 |
| Calmar | -0.21 | 0.37 | 1.10 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +13.30 % / 1425 d | +77.29 % / 850 d | +28.64 % / 437 d | +81.65 % / 1108 d |
| Profit factor | 0.85 | — | — | — |
| Win rate | +31.17 % | — | — | — |
| Expectancy por trade | -1.83 | — | — | — |
| Trades / duración media | 555 / 23.9 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +22.85 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,005.62 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 8,933.19 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +6.53 %, Sharpe 0.22, max DD +13.34 %, 847 trades.

## Gate 1 — backtest -> paper: no aprobado (6 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -0.60 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.85 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.29 %) | 13.30 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 847 | OK |  |
| Trades curva OOS | >= 40 | 555 | OK |  |
| Régimen: retorno 2020 | > 0 | +11.31 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +6.81 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -4.38 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -2.29 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 6.96 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 21.43 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 25.22 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.05 % | 2.34 % | 28 | -4.40 |
| 2020 | +11.31 % | 3.60 % | 168 | 1,134.45 |
| 2021 | +6.81 % | 3.06 % | 158 | 780.65 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -4.38 % | 5.97 % | 192 | -508.15 |
| 2024 | -2.29 % | 6.96 % | 184 | -233.93 |
| 2025 (parcial) | -4.05 % | 5.95 % | 117 | -422.74 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 555 trades, semilla 42: max DD p50 +14.48 %, p95 +25.22 %, p99 +29.94 %; retorno p05 -23.66 %, p50 -10.36 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +13.88 %, p95 +22.47 %, p99 +26.01 %; retorno p05 -20.65 %, p50 -10.24 %.

## Meseta ±20 %

14 variantes, pasan +21.43 % (PF > 1.1 y retorno > 0). Informativo: +35.71 % de las variantes tiene Sharpe >= 0.5 x el base (0.22). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_period=8, multiplier=2.4, stop_atr_mult=2.4 | -12.71 % | 0.92 | -0.35 | 1200 | no |
| atr_period=12, multiplier=2.4, stop_atr_mult=2.4 | -9.48 % | 0.95 | -0.24 | 1216 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=2.4 | -8.93 % | 0.92 | -0.29 | 770 | no |
| multiplier=3.6 | -5.57 % | 0.95 | -0.16 | 708 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=2.4 | -4.30 % | 0.97 | -0.12 | 773 | no |
| atr_period=12, multiplier=3.6, stop_atr_mult=3.6 | -3.08 % | 0.97 | -0.09 | 652 | no |
| stop_atr_mult=2.4 | -2.47 % | 0.99 | -0.05 | 952 | no |
| atr_period=8, multiplier=3.6, stop_atr_mult=3.6 | -1.50 % | 0.99 | -0.03 | 644 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
