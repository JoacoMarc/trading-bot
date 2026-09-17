# WF-0010 — pullback_rsi 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 26.7 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +0.06 % | 0.08 | 0.93 % | 75 | 1.08 | 0 | 77 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.32 % | 0.81 | 0.38 % | 16 | 1.88 | 0 | 25 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -1.41 % | -1.60 | 2.00 % | 97 | 0.67 | 0 | 91 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -1.50 % | -1.69 | 2.12 % | 78 | 0.63 | 0 | 75 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -2.61 % | -2.57 | 3.12 % | 106 | 0.54 | 1 (-16.28) | 69 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | -3.64 % | -2.82 | 3.95 % | 91 | 0.40 | 1 (-8.66) | 76 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -0.98 % | -1.07 | 1.41 % | 66 | 0.71 | 0 | 70 |

2 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | -9.42 % | +175.83 % | +214.53 % | +174.95 % |
| CAGR | -2.44 % | +28.87 % | +33.17 % | +28.77 % |
| Sharpe (diario) | -1.44 | 0.76 | 1.07 | 0.72 |
| Sortino (diario) | -1.64 | 1.12 | 1.74 | 1.03 |
| Calmar | -0.23 | 0.37 | 1.23 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +10.41 % / 1355 d | +77.11 % / 852 d | +26.93 % / 438 d | +81.53 % / 1108 d |
| Profit factor | 0.63 | — | — | — |
| Win rate | +59.92 % | — | — | — |
| Expectancy por trade | -1.67 | — | — | — |
| Trades / duración media | 529 / 14.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +14.72 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 510.35 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 9,058.25 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -12.10 %, Sharpe -1.26, max DD +13.04 %, 831 trades.

## Gate 1 — backtest -> paper: no aprobado (8 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -1.44 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.63 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 10.41 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 2/8 (25 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 831 | OK |  |
| Trades curva OOS | >= 40 | 529 | OK |  |
| Régimen: retorno 2020 | > 0 | -2.21 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | -0.85 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | -1.71 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -6.53 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 6.96 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 13.28 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | +0.21 % | 0.32 % | 20 | 21.37 |
| 2020 | -2.21 % | 2.75 % | 183 | -216.24 |
| 2021 | -0.85 % | 2.34 % | 173 | -64.36 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | -1.71 % | 2.68 % | 176 | -154.29 |
| 2024 | -6.53 % | 6.96 % | 197 | -592.94 |
| 2025 (parcial) | -1.54 % | 1.96 % | 82 | -122.53 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 529 trades, semilla 42: max DD p50 +9.26 %, p95 +13.28 %, p99 +15.14 %; retorno p05 -12.95 %, p50 -8.78 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +10.04 %, p95 +14.56 %, p99 +16.32 %; retorno p05 -14.16 %, p50 -9.52 %.

## Meseta ±20 %

14 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| rsi_entry=12, rsi_exit=56, stop_atr_mult=2.0 | -21.21 % | 0.56 | -2.13 | 1014 | no |
| rsi_entry=8, rsi_exit=56, stop_atr_mult=2.0 | -18.07 % | 0.54 | -1.94 | 778 | no |
| stop_atr_mult=2.0 | -16.17 % | 0.68 | -1.43 | 872 | no |
| rsi_exit=56 | -14.44 % | 0.57 | -1.75 | 870 | no |
| rsi_entry=8, rsi_exit=84, stop_atr_mult=2.0 | -14.24 % | 0.75 | -1.11 | 694 | no |
| rsi_entry=12 | -13.52 % | 0.68 | -1.39 | 920 | no |
| rsi_entry=12, rsi_exit=56, stop_atr_mult=3.0 | -13.36 % | 0.57 | -1.82 | 953 | no |
| rsi_entry=12, rsi_exit=84, stop_atr_mult=2.0 | -13.28 % | 0.80 | -0.94 | 863 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados. En esta corrida fallan: Sharpe OOS = -1.44; Profit factor OOS = 0.63; Ventanas OOS positivas = 2/8 (25 %); Régimen: retorno 2020 = -2.21 %; Régimen: retorno 2021 = -0.85 %; Régimen: retorno 2023 = -1.71 %; Régimen: retorno 2024 = -6.53 %; Meseta ±20 % = 0.00 %.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
