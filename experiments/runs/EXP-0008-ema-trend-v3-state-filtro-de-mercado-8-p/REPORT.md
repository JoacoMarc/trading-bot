# EXP-0008 — ema_trend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v3.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 4d776a274063; activación tardía: LINK/USDT desde 2019-08-04, SOL/USDT desde 2021-02-27
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > EMA200 y retorno 30 d > 0)
- Reproducibilidad: git d27b4e4, params 3067ccea6a, datos 4d776a274063, 7.8 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `adx_period` | `14` |
| `adx_threshold` | `20.0` |
| `atr_period` | `14` |
| `cooldown_candles` | `2` |
| `ema_fast` | `20` |
| `ema_regime` | `200` |
| `ema_slow` | `50` |
| `entry_mode` | `state` |
| `stop_atr_mult` | `2.0` |
| `trailing_atr_mult` | `3.0` |
| `warmup_multiplier` | `6` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | +225.42 % | +972.20 % | +1251.80 % | +750.31 % |
| CAGR | +21.40 % | +47.67 % | +53.40 % | +42.15 % |
| Sharpe (diario) | 1.01 | 0.93 | 0.95 | 1.10 |
| Sortino (diario) | 1.68 | 1.37 | 1.35 | 1.73 |
| Calmar | 0.68 | 0.62 | 0.66 | 0.92 |
| Max drawdown / mayor tramo bajo agua | +31.46 % / 714 d | +77.04 % / 851 d | +81.13 % / 1390 d | +45.96 % / 559 d |
| Profit factor | 1.33 | — | — | — |
| Win rate | +36.71 % | — | — | — |
| Expectancy por trade | 33.20 | — | — | — |
| Trades / duración media | 681 / 85.5 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +42.04 % | +99.99 % | +99.99 % | +47.77 % |
| Fees pagados / shortfall medio | 6,094.72 / 5.8 bps | 10.00 / 5.0 bps | 10.00 / 6.4 bps | 4,762.41 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 32,542.09 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -11.55 % | +12.36 % | 32 | -1,154.08 |
| 2020 | +73.24 % | +15.05 % | 139 | 5,285.96 |
| 2021 | +115.50 % | +11.86 % | 131 | 18,912.14 |
| 2022 | -3.93 % | +10.57 % | 10 | -1,297.36 |
| 2023 | +17.52 % | +15.41 % | 146 | 5,888.20 |
| 2024 | -0.05 % | +20.64 % | 144 | -314.60 |
| 2025 | -12.67 % | +31.46 % | 79 | -4,711.71 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 73 | -358.58 | +35.62 % |
| BNB/USDT | 90 | 5,896.39 | +33.33 % |
| BTC/USDT | 111 | 5,495.01 | +36.04 % |
| ETH/USDT | 105 | 3,289.58 | +37.14 % |
| LINK/USDT | 88 | 1,873.91 | +34.09 % |
| LTC/USDT | 81 | -741.75 | +37.04 % |
| SOL/USDT | 63 | 10,414.65 | +50.79 % |
| XRP/USDT | 70 | -3,260.66 | +32.86 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 112 |
| stop | 171 |
| trailing | 398 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:daily_loss_limit | 115 |
| entry_rejected:drawdown_halt | 50 |
| entry_rejected:market_filter | 654 |
| entry_rejected:max_positions | 715 |
| protection_cleared:daily_loss_limit | 36 |
| protection_cleared:drawdown_halt | 2 |
| protection_cleared:market_filter | 66 |
| protection_triggered:daily_loss_limit | 36 |
| protection_triggered:drawdown_halt | 2 |
| protection_triggered:market_filter | 67 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BNB/USDT | 2024-03-17 16:00 @ 588.50 | 2024-03-19 03:59 @ 536.18 | stop | -445.73 | -9.08 % |
| XRP/USDT | 2024-07-31 08:00 @ 0.6469 | 2024-08-01 03:59 @ 0.6151 | stop | -432.12 | -5.11 % |
| XRP/USDT | 2024-08-01 12:00 @ 0.6105 | 2024-08-01 19:59 @ 0.5785 | stop | -426.03 | -5.44 % |
| XRP/USDT | 2024-09-30 04:00 @ 0.6454 | 2024-09-30 15:59 @ 0.6179 | stop | -412.22 | -4.46 % |
| ADA/USDT | 2024-12-09 08:00 @ 1.1573 | 2024-12-09 23:59 @ 1.0778 | stop | -402.87 | -7.06 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BNB/USDT | 2024-03-05 20:00 @ 376.99 | 2024-03-14 19:59 @ 575.09 | trailing | 3,537.42 | +52.30 % |
| SOL/USDT | 2023-10-17 16:00 @ 23.91 | 2023-11-02 19:59 @ 38.98 | trailing | 3,333.66 | +62.76 % |
| SOL/USDT | 2021-08-05 16:00 @ 36.73 | 2021-08-17 23:59 @ 61.07 | trailing | 2,155.39 | +66.00 % |
| BNB/USDT | 2021-02-14 16:00 @ 131.66 | 2021-02-20 23:59 @ 261.56 | trailing | 1,753.00 | +98.36 % |
| SOL/USDT | 2024-03-05 20:00 @ 119.30 | 2024-03-19 07:59 @ 179.89 | trailing | 1,638.40 | +50.54 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (control: diagnóstico de v3 en muestra completa)
- **Por qué**: misma config que WF-0005 sobre 2019-08 → 2025-09 para leer lo que el walk-forward no guarda. +225.4 %, Sharpe 1.01, DD 31.5 %, PF 1.33, 681 trades; B&H BTC filtrado +750.3 % / Sharpe 1.10 / DD 46.0 %: también en la muestra completa el filtro solo rinde más que la estrategia por unidad de riesgo. No es evidencia nueva sobre la estrategia; sirve para el diagnóstico de 2024.
- **Qué se aprendió**: el circuit breaker por DD (20 %) disparó 2 veces y rechazó 50 entradas; 2024 cierra en −0.05 % con 144 trades y DD intra-año 20.6 %, mientras la cadena OOS de WF-0005 (que re-basa el pico cada 6 meses y no dispara) da +30 %: el signo del año depende del estado del breaker, no de la señal. El filtro conmutó 67 veces (654 rechazos); la pérdida diaria del 3 % disparó 36 veces (115 rechazos) porque 3 slots sobre pares con correlación 0.65 pierden juntos. 2025 (parcial) −12.7 %.
- **Siguiente experimento propuesto**: ninguno propio; la familia queda cerrada en WF-0005. Deuda: listar `protection_triggered` por año en el REPORT del walk-forward.
