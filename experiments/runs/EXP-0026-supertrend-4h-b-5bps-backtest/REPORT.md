# EXP-0026 — supertrend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
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
| Retorno total | +16.08 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | +2.48 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | 0.43 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | 0.69 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.34 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +7.37 % / 727 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 1.26 | — | — | — |
| Win rate | +35.44 % | — | — | — |
| Expectancy por trade | 5.75 | — | — | — |
| Trades / duración media | 285 / 95.8 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +25.02 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 517.05 / 5.8 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 11,607.73 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -1.36 % | +1.36 % | 4 | -136.00 |
| 2020 | +4.16 % | +6.02 % | 51 | 287.52 |
| 2021 | +7.98 % | +4.28 % | 59 | 949.72 |
| 2022 | +0.00 % | +1.11 % | 0 | 0.00 |
| 2023 | +2.58 % | +7.37 % | 76 | 292.12 |
| 2024 | -1.14 % | +7.08 % | 58 | -120.02 |
| 2025 | +3.18 % | +6.12 % | 37 | 364.90 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 36 | -321.59 | +36.11 % |
| BNB/USDT | 44 | 640.93 | +36.36 % |
| BTC/USDT | 47 | 112.24 | +25.53 % |
| ETH/USDT | 36 | 229.88 | +30.56 % |
| LINK/USDT | 33 | -323.57 | +24.24 % |
| LTC/USDT | 31 | 578.12 | +54.84 % |
| SOL/USDT | 30 | 496.51 | +43.33 % |
| XRP/USDT | 28 | 225.71 | +39.29 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 1 |
| stop | 13 |
| trailing | 271 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 702 |
| entry_rejected:max_positions | 145 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2025-06-16 20:00 @ 108706.34 | 2025-06-17 11:59 @ 105543.80 | stop | -61.46 | -3.11 % |
| BTC/USDT | 2024-06-12 16:00 @ 69768.87 | 2024-06-12 19:59 @ 67270.93 | stop | -60.74 | -3.78 % |
| BTC/USDT | 2024-05-27 16:00 @ 70409.05 | 2024-05-28 03:59 @ 67856.85 | stop | -60.67 | -3.82 % |
| BTC/USDT | 2023-04-18 12:00 @ 30395.79 | 2023-04-19 11:59 @ 29408.80 | trailing | -59.45 | -3.44 % |
| LINK/USDT | 2024-04-08 12:00 @ 18.606 | 2024-04-09 11:59 @ 17.543 | trailing | -59.43 | -5.91 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| XRP/USDT | 2023-10-20 00:00 @ 0.5200 | 2023-11-07 03:59 @ 0.6660 | trailing | 333.00 | +27.85 % |
| BTC/USDT | 2020-10-08 16:00 @ 10902.41 | 2020-10-26 19:59 @ 12769.81 | trailing | 286.85 | +16.91 % |
| BTC/USDT | 2024-11-06 04:00 @ 74385.71 | 2024-11-25 15:59 @ 95664.07 | trailing | 280.11 | +28.38 % |
| XRP/USDT | 2021-01-29 08:00 @ 0.2783 | 2021-02-01 15:59 @ 0.4678 | trailing | 272.73 | +67.82 % |
| BNB/USDT | 2023-12-19 12:00 @ 252.23 | 2023-12-29 19:59 @ 308.70 | trailing | 247.56 | +22.17 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
