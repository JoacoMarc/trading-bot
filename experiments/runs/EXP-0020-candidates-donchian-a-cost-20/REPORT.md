# EXP-0020 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params c8d4a6af5b, datos 40a0aa8573b9, 2.2 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +17.86 % | +970.60 % | +1258.53 % | +650.76 % |
| CAGR | +2.74 % | +47.63 % | +53.52 % | +39.27 % |
| Sharpe (diario) | 0.87 | 0.93 | 0.96 | 1.07 |
| Sortino (diario) | 1.49 | 1.37 | 1.35 | 1.69 |
| Calmar | 0.46 | 0.62 | 0.66 | 0.97 |
| Max drawdown / mayor tramo bajo agua | +5.97 % / 784 d | +77.04 % / 851 d | +81.19 % / 1390 d | +40.63 % / 729 d |
| Profit factor | 1.57 | — | — | — |
| Win rate | +36.47 % | — | — | — |
| Expectancy por trade | 7.13 | — | — | — |
| Trades / duración media | 255 / 98.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +28.02 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 230.08 / 20.7 bps | 10.00 / 20.0 bps | 10.00 / 21.7 bps | 4,090.08 / 20.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 11,786.48 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.30 % | +1.59 % | 8 | -30.19 |
| 2020 | +6.58 % | +2.03 % | 41 | 599.16 |
| 2021 | +6.49 % | +1.95 % | 62 | 756.28 |
| 2022 | +0.00 % | +1.88 % | 0 | 0.00 |
| 2023 | +5.06 % | +3.35 % | 53 | 576.57 |
| 2024 | +0.17 % | +3.67 % | 55 | 29.48 |
| 2025 | -1.03 % | +5.97 % | 36 | -113.48 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 27 | 257.54 | +40.74 % |
| BNB/USDT | 33 | 477.44 | +42.42 % |
| BTC/USDT | 50 | 194.79 | +36.00 % |
| ETH/USDT | 34 | 195.43 | +35.29 % |
| LINK/USDT | 40 | -241.60 | +25.00 % |
| LTC/USDT | 21 | 33.08 | +33.33 % |
| SOL/USDT | 30 | 395.10 | +43.33 % |
| XRP/USDT | 20 | 506.03 | +40.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 7 |
| stop | 18 |
| trailing | 230 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 894 |
| entry_rejected:max_positions | 663 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2025-06-29 12:00 @ 108694.08 | 2025-07-01 11:59 @ 106271.70 | trailing | -34.00 | -2.43 % |
| BNB/USDT | 2025-04-23 00:00 @ 619.74 | 2025-04-23 19:59 @ 601.30 | stop | -33.62 | -3.17 % |
| BNB/USDT | 2024-07-21 16:00 @ 600.30 | 2024-07-23 07:59 @ 577.09 | trailing | -32.78 | -4.06 % |
| BTC/USDT | 2025-05-19 00:00 @ 106667.18 | 2025-05-19 07:59 @ 102952.49 | stop | -32.77 | -3.68 % |
| BTC/USDT | 2025-01-19 20:00 @ 106412.40 | 2025-01-19 23:59 @ 101563.79 | stop | -32.36 | -4.75 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| XRP/USDT | 2025-07-07 16:00 @ 2.3435 | 2025-07-23 15:59 @ 3.3471 | trailing | 293.78 | +42.58 % |
| SOL/USDT | 2023-10-19 16:00 @ 24.82 | 2023-11-02 19:59 @ 38.92 | trailing | 266.52 | +56.55 % |
| ADA/USDT | 2021-02-02 00:00 @ 0.4097 | 2021-02-14 15:59 @ 0.8084 | trailing | 200.45 | +97.02 % |
| ETH/USDT | 2024-02-12 16:00 @ 2562.99 | 2024-02-28 19:59 @ 3169.98 | trailing | 185.01 | +23.46 % |
| XRP/USDT | 2023-10-20 00:00 @ 0.5208 | 2023-11-07 03:59 @ 0.6650 | trailing | 178.57 | +27.46 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: El perfil moderado no alcanza el Sharpe OOS mínimo del protocolo (WF-0012 y costos adversos). El beneficio continuo no basta para aprobar. Sin paper ni holdout.
- **Qué se aprendió**: La meseta positiva y la caída acotada no compensan el incumplimiento del criterio OOS.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
