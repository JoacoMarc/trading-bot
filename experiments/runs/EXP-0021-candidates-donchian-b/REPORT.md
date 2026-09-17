# EXP-0021 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params c8d4a6af5b, datos 40a0aa8573b9, 2.2 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_mult` | `3.0` |
| `entry_period` | `60` |
| `exit_period` | `20` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +90.63 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | +11.18 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | 1.28 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | 2.25 | 1.37 | 1.35 | 1.82 |
| Calmar | 1.26 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +8.87 % / 776 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 1.92 | — | — | — |
| Win rate | +38.92 % | — | — | — |
| Expectancy por trade | 27.25 | — | — | — |
| Trades / duración media | 334 / 100.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +29.05 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 789.60 / 5.7 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 19,063.06 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.03 % | +3.89 % | 9 | -3.19 |
| 2020 | +16.77 % | +5.05 % | 59 | 1,515.64 |
| 2021 | +18.79 % | +4.89 % | 80 | 2,366.06 |
| 2022 | +0.00 % | +4.78 % | 0 | 0.00 |
| 2023 | +19.38 % | +7.34 % | 70 | 2,691.66 |
| 2024 | +9.44 % | +6.84 % | 71 | 1,574.03 |
| 2025 | +5.23 % | +8.87 % | 45 | 957.42 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 39 | 347.38 | +38.46 % |
| BNB/USDT | 38 | 1,132.16 | +39.47 % |
| BTC/USDT | 60 | 827.34 | +33.33 % |
| ETH/USDT | 49 | 2,119.31 | +44.90 % |
| LINK/USDT | 47 | 831.63 | +31.91 % |
| LTC/USDT | 33 | -264.88 | +30.30 % |
| SOL/USDT | 40 | 1,509.89 | +47.50 % |
| XRP/USDT | 28 | 2,598.79 | +50.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 10 |
| stop | 21 |
| trailing | 303 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 888 |
| entry_rejected:max_positions | 455 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2025-06-29 12:00 @ 108531.36 | 2025-07-01 11:59 @ 106268.78 | trailing | -97.17 | -2.28 % |
| BTC/USDT | 2025-05-19 00:00 @ 106507.50 | 2025-05-19 07:59 @ 102947.63 | stop | -96.76 | -3.54 % |
| BNB/USDT | 2025-04-23 00:00 @ 618.81 | 2025-04-23 23:59 @ 601.27 | stop | -96.43 | -3.03 % |
| BTC/USDT | 2025-01-19 20:00 @ 106253.10 | 2025-01-19 23:59 @ 101557.22 | stop | -95.43 | -4.62 % |
| BTC/USDT | 2024-12-05 04:00 @ 103015.49 | 2024-12-05 23:59 @ 97838.95 | trailing | -95.34 | -5.22 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LINK/USDT | 2023-10-21 08:00 @ 7.844 | 2023-11-13 23:59 @ 14.423 | trailing | 1,202.70 | +83.59 % |
| XRP/USDT | 2025-07-07 16:00 @ 2.3400 | 2025-07-23 15:59 @ 3.3521 | trailing | 886.54 | +43.01 % |
| XRP/USDT | 2024-11-12 12:00 @ 0.6476 | 2024-11-24 15:59 @ 1.3167 | trailing | 818.37 | +103.02 % |
| ETH/USDT | 2025-07-09 16:00 @ 2658.17 | 2025-07-23 19:59 @ 3571.46 | trailing | 679.39 | +34.12 % |
| SOL/USDT | 2023-10-19 16:00 @ 24.79 | 2023-11-02 19:59 @ 38.98 | trailing | 661.86 | +56.98 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: iterar (investigación; no autorizado para paper)
- **Por qué**: El perfil B está limitado a backtest por el protocolo. El resultado base supera criterios previos al holdout, pero no se evaluó holdout y no se reemplaza A por B mirando resultados.
- **Qué se aprendió**: Es la alternativa nueva con mejor combinación de actividad y resultados históricos; cambia tamaño y número de posiciones respecto de A. No constituye aprobación de Gate 1 completo.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
