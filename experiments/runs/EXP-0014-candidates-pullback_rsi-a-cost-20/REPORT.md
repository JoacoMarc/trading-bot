# EXP-0014 — pullback_rsi 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 20 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 2.2 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | -21.24 % | +970.60 % | +1258.53 % | +650.76 % |
| CAGR | -3.85 % | +47.63 % | +53.52 % | +39.27 % |
| Sharpe (diario) | -2.25 | 0.93 | 0.96 | 1.07 |
| Sortino (diario) | -2.47 | 1.37 | 1.35 | 1.69 |
| Calmar | -0.18 | 0.62 | 0.66 | 0.97 |
| Max drawdown / mayor tramo bajo agua | +21.80 % / 2124 d | +77.04 % / 851 d | +81.19 % / 1390 d | +40.63 % / 729 d |
| Profit factor | 0.47 | — | — | — |
| Win rate | +52.19 % | — | — | — |
| Expectancy por trade | -2.42 | — | — | — |
| Trades / duración media | 843 / 14.2 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.01 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 660.85 / 20.7 bps | 10.00 / 20.0 bps | 10.00 / 21.7 bps | 4,090.08 / 20.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 7,875.62 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -0.05 % | +0.34 % | 20 | -4.60 |
| 2020 | -4.11 % | +4.49 % | 183 | -405.77 |
| 2021 | -2.53 % | +7.01 % | 174 | -223.40 |
| 2022 | +0.00 % | +6.83 % | 0 | 0.00 |
| 2023 | -4.20 % | +10.94 % | 176 | -379.31 |
| 2024 | -9.09 % | +19.17 % | 198 | -787.22 |
| 2025 | -3.19 % | +21.80 % | 92 | -241.88 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 97 | -317.78 | +58.76 % |
| BNB/USDT | 104 | -340.84 | +45.19 % |
| BTC/USDT | 127 | -432.56 | +44.88 % |
| ETH/USDT | 113 | -301.32 | +51.33 % |
| LINK/USDT | 109 | -20.03 | +59.63 % |
| LTC/USDT | 119 | -283.85 | +53.78 % |
| SOL/USDT | 90 | -133.30 | +57.78 % |
| XRP/USDT | 84 | -212.50 | +47.62 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 726 |
| stop | 117 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 15 |
| entry_rejected:market_filter | 778 |
| entry_rejected:max_positions | 750 |
| protection_cleared:drawdown_halt | 1 |
| protection_cleared:market_filter | 59 |
| protection_triggered:drawdown_halt | 1 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-08-25 12:00 @ 11637.67 | 2020-08-25 15:59 @ 11318.10 | stop | -28.46 | -2.94 % |
| BTC/USDT | 2020-02-25 00:00 @ 9674.84 | 2020-02-25 19:59 @ 9281.26 | stop | -27.44 | -4.26 % |
| BTC/USDT | 2020-02-16 00:00 @ 9924.27 | 2020-02-17 15:59 @ 9487.42 | stop | -27.29 | -4.60 % |
| BTC/USDT | 2023-04-16 08:00 @ 30405.66 | 2023-04-17 11:59 @ 29664.56 | stop | -27.10 | -2.64 % |
| BTC/USDT | 2020-09-02 20:00 @ 11411.99 | 2020-09-03 15:59 @ 10941.73 | stop | -26.96 | -4.32 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LTC/USDT | 2024-10-15 16:00 @ 66.40 | 2024-10-15 20:00 @ 69.58 | signal | 25.30 | +4.58 % |
| ETH/USDT | 2025-05-08 00:00 @ 1814.74 | 2025-05-08 04:00 @ 1897.28 | signal | 21.69 | +4.34 % |
| LINK/USDT | 2025-08-11 16:00 @ 22.004 | 2025-08-12 16:00 @ 23.981 | signal | 21.03 | +8.78 % |
| BNB/USDT | 2021-10-27 16:00 @ 455.61 | 2021-10-28 12:00 @ 477.34 | signal | 20.15 | +4.56 % |
| LTC/USDT | 2023-07-13 00:00 @ 96.41 | 2023-07-13 08:00 @ 100.09 | signal | 17.51 | +3.61 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
