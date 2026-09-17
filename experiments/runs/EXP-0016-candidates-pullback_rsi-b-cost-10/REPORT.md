# EXP-0016 — pullback_rsi 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 2.4 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | -35.33 % | +971.66 % | +1259.71 % | +744.80 % |
| CAGR | -6.91 % | +47.65 % | +53.54 % | +41.99 % |
| Sharpe (diario) | -1.60 | 0.93 | 0.96 | 1.13 |
| Sortino (diario) | -1.80 | 1.37 | 1.35 | 1.78 |
| Calmar | -0.19 | 0.62 | 0.66 | 1.07 |
| Max drawdown / mayor tramo bajo agua | +36.95 % / 2024 d | +77.04 % / 851 d | +81.19 % / 1390 d | +39.43 % / 717 d |
| Profit factor | 0.60 | — | — | — |
| Win rate | +58.36 % | — | — | — |
| Expectancy por trade | -3.23 | — | — | — |
| Trades / duración media | 1059 / 14.1 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.27 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 1,542.96 / 10.8 bps | 10.00 / 10.0 bps | 10.00 / 13.0 bps | 4,435.50 / 10.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 6,466.84 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.24 % | +0.62 % | 24 | 24.41 |
| 2020 | -6.63 % | +7.93 % | 240 | -658.72 |
| 2021 | -5.45 % | +14.14 % | 229 | -480.86 |
| 2022 | +0.00 % | +12.67 % | 0 | 0.00 |
| 2023 | -7.31 % | +19.92 % | 233 | -628.84 |
| 2024 | -17.41 % | +33.77 % | 240 | -1,392.97 |
| 2025 | -4.53 % | +36.95 % | 93 | -287.93 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 133 | -464.71 | +63.16 % |
| BNB/USDT | 127 | -532.47 | +56.69 % |
| BTC/USDT | 161 | -650.09 | +54.04 % |
| ETH/USDT | 147 | -617.38 | +59.18 % |
| LINK/USDT | 134 | -28.86 | +61.19 % |
| LTC/USDT | 142 | -485.23 | +55.63 % |
| SOL/USDT | 105 | -226.49 | +61.90 % |
| XRP/USDT | 110 | -419.68 | +56.36 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 911 |
| stop | 148 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 93 |
| entry_rejected:market_filter | 774 |
| entry_rejected:max_positions | 429 |
| protection_cleared:drawdown_halt | 2 |
| protection_cleared:market_filter | 59 |
| protection_triggered:drawdown_halt | 2 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-08-25 12:00 @ 11626.06 | 2020-08-25 15:59 @ 11317.84 | stop | -54.80 | -2.85 % |
| BTC/USDT | 2020-02-16 00:00 @ 9914.37 | 2020-02-17 15:59 @ 9487.03 | stop | -53.88 | -4.51 % |
| BTC/USDT | 2020-02-25 00:00 @ 9665.18 | 2020-02-25 19:59 @ 9280.91 | stop | -53.80 | -4.17 % |
| ADA/USDT | 2020-02-25 00:00 @ 0.0592 | 2020-02-26 03:59 @ 0.0551 | stop | -53.44 | -7.12 % |
| BNB/USDT | 2020-07-27 00:00 @ 19.58 | 2020-07-27 15:59 @ 18.55 | stop | -52.89 | -5.46 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ADA/USDT | 2020-12-16 08:00 @ 0.1519 | 2020-12-16 16:00 @ 0.1617 | signal | 46.06 | +6.25 % |
| LTC/USDT | 2024-10-15 16:00 @ 66.33 | 2024-10-15 20:00 @ 69.65 | signal | 45.61 | +4.80 % |
| ADA/USDT | 2023-01-31 08:00 @ 0.3750 | 2023-01-31 16:00 @ 0.3956 | signal | 40.70 | +5.29 % |
| BNB/USDT | 2021-10-27 16:00 @ 455.16 | 2021-10-28 12:00 @ 477.82 | signal | 39.37 | +4.77 % |
| LINK/USDT | 2025-08-11 16:00 @ 21.982 | 2025-08-12 16:00 @ 24.005 | signal | 35.17 | +8.99 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
