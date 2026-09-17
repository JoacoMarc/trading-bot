# WF-0050 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos 40a0aa8573b9, 29.8 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.49 % | 0.19 | 4.91 % | 35 | 1.07 | 0 | 62 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.74 % | 0.40 | 1.66 % | 7 | 1.45 | 0 | 15 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.17 % | 0.01 | 3.43 % | 37 | 0.98 | 0 | 46 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +17.30 % | 2.86 | 4.86 % | 30 | 3.50 | 1 (-36.37) | 71 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +3.45 % | 0.86 | 5.05 % | 37 | 1.42 | 1 (-29.44) | 60 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +5.41 % | 1.19 | 5.17 % | 36 | 1.69 | 0 | 73 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +5.42 % | 1.17 | 7.27 % | 31 | 1.68 | 0 | 106 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +36.29 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | +8.05 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | 1.01 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | 1.77 | 1.12 | 1.74 | 1.03 |
| Calmar | 0.90 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +8.92 % / 776 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 1.70 | — | — | — |
| Win rate | +35.21 % | — | — | — |
| Expectancy por trade | 15.79 | — | — | — |
| Trades / duración media | 213 / 100.6 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +28.06 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 381.93 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 13,628.55 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +87.51 %, Sharpe 1.27, max DD +8.87 %, 328 trades.

## Gate 1 — backtest -> paper: aprobado (falta el holdout)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 1.01 | OK |  |
| Profit factor OOS | >= 1.3 | 1.70 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 8.92 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 100 | 328 | OK |  |
| Trades curva OOS | >= 40 | 213 | OK |  |
| Régimen: retorno 2020 | > 0 | +16.77 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +18.79 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +19.38 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +9.44 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 7.26 % (2025) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 10.67 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.03 % | 3.89 % | 9 | -3.19 |
| 2020 | +16.77 % | 5.05 % | 59 | 1,515.64 |
| 2021 | +18.79 % | 4.89 % | 80 | 2,366.06 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +19.38 % | 5.00 % | 70 | 2,691.66 |
| 2024 | +9.44 % | 6.84 % | 71 | 1,574.03 |
| 2025 (parcial) | +3.50 % | 7.26 % | 39 | 643.98 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 213 trades, semilla 42: max DD p50 +5.53 %, p95 +10.67 %, p99 +14.14 %; retorno p05 +8.23 %, p50 +33.22 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +9.68 %, p95 +16.83 %, p99 +20.71 %; retorno p05 -0.43 %, p50 +33.48 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.27). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, entry_period=48, exit_period=24 | +61.91 % | 1.50 | 0.92 | 438 | sí |
| atr_mult=2.4, entry_period=48, exit_period=16 | +62.15 % | 1.50 | 0.92 | 438 | sí |
| atr_mult=2.4, entry_period=72, exit_period=24 | +66.45 % | 1.57 | 1.00 | 400 | sí |
| atr_mult=2.4, entry_period=72, exit_period=16 | +66.69 % | 1.57 | 1.00 | 400 | sí |
| atr_mult=2.4 | +66.75 % | 1.56 | 0.99 | 419 | sí |
| entry_period=72 | +81.16 % | 1.89 | 1.24 | 314 | sí |
| exit_period=16 | +84.42 % | 1.89 | 1.26 | 331 | sí |
| entry_period=48 | +87.27 % | 1.88 | 1.27 | 342 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: referencia (reproducción; no autoriza paper)
- **Por qué**: Curvas equity.csv y trades.csv idénticas a sus controles anteriores. Mantiene las restricciones del protocolo original; B solo histórico.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
