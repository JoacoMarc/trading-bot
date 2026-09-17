# EXP-0017 — pullback_rsi 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 2.2 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | -47.24 % | +970.60 % | +1258.53 % | +650.76 % |
| CAGR | -9.97 % | +47.63 % | +53.52 % | +39.27 % |
| Sharpe (diario) | -2.32 | 0.93 | 0.96 | 1.07 |
| Sortino (diario) | -2.53 | 1.37 | 1.35 | 1.69 |
| Calmar | -0.21 | 0.62 | 0.66 | 0.97 |
| Max drawdown / mayor tramo bajo agua | +48.11 % / 2024 d | +77.04 % / 851 d | +81.19 % / 1390 d | +40.63 % / 729 d |
| Profit factor | 0.47 | — | — | — |
| Win rate | +51.80 % | — | — | — |
| Expectancy por trade | -4.26 | — | — | — |
| Trades / duración media | 1083 / 14.2 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.66 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 1,446.59 / 20.8 bps | 10.00 / 20.0 bps | 10.00 / 21.7 bps | 4,090.08 / 20.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 5,275.54 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.17 % | +0.67 % | 24 | -16.21 |
| 2020 | -9.84 % | +10.76 % | 240 | -976.16 |
| 2021 | -8.60 % | +19.16 % | 230 | -743.44 |
| 2022 | +0.00 % | +18.21 % | 0 | 0.00 |
| 2023 | -9.92 % | +26.88 % | 212 | -800.39 |
| 2024 | -22.71 % | +43.55 % | 254 | -1,644.02 |
| 2025 | -7.89 % | +48.11 % | 123 | -429.22 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 136 | -629.25 | +59.56 % |
| BNB/USDT | 131 | -695.72 | +47.33 % |
| BTC/USDT | 167 | -990.07 | +44.31 % |
| ETH/USDT | 153 | -740.73 | +51.63 % |
| LINK/USDT | 134 | -149.11 | +57.46 % |
| LTC/USDT | 143 | -559.68 | +51.75 % |
| SOL/USDT | 111 | -314.64 | +57.66 % |
| XRP/USDT | 108 | -530.24 | +46.30 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 926 |
| stop | 157 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 27 |
| entry_rejected:market_filter | 789 |
| entry_rejected:max_positions | 446 |
| protection_cleared:drawdown_halt | 2 |
| protection_cleared:market_filter | 59 |
| protection_triggered:drawdown_halt | 2 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-08-25 12:00 @ 11637.67 | 2020-08-25 15:59 @ 11318.10 | stop | -55.35 | -2.94 % |
| BTC/USDT | 2020-02-16 00:00 @ 9924.27 | 2020-02-17 15:59 @ 9487.42 | stop | -54.64 | -4.60 % |
| BTC/USDT | 2020-02-25 00:00 @ 9674.84 | 2020-02-25 19:59 @ 9281.26 | stop | -54.58 | -4.26 % |
| XRP/USDT | 2019-11-07 16:00 @ 0.2898 | 2019-11-08 15:59 @ 0.2718 | stop | -53.46 | -6.41 % |
| ETH/USDT | 2020-05-20 20:00 @ 210.01 | 2020-05-21 15:59 @ 198.91 | stop | -53.05 | -5.48 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ADA/USDT | 2020-12-16 08:00 @ 0.1521 | 2020-12-16 16:00 @ 0.1616 | signal | 42.98 | +6.04 % |
| LTC/USDT | 2024-10-15 16:00 @ 66.40 | 2024-10-15 20:00 @ 69.58 | signal | 37.42 | +4.58 % |
| ADA/USDT | 2023-01-31 08:00 @ 0.3754 | 2023-01-31 16:00 @ 0.3952 | signal | 36.20 | +5.07 % |
| BNB/USDT | 2021-10-27 16:00 @ 455.61 | 2021-10-28 12:00 @ 477.34 | signal | 35.23 | +4.56 % |
| LTC/USDT | 2023-01-23 04:00 @ 88.05 | 2023-01-23 12:00 @ 91.81 | signal | 30.08 | +4.07 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
