# WF-0006 — regime_bh 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares BTC/USDT, hash 4b239758a1fc
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 100 % del cash por posición, máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git f1dd153, params 937532e2f5, datos 4b239758a1fc, 13.1 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | -5.10 % | -0.34 | 11.56 % | 6 | 0.47 | 0 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | +0.00 % | - | -0.00 % | 0 | - | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +9.51 % | 1.91 | 2.99 % | 0 | - | 1 (+957.45) | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | +13.43 % | 1.05 | 8.56 % | 6 | 3.20 | 0 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +21.30 % | 1.85 | 10.52 % | 3 | 3.37 | 1 (-126.29) | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +24.35 % | 1.73 | 10.96 % | 7 | 32.30 | 1 (-235.32) | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +12.25 % | 1.00 | 14.45 % | 8 | 2.00 | 1 (-110.98) | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +6.68 % | 1.13 | 6.01 % | 4 | 1.39 | 1 (+478.93) | 0 |

5 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) |
|---|---|---|---|
| Retorno total | +112.90 % | +175.83 % | +193.20 % |
| CAGR | +20.80 % | +28.87 % | +30.86 % |
| Sharpe (diario) | 1.04 | 0.76 | 1.01 |
| Sortino (diario) | 1.69 | 1.12 | 1.63 |
| Calmar | 1.17 | 0.37 | 1.11 |
| Max drawdown / mayor tramo bajo agua | +17.84 % / 438 d | +77.11 % / 852 d | +27.78 % / 464 d |
| Profit factor | 2.64 | — | — |
| Win rate | +41.18 % | — | — |
| Expectancy por trade | 215.28 | — | — |
| Trades / duración media | 34 / 368.8 h | 0 / — h | 0 / — h |
| Exposición | +41.17 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 476.23 / 5.0 bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 21,289.94 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +397.90 %, Sharpe 1.20, max DD +25.22 %, 56 trades.

## Gate 1 — backtest -> paper: aprobado (falta el holdout)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 1.04 | OK |  |
| Profit factor OOS | >= 1.3 | 2.64 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 17.84 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 1/1 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 30 | 56 | OK |  |
| Trades curva OOS | >= 15 | 34 | OK |  |
| Régimen: retorno 2020 | > 0 | +109.51 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +31.70 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +60.27 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +35.86 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | +0.00 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 22.69 % (2021) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 29.89 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -19.23 % | 20.58 % | 9 | -1,922.23 |
| 2020 | +109.51 % | 13.01 % | 8 | 203.39 |
| 2021 | +31.70 % | 22.69 % | 10 | 14,009.20 |
| 2022 | +0.00 % | 0.00 % | 0 | 0.00 |
| 2023 | +60.27 % | 8.56 % | 6 | 5,428.97 |
| 2024 | +35.86 % | 13.40 % | 16 | 20,818.14 |
| 2025 (parcial) | +2.60 % | 10.42 % | 7 | -941.87 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 34 trades, semilla 42: max DD p50 +12.61 %, p95 +29.89 %, p99 +42.16 %; retorno p05 -3.97 %, p50 +69.87 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +18.95 %, p95 +30.90 %, p99 +37.64 %; retorno p05 +17.51 %, p50 +119.95 %.

## Meseta ±20 %

14 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.20). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| momentum_days=25 | +189.60 % | 2.05 | 0.85 | 66 | sí |
| momentum_days=25, sma_days=160, stop_pct=0.15 | +220.61 % | 2.08 | 0.92 | 68 | sí |
| momentum_days=25, sma_days=240, stop_pct=0.15 | +254.56 % | 2.03 | 0.98 | 73 | sí |
| momentum_days=25, sma_days=160, stop_pct=0.25 | +268.56 % | 2.38 | 1.02 | 68 | sí |
| momentum_days=25, sma_days=240, stop_pct=0.25 | +286.00 % | 2.24 | 1.05 | 71 | sí |
| stop_pct=0.15 | +388.13 % | 2.61 | 1.19 | 56 | sí |
| sma_days=160 | +391.62 % | 2.58 | 1.19 | 60 | sí |
| stop_pct=0.25 | +397.90 % | 2.65 | 1.20 | 56 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: go
- **Por qué**: la spec v1 queda en "confirma": los ocho criterios prefijados se cumplen y ninguno de refutación se dispara. Sharpe OOS 1.04 ≥ 0.8 y > 0.76 del B&H BTC; DD OOS 17.84 %; 2022 = 0.00 % (en cash todo el año); DD intra-año máx. 22.69 % (2021), 2020 13.01 %; PF 2.64; meseta 14/14 con PF > 1.1 y retorno > 0 y 14/14 con Sharpe ≥ 0.5 × base (mín. 0.85); Sharpe de la muestra completa sin 2022 = 1.3 (retornos diarios de EXP-0009, rf 0, √365; B&H BTC 1.38, filtrado 1.23; el umbral de refutación era 0.69). Gate 1 `aprobado (falta el holdout)` con umbrales de trades 30/15 (ADR-0010). Contra el B&H BTC filtrado (mismo régimen, λ = 1, sin protecciones): Δ Sharpe +0.03, bootstrap por bloques de la diferencia p05 −0.08 / p95 +0.17, P(Δ > 0) 0.69; contra el B&H BTC: Δ +0.29, p05 −0.35 / p95 +1.04, P 0.79. La ventaja sobre el B&H es probable, no significativa: la muestra tiene un solo bear completo.
- **Qué se aprendió**: λ 0.6 y las protecciones no aportan Sharpe (el filtrado escalado a la misma volatilidad da +107.7 % y DD 17.8 % vs +112.9 % y 17.8 %): compran DD. Sin 2022 el B&H BTC tiene mejor Sharpe que la estrategia (1.62 vs 1.21 en OOS): la ventaja es evitar el bear, que es exactamente la hipótesis, y por eso esta muestra no puede confirmarla más de una vez. El PnL OOS vive en 15 trades > 96 h (+11,113, win rate 67 %); los 19 restantes pierden −3,794; top 5 = 142 %; sin top 10 PF 0.03: PF, expectancy y el MC por trades describen mal la familia; el bootstrap por bloques (DD p50 19.0 %, p95 30.9 %, p99 37.6 %; retorno p05 +17.5 %) es la métrica a mirar. La meseta pasa pero es una pendiente en `momentum_days` (25: Sharpe 0.85–1.05; 35: 1.25–1.29); `sma_days` y `stop_pct` no mueven nada. Stop 20 %: 0/34 ejecuciones. La curva OOS estuvo en cash 14 meses seguidos (2021-11 → 2023-01).
- **Siguiente experimento propuesto**: corrida del holdout, una sola vez, con λ fijada antes en 0.5 (WF-0008: DD histórico 21.4 % vs 25.2 %, bloques p95 26.6 % vs 30.9 %, mismo Sharpe y PF). Escrito en la spec antes de correr: el holdout tendrá ~8–15 trades, el criterio que discrimina es DD ≤ 25 %, un pase es evidencia débil y un fallo refuta. Si pasa: paper con la misma config (Fase 7). No probar `momentum_days` 35 ni salida solo por SMA sobre esta muestra: quedan como hipótesis para datos futuros.
