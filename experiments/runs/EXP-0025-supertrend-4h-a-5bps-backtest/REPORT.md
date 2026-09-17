# EXP-0025 — supertrend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git d4576bd, params 68e7dfee94, datos 40a0aa8573b9, 2.3 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `6` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +7.74 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | +1.23 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | 0.51 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | 0.82 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.46 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +2.70 % / 523 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 1.38 | — | — | — |
| Win rate | +37.04 % | — | — | — |
| Expectancy por trade | 3.68 | — | — | — |
| Trades / duración media | 216 / 95.9 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +24.03 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 185.93 / 5.8 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 10,774.36 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.68 % | +0.68 % | 4 | -68.16 |
| 2020 | +1.31 % | +2.41 % | 40 | 112.40 |
| 2021 | +1.12 % | +1.92 % | 47 | 136.04 |
| 2022 | +0.00 % | +0.46 % | 0 | 0.00 |
| 2023 | +2.83 % | +2.16 % | 55 | 292.12 |
| 2024 | +0.78 % | +2.70 % | 42 | 88.61 |
| 2025 | +2.18 % | +2.04 % | 28 | 233.80 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 24 | -149.77 | +33.33 % |
| BNB/USDT | 33 | 371.48 | +42.42 % |
| BTC/USDT | 37 | 158.74 | +29.73 % |
| ETH/USDT | 28 | 0.03 | +28.57 % |
| LINK/USDT | 25 | -75.33 | +28.00 % |
| LTC/USDT | 26 | 199.97 | +53.85 % |
| SOL/USDT | 23 | 253.97 | +47.83 % |
| XRP/USDT | 20 | 35.72 | +35.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 1 |
| stop | 8 |
| trailing | 207 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 702 |
| entry_rejected:max_positions | 214 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2024-06-12 16:00 @ 69768.87 | 2024-06-12 19:59 @ 67270.93 | stop | -28.12 | -3.78 % |
| BTC/USDT | 2024-05-27 16:00 @ 70409.05 | 2024-05-28 03:59 @ 67856.85 | stop | -28.01 | -3.82 % |
| BTC/USDT | 2023-04-18 12:00 @ 30395.79 | 2023-04-19 11:59 @ 29408.80 | trailing | -27.47 | -3.44 % |
| BTC/USDT | 2024-10-24 20:00 @ 68343.95 | 2024-10-25 19:59 @ 66097.32 | trailing | -27.38 | -3.48 % |
| ETH/USDT | 2024-01-02 04:00 @ 2387.62 | 2024-01-03 15:59 @ 2288.95 | trailing | -26.89 | -4.33 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| XRP/USDT | 2023-10-20 00:00 @ 0.5200 | 2023-11-07 03:59 @ 0.6660 | trailing | 161.05 | +27.85 % |
| BTC/USDT | 2020-10-08 16:00 @ 10902.41 | 2020-10-26 19:59 @ 12769.81 | trailing | 148.88 | +16.91 % |
| BTC/USDT | 2024-11-06 04:00 @ 74385.71 | 2024-11-25 15:59 @ 95664.07 | trailing | 134.04 | +28.38 % |
| BNB/USDT | 2023-12-19 12:00 @ 252.23 | 2023-12-29 19:59 @ 308.70 | trailing | 115.84 | +22.17 % |
| BNB/USDT | 2021-10-28 16:00 @ 487.25 | 2021-11-10 07:59 @ 624.39 | trailing | 106.92 | +27.92 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
