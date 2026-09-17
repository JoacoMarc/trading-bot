# EXP-0029 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash a6067cb13733; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos a6067cb13733, 4.7 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | -0.04 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | -0.01 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | -0.01 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | -0.01 | 1.37 | 1.35 | 1.82 |
| Calmar | -0.00 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +1.47 % / 740 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 0.98 | — | — | — |
| Win rate | +38.46 % | — | — | — |
| Expectancy por trade | -0.21 | — | — | — |
| Trades / duración media | 13 / 85.8 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +1.63 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 8.55 / 5.8 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 9,996.41 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.00 % | -0.00 % | 0 | 0.00 |
| 2020 | +0.00 % | -0.00 % | 0 | 0.00 |
| 2021 | -0.33 % | +1.47 % | 10 | -32.41 |
| 2022 | +0.00 % | +0.46 % | 0 | 0.00 |
| 2023 | +0.11 % | +0.63 % | 2 | 10.93 |
| 2024 | +0.19 % | +0.46 % | 1 | 18.76 |
| 2025 | +0.00 % | +0.29 % | 0 | 0.00 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 1 | 3.86 | +100.00 % |
| BNB/USDT | 2 | 57.20 | +50.00 % |
| ETH/USDT | 2 | -1.35 | +50.00 % |
| LINK/USDT | 1 | -23.37 | +0.00 % |
| LTC/USDT | 2 | 4.01 | +50.00 % |
| SOL/USDT | 3 | -17.52 | +33.33 % |
| XRP/USDT | 2 | -25.54 | +0.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| stop | 1 |
| trailing | 12 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 10 |
| entry_rejected:max_positions | 5 |
| entry_rejected:prediction_missing | 743 |
| entry_rejected:prediction_veto | 2319 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| SOL/USDT | 2021-03-22 12:00 @ 16.41 | 2021-03-22 23:59 @ 14.95 | stop | -25.53 | -9.09 % |
| LINK/USDT | 2021-03-09 00:00 @ 31.839 | 2021-03-11 03:59 @ 28.758 | trailing | -23.37 | -9.87 % |
| SOL/USDT | 2021-03-11 20:00 @ 15.74 | 2021-03-12 23:59 @ 14.26 | trailing | -20.90 | -9.59 % |
| BNB/USDT | 2023-04-11 04:00 @ 327.57 | 2023-04-11 23:59 @ 322.59 | trailing | -17.97 | -1.72 % |
| ETH/USDT | 2021-03-10 00:00 @ 1871.44 | 2021-03-15 07:59 @ 1772.49 | trailing | -16.06 | -5.48 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BNB/USDT | 2021-03-28 04:00 @ 278.13 | 2021-04-07 11:59 @ 356.50 | trailing | 75.17 | +27.95 % |
| SOL/USDT | 2023-04-11 08:00 @ 22.49 | 2023-04-19 11:59 @ 23.94 | trailing | 28.90 | +6.24 % |
| LTC/USDT | 2024-03-26 20:00 @ 95.19 | 2024-04-01 15:59 @ 101.13 | trailing | 18.76 | +6.03 % |
| ETH/USDT | 2021-03-31 20:00 @ 1901.59 | 2021-04-04 03:59 @ 1981.14 | trailing | 14.71 | +3.98 % |
| ADA/USDT | 2021-03-16 20:00 @ 1.2269 | 2021-03-18 19:59 @ 1.2546 | trailing | 3.86 | +2.06 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (ML v1 no promovible; Gate 1 incompleto)
- **Por qué**: Cobertura histórica incompleta y solo 3–5 cierres en cuatro años OOS. La comparación incremental falla. No abrir holdout ni reducir umbral para rescatar resultados.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
