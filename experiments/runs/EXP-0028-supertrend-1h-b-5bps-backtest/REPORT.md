# EXP-0028 — supertrend 1h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 9.4 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +9.69 % | +972.20 % | +1246.97 % | +796.12 % |
| CAGR | +1.53 % | +47.67 % | +53.31 % | +43.38 % |
| Sharpe (diario) | 0.18 | 0.93 | 0.95 | 1.15 |
| Sortino (diario) | 0.34 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.05 | 0.62 | 0.66 | 1.07 |
| Max drawdown / mayor tramo bajo agua | +32.47 % / 1608 d | +77.20 % / 846 d | +81.07 % / 1390 d | +40.66 % / 711 d |
| Profit factor | 1.04 | — | — | — |
| Win rate | +33.51 % | — | — | — |
| Expectancy por trade | 0.97 | — | — | — |
| Trades / duración media | 1119 / 25.8 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +25.40 % | +100.00 % | +100.00 % | +43.42 % |
| Fees pagados / shortfall medio | 3,851.47 / 5.8 bps | 10.00 / 5.0 bps | 10.00 / 6.5 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 00:59 → 2025-08-31 23:59 UTC (2223 días, 53308 velas). Equity inicial 10,000.00 → final 10,968.67 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -1.56 % | +5.50 % | 36 | -155.52 |
| 2020 | +21.57 % | +8.14 % | 227 | 2,128.73 |
| 2021 | +14.56 % | +8.64 % | 214 | 1,768.14 |
| 2022 | +0.00 % | +5.48 % | 0 | 0.00 |
| 2023 | -11.13 % | +18.64 % | 257 | -1,507.01 |
| 2024 | -9.10 % | +23.66 % | 212 | -1,078.10 |
| 2025 | -0.96 % | +32.47 % | 173 | -73.18 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 158 | -118.79 | +32.91 % |
| BNB/USDT | 151 | 617.17 | +31.79 % |
| BTC/USDT | 149 | -425.49 | +31.54 % |
| ETH/USDT | 161 | 1,226.35 | +35.40 % |
| LINK/USDT | 155 | 141.33 | +34.84 % |
| LTC/USDT | 139 | -1,173.73 | +33.09 % |
| SOL/USDT | 96 | 729.78 | +35.42 % |
| XRP/USDT | 110 | 86.45 | +33.64 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| stop | 75 |
| trailing | 1044 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 63 |
| entry_rejected:market_filter | 2605 |
| entry_rejected:max_positions | 658 |
| protection_cleared:daily_loss_limit | 3 |
| protection_cleared:drawdown_halt | 1 |
| protection_cleared:market_filter | 59 |
| protection_triggered:daily_loss_limit | 3 |
| protection_triggered:drawdown_halt | 1 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2021-05-10 04:00 @ 59386.45 | 2021-05-10 10:59 @ 57594.78 | trailing | -76.10 | -3.21 % |
| BNB/USDT | 2021-09-19 17:00 @ 417.61 | 2021-09-19 22:59 @ 406.36 | stop | -74.68 | -2.89 % |
| BNB/USDT | 2021-08-17 12:00 @ 432.79 | 2021-08-17 19:59 @ 413.95 | stop | -74.02 | -4.55 % |
| BTC/USDT | 2021-04-12 07:00 @ 60860.10 | 2021-04-12 10:59 @ 59359.83 | trailing | -73.95 | -2.66 % |
| LTC/USDT | 2021-09-15 22:00 @ 191.20 | 2021-09-16 20:59 @ 183.46 | stop | -73.86 | -4.24 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BNB/USDT | 2021-02-17 11:00 @ 136.72 | 2021-02-20 01:59 @ 273.01 | trailing | 1,187.32 | +99.39 % |
| XRP/USDT | 2021-04-04 23:00 @ 0.6270 | 2021-04-07 09:59 @ 0.9147 | trailing | 598.50 | +45.64 % |
| ADA/USDT | 2020-05-27 06:00 @ 0.0554 | 2020-05-31 14:59 @ 0.0777 | trailing | 558.97 | +40.01 % |
| XRP/USDT | 2020-11-19 13:00 @ 0.2970 | 2020-11-22 01:59 @ 0.4095 | trailing | 525.18 | +37.64 % |
| BTC/USDT | 2024-02-26 15:00 @ 51712.88 | 2024-02-28 17:59 @ 60128.26 | trailing | 487.33 | +16.06 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
