# WF-0047 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos 40a0aa8573b9, 27.1 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.67 % | 0.54 | 1.87 % | 26 | 1.24 | 0 | 90 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.39 % | 0.73 | 0.48 % | 4 | 1.84 | 0 | 20 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.09 % | -0.04 | 1.56 % | 29 | 0.97 | 0 | 67 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +4.94 % | 2.42 | 1.75 % | 23 | 3.22 | 1 (-16.16) | 99 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.37 % | 0.25 | 2.56 % | 29 | 1.16 | 1 (-14.26) | 96 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.35 % | 0.28 | 2.02 % | 27 | 1.15 | 0 | 106 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +0.09 % | 0.07 | 3.25 % | 25 | 1.04 | 0 | 136 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +6.81 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | +1.66 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | 0.61 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | 1.01 | 1.12 | 1.74 | 1.03 |
| Calmar | 0.32 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +5.11 % / 777 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 1.40 | — | — | — |
| Win rate | +34.36 % | — | — | — |
| Expectancy por trade | 4.45 | — | — | — |
| Trades / duración media | 163 / 97.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +26.76 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 142.94 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,680.63 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +21.74 %, Sharpe 1.06, max DD +5.18 %, 249 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.61 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.40 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 5.11 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 100 | 249 | OK |  |
| Trades curva OOS | >= 40 | 163 | OK |  |
| Régimen: retorno 2020 | > 0 | +7.09 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +7.56 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +5.73 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +0.82 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 3.87 % (2025) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 6.07 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.23 % | 1.56 % | 8 | -22.55 |
| 2020 | +7.09 % | 1.96 % | 41 | 648.66 |
| 2021 | +7.56 % | 1.87 % | 61 | 875.05 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +5.73 % | 2.00 % | 53 | 662.13 |
| 2024 | +0.82 % | 3.32 % | 55 | 108.18 |
| 2025 (parcial) | -0.62 % | 3.87 % | 31 | -69.05 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 163 trades, semilla 42: max DD p50 +3.14 %, p95 +6.07 %, p99 +7.70 %; retorno p05 -1.71 %, p50 +6.89 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +4.22 %, p95 +7.77 %, p99 +9.65 %; retorno p05 -3.46 %, p50 +6.10 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.06). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, entry_period=72, exit_period=24 | +14.28 % | 1.40 | 0.67 | 314 | sí |
| atr_mult=2.4, entry_period=72, exit_period=16 | +14.35 % | 1.40 | 0.67 | 314 | sí |
| atr_mult=2.4 | +14.94 % | 1.40 | 0.69 | 324 | sí |
| atr_mult=2.4, entry_period=48, exit_period=24 | +15.44 % | 1.40 | 0.70 | 336 | sí |
| atr_mult=2.4, entry_period=48, exit_period=16 | +15.51 % | 1.40 | 0.70 | 336 | sí |
| entry_period=48 | +21.72 % | 1.74 | 1.06 | 257 | sí |
| exit_period=16 | +21.81 % | 1.74 | 1.06 | 251 | sí |
| exit_period=24 | +22.93 % | 1.79 | 1.11 | 247 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: referencia (reproducción; no autoriza paper)
- **Por qué**: Curvas equity.csv y trades.csv idénticas a sus controles anteriores. Mantiene las restricciones del protocolo original; B solo histórico.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
