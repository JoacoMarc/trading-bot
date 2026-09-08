# EXP-0005 — ema_trend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares BTC/USDT, ETH/USDT, hash 183890dbdbc6
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off
- Reproducibilidad: git 8def2fc, params b978b0fa53, datos 183890dbdbc6, 1.8 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `adx_period` | `14` |
| `adx_threshold` | `20.0` |
| `atr_period` | `14` |
| `cooldown_candles` | `2` |
| `ema_fast` | `20` |
| `ema_regime` | `200` |
| `ema_slow` | `50` |
| `entry_mode` | `cross` |
| `stop_atr_mult` | `2.0` |
| `trailing_atr_mult` | `3.0` |
| `warmup_multiplier` | `6` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado |
|---|---|---|---|
| Retorno total | +69.89 % | +972.20 % | +1439.95 % |
| CAGR | +9.10 % | +47.67 % | +56.72 % |
| Sharpe (diario) | 1.17 | 0.93 | 0.99 |
| Sortino (diario) | 2.31 | 1.37 | 1.42 |
| Calmar | 1.26 | 0.62 | 0.71 |
| Max drawdown / mayor tramo bajo agua | +7.23 % / 573 d | +77.04 % / 851 d | +79.35 % / 1132 d |
| Profit factor | 2.60 | — | — |
| Win rate | +41.77 % | — | — |
| Expectancy por trade | 88.64 | — | — |
| Trades / duración media | 79 / 114.8 h | 0 / — h | 0 / — h |
| Exposición | +13.35 % | +99.99 % | +99.99 % |
| Fees pagados / shortfall medio | 488.54 / 5.0 bps | 10.00 / 5.0 bps | 10.00 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 16,989.46 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +1.00 % | +3.61 % | 4 | 100.43 |
| 2020 | +25.90 % | +6.23 % | 19 | 2,241.86 |
| 2021 | +13.44 % | +5.57 % | 13 | 2,087.20 |
| 2022 | +4.47 % | +3.87 % | 9 | 646.56 |
| 2023 | +2.16 % | +4.43 % | 15 | 327.91 |
| 2024 | +11.66 % | +7.23 % | 14 | 1,799.13 |
| 2025 | -1.18 % | +2.71 % | 5 | -200.65 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 40 | 3,371.54 | +40.00 % |
| ETH/USDT | 39 | 3,630.89 | +43.59 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 1 |
| stop | 22 |
| trailing | 56 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| — | 0 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ETH/USDT | 2025-08-22 20:00 @ 4835.42 | 2025-08-25 07:59 @ 4585.23 | stop | -179.63 | -5.37 % |
| ETH/USDT | 2025-06-03 20:00 @ 2626.51 | 2025-06-05 19:59 @ 2536.88 | trailing | -155.96 | -3.61 % |
| ETH/USDT | 2023-12-14 20:00 @ 2294.14 | 2023-12-15 23:59 @ 2207.95 | stop | -155.77 | -3.95 % |
| ETH/USDT | 2022-02-15 16:00 @ 3124.18 | 2022-02-17 15:59 @ 2970.72 | stop | -152.59 | -5.11 % |
| ETH/USDT | 2021-12-08 20:00 @ 4383.57 | 2021-12-09 19:59 @ 4124.24 | stop | -151.60 | -6.11 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ETH/USDT | 2020-01-27 00:00 @ 168.00 | 2020-02-16 03:59 @ 260.07 | trailing | 1,399.97 | +54.55 % |
| BTC/USDT | 2024-11-06 04:00 @ 74385.71 | 2024-11-25 15:59 @ 95664.07 | trailing | 1,111.77 | +28.38 % |
| ETH/USDT | 2020-12-26 16:00 @ 628.83 | 2021-01-04 11:59 @ 901.49 | trailing | 950.36 | +43.12 % |
| BTC/USDT | 2023-10-16 16:00 @ 28078.20 | 2023-11-03 11:59 @ 34172.96 | trailing | 810.58 | +21.48 % |
| ETH/USDT | 2021-04-26 04:00 @ 2456.13 | 2021-05-10 23:59 @ 3742.45 | trailing | 739.65 | +52.12 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (control: defaults sin costo)
- **Por qué**: pérdida diaria 3 % y DD 20 % (reanuda bajo 10 % o tras 30 d) no dispararon en 2,223 días: 0 eventos y métricas idénticas a EXP-0003/0004 (79 trades, 16,989.46, Sharpe 1.17, DD 7.23 %).
- **Qué se aprendió**: el costo cero es por construcción, no evidencia de robustez: el peor día fue −2.96 % (2020-12-01, dos posiciones devolviendo ganancia no realizada), 4 bps bajo el umbral, y el DD máximo 7.23 % está a 2.8× del 20 %. Con 30 días ≥ 1 % y 3 ≥ 2 % en la línea base, el 3 % diario va a disparar apenas haya 3 posiciones simultáneas (8 pares); el 20 % es un seguro contra catástrofe, no una protección operativa para esta estrategia.
- **Siguiente experimento propuesto**: mantener los defaults en EXP-0007 (universo v1, 8 pares, 4h) y contar eventos ahí; no ajustar niveles antes de ver esa distribución.
