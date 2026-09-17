# EXP-0024 — regime_bh 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares BTC/USDT, hash 95037f50a96a
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: fracción fija 50 % de la equity por posición (acotada por el cash libre), máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Reproducibilidad: git bf0f088, params 937532e2f5, datos 95037f50a96a, 0.6 s en MacBook-Air-4.local

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Métricas

| Métrica | Estrategia | B&H BTC | B&H BTC filtrado |
|---|---|---|---|
| Retorno total | +302.75 % | +972.20 % | +796.12 % |
| CAGR | +25.72 % | +47.67 % | +43.38 % |
| Sharpe (diario) | 1.17 | 0.93 | 1.15 |
| Sortino (diario) | 1.87 | 1.37 | 1.82 |
| Calmar | 1.20 | 0.62 | 1.12 |
| Max drawdown / mayor tramo bajo agua | +21.44 % / 706 d | +77.04 % / 851 d | +38.82 % / 709 d |
| Profit factor | 2.79 | — | — |
| Win rate | +40.68 % | — | — |
| Expectancy por trade | 513.37 | — | — |
| Trades / duración media | 59 / 392.5 h | 0 / — h | 0 / — h |
| Exposición | +43.41 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 1,375.52 / 5.0 bps | 10.00 / 5.0 bps | 4,620.26 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 40,274.78 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -16.24 % | +17.42 % | 9 | -1,623.50 |
| 2020 | +91.28 % | +21.44 % | 8 | 193.02 |
| 2021 | +25.89 % | +21.15 % | 12 | 11,604.16 |
| 2022 | +0.00 % | +15.19 % | 0 | 0.00 |
| 2023 | +49.10 % | +15.19 % | 6 | 4,070.76 |
| 2024 | +30.19 % | +11.29 % | 16 | 14,917.85 |
| 2025 | +2.87 % | +15.27 % | 8 | 1,126.81 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 59 | 30,289.11 | +40.68 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 59 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| protection_cleared:daily_loss_limit | 38 |
| protection_cleared:drawdown_halt | 2 |
| protection_triggered:daily_loss_limit | 38 |
| protection_triggered:drawdown_halt | 2 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2024-07-20 00:00 @ 66693.35 | 2024-08-04 00:00 @ 60667.64 | signal | -1,611.08 | -9.23 % |
| BTC/USDT | 2021-04-14 00:00 @ 63606.80 | 2021-04-19 00:00 @ 56121.93 | signal | -1,408.23 | -11.96 % |
| BTC/USDT | 2024-01-09 00:00 @ 46974.52 | 2024-01-13 00:00 @ 42761.34 | signal | -1,406.68 | -9.16 % |
| BTC/USDT | 2025-01-18 00:00 @ 104129.51 | 2025-02-03 00:00 @ 97651.73 | signal | -1,224.85 | -6.41 % |
| BTC/USDT | 2025-01-07 00:00 @ 102286.72 | 2025-01-08 00:00 @ 96906.12 | signal | -1,070.84 | -5.46 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-10-04 00:00 @ 10547.35 | 2021-02-07 00:00 @ 39161.41 | signal | 11,591.12 | +270.82 % |
| BTC/USDT | 2024-10-15 00:00 @ 66117.05 | 2024-12-22 00:00 @ 97243.35 | signal | 7,601.39 | +46.83 % |
| BTC/USDT | 2023-10-17 00:00 @ 28515.03 | 2024-01-08 00:00 @ 43907.04 | signal | 6,504.68 | +53.72 % |
| BTC/USDT | 2024-02-10 00:00 @ 47156.35 | 2024-04-04 00:00 @ 65930.28 | signal | 5,632.57 | +39.57 % |
| BTC/USDT | 2023-03-13 00:00 @ 22009.05 | 2023-04-23 00:00 @ 27802.94 | signal | 2,756.11 | +26.10 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (control histórico; no habilita dinero real)
- **Por qué**: Repite la referencia con el mismo código, costos y rango de las candidatas. El WF reproduce WF-0008; no reabre ni modifica el holdout previo EXP-0010.
- **Qué se aprendió**: La menor frecuencia conserva mejor retorno histórico, con mayor volatilidad y caída que Donchian. No sustituye los gates pendientes de la referencia.
- **Siguiente experimento propuesto**: ninguno dentro de este protocolo; preservar parámetros y holdout. Ver [comparación consolidada](../../candidates-2026-09-17/REPORT.md).
