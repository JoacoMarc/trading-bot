# WF-0011 — pullback_rsi 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 28.1 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -1.68 % | -0.69 | 4.71 % | 101 | 0.81 | 0 | 47 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +1.69 % | 1.57 | 0.75 % | 23 | 3.30 | 0 | 18 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -5.05 % | -2.22 | 6.87 % | 127 | 0.55 | 0 | 55 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -4.25 % | -1.71 | 5.61 % | 102 | 0.59 | 0 | 47 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -7.01 % | -2.43 | 8.39 % | 133 | 0.52 | 1 (-31.14) | 33 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -7.95 % | -2.63 | 8.70 % | 122 | 0.43 | 1 (-16.56) | 44 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -3.40 % | -1.57 | 4.43 % | 86 | 0.62 | 0 | 46 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -24.83 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | -6.89 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | -1.56 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | -1.76 | 1.12 | 1.74 | 1.03 |
| Calmar | -0.26 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +26.51 % / 1413 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 0.60 | — | — | — |
| Win rate | +58.79 % | — | — | — |
| Expectancy por trade | -3.78 | — | — | — |
| Trades / duración media | 694 / 14.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.64 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,312.67 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 7,516.88 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -30.54 %, Sharpe -1.35, max DD +32.43 %, 1075 trades.

## Gate 1 — backtest -> paper: no aprobado (10 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -1.56 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.60 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 26.51 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 1075 | OK |  |
| Trades curva OOS | >= 40 | 694 | OK |  |
| Régimen: retorno 2020 | > 0 | -5.02 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | -4.25 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -5.14 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -16.47 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 17.39 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 36.33 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.49 % | 0.61 % | 24 | 48.95 |
| 2020 | -5.02 % | 6.51 % | 240 | -498.70 |
| 2021 | -4.25 % | 8.57 % | 229 | -376.59 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -5.14 % | 8.57 % | 233 | -452.22 |
| 2024 | -16.47 % | 17.39 % | 240 | -1,392.57 |
| 2025 (parcial) | -4.07 % | 5.23 % | 109 | -272.27 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 694 trades, semilla 42: max DD p50 +27.05 %, p95 +36.33 %, p99 +40.27 %; retorno p05 -35.65 %, p50 -26.26 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +26.15 %, p95 +35.60 %, p99 +39.09 %; retorno p05 -34.88 %, p50 -25.04 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| rsi_entry=12, rsi_exit=56, stop_atr_mult=2.0 | -42.46 % | 0.58 | -1.99 | 1296 | no |
| stop_atr_mult=2.0 | -37.74 % | 0.65 | -1.52 | 1072 | no |
| rsi_entry=8, rsi_exit=56, stop_atr_mult=2.0 | -36.07 % | 0.56 | -1.80 | 949 | no |
| rsi_entry=12, rsi_exit=84, stop_atr_mult=2.0 | -33.26 % | 0.79 | -1.00 | 1119 | no |
| rsi_entry=12 | -32.86 % | 0.66 | -1.42 | 1197 | no |
| rsi_entry=8, rsi_exit=84, stop_atr_mult=2.0 | -31.31 % | 0.77 | -1.05 | 896 | no |
| rsi_exit=56 | -30.83 % | 0.59 | -1.64 | 1113 | no |
| rsi_entry=12, rsi_exit=56, stop_atr_mult=3.0 | -29.31 % | 0.59 | -1.73 | 1240 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados. En esta corrida fallan: Sharpe OOS = -1.56; Profit factor OOS = 0.60; Max DD OOS = 26.51 %; Ventanas OOS positivas = 1/8 (12 %); Régimen: retorno 2020 = -5.02 %; Régimen: retorno 2021 = -4.25 %; Régimen: retorno 2023 = -5.14 %; Régimen: retorno 2024 = -16.47 %; Meseta ±20 % = 0.00 %; Monte Carlo DD p95 = 36.33 %.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
