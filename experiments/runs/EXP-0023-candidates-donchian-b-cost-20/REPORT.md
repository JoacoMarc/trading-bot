# EXP-0023 — donchian 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `donchian` · spec: `docs/strategy/donchian-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
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
| Retorno total | +74.61 % | +970.60 % | +1258.53 % | +650.76 % |
| CAGR | +9.59 % | +47.63 % | +53.52 % | +39.27 % |
| Sharpe (diario) | 1.11 | 0.93 | 0.96 | 1.07 |
| Sortino (diario) | 1.90 | 1.37 | 1.35 | 1.69 |
| Calmar | 0.93 | 0.62 | 0.66 | 0.97 |
| Max drawdown / mayor tramo bajo agua | +10.37 % / 777 d | +77.04 % / 851 d | +81.19 % / 1390 d | +40.63 % / 729 d |
| Profit factor | 1.74 | — | — | — |
| Win rate | +38.10 % | — | — | — |
| Expectancy por trade | 22.32 | — | — | — |
| Trades / duración media | 336 / 99.4 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +28.96 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 756.86 / 20.7 bps | 10.00 / 20.0 bps | 10.00 / 21.7 bps | 4,090.08 / 20.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 17,461.46 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.23 % | +3.97 % | 9 | -22.34 |
| 2020 | +15.21 % | +5.21 % | 59 | 1,362.27 |
| 2021 | +16.38 % | +5.18 % | 81 | 2,050.22 |
| 2022 | +0.00 % | +5.15 % | 0 | 0.00 |
| 2023 | +17.39 % | +8.58 % | 70 | 2,331.39 |
| 2024 | +7.68 % | +7.67 % | 71 | 1,217.64 |
| 2025 | +3.25 % | +10.37 % | 46 | 561.54 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 39 | 261.30 | +38.46 % |
| BNB/USDT | 38 | 965.76 | +39.47 % |
| BTC/USDT | 60 | 544.40 | +33.33 % |
| ETH/USDT | 50 | 1,727.96 | +42.00 % |
| LINK/USDT | 47 | 680.42 | +29.79 % |
| LTC/USDT | 33 | -322.60 | +30.30 % |
| SOL/USDT | 41 | 1,262.92 | +46.34 % |
| XRP/USDT | 28 | 2,380.56 | +50.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 10 |
| stop | 22 |
| trailing | 304 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 889 |
| entry_rejected:max_positions | 454 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2025-06-29 12:00 @ 108694.08 | 2025-07-01 11:59 @ 106271.70 | trailing | -95.98 | -2.43 % |
| BNB/USDT | 2025-04-23 00:00 @ 619.74 | 2025-04-23 19:59 @ 601.30 | stop | -94.18 | -3.17 % |
| BTC/USDT | 2025-05-19 00:00 @ 106667.18 | 2025-05-19 07:59 @ 102952.49 | stop | -93.64 | -3.68 % |
| BTC/USDT | 2025-01-19 20:00 @ 106412.40 | 2025-01-19 23:59 @ 101563.79 | stop | -91.78 | -4.75 % |
| BTC/USDT | 2024-12-05 04:00 @ 103169.93 | 2024-12-05 23:59 @ 97846.25 | trailing | -91.55 | -5.36 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LINK/USDT | 2023-10-21 08:00 @ 7.856 | 2023-11-13 23:59 @ 14.402 | trailing | 1,142.24 | +83.04 % |
| XRP/USDT | 2025-07-07 16:00 @ 2.3435 | 2025-07-23 15:59 @ 3.3471 | trailing | 808.50 | +42.58 % |
| XRP/USDT | 2024-11-12 12:00 @ 0.6485 | 2024-11-24 15:59 @ 1.3147 | trailing | 762.54 | +102.43 % |
| SOL/USDT | 2023-10-19 16:00 @ 24.82 | 2023-11-02 19:59 @ 38.92 | trailing | 627.88 | +56.55 % |
| ETH/USDT | 2025-07-09 16:00 @ 2662.16 | 2025-07-23 19:59 @ 3566.10 | trailing | 618.25 | +33.72 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: iterar (investigación; no autorizado para paper)
- **Por qué**: El perfil B está limitado a backtest por el protocolo. El resultado base supera criterios previos al holdout, pero no se evaluó holdout y no se reemplaza A por B mirando resultados.
- **Qué se aprendió**: Es la alternativa nueva con mejor combinación de actividad y resultados históricos; cambia tamaño y número de posiciones respecto de A. No constituye aprobación de Gate 1 completo.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
