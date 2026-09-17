# EXP-0015 — pullback_rsi 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 0.50 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 75 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 2.3 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | -30.69 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | -5.85 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | -1.33 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | -1.52 | 1.37 | 1.35 | 1.82 |
| Calmar | -0.18 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +32.72 % / 2024 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 0.66 | — | — | — |
| Win rate | +60.70 % | — | — | — |
| Expectancy por trade | -2.71 | — | — | — |
| Trades / duración media | 1089 / 14.2 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.84 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 1,644.09 / 5.8 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 6,930.61 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.49 % | +0.61 % | 24 | 48.95 |
| 2020 | -5.02 % | +6.51 % | 240 | -498.70 |
| 2021 | -4.25 % | +11.91 % | 229 | -376.59 |
| 2022 | +0.00 % | +10.17 % | 0 | 0.00 |
| 2023 | -5.14 % | +15.84 % | 233 | -452.22 |
| 2024 | -16.47 % | +29.51 % | 240 | -1,392.57 |
| 2025 | -4.28 % | +32.72 % | 123 | -285.35 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 138 | -444.59 | +63.04 % |
| BNB/USDT | 131 | -500.38 | +60.31 % |
| BTC/USDT | 164 | -499.12 | +59.76 % |
| ETH/USDT | 156 | -517.85 | +62.82 % |
| LINK/USDT | 138 | -8.49 | +62.32 % |
| LTC/USDT | 142 | -432.93 | +56.34 % |
| SOL/USDT | 109 | -171.67 | +62.39 % |
| XRP/USDT | 111 | -381.44 | +58.56 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 935 |
| stop | 154 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 25 |
| entry_rejected:market_filter | 782 |
| entry_rejected:max_positions | 448 |
| protection_cleared:drawdown_halt | 1 |
| protection_cleared:market_filter | 59 |
| protection_triggered:drawdown_halt | 1 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-08-25 12:00 @ 11620.25 | 2020-08-25 19:59 @ 11317.70 | stop | -54.49 | -2.80 % |
| BTC/USDT | 2020-02-16 00:00 @ 9909.42 | 2020-02-17 15:59 @ 9486.83 | stop | -53.51 | -4.46 % |
| BTC/USDT | 2020-02-25 00:00 @ 9660.35 | 2020-02-25 19:59 @ 9280.73 | stop | -53.42 | -4.13 % |
| ETH/USDT | 2020-08-11 12:00 @ 391.66 | 2020-08-11 23:59 @ 371.76 | stop | -52.95 | -5.28 % |
| BNB/USDT | 2020-08-07 04:00 @ 22.78 | 2020-08-07 19:59 @ 21.49 | stop | -52.87 | -5.86 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LTC/USDT | 2024-10-15 16:00 @ 66.30 | 2024-10-15 20:00 @ 69.68 | signal | 49.32 | +4.89 % |
| ADA/USDT | 2020-12-16 08:00 @ 0.1518 | 2020-12-16 16:00 @ 0.1618 | signal | 47.90 | +6.38 % |
| ADA/USDT | 2023-01-31 08:00 @ 0.3748 | 2023-01-31 16:00 @ 0.3958 | signal | 42.95 | +5.40 % |
| BNB/USDT | 2021-10-27 16:00 @ 454.93 | 2021-10-28 12:00 @ 478.06 | signal | 41.42 | +4.88 % |
| ETH/USDT | 2025-05-08 00:00 @ 1812.02 | 2025-05-08 04:00 @ 1900.13 | signal | 40.70 | +4.66 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
