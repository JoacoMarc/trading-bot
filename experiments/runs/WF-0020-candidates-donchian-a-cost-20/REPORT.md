# WF-0020 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params c8d4a6af5b, datos 40a0aa8573b9, 31.3 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.47 % | 0.37 | 1.95 % | 26 | 1.16 | 0 | 90 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.34 % | 0.63 | 0.51 % | 4 | 1.68 | 0 | 20 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.43 % | -0.24 | 1.86 % | 29 | 0.86 | 0 | 67 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +4.63 % | 2.26 | 1.85 % | 23 | 2.95 | 1 (-17.20) | 99 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.03 % | 0.03 | 2.78 % | 29 | 1.06 | 1 (-14.69) | 96 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.06 % | 0.06 | 2.14 % | 27 | 1.04 | 0 | 106 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -0.31 % | -0.17 | 3.54 % | 25 | 0.93 | 0 | 136 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +4.78 % | +172.55 % | +181.86 % | +171.69 % |
| CAGR | +1.17 % | +28.49 % | +29.57 % | +28.39 % |
| Sharpe (diario) | 0.43 | 0.75 | 0.98 | 0.72 |
| Sortino (diario) | 0.70 | 1.11 | 1.59 | 1.02 |
| Calmar | 0.20 | 0.37 | 1.04 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +5.89 % / 784 d | +77.18 % / 852 d | +28.57 % / 438 d | +81.59 % / 1109 d |
| Profit factor | 1.28 | — | — | — |
| Win rate | +33.74 % | — | — | — |
| Expectancy por trade | 3.27 | — | — | — |
| Trades / duración media | 163 / 97.3 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +26.74 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 142.75 / 20.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,477.53 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +17.82 %, Sharpe 0.88, max DD +5.97 %, 250 trades.

## Gate 1 — backtest -> paper: no aprobado (2 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.75) | 0.43 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.28 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.18 %) | 5.89 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 250 | OK |  |
| Trades curva OOS | >= 40 | 163 | OK |  |
| Régimen: retorno 2020 | > 0 | +6.58 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +6.49 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +5.06 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +0.17 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 4.21 % (2025) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 7.11 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.30 % | 1.59 % | 8 | -30.19 |
| 2020 | +6.58 % | 2.03 % | 41 | 599.16 |
| 2021 | +6.49 % | 1.95 % | 62 | 756.28 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +5.06 % | 2.33 % | 53 | 576.57 |
| 2024 | +0.17 % | 3.67 % | 55 | 29.48 |
| 2025 (parcial) | -1.07 % | 4.21 % | 31 | -119.55 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 163 trades, semilla 42: max DD p50 +3.64 %, p95 +7.11 %, p99 +9.13 %; retorno p05 -3.65 %, p50 +4.97 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +4.79 %, p95 +8.88 %, p99 +10.91 %; retorno p05 -5.24 %, p50 +4.15 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (0.88). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, entry_period=72, exit_period=24 | +9.55 % | 1.25 | 0.46 | 315 | sí |
| atr_mult=2.4, entry_period=72, exit_period=16 | +9.61 % | 1.26 | 0.46 | 315 | sí |
| atr_mult=2.4 | +9.94 % | 1.25 | 0.47 | 325 | sí |
| atr_mult=2.4, entry_period=48, exit_period=24 | +10.24 % | 1.25 | 0.48 | 337 | sí |
| atr_mult=2.4, entry_period=48, exit_period=16 | +10.30 % | 1.25 | 0.48 | 337 | sí |
| entry_period=48 | +17.69 % | 1.57 | 0.88 | 258 | sí |
| exit_period=16 | +17.86 % | 1.58 | 0.88 | 252 | sí |
| exit_period=24 | +19.01 % | 1.62 | 0.93 | 248 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: El perfil moderado no alcanza el Sharpe OOS mínimo del protocolo (WF-0012 y costos adversos). El beneficio continuo no basta para aprobar. Sin paper ni holdout. En esta corrida fallan: Sharpe OOS = 0.43; Profit factor OOS = 1.28.
- **Qué se aprendió**: La meseta positiva y la caída acotada no compensan el incumplimiento del criterio OOS.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
