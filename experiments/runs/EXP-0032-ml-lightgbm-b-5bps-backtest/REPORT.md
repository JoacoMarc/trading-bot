# EXP-0032 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash e61213fad5d5; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git af1b65f, params c8d4a6af5b, datos e61213fad5d5, 2.6 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +2.19 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | +0.36 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | 0.17 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | 0.25 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.12 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +3.01 % / 1574 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 1.57 | — | — | — |
| Win rate | +35.00 % | — | — | — |
| Expectancy por trade | 11.09 | — | — | — |
| Trades / duración media | 20 / 105.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +2.13 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 22.52 / 5.4 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 10,218.82 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.00 % | -0.00 % | 0 | 0.00 |
| 2020 | +0.00 % | -0.00 % | 0 | 0.00 |
| 2021 | +2.19 % | +3.01 % | 20 | 221.88 |
| 2022 | +0.00 % | +2.48 % | 0 | 0.00 |
| 2023 | +0.00 % | +2.48 % | 0 | 0.00 |
| 2024 | +0.00 % | +2.48 % | 0 | 0.00 |
| 2025 | +0.00 % | +2.48 % | 0 | 0.00 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 1 | -50.31 | +0.00 % |
| BNB/USDT | 2 | 63.71 | +50.00 % |
| BTC/USDT | 3 | -71.67 | +0.00 % |
| ETH/USDT | 3 | -9.61 | +33.33 % |
| LINK/USDT | 1 | -35.91 | +0.00 % |
| LTC/USDT | 4 | -41.01 | +25.00 % |
| SOL/USDT | 3 | 139.80 | +66.67 % |
| XRP/USDT | 3 | 226.89 | +66.67 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| trailing | 20 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 25 |
| entry_rejected:max_positions | 11 |
| entry_rejected:prediction_missing | 743 |
| entry_rejected:prediction_veto | 2249 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ADA/USDT | 2021-05-09 16:00 @ 1.7927 | 2021-05-10 23:59 @ 1.5418 | trailing | -50.31 | -14.18 % |
| XRP/USDT | 2021-11-03 08:00 @ 1.2022 | 2021-11-06 11:59 @ 1.1285 | trailing | -42.81 | -6.32 % |
| BTC/USDT | 2021-04-02 04:00 @ 59899.73 | 2021-04-03 23:59 @ 57062.72 | trailing | -42.63 | -4.93 % |
| ETH/USDT | 2021-11-03 00:00 @ 4591.98 | 2021-11-06 11:59 @ 4380.62 | trailing | -38.85 | -4.80 % |
| LINK/USDT | 2021-04-15 00:00 @ 41.358 | 2021-04-18 03:59 @ 37.913 | trailing | -35.91 | -8.52 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| XRP/USDT | 2021-04-03 04:00 @ 0.6236 | 2021-04-07 15:59 @ 0.8566 | trailing | 178.04 | +37.13 % |
| SOL/USDT | 2021-04-18 20:00 @ 30.22 | 2021-05-04 03:59 @ 43.82 | trailing | 114.65 | +44.76 % |
| XRP/USDT | 2021-04-10 08:00 @ 1.1506 | 2021-04-16 11:59 @ 1.5472 | trailing | 91.66 | +34.23 % |
| BNB/USDT | 2021-04-08 16:00 @ 418.42 | 2021-04-16 03:59 @ 523.78 | trailing | 89.80 | +24.96 % |
| ETH/USDT | 2021-05-04 00:00 @ 3432.76 | 2021-05-10 23:59 @ 3742.45 | trailing | 56.18 | +8.81 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (ML v1 no promovible; Gate 1 incompleto)
- **Por qué**: Cobertura histórica incompleta y solo 3–5 cierres en cuatro años OOS. La comparación incremental falla. No abrir holdout ni reducir umbral para rescatar resultados.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
