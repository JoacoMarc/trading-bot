# WF-0009 — regime_bh 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares BTC/USDT, hash 4b239758a1fc
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 100 % del cash por posición, máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git f1dd153, params 937532e2f5, datos 4b239758a1fc, 1.9 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -6.42 % | -0.33 | 14.18 % | 6 | 0.46 | 0 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +11.89 % | 1.92 | 3.64 % | 0 | - | 1 (+1,196.80) | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | +16.65 % | 1.07 | 10.29 % | 6 | 3.16 | 0 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +25.87 % | 1.84 | 12.86 % | 3 | 3.18 | 1 (-164.26) | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +30.44 % | 1.77 | 12.90 % | 7 | 31.67 | 1 (-310.07) | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +14.51 % | 0.99 | 17.36 % | 8 | 1.93 | 1 (-141.91) | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +8.27 % | 1.15 | 7.49 % | 4 | 1.38 | 1 (+600.89) | 0 |

5 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) |
|---|---|---|---|
| Retorno total | +148.63 % | +175.83 % | +193.20 % |
| CAGR | +25.57 % | +28.87 % | +30.86 % |
| Sharpe (diario) | 1.05 | 0.76 | 1.01 |
| Sortino (diario) | 1.71 | 1.12 | 1.63 |
| Calmar | 1.19 | 0.37 | 1.11 |
| Max drawdown / mayor tramo bajo agua | +21.45 % / 438 d | +77.11 % / 852 d | +27.78 % / 464 d |
| Profit factor | 2.58 | — | — |
| Win rate | +41.18 % | — | — |
| Expectancy por trade | 264.58 | — | — |
| Trades / duración media | 34 / 368.8 h | 0 / — h | 0 / — h |
| Exposición | +41.17 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 604.24 / 5.0 bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 24,863.31 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +564.97 %, Sharpe 1.22, max DD +28.63 %, 52 trades.

## Gate 1 — backtest -> paper: no aprobado (2 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 1.05 | OK |  |
| Profit factor OOS | >= 1.3 | 2.58 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 21.45 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 1/1 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 30 | 52 | OK |  |
| Trades curva OOS | >= 15 | 34 | OK |  |
| Régimen: retorno 2020 | > 0 | +136.64 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +36.03 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +77.89 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +44.06 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 25.22 % (2021) | FALLA | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | - | n/a | correr con --plateau |
| Monte Carlo DD p95 | <= 35 % | 37.66 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -21.39 % | 23.04 % | 6 | -2,139.07 |
| 2020 | +136.64 % | 15.97 % | 8 | 211.00 |
| 2021 | +36.03 % | 25.22 % | 10 | 17,235.28 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +77.89 % | 10.29 % | 6 | 7,769.55 |
| 2024 | +44.06 % | 16.48 % | 16 | 31,777.77 |
| 2025 (parcial) | +2.55 % | 12.77 % | 6 | -1,987.48 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 34 trades, semilla 42: max DD p50 +15.34 %, p95 +37.66 %, p99 +53.44 %; retorno p05 -6.21 %, p50 +85.92 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +22.93 %, p95 +36.74 %, p99 +44.54 %; retorno p05 +19.87 %, p50 +159.11 %.

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: λ 0.75 descartada; el control cumplió su función. Sharpe OOS 1.05 (igual que 0.5 y 0.6) pero DD intra-2021 25.22 % y MC p95 37.66 % fallan el gate; bloques p95 36.74 %; DD completa 28.63 %; 2019 (parcial) −21.4 %. El retorno extra (+148.6 % vs +112.9 %) es solo apalancamiento del mismo camino.
- **Qué se aprendió**: con el presupuesto de la spec (intra-año ≤ 25 %, MC p95 ≤ 35 %) la λ máxima interpolada es ≈ 0.70; medida desde el pico histórico, ≈ 0.59. No hay retorno por unidad de riesgo que ganar moviendo λ: es una perilla de DD.
- **Siguiente experimento propuesto**: ninguno; no volver a probar λ > 0.6 en esta familia.
