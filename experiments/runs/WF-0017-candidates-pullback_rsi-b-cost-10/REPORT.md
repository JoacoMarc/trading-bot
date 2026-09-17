# WF-0017 — pullback_rsi 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 30.6 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -2.36 % | -0.99 | 4.95 % | 101 | 0.73 | 0 | 47 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +1.51 % | 1.43 | 0.76 % | 23 | 2.93 | 0 | 18 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -6.29 % | -2.72 | 7.68 % | 127 | 0.46 | 0 | 55 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -5.16 % | -2.10 | 6.28 % | 102 | 0.52 | 0 | 47 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -8.16 % | -2.84 | 9.34 % | 133 | 0.45 | 1 (-31.33) | 33 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -8.85 % | -2.98 | 9.51 % | 122 | 0.38 | 1 (-16.79) | 44 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -4.25 % | -1.98 | 5.07 % | 86 | 0.54 | 0 | 46 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -29.39 % | +174.73 % | +203.24 % | +173.86 % |
| CAGR | -8.33 % | +28.74 % | +31.96 % | +28.64 % |
| Sharpe (diario) | -1.90 | 0.76 | 1.04 | 0.72 |
| Sortino (diario) | -2.11 | 1.11 | 1.69 | 1.03 |
| Calmar | -0.27 | 0.37 | 1.16 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +30.68 % / 1413 d | +77.14 % / 852 d | +27.48 % / 438 d | +81.55 % / 1108 d |
| Profit factor | 0.52 | — | — | — |
| Win rate | +55.33 % | — | — | — |
| Expectancy por trade | -4.63 | — | — | — |
| Trades / duración media | 694 / 14.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.64 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,306.22 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 7,060.69 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -34.93 %, Sharpe -1.61, max DD +36.32 %, 1045 trades.

## Gate 1 — backtest -> paper: no aprobado (10 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -1.90 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.52 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.14 %) | 30.68 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 1045 | OK |  |
| Trades curva OOS | >= 40 | 694 | OK |  |
| Régimen: retorno 2020 | > 0 | -6.63 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | -5.45 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -7.31 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -17.41 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 18.27 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 42.00 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.24 % | 0.62 % | 24 | 24.41 |
| 2020 | -6.63 % | 7.93 % | 240 | -658.72 |
| 2021 | -5.45 % | 9.28 % | 229 | -480.86 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -7.31 % | 10.27 % | 233 | -628.84 |
| 2024 | -17.41 % | 18.27 % | 240 | -1,392.97 |
| 2025 (parcial) | -3.94 % | 4.88 % | 79 | -250.49 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 694 trades, semilla 42: max DD p50 +32.74 %, p95 +42.00 %, p99 +45.90 %; retorno p05 -41.49 %, p50 -32.20 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +30.33 %, p95 +39.70 %, p99 +43.07 %; retorno p05 -39.11 %, p50 -29.56 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| rsi_entry=12, rsi_exit=56, stop_atr_mult=2.0 | -50.55 % | 0.48 | -2.58 | 1228 | no |
| stop_atr_mult=2.0 | -44.85 % | 0.59 | -1.86 | 1134 | no |
| rsi_entry=8, rsi_exit=56, stop_atr_mult=2.0 | -42.38 % | 0.49 | -2.18 | 966 | no |
| rsi_entry=12 | -40.22 % | 0.58 | -1.83 | 1171 | no |
| rsi_entry=12, rsi_exit=84, stop_atr_mult=2.0 | -38.29 % | 0.74 | -1.21 | 1105 | no |
| rsi_exit=56 | -37.23 % | 0.49 | -2.13 | 1065 | no |
| rsi_entry=12, rsi_exit=56, stop_atr_mult=3.0 | -35.76 % | 0.49 | -2.21 | 1201 | no |
| rsi_entry=8, rsi_exit=84, stop_atr_mult=2.0 | -35.29 % | 0.72 | -1.25 | 851 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados. En esta corrida fallan: Sharpe OOS = -1.90; Profit factor OOS = 0.52; Max DD OOS = 30.68 %; Ventanas OOS positivas = 1/8 (12 %); Régimen: retorno 2020 = -6.63 %; Régimen: retorno 2021 = -5.45 %; Régimen: retorno 2023 = -7.31 %; Régimen: retorno 2024 = -17.41 %; Meseta ±20 % = 0.00 %; Monte Carlo DD p95 = 42.00 %.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
