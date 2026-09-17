# WF-0018 — pullback_rsi 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 28.9 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -4.20 % | -1.74 | 5.91 % | 102 | 0.57 | 0 | 47 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +1.15 % | 1.13 | 0.78 % | 23 | 2.30 | 0 | 18 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -8.67 % | -3.72 | 9.33 % | 127 | 0.33 | 0 | 55 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -6.93 % | -2.84 | 7.60 % | 102 | 0.40 | 0 | 47 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -11.20 % | -3.89 | 11.86 % | 134 | 0.32 | 1 (-31.27) | 33 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -10.63 % | -3.65 | 11.14 % | 122 | 0.29 | 1 (-17.25) | 44 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -5.94 % | -2.73 | 6.36 % | 86 | 0.41 | 0 | 46 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -38.52 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | -11.45 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | -2.62 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | -2.82 | 1.11 | 1.59 | 1.02 |
| Calmar | -0.29 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +39.18 % / 1439 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 0.39 | — | — | — |
| Win rate | +48.42 % | — | — | — |
| Expectancy por trade | -6.46 | — | — | — |
| Trades / duración media | 696 / 14.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.57 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,295.79 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 6,148.43 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -46.77 %, Sharpe -2.33, max DD +47.30 %, 1069 trades.

## Gate 1 — backtest -> paper: no aprobado (10 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | -2.62 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.39 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 39.18 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 1069 | OK |  |
| Trades curva OOS | >= 40 | 696 | OK |  |
| Régimen: retorno 2020 | > 0 | -9.84 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | -8.60 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -9.92 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -22.71 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 23.43 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 54.82 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.17 % | 0.67 % | 24 | -16.21 |
| 2020 | -9.84 % | 10.76 % | 240 | -976.16 |
| 2021 | -8.60 % | 11.46 % | 230 | -743.44 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -9.92 % | 12.07 % | 212 | -800.39 |
| 2024 | -22.71 % | 23.43 % | 254 | -1,644.02 |
| 2025 (parcial) | -7.07 % | 7.54 % | 109 | -384.79 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 696 trades, semilla 42: max DD p50 +45.38 %, p95 +54.82 %, p99 +58.98 %; retorno p05 -54.57 %, p50 -45.05 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +38.98 %, p95 +48.02 %, p99 +51.43 %; retorno p05 -47.80 %, p50 -38.61 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| rsi_entry=12, rsi_exit=56, stop_atr_mult=2.0 | -63.04 % | 0.36 | -3.41 | 1273 | no |
| stop_atr_mult=2.0 | -55.37 % | 0.46 | -2.56 | 1067 | no |
| rsi_entry=12, rsi_exit=84, stop_atr_mult=2.0 | -54.99 % | 0.61 | -1.99 | 1111 | no |
| rsi_entry=8, rsi_exit=56, stop_atr_mult=2.0 | -52.72 % | 0.36 | -2.90 | 939 | no |
| rsi_entry=12 | -49.53 % | 0.44 | -2.61 | 1103 | no |
| rsi_entry=8, rsi_exit=84, stop_atr_mult=2.0 | -49.17 % | 0.61 | -1.89 | 894 | no |
| rsi_exit=56 | -48.79 % | 0.37 | -2.93 | 1117 | no |
| rsi_entry=12, rsi_exit=56, stop_atr_mult=3.0 | -45.78 % | 0.37 | -3.02 | 1247 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados. En esta corrida fallan: Sharpe OOS = -2.62; Profit factor OOS = 0.39; Max DD OOS = 39.18 %; Ventanas OOS positivas = 1/8 (12 %); Régimen: retorno 2020 = -9.84 %; Régimen: retorno 2021 = -8.60 %; Régimen: retorno 2023 = -9.92 %; Régimen: retorno 2024 = -22.71 %; Meseta ±20 % = 0.00 %; Monte Carlo DD p95 = 54.82 %.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
