# EXP-0001 — Buy & hold BTC

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `buy_hold_bh_btc` · spec: —
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 0 velas, pares BTC/USDT, ETH/USDT, hash 183890dbdbc6
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: benchmark: sin gestión de riesgo (compra única al inicio del rango)
- Reproducibilidad: git c78726e, params e67aa67341, datos 183890dbdbc6, 0.0 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `kind` | `bh_btc` |
| `weights` | `{'BTC/USDT': '1'}` |

## Métricas

| Métrica | Estrategia |
|---|---|
| Retorno total | +972.20 % |
| CAGR | +47.67 % |
| Sharpe (diario) | 0.93 |
| Sortino (diario) | 1.37 |
| Calmar | 0.62 |
| Max drawdown / mayor tramo bajo agua | +77.04 % / 851 d |
| Profit factor | — |
| Win rate | — |
| Expectancy por trade | — |
| Trades / duración media | 0 / — h |
| Exposición | +99.99 % |
| Fees pagados / shortfall medio | 10.00 / 5.0 bps |

Rango: 2019-08-01 00:00 → 2025-08-31 23:59 UTC (2223 días, 13337 velas). Equity inicial 10,000.00 → final 107,220.06 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -28.73 % | +45.71 % | 0 | 0.00 |
| 2020 | +301.98 % | +62.53 % | 0 | 0.00 |
| 2021 | +59.79 % | +54.12 % | 0 | 0.00 |
| 2022 | -64.21 % | +77.04 % | 0 | 0.00 |
| 2023 | +155.61 % | +75.87 % | 0 | 0.00 |
| 2024 | +121.31 % | +43.28 % | 0 | 0.00 |
| 2025 | +15.68 % | +30.64 % | 0 | 0.00 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| — | 0 | — | — |

### Motivos de salida

| Motivo | Trades |
|---|---|
| — | 0 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| — | 0 |

### Peores 5 trades

_Sin trades._

### Mejores 5 trades

_Sin trades._

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (línea base)
- **Por qué**: es la referencia del Gate 1 (Sharpe OOS ≥ Sharpe de B&H BTC; DD OOS ≤ 50 % del DD de B&H), no una estrategia: no se evalúa contra los gates. +972.2 % (CAGR 47.7 %), Sharpe 0.93, Sortino 1.37, Calmar 0.62, max DD 77.0 % (2022: −64.2 %), 851 días bajo agua, 2019 −28.7 %. Mismo git (c78726e) y mismos datos (183890dbdbc6) que EXP-0002 y EXP-0003; los costos (10 USDT + 5 bps) son irrelevantes.
- **Qué se aprendió**: la columna "Max DD" por año mide contra el pico histórico, no contra el inicio del año (2023: +155.6 % con DD 75.9 %); el criterio "ningún año con DD > 25 %" del gate tiene que fijar la base (intra-año vs pico histórico) antes de la Fase 6. Comparar +972 % contra una estrategia con 13 % de exposición dice poco: falta un benchmark escalado a la volatilidad de la estrategia.
- **Siguiente experimento propuesto**: en WF-0001 recalcular B&H BTC por ventana OOS (mismo período que la curva OOS concatenada). Agregar al reporte un benchmark "B&H BTC escalado a la vol de la estrategia" (k = σ_estrategia / σ_B&H sobre retornos diarios); para EXP-0003 da k = 0.122 → +51.8 % / DD 14.2 %.
