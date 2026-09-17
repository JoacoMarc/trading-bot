# EXP-0018 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
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
| Retorno total | +21.88 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | +3.30 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | 1.05 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | 1.85 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.64 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +5.18 % / 777 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 1.74 | — | — | — |
| Win rate | +37.40 % | — | — | — |
| Expectancy por trade | 8.73 | — | — | — |
| Trades / duración media | 254 / 98.9 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +28.04 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 234.01 / 5.7 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 12,187.62 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.23 % | +1.56 % | 8 | -22.55 |
| 2020 | +7.09 % | +1.96 % | 41 | 648.66 |
| 2021 | +7.56 % | +1.87 % | 61 | 875.05 |
| 2022 | +0.00 % | +1.74 % | 0 | 0.00 |
| 2023 | +5.73 % | +2.86 % | 53 | 662.13 |
| 2024 | +0.82 % | +3.32 % | 55 | 108.18 |
| 2025 | -0.51 % | +5.18 % | 36 | -53.91 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 27 | 282.86 | +40.74 % |
| BNB/USDT | 33 | 533.23 | +42.42 % |
| BTC/USDT | 50 | 281.79 | +36.00 % |
| ETH/USDT | 34 | 299.95 | +38.24 % |
| LINK/USDT | 39 | -203.98 | +28.21 % |
| LTC/USDT | 21 | 52.70 | +33.33 % |
| SOL/USDT | 30 | 429.06 | +43.33 % |
| XRP/USDT | 20 | 541.96 | +40.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 7 |
| stop | 17 |
| trailing | 230 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 894 |
| entry_rejected:max_positions | 662 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BNB/USDT | 2025-04-23 00:00 @ 618.81 | 2025-04-23 23:59 @ 601.27 | stop | -33.02 | -3.03 % |
| BTC/USDT | 2025-06-29 12:00 @ 108531.36 | 2025-07-01 11:59 @ 106268.78 | trailing | -32.93 | -2.28 % |
| BTC/USDT | 2025-05-19 00:00 @ 106507.50 | 2025-05-19 07:59 @ 102947.63 | stop | -32.42 | -3.54 % |
| BTC/USDT | 2025-01-19 20:00 @ 106253.10 | 2025-01-19 23:59 @ 101557.22 | stop | -32.27 | -4.62 % |
| BTC/USDT | 2024-12-05 04:00 @ 103015.49 | 2024-12-05 23:59 @ 97838.95 | trailing | -31.78 | -5.22 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| XRP/USDT | 2025-07-07 16:00 @ 2.3400 | 2025-07-23 15:59 @ 3.3521 | trailing | 305.75 | +43.01 % |
| SOL/USDT | 2023-10-19 16:00 @ 24.79 | 2023-11-02 19:59 @ 38.98 | trailing | 273.48 | +56.98 % |
| ADA/USDT | 2021-02-02 00:00 @ 0.4091 | 2021-02-14 15:59 @ 0.8096 | trailing | 202.56 | +97.60 % |
| ETH/USDT | 2024-02-12 16:00 @ 2559.15 | 2024-02-28 19:59 @ 3174.75 | trailing | 191.92 | +23.83 % |
| XRP/USDT | 2023-10-20 00:00 @ 0.5200 | 2023-11-07 03:59 @ 0.6660 | trailing | 184.36 | +27.85 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: El perfil moderado no alcanza el Sharpe OOS mínimo del protocolo (WF-0012 y costos adversos). El beneficio continuo no basta para aprobar. Sin paper ni holdout.
- **Qué se aprendió**: La meseta positiva y la caída acotada no compensan el incumplimiento del criterio OOS.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
