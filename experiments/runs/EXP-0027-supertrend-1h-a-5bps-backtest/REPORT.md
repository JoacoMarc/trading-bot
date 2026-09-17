# EXP-0027 — supertrend 1h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `supertrend` · spec: `docs/strategy/supertrend-v1.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 4848 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 07f2965aa468; activación tardía: LINK/USDT desde 2019-08-07, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git d4576bd, params 9f823b9a22, datos 07f2965aa468, 10.8 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `atr_period` | `10` |
| `bars_per_day` | `24` |
| `multiplier` | `3.0` |
| `stop_atr_mult` | `3.0` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +15.20 % | +972.20 % | +1246.97 % | +796.12 % |
| CAGR | +2.35 % | +47.67 % | +53.31 % | +43.38 % |
| Sharpe (diario) | 0.45 | 0.93 | 0.95 | 1.15 |
| Sortino (diario) | 0.90 | 1.37 | 1.35 | 1.82 |
| Calmar | 0.22 | 0.62 | 0.66 | 1.07 |
| Max drawdown / mayor tramo bajo agua | +10.73 % / 939 d | +77.20 % / 846 d | +81.07 % / 1390 d | +40.66 % / 711 d |
| Profit factor | 1.15 | — | — | — |
| Win rate | +34.50 % | — | — | — |
| Expectancy por trade | 1.89 | — | — | — |
| Trades / duración media | 855 / 25.9 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +25.06 % | +100.00 % | +100.00 % | +43.42 % |
| Fees pagados / shortfall medio | 1,637.11 / 5.9 bps | 10.00 / 5.0 bps | 10.00 / 6.5 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 00:59 → 2025-08-31 23:59 UTC (2223 días, 53308 velas). Equity inicial 10,000.00 → final 11,520.38 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.11 % | +2.30 % | 28 | 11.17 |
| 2020 | +12.76 % | +3.44 % | 168 | 1,281.47 |
| 2021 | +8.09 % | +3.04 % | 157 | 935.34 |
| 2022 | +0.00 % | +1.46 % | 0 | 0.00 |
| 2023 | -2.96 % | +5.83 % | 191 | -347.86 |
| 2024 | -0.66 % | +6.09 % | 183 | -51.44 |
| 2025 | -2.06 % | +10.73 % | 128 | -214.93 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 119 | -14.70 | +31.93 % |
| BNB/USDT | 111 | 835.58 | +34.23 % |
| BTC/USDT | 121 | 140.55 | +32.23 % |
| ETH/USDT | 108 | 748.63 | +39.81 % |
| LINK/USDT | 116 | -99.43 | +33.62 % |
| LTC/USDT | 110 | -430.72 | +33.64 % |
| SOL/USDT | 80 | 477.86 | +38.75 % |
| XRP/USDT | 90 | -44.01 | +33.33 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| stop | 58 |
| trailing | 797 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 2605 |
| entry_rejected:max_positions | 985 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2024-06-02 12:00 @ 68285.66 | 2024-06-02 18:59 @ 67571.78 | stop | -37.54 | -1.24 % |
| BNB/USDT | 2023-05-07 15:00 @ 325.37 | 2023-05-07 23:59 @ 322.01 | stop | -36.64 | -1.23 % |
| BTC/USDT | 2023-11-01 13:00 @ 34808.00 | 2023-11-01 14:59 @ 34297.65 | stop | -34.83 | -1.66 % |
| ETH/USDT | 2023-07-12 15:00 @ 1894.30 | 2023-07-12 19:59 @ 1868.26 | stop | -34.69 | -1.57 % |
| ETH/USDT | 2023-12-10 21:00 @ 2377.40 | 2023-12-11 01:59 @ 2337.50 | stop | -34.53 | -1.88 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BNB/USDT | 2021-02-17 11:00 @ 136.72 | 2021-02-20 01:59 @ 273.01 | trailing | 553.85 | +99.39 % |
| BNB/USDT | 2024-06-03 01:00 @ 605.11 | 2024-06-06 16:59 @ 699.28 | trailing | 378.98 | +15.35 % |
| BTC/USDT | 2024-02-26 15:00 @ 51712.88 | 2024-02-28 17:59 @ 60128.26 | trailing | 362.03 | +16.06 % |
| ADA/USDT | 2020-05-27 06:00 @ 0.0554 | 2020-05-31 14:59 @ 0.0777 | trailing | 288.67 | +40.01 % |
| XRP/USDT | 2020-11-19 13:00 @ 0.2970 | 2020-11-22 01:59 @ 0.4095 | trailing | 250.67 | +37.64 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Supertrend v1 falla criterios fuera de muestra, incluido Sharpe. Costos adversos no lo rescatan; no abrir holdout.
- **Qué se aprendió**: ver [informe conjunto](../../research-2026-09-17/REPORT.md).
- **Siguiente experimento propuesto**: ninguno para rescatar esta configuración; conservar la referencia paper.
