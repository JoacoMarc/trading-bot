# WF-0043 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash e61213fad5d5; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos e61213fad5d5, 56.9 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -0.04 % | -0.13 | 0.39 % | 3 | 0.81 | 0 | 6 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -0.04 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | -0.01 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | -0.05 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | -0.07 | 1.11 | 1.59 | 1.02 |
| Calmar | -0.03 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +0.39 % / 1361 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 0.81 | — | — | — |
| Win rate | +33.33 % | — | — | — |
| Expectancy por trade | -1.38 | — | — | — |
| Trades / duración media | 3 / 104.0 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +0.54 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 2.39 / 20.1 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 9,995.51 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +0.28 %, Sharpe 0.06, max DD +1.04 %, 16 trades.

## Gate 1 — backtest -> paper: incompleto (16 criterios sin evaluar)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | -0.05 | n/a | ; evidencia ML con cobertura incompleta |
| Profit factor OOS | >= 1.3 | 0.81 | n/a | ; evidencia ML con cobertura incompleta |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 0.39 % | n/a | ; evidencia ML con cobertura incompleta |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | n/a | ; evidencia ML con cobertura incompleta |
| Ventanas OOS positivas | >= 60 % | 0/8 (0 %) | n/a | secundario; evidencia ML con cobertura incompleta |
| Trades muestra completa | >= 100 | 16 | n/a | ; evidencia ML con cobertura incompleta |
| Trades curva OOS | >= 40 | 3 | n/a | ; evidencia ML con cobertura incompleta |
| Régimen: retorno 2020 | > 0 | +0.00 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2021 | > 0 | +0.28 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2023 | > 0 | +0.00 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2024 | > 0 | +0.00 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Régimen: max DD intra-año | <= 25 % | 1.04 % (2021) | n/a | muestra completa, parámetros fijos; evidencia ML con cobertura incompleta |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 58.33 % | n/a | ; evidencia ML con cobertura incompleta |
| Monte Carlo DD p95 | <= 35 % | 0.42 % | n/a | ; evidencia ML con cobertura incompleta |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |
| Cobertura temporal ML | modelo válido en todo el rango | 2019, 2020, 2021 | n/a | Features inválidas bloquean compras y se reportan aparte. |

## Regímenes por año (muestra completa, parámetros fijos; receta fija ML con reentrenamiento mensual)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.00 % | 0.00 % | 0 | 0.00 |
| 2020 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2021 | +0.28 % | 1.04 % | 16 | 29.63 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2024 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2025 (parcial) | +0.00 % | 0.00 % | 0 | 0.00 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 3 trades, semilla 42: max DD p50 +0.22 %, p95 +0.42 %, p99 +0.60 %; retorno p05 -0.42 %, p50 -0.04 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +0.33 %, p95 +0.61 %, p99 +0.76 %; retorno p05 -0.38 %, p50 -0.04 %.

## Meseta ±20 %

24 variantes, pasan +58.33 % (PF > 1.1 y retorno > 0). Informativo: +58.33 % de las variantes tiene Sharpe >= 0.5 x el base (0.06). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, prediction_threshold=0.55 | -0.68 % | 0.71 | -0.16 | 20 | no |
| prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=2.4, entry_period=48, exit_period=16, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=3.6, entry_period=48, exit_period=16, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=2.4, entry_period=48, exit_period=24, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=3.6, entry_period=48, exit_period=24, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=2.4, entry_period=72, exit_period=16, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |
| atr_mult=3.6, entry_period=72, exit_period=16, prediction_threshold=0.66 | +0.00 % | - | - | 0 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (ML v1 no promovible; Gate 1 incompleto)
- **Por qué**: Cobertura histórica incompleta y solo 3–5 cierres en cuatro años OOS. La comparación incremental falla. No abrir holdout ni reducir umbral para rescatar resultados.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
