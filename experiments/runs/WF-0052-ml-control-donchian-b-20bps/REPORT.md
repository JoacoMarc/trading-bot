# WF-0052 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos 40a0aa8573b9, 30.1 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -0.09 % | 0.00 | 5.20 % | 35 | 1.00 | 0 | 62 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.59 % | 0.32 | 1.73 % | 7 | 1.34 | 0 | 15 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -1.05 % | -0.18 | 4.20 % | 37 | 0.86 | 0 | 46 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +16.40 % | 2.72 | 5.04 % | 30 | 3.23 | 1 (-38.57) | 71 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +2.53 % | 0.64 | 5.61 % | 37 | 1.30 | 1 (-30.17) | 60 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +4.66 % | 1.03 | 5.44 % | 36 | 1.57 | 0 | 73 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +3.77 % | 0.82 | 8.33 % | 32 | 1.42 | 0 | 105 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +28.89 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | +6.55 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | 0.83 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | 1.42 | 1.11 | 1.59 | 1.02 |
| Calmar | 0.63 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +10.41 % / 777 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 1.54 | — | — | — |
| Win rate | +34.11 % | — | — | — |
| Expectancy por trade | 13.00 | — | — | — |
| Trades / duración media | 214 / 99.8 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +27.93 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 381.91 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 12,889.06 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +72.06 %, Sharpe 1.10, max DD +10.37 %, 330 trades.

## Gate 1 — backtest -> paper: aprobado (falta el holdout)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | 0.83 | OK |  |
| Profit factor OOS | >= 1.3 | 1.54 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 10.41 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 330 | OK |  |
| Trades curva OOS | >= 40 | 214 | OK |  |
| Régimen: retorno 2020 | > 0 | +15.21 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +16.38 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +17.39 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +7.68 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 8.31 % (2025) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 12.76 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.23 % | 3.97 % | 9 | -22.34 |
| 2020 | +15.21 % | 5.21 % | 59 | 1,362.27 |
| 2021 | +16.38 % | 5.18 % | 81 | 2,050.22 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +17.39 % | 5.84 % | 70 | 2,331.39 |
| 2024 | +7.68 % | 7.67 % | 71 | 1,217.64 |
| 2025 (parcial) | +1.74 % | 8.31 % | 40 | 304.16 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 214 trades, semilla 42: max DD p50 +6.51 %, p95 +12.76 %, p99 +16.52 %; retorno p05 +2.59 %, p50 +26.97 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +10.98 %, p95 +19.26 %, p99 +23.64 %; retorno p05 -5.80 %, p50 +26.32 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.10). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, entry_period=48, exit_period=24 | +44.13 % | 1.35 | 0.70 | 439 | sí |
| atr_mult=2.4, entry_period=48, exit_period=16 | +44.34 % | 1.35 | 0.71 | 439 | sí |
| atr_mult=2.4 | +49.31 % | 1.41 | 0.78 | 420 | sí |
| atr_mult=2.4, entry_period=72, exit_period=24 | +49.99 % | 1.42 | 0.80 | 401 | sí |
| atr_mult=2.4, entry_period=72, exit_period=16 | +50.21 % | 1.42 | 0.80 | 401 | sí |
| entry_period=72 | +66.86 % | 1.71 | 1.07 | 316 | sí |
| exit_period=16 | +69.05 % | 1.70 | 1.08 | 333 | sí |
| entry_period=48 | +71.20 % | 1.70 | 1.09 | 344 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: referencia (reproducción; no autoriza paper)
- **Por qué**: Curvas equity.csv y trades.csv idénticas a sus controles anteriores. Mantiene las restricciones del protocolo original; B solo histórico.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
