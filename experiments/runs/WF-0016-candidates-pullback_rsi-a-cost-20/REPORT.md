# WF-0016 — pullback_rsi 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 27.4 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -0.84 % | -0.97 | 1.34 % | 76 | 0.74 | 0 | 77 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.14 % | 0.36 | 0.39 % | 16 | 1.33 | 0 | 25 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -2.82 % | -3.00 | 3.02 % | 97 | 0.41 | 0 | 91 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -2.58 % | -2.91 | 2.81 % | 78 | 0.41 | 0 | 75 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -4.25 % | -4.04 | 4.52 % | 107 | 0.32 | 1 (-16.82) | 67 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -4.67 % | -3.71 | 4.90 % | 91 | 0.28 | 1 (-9.19) | 76 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -2.27 % | -2.40 | 2.45 % | 67 | 0.42 | 0 | 69 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -16.14 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | -4.31 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | -2.49 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | -2.69 | 1.11 | 1.59 | 1.02 |
| Calmar | -0.26 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +16.56 % / 1431 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 0.41 | — | — | — |
| Win rate | +48.87 % | — | — | — |
| Expectancy por trade | -3.08 | — | — | — |
| Trades / duración media | 532 / 14.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +14.69 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 509.29 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 8,386.05 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -21.07 %, Sharpe -2.27, max DD +21.40 %, 832 trades.

## Gate 1 — backtest -> paper: no aprobado (8 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | -2.49 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.41 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 16.56 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 832 | OK |  |
| Trades curva OOS | >= 40 | 532 | OK |  |
| Régimen: retorno 2020 | > 0 | -4.11 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | -2.53 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -4.20 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -9.09 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 9.47 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 20.72 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.05 % | 0.34 % | 20 | -4.60 |
| 2020 | -4.11 % | 4.44 % | 183 | -405.77 |
| 2021 | -2.53 % | 3.50 % | 174 | -223.40 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -4.20 % | 4.72 % | 176 | -379.31 |
| 2024 | -9.09 % | 9.47 % | 198 | -787.22 |
| 2025 (parcial) | -2.97 % | 3.13 % | 81 | -226.81 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 532 trades, semilla 42: max DD p50 +16.51 %, p95 +20.72 %, p99 +22.29 %; retorno p05 -20.57 %, p50 -16.30 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +16.36 %, p95 +21.33 %, p99 +23.26 %; retorno p05 -21.13 %, p50 -16.14 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| rsi_entry=12, rsi_exit=56, stop_atr_mult=2.0 | -32.93 % | 0.36 | -3.43 | 997 | no |
| stop_atr_mult=2.0 | -27.62 % | 0.47 | -2.55 | 881 | no |
| rsi_entry=8, rsi_exit=56, stop_atr_mult=2.0 | -27.52 % | 0.36 | -3.00 | 784 | no |
| rsi_entry=12, rsi_exit=84, stop_atr_mult=2.0 | -25.51 % | 0.62 | -1.92 | 874 | no |
| rsi_exit=56 | -22.94 % | 0.36 | -2.90 | 844 | no |
| rsi_entry=12 | -22.73 % | 0.47 | -2.49 | 890 | no |
| rsi_entry=8, rsi_exit=84, stop_atr_mult=2.0 | -22.69 % | 0.60 | -1.85 | 688 | no |
| rsi_entry=12, rsi_exit=56, stop_atr_mult=3.0 | -21.73 % | 0.36 | -3.06 | 952 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados. En esta corrida fallan: Sharpe OOS = -2.49; Profit factor OOS = 0.41; Ventanas OOS positivas = 1/8 (12 %); Régimen: retorno 2020 = -4.11 %; Régimen: retorno 2021 = -2.53 %; Régimen: retorno 2023 = -4.20 %; Régimen: retorno 2024 = -9.09 %; Meseta ±20 % = 0.00 %.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
