# WF-0035 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash a6067cb13733; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos a6067cb13733, 69.5 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | +0.11 % | 0.34 | 0.39 % | 2 | 1.61 | 0 | 1 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.19 % | 0.48 | 0.29 % | 1 | - | 0 | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +0.29 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | +0.07 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | 0.21 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | 0.38 | 1.12 | 1.74 | 1.03 |
| Calmar | 0.16 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +0.46 % / 487 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 2.65 | — | — | — |
| Win rate | +66.67 % | — | — | — |
| Expectancy por trade | 9.92 | — | — | — |
| Trades / duración media | 3 / 118.7 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +0.95 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 3.69 / 5.9 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,029.45 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -0.04 %, Sharpe -0.01, max DD +1.47 %, 13 trades.

## Gate 1 — backtest -> paper: incompleto (16 criterios sin evaluar)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.21 | n/a | ; evidencia ML con cobertura incompleta |
| Profit factor OOS | >= 1.3 | 2.65 | n/a | ; evidencia ML con cobertura incompleta |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 0.46 % | n/a | ; evidencia ML con cobertura incompleta |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | n/a | ; evidencia ML con cobertura incompleta |
| Ventanas OOS positivas | >= 60 % | 2/8 (25 %) | n/a | secundario; evidencia ML con cobertura incompleta |
| Trades muestra completa | >= 100 | 13 | n/a | ; evidencia ML con cobertura incompleta |
| Trades curva OOS | >= 40 | 3 | n/a | ; evidencia ML con cobertura incompleta |
| Régimen: retorno 2020 | > 0 | +0.00 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2021 | > 0 | -0.33 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2023 | > 0 | +0.11 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2024 | > 0 | +0.19 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: max DD intra-año | <= 25 % | 1.47 % (2021) | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 41.67 % | n/a | ; evidencia ML con cobertura incompleta |
| Monte Carlo DD p95 | <= 35 % | 0.36 % | n/a | ; evidencia ML con cobertura incompleta |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |
| Cobertura temporal ML | modelo válido en todo el rango | 2019, 2020, 2021 | n/a | Features inválidas bloquean compras y se reportan aparte. |

## Regímenes por año (muestra completa, parámetros fijos; receta fija ML con reentrenamiento mensual)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.00 % | 0.00 % | 0 | 0.00 |
| 2020 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2021 | -0.33 % | 1.47 % | 10 | -32.41 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +0.11 % | 0.39 % | 2 | 10.93 |
| 2024 | +0.19 % | 0.29 % | 1 | 18.76 |
| 2025 (parcial) | +0.00 % | 0.00 % | 0 | 0.00 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 3 trades, semilla 42: max DD p50 +0.18 %, p95 +0.36 %, p99 +0.54 %; retorno p05 -0.17 %, p50 +0.30 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +0.35 %, p95 +0.55 %, p99 +0.67 %; retorno p05 -0.14 %, p50 +0.27 %.

## Meseta ±20 %

24 variantes, pasan +41.67 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, prediction_threshold=0.55 | -0.22 % | 0.85 | -0.06 | 14 | no |
| entry_period=48, prediction_threshold=0.55 | -0.13 % | 0.93 | -0.03 | 14 | no |
| exit_period=16, prediction_threshold=0.55 | -0.04 % | 0.98 | -0.01 | 13 | no |
| exit_period=24, prediction_threshold=0.55 | -0.04 % | 0.98 | -0.01 | 13 | no |
| prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=2.4, entry_period=48, exit_period=16, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=3.6, entry_period=48, exit_period=16, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=2.4, entry_period=48, exit_period=24, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (ML v1 no promovible; Gate 1 incompleto)
- **Por qué**: Cobertura histórica incompleta y solo 3–5 cierres en cuatro años OOS. La comparación incremental falla. No abrir holdout ni reducir umbral para rescatar resultados.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
