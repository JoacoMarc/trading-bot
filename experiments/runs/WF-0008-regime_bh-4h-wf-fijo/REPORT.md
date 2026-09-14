# WF-0008 — regime_bh 4h walk-forward IS 24 m / OOS 6 m (fijo)

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
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -4.25 % | -0.35 | 9.76 % | 6 | 0.47 | 0 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +7.93 % | 1.90 | 2.54 % | 0 | - | 1 (+797.88) | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | +11.25 % | 1.04 | 7.33 % | 6 | 3.23 | 0 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +18.08 % | 1.85 | 8.91 % | 3 | 3.50 | 1 (-102.26) | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +20.26 % | 1.70 | 9.53 % | 7 | 32.74 | 1 (-189.04) | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +10.59 % | 1.01 | 12.38 % | 8 | 2.04 | 1 (-90.96) | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +5.59 % | 1.12 | 5.03 % | 4 | 1.40 | 1 (+397.99) | 0 |

5 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) |
|---|---|---|---|
| Retorno total | +90.65 % | +175.83 % | +193.20 % |
| CAGR | +17.51 % | +28.87 % | +30.86 % |
| Sharpe (diario) | 1.04 | 0.76 | 1.01 |
| Sortino (diario) | 1.67 | 1.12 | 1.63 |
| Calmar | 1.15 | 0.37 | 1.11 |
| Max drawdown / mayor tramo bajo agua | +15.28 % / 438 d | +77.11 % / 852 d | +27.78 % / 464 d |
| Profit factor | 2.68 | — | — |
| Win rate | +41.18 % | — | — |
| Expectancy por trade | 181.43 | — | — |
| Trades / duración media | 34 / 368.8 h | 0 / — h | 0 / — h |
| Exposición | +41.17 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 392.79 / 5.0 bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 19,064.99 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +300.23 %, Sharpe 1.18, max DD +21.44 %, 58 trades.

## Gate 1 — backtest -> paper: incompleto (1 criterios sin evaluar)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 1.04 | OK |  |
| Profit factor OOS | >= 1.3 | 2.68 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 15.28 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 1/1 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 30 | 58 | OK |  |
| Trades curva OOS | >= 15 | 34 | OK |  |
| Régimen: retorno 2020 | > 0 | +91.28 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +25.89 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +49.10 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +30.19 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 21.15 % (2021) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | - | n/a | correr con --plateau |
| Monte Carlo DD p95 | <= 35 % | 24.75 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -16.24 % | 17.42 % | 9 | -1,623.50 |
| 2020 | +91.28 % | 10.98 % | 8 | 193.02 |
| 2021 | +25.89 % | 21.15 % | 12 | 11,604.16 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +49.10 % | 7.33 % | 6 | 4,070.76 |
| 2024 | +30.19 % | 11.29 % | 16 | 14,917.85 |
| 2025 (parcial) | +2.22 % | 8.75 % | 7 | -613.77 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 34 trades, semilla 42: max DD p50 +10.77 %, p95 +24.75 %, p99 +34.40 %; retorno p05 -2.78 %, p50 +59.02 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +16.17 %, p95 +26.56 %, p99 +32.66 %; retorno p05 +15.33 %, p50 +95.92 %.

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (control)
- **Por qué**: control λ 0.5, candidata a config final. OOS +90.6 %, Sharpe 1.04, DD 15.28 %, PF 2.68, 34 trades (los mismos que WF-0006); muestra completa +300 %, Sharpe 1.18, DD 21.44 %, intra-2021 21.15 %; MC por trades p95 24.75 %, bloques p95 26.56 %. Todo lo evaluable del gate pasa; la meseta queda n/a por diseño (se corrió en WF-0006 y no depende de λ).
- **Qué se aprendió**: el Sharpe es invariante a λ (1.04 / 1.04 / 1.05 en 0.5 / 0.6 / 0.75) y el PF también (2.68 / 2.64 / 2.58); el DD escala casi lineal (OOS 15.3 / 17.8 / 21.5 %; completa 21.4 / 25.2 / 28.6 %). λ 0.5 es la única de las tres que deja el DD histórico bajo 25 % con margen; cuesta 3.3 pp de CAGR OOS (17.5 % vs 20.8 %).
- **Siguiente experimento propuesto**: esta λ es la config final para el holdout y para paper (`risk.position_fraction: 0.5` en `configs/regime-bh.yaml`); decidido antes de correr el holdout y sin volver a cambiarla después.
