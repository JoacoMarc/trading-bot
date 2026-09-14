# WF-0007 — regime_bh 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ETH/USDT, hash 101aa900d36f
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 100 % del cash por posición, máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado ETH/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git f1dd153, params 937532e2f5, datos 101aa900d36f, 1.9 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +12.87 % | 0.88 | 19.89 % | 5 | 3.69 | 0 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | -2.13 % | -1.59 | 2.13 % | 1 | 0.00 | 0 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +7.08 % | 1.15 | 4.57 % | 0 | - | 1 (+713.84) | 0 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -6.15 % | -0.57 | 16.66 % | 14 | 0.64 | 0 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +2.09 % | 0.29 | 15.32 % | 4 | 1.30 | 1 (-94.96) | 0 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +23.92 % | 1.54 | 15.51 % | 5 | 5.45 | 0 | 0 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +3.76 % | 0.43 | 15.93 % | 3 | 2.03 | 0 | 0 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +26.75 % | 3.20 | 4.99 % | 1 | 0.00 | 1 (+2,782.27) | 0 |

3 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC filtrado (OOS) | B&H ETH (OOS) |
|---|---|---|---|
| Retorno total | +84.69 % | +152.78 % | +44.37 % |
| CAGR | +16.58 % | +26.09 % | +9.62 % |
| Sharpe (diario) | 0.77 | 0.81 | 0.48 |
| Sortino (diario) | 1.22 | 1.30 | 0.71 |
| Calmar | 0.83 | 0.93 | 0.12 |
| Max drawdown / mayor tramo bajo agua | +19.89 % / 588 d | +28.04 % / 520 d | +81.15 % / 1359 d |
| Profit factor | 1.77 | — | — |
| Win rate | +30.30 % | — | — |
| Expectancy por trade | 104.25 | — | — |
| Trades / duración media | 33 / 329.9 h | 0 / — h | 0 / — h |
| Exposición | +34.27 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 434.77 / 5.0 bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 18,469.20 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +869.41 %, Sharpe 1.24, max DD +38.66 %, 48 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (-) | 0.77 | n/a | sin B&H BTC en el rango |
| Profit factor OOS | >= 1.3 | 1.77 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (-) | 19.89 % | n/a | sin B&H BTC en el rango |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 1/1 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 30 | 48 | OK |  |
| Trades curva OOS | >= 15 | 33 | OK |  |
| Régimen: retorno 2020 | > 0 | +119.03 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +176.63 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +16.22 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +15.31 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | -2.13 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 38.66 % (2021) | FALLA | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | - | n/a | correr con --plateau |
| Monte Carlo DD p95 | <= 35 % | 31.57 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -2.08 % | 5.70 % | 1 | -208.38 |
| 2020 | +119.03 % | 26.85 % | 11 | 9,348.02 |
| 2021 | +176.63 % | 38.66 % | 7 | 40,187.40 |
| 2022 | -2.13 % | 2.13 % | 1 | -1,264.60 |
| 2023 | +16.22 % | 17.37 % | 15 | 32.86 |
| 2024 | +15.31 % | 15.93 % | 11 | 19,719.93 |
| 2025 (parcial) | +24.58 % | 4.99 % | 2 | -2,105.74 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 33 trades, semilla 42: max DD p50 +13.79 %, p95 +31.57 %, p99 +42.39 %; retorno p05 -14.84 %, p50 +33.69 %.

Informativo (ADR-0010), bootstrap por bloques de 20 días de los 1460 retornos diarios OOS: max DD p50 +28.68 %, p95 +47.94 %, p99 +56.48 %; retorno p05 -22.45 %, p50 +63.20 %.

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (control)
- **Por qué**: control ETH/USDT con la misma config; informativo, no cambia el veredicto de WF-0006. OOS +84.7 %, Sharpe 0.77, DD 19.9 %, PF 1.77, 33 trades vs B&H ETH +44.4 % / 0.48 / 81.2 % y ETH filtrado λ = 1 +152.8 % / 0.81 / 28.0 % (la columna dice "B&H BTC filtrado" por una constante del reporte: es ETH). Mismo delta que en BTC frente al B&H crudo (+0.29 de Sharpe, DD ÷ 4), pero no llega a 0.8 ni a su propio filtrado, y en la muestra completa el DD intra-2021 es 38.66 % (2020: 26.85 %): con λ 0.6 ETH revienta el presupuesto de DD (necesitaría λ ≈ 0.4). Los criterios contra B&H BTC quedan n/a porque el universo no tiene BTC.
- **Qué se aprendió**: la regla es del mercado, no del activo: funciona en la misma dirección en ETH. El lateral de 2023 realizó el peor caso de la spec: 16 entradas, PF 0.63, −650 USDT; 14 de 33 trades duraron ≤ 48 h con win rate 0 % (−2,173); sin top 10 PF 0.00. Bootstrap por bloques p95 47.9 % y retorno p05 −22.5 %: ETH con λ 0.6 es otra estrategia de riesgo. 2022: −2.1 % (1 trade).
- **Siguiente experimento propuesto**: ninguno ahora. Un `regime_bh` multi-activo exigiría λ por par (deuda de ADR-0010) y presupuesto de DD por activo; se evalúa después del holdout de BTC y con datos nuevos. Deuda: la etiqueta del benchmark filtrado debe llevar el par de referencia.
