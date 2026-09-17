# EXP-0013 — pullback_rsi 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `pullback_rsi` · spec: `docs/strategy/pullback-rsi-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 40a0aa8573b9; activación tardía: LINK/USDT desde 2019-08-06, SOL/USDT desde 2021-03-01
- Costos: fee 0.100 % en el activo recibido, slippage 10 bps
- Riesgo: riesgo/trade 0.25 %, tope 25 % del cash por posición, máx. 2 posiciones, exposición máx. 50 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0)
- Reproducibilidad: git bf0f088, params bac0a7838b, datos 40a0aa8573b9, 2.5 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `rsi_entry` | `10` |
| `rsi_exit` | `70` |
| `stop_atr_mult` | `2.5` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado | B&H BTC filtrado |
|---|---|---|---|---|
| Retorno total | -15.10 % | +971.66 % | +1259.71 % | +744.80 % |
| CAGR | -2.65 % | +47.65 % | +53.54 % | +41.99 % |
| Sharpe (diario) | -1.56 | 0.93 | 0.96 | 1.13 |
| Sortino (diario) | -1.77 | 1.37 | 1.35 | 1.78 |
| Calmar | -0.17 | 0.62 | 0.66 | 1.07 |
| Max drawdown / mayor tramo bajo agua | +15.96 % / 2024 d | +77.04 % / 851 d | +81.19 % / 1390 d | +39.43 % / 717 d |
| Profit factor | 0.61 | — | — | — |
| Win rate | +59.26 % | — | — | — |
| Expectancy por trade | -1.70 | — | — | — |
| Trades / duración media | 842 / 14.3 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +15.14 % | +99.99 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 683.71 / 10.7 bps | 10.00 / 10.0 bps | 10.00 / 13.0 bps | 4,435.50 / 10.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 8,489.59 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +0.12 % | +0.33 % | 20 | 11.80 |
| 2020 | -2.85 % | +3.31 % | 183 | -280.03 |
| 2021 | -1.31 % | +4.87 % | 173 | -109.10 |
| 2022 | +0.00 % | +4.48 % | 0 | 0.00 |
| 2023 | -2.55 % | +7.23 % | 176 | -232.83 |
| 2024 | -7.33 % | +14.08 % | 197 | -657.08 |
| 2025 | -2.07 % | +15.96 % | 93 | -161.06 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 97 | -256.43 | +60.82 % |
| BNB/USDT | 105 | -271.19 | +56.19 % |
| BTC/USDT | 126 | -281.06 | +56.35 % |
| ETH/USDT | 113 | -215.79 | +60.18 % |
| LINK/USDT | 109 | 43.80 | +64.22 % |
| LTC/USDT | 119 | -182.02 | +59.66 % |
| SOL/USDT | 89 | -99.08 | +61.80 % |
| XRP/USDT | 84 | -166.54 | +54.76 % |

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
| BTC/USDT | 2020-08-25 12:00 @ 11626.06 | 2020-08-25 15:59 @ 11317.84 | stop | -27.77 | -2.85 % |
| BTC/USDT | 2023-04-16 08:00 @ 30375.32 | 2023-04-17 11:59 @ 29663.98 | stop | -26.99 | -2.54 % |
| BTC/USDT | 2020-02-25 00:00 @ 9665.18 | 2020-02-25 19:59 @ 9280.91 | stop | -26.91 | -4.17 % |
| BTC/USDT | 2020-02-16 00:00 @ 9914.37 | 2020-02-17 15:59 @ 9487.03 | stop | -26.79 | -4.51 % |
| BTC/USDT | 2020-09-02 20:00 @ 11400.60 | 2020-09-03 15:59 @ 10941.32 | stop | -26.61 | -4.22 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LTC/USDT | 2024-10-15 16:00 @ 66.33 | 2024-10-15 20:00 @ 69.65 | signal | 28.05 | +4.80 % |
| ETH/USDT | 2025-05-08 00:00 @ 1812.93 | 2025-05-08 04:00 @ 1899.18 | signal | 24.32 | +4.55 % |
| LINK/USDT | 2025-08-11 16:00 @ 21.982 | 2025-08-12 16:00 @ 24.005 | signal | 23.19 | +8.99 % |
| BNB/USDT | 2021-10-27 16:00 @ 455.16 | 2021-10-28 12:00 @ 477.82 | signal | 21.57 | +4.77 % |
| LTC/USDT | 2023-07-13 00:00 @ 96.31 | 2023-07-13 08:00 @ 100.19 | signal | 19.21 | +3.82 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go
- **Por qué**: Resultados netos negativos y criterios de validación fallidos. Las candidatas quedan desactivadas; no se evalúa holdout ni se ajustan parámetros para rescatar resultados.
- **Qué se aprendió**: Aumentar la cantidad de movimientos eleva costos sin producir ventaja neta; el perfil B agrava las pérdidas.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
