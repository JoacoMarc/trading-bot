# EXP-0019 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params c8d4a6af5b, datos 40a0aa8573b9, 2.1 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +20.75 % | +971.66 % | +1259.71 % | +744.80 % |
| CAGR | +3.15 % | +47.65 % | +53.54 % | +41.99 % |
| Sharpe (diario) | 1.00 | 0.93 | 0.96 | 1.13 |
| Sortino (diario) | 1.75 | 1.37 | 1.35 | 1.78 |
| Calmar | 0.58 | 0.62 | 0.66 | 1.07 |
| Max drawdown / mayor tramo bajo agua | +5.44 % / 779 d | +77.04 % / 851 d | +81.19 % / 1390 d | +39.43 % / 717 d |
| Profit factor | 1.69 | — | — | — |
| Win rate | +37.40 % | — | — | — |
| Expectancy por trade | 8.29 | — | — | — |
| Trades / duración media | 254 / 98.8 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +28.04 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 232.90 / 10.7 bps | 10.00 / 10.0 bps | 10.00 / 13.0 bps | 4,435.50 / 10.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 12,074.64 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.26 % | +1.57 % | 8 | -25.76 |
| 2020 | +6.92 % | +1.98 % | 41 | 632.14 |
| 2021 | +7.41 % | +1.89 % | 61 | 857.02 |
| 2022 | +0.00 % | +1.78 % | 0 | 0.00 |
| 2023 | +5.50 % | +3.02 % | 53 | 634.24 |
| 2024 | +0.60 % | +3.44 % | 55 | 81.56 |
| 2025 | -0.69 % | +5.44 % | 36 | -74.48 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 27 | 274.04 | +40.74 % |
| BNB/USDT | 33 | 514.58 | +42.42 % |
| BTC/USDT | 50 | 252.35 | +36.00 % |
| ETH/USDT | 34 | 284.43 | +38.24 % |
| LINK/USDT | 39 | -215.12 | +28.21 % |
| LTC/USDT | 21 | 46.03 | +33.33 % |
| SOL/USDT | 30 | 418.24 | +43.33 % |
| XRP/USDT | 20 | 530.17 | +40.00 % |

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
| BTC/USDT | 2025-06-29 12:00 @ 108585.60 | 2025-07-01 11:59 @ 106269.81 | trailing | -33.36 | -2.33 % |
| BNB/USDT | 2025-04-23 00:00 @ 619.12 | 2025-04-23 23:59 @ 601.28 | stop | -33.28 | -3.08 % |
| BTC/USDT | 2025-05-19 00:00 @ 106560.73 | 2025-05-19 07:59 @ 102949.30 | stop | -32.59 | -3.59 % |
| BTC/USDT | 2025-01-19 20:00 @ 106306.20 | 2025-01-19 23:59 @ 101559.46 | stop | -32.35 | -4.66 % |
| BTC/USDT | 2024-12-05 04:00 @ 103066.97 | 2024-12-05 23:59 @ 97841.44 | trailing | -31.85 | -5.27 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| XRP/USDT | 2025-07-07 16:00 @ 2.3412 | 2025-07-23 15:59 @ 3.3504 | trailing | 302.16 | +42.86 % |
| SOL/USDT | 2023-10-19 16:00 @ 24.80 | 2023-11-02 19:59 @ 38.96 | trailing | 271.65 | +56.84 % |
| ADA/USDT | 2021-02-02 00:00 @ 0.4093 | 2021-02-14 15:59 @ 0.8092 | trailing | 201.85 | +97.41 % |
| ETH/USDT | 2024-02-12 16:00 @ 2560.43 | 2024-02-28 19:59 @ 3173.16 | trailing | 189.93 | +23.71 % |
| XRP/USDT | 2023-10-20 00:00 @ 0.5203 | 2023-11-07 03:59 @ 0.6656 | trailing | 182.62 | +27.70 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: El perfil moderado no alcanza el Sharpe OOS mínimo del protocolo (WF-0012 y costos adversos). El beneficio continuo no basta para aprobar. Sin paper ni holdout.
- **Qué se aprendió**: La meseta positiva y la caída acotada no compensan el incumplimiento del criterio OOS.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
