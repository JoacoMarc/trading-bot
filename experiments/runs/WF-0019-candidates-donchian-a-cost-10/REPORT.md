# WF-0019 — donchian 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params c8d4a6af5b, datos 40a0aa8573b9, 28.3 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.61 % | 0.48 | 1.90 % | 26 | 1.22 | 0 | 90 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.37 % | 0.69 | 0.49 % | 4 | 1.79 | 0 | 20 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -0.21 % | -0.11 | 1.67 % | 29 | 0.93 | 0 | 67 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +4.83 % | 2.36 | 1.79 % | 23 | 3.13 | 1 (-16.51) | 99 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +0.25 % | 0.18 | 2.63 % | 29 | 1.13 | 1 (-14.40) | 96 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.25 % | 0.20 | 2.06 % | 27 | 1.11 | 0 | 106 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -0.05 % | -0.01 | 3.35 % | 25 | 1.00 | 0 | 136 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +6.12 % | +174.73 % | +203.24 % | +173.86 % |
| CAGR | +1.50 % | +28.74 % | +31.96 % | +28.64 % |
| Sharpe (diario) | 0.55 | 0.76 | 1.04 | 0.72 |
| Sortino (diario) | 0.90 | 1.11 | 1.69 | 1.03 |
| Calmar | 0.28 | 0.37 | 1.16 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +5.37 % / 779 d | +77.14 % / 852 d | +27.48 % / 438 d | +81.55 % / 1108 d |
| Profit factor | 1.36 | — | — | — |
| Win rate | +34.36 % | — | — | — |
| Expectancy por trade | 4.06 | — | — | — |
| Trades / duración media | 163 / 97.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +26.76 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 142.88 / 10.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 10,612.12 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +20.64 %, Sharpe 1.01, max DD +5.44 %, 249 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.55 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.36 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.14 %) | 5.37 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 249 | OK |  |
| Trades curva OOS | >= 40 | 163 | OK |  |
| Régimen: retorno 2020 | > 0 | +6.92 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +7.41 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +5.50 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +0.60 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 3.99 % (2025) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 6.40 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -0.26 % | 1.57 % | 8 | -25.76 |
| 2020 | +6.92 % | 1.98 % | 41 | 632.14 |
| 2021 | +7.41 % | 1.89 % | 61 | 857.02 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +5.50 % | 2.11 % | 53 | 634.24 |
| 2024 | +0.60 % | 3.44 % | 55 | 81.56 |
| 2025 (parcial) | -0.77 % | 3.99 % | 31 | -86.51 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 163 trades, semilla 42: max DD p50 +3.30 %, p95 +6.40 %, p99 +8.11 %; retorno p05 -2.35 %, p50 +6.26 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +4.40 %, p95 +8.14 %, p99 +10.05 %; retorno p05 -4.05 %, p50 +5.42 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.01). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| atr_mult=2.4, entry_period=72, exit_period=24 | +12.48 % | 1.34 | 0.59 | 315 | sí |
| atr_mult=2.4, entry_period=72, exit_period=16 | +12.55 % | 1.34 | 0.59 | 315 | sí |
| atr_mult=2.4 | +13.04 % | 1.34 | 0.61 | 325 | sí |
| atr_mult=2.4, entry_period=48, exit_period=24 | +13.48 % | 1.34 | 0.61 | 337 | sí |
| atr_mult=2.4, entry_period=48, exit_period=16 | +13.54 % | 1.34 | 0.62 | 337 | sí |
| entry_period=48 | +20.58 % | 1.69 | 1.01 | 257 | sí |
| exit_period=16 | +20.71 % | 1.69 | 1.01 | 251 | sí |
| exit_period=24 | +21.84 % | 1.74 | 1.06 | 247 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: El perfil moderado no alcanza el Sharpe OOS mínimo del protocolo (WF-0012 y costos adversos). El beneficio continuo no basta para aprobar. Sin paper ni holdout. En esta corrida fallan: Sharpe OOS = 0.55.
- **Qué se aprendió**: La meseta positiva y la caída acotada no compensan el incumplimiento del criterio OOS.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
