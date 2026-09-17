# EXP-0012 — pullback_rsi 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
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
| Retorno total | -12.17 % | +972.20 % | +1260.72 % | +796.12 % |
| CAGR | -2.11 % | +47.67 % | +53.56 % | +43.38 % |
| Sharpe (diario) | -1.24 | 0.93 | 0.96 | 1.15 |
| Sortino (diario) | -1.43 | 1.37 | 1.35 | 1.82 |
| Calmar | -0.16 | 0.62 | 0.66 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +13.22 % / 1894 d | +77.04 % / 851 d | +81.19 % / 1390 d | +38.82 % / 709 d |
| Profit factor | 0.69 | — | — | — |
| Win rate | +61.76 % | — | — | — |
| Expectancy por trade | -1.35 | — | — | — |
| Trades / duración media | 842 / 14.3 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.14 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 695.13 / 5.7 bps | 10.00 / 5.0 bps | 10.00 / 5.9 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 8,783.03 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.21 % | +0.32 % | 20 | 21.37 |
| 2020 | -2.21 % | +2.75 % | 183 | -216.24 |
| 2021 | -0.85 % | +3.94 % | 173 | -64.36 |
| 2022 | +0.00 % | +3.46 % | 0 | 0.00 |
| 2023 | -1.71 % | +5.48 % | 176 | -154.29 |
| 2024 | -6.53 % | +11.66 % | 197 | -592.94 |
| 2025 | -1.61 % | +13.22 % | 93 | -126.52 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 97 | -229.27 | +61.86 % |
| BNB/USDT | 105 | -229.74 | +59.05 % |
| BTC/USDT | 126 | -215.09 | +61.90 % |
| ETH/USDT | 113 | -170.44 | +63.72 % |
| LINK/USDT | 109 | 77.20 | +66.97 % |
| LTC/USDT | 119 | -146.68 | +59.66 % |
| SOL/USDT | 89 | -76.98 | +61.80 % |
| XRP/USDT | 84 | -141.99 | +58.33 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 729 |
| stop | 113 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:market_filter | 790 |
| entry_rejected:max_positions | 753 |
| protection_cleared:market_filter | 59 |
| protection_triggered:market_filter | 59 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-08-25 12:00 @ 11620.25 | 2020-08-25 19:59 @ 11317.70 | stop | -27.42 | -2.80 % |
| BTC/USDT | 2023-04-16 08:00 @ 30360.15 | 2023-04-17 11:59 @ 29663.66 | stop | -26.90 | -2.49 % |
| BTC/USDT | 2020-02-25 00:00 @ 9660.35 | 2020-02-25 19:59 @ 9280.73 | stop | -26.64 | -4.13 % |
| BTC/USDT | 2020-02-16 00:00 @ 9909.42 | 2020-02-17 15:59 @ 9486.83 | stop | -26.54 | -4.46 % |
| BTC/USDT | 2020-09-02 20:00 @ 11394.91 | 2020-09-03 15:59 @ 10941.10 | stop | -26.44 | -4.18 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LTC/USDT | 2024-10-15 16:00 @ 66.30 | 2024-10-15 20:00 @ 69.68 | signal | 29.35 | +4.89 % |
| ETH/USDT | 2025-05-08 00:00 @ 1812.02 | 2025-05-08 04:00 @ 1900.13 | signal | 25.64 | +4.66 % |
| LINK/USDT | 2025-08-11 16:00 @ 21.971 | 2025-08-12 16:00 @ 24.017 | signal | 24.26 | +9.10 % |
| BNB/USDT | 2021-10-27 16:00 @ 454.93 | 2021-10-28 12:00 @ 478.06 | signal | 22.26 | +4.88 % |
| LTC/USDT | 2023-07-13 00:00 @ 96.26 | 2023-07-13 08:00 @ 100.24 | signal | 20.07 | +3.93 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
