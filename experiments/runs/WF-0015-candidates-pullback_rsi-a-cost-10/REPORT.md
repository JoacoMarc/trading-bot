# WF-0015 — pullback_rsi 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
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
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -0.20 % | -0.23 | 1.03 % | 75 | 0.96 | 0 | 77 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.26 % | 0.67 | 0.38 % | 16 | 1.68 | 0 | 25 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -1.89 % | -2.06 | 2.34 % | 97 | 0.57 | 0 | 91 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -1.86 % | -2.10 | 2.35 % | 78 | 0.55 | 0 | 75 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -3.09 % | -3.05 | 3.53 % | 106 | 0.46 | 1 (-16.50) | 69 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -3.98 % | -3.12 | 4.27 % | 91 | 0.36 | 1 (-8.84) | 76 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -1.32 % | -1.48 | 1.67 % | 66 | 0.61 | 0 | 70 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -11.55 % | +174.73 % | +203.24 % | +173.86 % |
| CAGR | -3.02 % | +28.74 % | +31.96 % | +28.64 % |
| Sharpe (diario) | -1.78 | 0.76 | 1.04 | 0.72 |
| Sortino (diario) | -1.99 | 1.11 | 1.69 | 1.03 |
| Calmar | -0.25 | 0.37 | 1.16 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +12.25 % / 1421 d | +77.14 % / 852 d | +27.48 % / 438 d | +81.55 % / 1108 d |
| Profit factor | 0.55 | — | — | — |
| Win rate | +56.90 % | — | — | — |
| Expectancy por trade | -2.12 | — | — | — |
| Trades / duración media | 529 / 14.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +14.72 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 509.38 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 8,844.59 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -15.00 %, Sharpe -1.58, max DD +15.70 %, 831 trades.

## Gate 1 — backtest -> paper: no aprobado (8 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -1.78 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.55 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.14 %) | 12.25 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 1/8 (12 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 831 | OK |  |
| Trades curva OOS | >= 40 | 529 | OK |  |
| Régimen: retorno 2020 | > 0 | -2.85 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | -1.31 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -2.55 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -7.33 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 7.75 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 15.48 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.12 % | 0.33 % | 20 | 11.80 |
| 2020 | -2.85 % | 3.31 % | 183 | -280.03 |
| 2021 | -1.31 % | 2.63 % | 173 | -109.10 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -2.55 % | 3.36 % | 176 | -232.83 |
| 2024 | -7.33 % | 7.75 % | 197 | -657.08 |
| 2025 (parcial) | -1.94 % | 2.28 % | 82 | -153.10 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 529 trades, semilla 42: max DD p50 +11.46 %, p95 +15.48 %, p99 +17.35 %; retorno p05 -15.24 %, p50 -11.13 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +12.01 %, p95 +16.66 %, p99 +18.42 %; retorno p05 -16.34 %, p50 -11.63 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| rsi_entry=12, rsi_exit=56, stop_atr_mult=2.0 | -25.86 % | 0.48 | -2.63 | 1019 | no |
| rsi_entry=8, rsi_exit=56, stop_atr_mult=2.0 | -20.39 % | 0.48 | -2.23 | 756 | no |
| stop_atr_mult=2.0 | -19.86 % | 0.60 | -1.81 | 850 | no |
| rsi_entry=12, rsi_exit=84, stop_atr_mult=2.0 | -17.78 % | 0.73 | -1.29 | 865 | no |
| rsi_entry=8, rsi_exit=84, stop_atr_mult=2.0 | -17.45 % | 0.70 | -1.38 | 696 | no |
| rsi_exit=56 | -17.44 % | 0.50 | -2.13 | 870 | no |
| rsi_entry=12 | -16.83 % | 0.60 | -1.76 | 920 | no |
| rsi_entry=12, rsi_exit=56, stop_atr_mult=3.0 | -16.28 % | 0.49 | -2.24 | 954 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados. En esta corrida fallan: Sharpe OOS = -1.78; Profit factor OOS = 0.55; Ventanas OOS positivas = 1/8 (12 %); Régimen: retorno 2020 = -2.85 %; Régimen: retorno 2021 = -1.31 %; Régimen: retorno 2023 = -2.55 %; Régimen: retorno 2024 = -7.33 %; Meseta ±20 % = 0.00 %.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
