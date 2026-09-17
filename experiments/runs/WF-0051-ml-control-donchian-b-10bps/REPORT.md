# WF-0051 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos 40a0aa8573b9, 29.1 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.30 % | 0.13 | 5.00 % | 35 | 1.05 | 0 | 62 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.69 % | 0.37 | 1.68 % | 7 | 1.42 | 0 | 15 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.47 % | -0.06 | 3.69 % | 37 | 0.93 | 0 | 46 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +17.00 % | 2.81 | 4.92 % | 30 | 3.41 | 1 (-37.11) | 71 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +3.15 % | 0.78 | 5.24 % | 37 | 1.38 | 1 (-29.69) | 60 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +5.16 % | 1.14 | 5.26 % | 36 | 1.65 | 0 | 73 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +5.08 % | 1.10 | 7.44 % | 31 | 1.62 | 0 | 106 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +34.05 % | +174.73 % | +203.24 % | +173.86 % |
| CAGR | +7.60 % | +28.74 % | +31.96 % | +28.64 % |
| Sharpe (diario) | 0.95 | 0.76 | 1.04 | 0.72 |
| Sortino (diario) | 1.67 | 1.11 | 1.69 | 1.03 |
| Calmar | 0.82 | 0.37 | 1.16 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +9.23 % / 776 d | +77.14 % / 852 d | +27.48 % / 438 d | +81.55 % / 1108 d |
| Profit factor | 1.65 | — | — | — |
| Win rate | +35.21 % | — | — | — |
| Expectancy por trade | 14.98 | — | — | — |
| Trades / duración media | 213 / 100.6 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +28.06 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 381.47 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 13,404.61 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +83.06 %, Sharpe 1.22, max DD +9.19 %, 328 trades.

## Gate 1 — backtest -> paper: aprobado (falta el holdout)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.95 | OK |  |
| Profit factor OOS | >= 1.3 | 1.65 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.14 %) | 9.23 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 100 | 328 | OK |  |
| Trades curva OOS | >= 40 | 213 | OK |  |
| Régimen: retorno 2020 | > 0 | +16.25 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +18.34 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +18.71 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +8.85 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 7.42 % (2025) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 11.26 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.14 % | 3.93 % | 9 | -13.52 |
| 2020 | +16.25 % | 5.10 % | 59 | 1,463.32 |
| 2021 | +18.34 % | 4.99 % | 80 | 2,300.22 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +18.71 % | 5.28 % | 70 | 2,574.60 |
| 2024 | +8.85 % | 7.12 % | 71 | 1,454.94 |
| 2025 (parcial) | +3.12 % | 7.42 % | 39 | 564.35 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 213 trades, semilla 42: max DD p50 +5.79 %, p95 +11.26 %, p99 +14.91 %; retorno p05 +6.55 %, p50 +31.48 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +10.01 %, p95 +17.51 %, p99 +21.50 %; retorno p05 -2.05 %, p50 +31.33 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.22). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, entry_period=48, exit_period=24 | +55.37 % | 1.44 | 0.84 | 439 | sí |
| atr_mult=2.4, entry_period=48, exit_period=16 | +55.59 % | 1.45 | 0.85 | 439 | sí |
| atr_mult=2.4 | +60.30 % | 1.50 | 0.92 | 420 | sí |
| atr_mult=2.4, entry_period=72, exit_period=24 | +60.40 % | 1.51 | 0.92 | 401 | sí |
| atr_mult=2.4, entry_period=72, exit_period=16 | +60.63 % | 1.51 | 0.93 | 401 | sí |
| entry_period=72 | +77.14 % | 1.84 | 1.20 | 314 | sí |
| exit_period=16 | +79.98 % | 1.83 | 1.21 | 331 | sí |
| entry_period=48 | +82.59 % | 1.83 | 1.21 | 342 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: referencia (reproducción; no autoriza paper)
- **Por qué**: Curvas equity.csv y trades.csv idénticas a sus controles anteriores. Mantiene las restricciones del protocolo original; B solo histórico.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
