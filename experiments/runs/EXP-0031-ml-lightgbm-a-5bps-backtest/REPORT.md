# EXP-0031 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash e61213fad5d5; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos e61213fad5d5, 2.4 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +0.98 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | +0.16 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | 0.20 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | 0.31 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.16 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +1.03 % / 1574 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 1.83 | — | — | — |
| Win rate | +40.00 % | — | — | — |
| Expectancy por trade | 6.67 | — | — | — |
| Trades / duración media | 15 / 113.3 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +2.07 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 8.22 / 5.4 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 10,098.44 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.00 % | -0.00 % | 0 | 0.00 |
| 2020 | +0.00 % | -0.00 % | 0 | 0.00 |
| 2021 | +0.98 % | +1.03 % | 15 | 100.08 |
| 2022 | +0.00 % | +0.71 % | 0 | 0.00 |
| 2023 | +0.00 % | +0.71 % | 0 | 0.00 |
| 2024 | +0.00 % | +0.71 % | 0 | 0.00 |
| 2025 | +0.00 % | +0.71 % | 0 | 0.00 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BNB/USDT | 2 | 31.69 | +50.00 % |
| BTC/USDT | 3 | -35.84 | +0.00 % |
| ETH/USDT | 2 | 8.47 | +50.00 % |
| LINK/USDT | 1 | -17.52 | +0.00 % |
| LTC/USDT | 3 | -7.83 | +33.33 % |
| SOL/USDT | 3 | 68.78 | +66.67 % |
| XRP/USDT | 1 | 52.32 | +100.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| trailing | 15 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 25 |
| entry_rejected:max_positions | 19 |
| entry_rejected:prediction_missing | 743 |
| entry_rejected:prediction_veto | 2257 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2021-04-02 04:00 @ 59899.73 | 2021-04-03 23:59 @ 57062.72 | trailing | -21.33 | -4.93 % |
| ETH/USDT | 2021-11-03 00:00 @ 4591.98 | 2021-11-06 11:59 @ 4380.62 | trailing | -19.06 | -4.80 % |
| LINK/USDT | 2021-04-15 00:00 @ 41.358 | 2021-04-18 03:59 @ 37.913 | trailing | -17.52 | -8.52 % |
| LTC/USDT | 2021-04-16 20:00 @ 311.88 | 2021-04-18 03:59 @ 282.35 | trailing | -17.26 | -9.66 % |
| BTC/USDT | 2021-02-06 04:00 @ 39406.62 | 2021-02-07 15:59 @ 37752.97 | trailing | -13.97 | -4.39 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| SOL/USDT | 2021-04-18 20:00 @ 30.22 | 2021-05-04 03:59 @ 43.82 | trailing | 56.55 | +44.76 % |
| XRP/USDT | 2021-04-05 04:00 @ 0.6817 | 2021-04-07 15:59 @ 0.8566 | trailing | 52.32 | +25.43 % |
| BNB/USDT | 2021-04-08 16:00 @ 418.42 | 2021-04-16 03:59 @ 523.78 | trailing | 44.69 | +24.96 % |
| ETH/USDT | 2021-05-04 00:00 @ 3432.76 | 2021-05-10 23:59 @ 3742.45 | trailing | 27.53 | +8.81 % |
| LTC/USDT | 2021-05-04 12:00 @ 317.62 | 2021-05-10 23:59 @ 350.52 | trailing | 20.69 | +10.15 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (ML v1 no promovible; Gate 1 incompleto)
- **Por qué**: Cobertura histórica incompleta y solo 3–5 cierres en cuatro años OOS. La comparación incremental falla. No abrir holdout ni reducir umbral para rescatar resultados.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
