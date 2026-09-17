# EXP-0022 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
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
| Retorno total | +86.00 % | +971.66 % | +1259.71 % | +744.80 % |
| CAGR | +10.73 % | +47.65 % | +53.54 % | +41.99 % |
| Sharpe (diario) | 1.23 | 0.93 | 0.96 | 1.13 |
| Sortino (diario) | 2.15 | 1.37 | 1.35 | 1.78 |
| Calmar | 1.17 | 0.62 | 0.66 | 1.07 |
| Max drawdown / mayor tramo bajo agua | +9.19 % / 776 d | +77.04 % / 851 d | +81.19 % / 1390 d | +39.43 % / 717 d |
| Profit factor | 1.87 | — | — | — |
| Win rate | +38.92 % | — | — | — |
| Expectancy por trade | 25.87 | — | — | — |
| Trades / duración media | 334 / 100.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +29.05 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 778.84 / 10.7 bps | 10.00 / 10.0 bps | 10.00 / 13.0 bps | 4,435.50 / 10.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 18,599.68 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.14 % | +3.93 % | 9 | -13.52 |
| 2020 | +16.25 % | +5.10 % | 59 | 1,463.32 |
| 2021 | +18.34 % | +4.99 % | 80 | 2,300.22 |
| 2022 | +0.00 % | +4.91 % | 0 | 0.00 |
| 2023 | +18.71 % | +7.76 % | 70 | 2,574.60 |
| 2024 | +8.85 % | +7.12 % | 71 | 1,454.94 |
| 2025 | +4.78 % | +9.19 % | 45 | 859.47 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 39 | 313.47 | +38.46 % |
| BNB/USDT | 38 | 1,075.30 | +39.47 % |
| BTC/USDT | 60 | 734.32 | +33.33 % |
| ETH/USDT | 49 | 2,031.41 | +44.90 % |
| LINK/USDT | 47 | 782.33 | +31.91 % |
| LTC/USDT | 33 | -285.65 | +30.30 % |
| SOL/USDT | 40 | 1,458.46 | +47.50 % |
| XRP/USDT | 28 | 2,529.39 | +50.00 % |

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
| BTC/USDT | 2025-06-29 12:00 @ 108585.60 | 2025-07-01 11:59 @ 106269.81 | trailing | -97.05 | -2.33 % |
| BTC/USDT | 2025-05-19 00:00 @ 106560.73 | 2025-05-19 07:59 @ 102949.30 | stop | -95.99 | -3.59 % |
| BNB/USDT | 2025-04-23 00:00 @ 619.12 | 2025-04-23 23:59 @ 601.28 | stop | -95.93 | -3.08 % |
| BTC/USDT | 2025-01-19 20:00 @ 106306.20 | 2025-01-19 23:59 @ 101559.46 | stop | -94.44 | -4.66 % |
| BTC/USDT | 2024-12-05 04:00 @ 103066.97 | 2024-12-05 23:59 @ 97841.44 | trailing | -94.31 | -5.27 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LINK/USDT | 2023-10-21 08:00 @ 7.848 | 2023-11-13 23:59 @ 14.416 | trailing | 1,185.23 | +83.41 % |
| XRP/USDT | 2025-07-07 16:00 @ 2.3412 | 2025-07-23 15:59 @ 3.3504 | trailing | 863.72 | +42.86 % |
| XRP/USDT | 2024-11-12 12:00 @ 0.6479 | 2024-11-24 15:59 @ 1.3160 | trailing | 801.36 | +102.81 % |
| ETH/USDT | 2025-07-09 16:00 @ 2659.50 | 2025-07-23 19:59 @ 3569.67 | trailing | 661.41 | +33.99 % |
| SOL/USDT | 2023-10-19 16:00 @ 24.80 | 2023-11-02 19:59 @ 38.96 | trailing | 652.01 | +56.84 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: iterar (investigación; no autorizado para paper)
- **Por qué**: El perfil B está limitado a backtest por el protocolo. El resultado base supera criterios previos al holdout, pero no se evaluó holdout y no se reemplaza A por B mirando resultados.
- **Qué se aprendió**: Es la alternativa nueva con mejor combinación de actividad y resultados históricos; cambia tamaño y número de posiciones respecto de A. No constituye aprobación de Gate 1 completo.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
