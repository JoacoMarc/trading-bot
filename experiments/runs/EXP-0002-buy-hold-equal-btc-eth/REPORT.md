# EXP-0002 — Buy & hold equiponderado

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `buy_hold_equal_weight` · spec: —
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 0 velas, pares BTC/USDT, ETH/USDT, hash 183890dbdbc6
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: benchmark: sin gestión de riesgo (compra única al inicio del rango)
- Reproducibilidad: git c78726e, params a7ee9ad771, datos 183890dbdbc6, 0.0 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `kind` | `equal_weight` |
| `weights` | `{'BTC/USDT': '0.5', 'ETH/USDT': '0.5'}` |

## Métricas

| Métrica | Estrategia |
|---|---|
| Retorno total | +1439.95 % |
| CAGR | +56.72 % |
| Sharpe (diario) | 0.99 |
| Sortino (diario) | 1.42 |
| Calmar | 0.71 |
| Max drawdown / mayor tramo bajo agua | +79.35 % / 1132 d |
| Profit factor | — |
| Win rate | — |
| Expectancy por trade | — |
| Trades / duración media | 0 / — h |
| Exposición | +99.99 % |
| Fees pagados / shortfall medio | 10.00 / 5.0 bps |

Rango: 2019-08-01 00:00 → 2025-08-31 23:59 UTC (2223 días, 13337 velas). Equity inicial 10,000.00 → final 153,994.57 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -34.84 % | +46.72 % | 0 | 0.00 |
| 2020 | +378.18 % | +60.15 % | 0 | 0.00 |
| 2021 | +243.16 % | +57.56 % | 0 | 0.00 |
| 2022 | -66.77 % | +79.35 % | 0 | 0.00 |
| 2023 | +105.72 % | +75.47 % | 0 | 0.00 |
| 2024 | +67.77 % | +52.05 % | 0 | 0.00 |
| 2025 | +25.57 % | +52.16 % | 0 | 0.00 |

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
- **Por qué**: techo de retorno del universo de EXP-0003, no el benchmark del gate (el gate usa B&H BTC). +1,440 % (CAGR 56.7 %), Sharpe 0.99, DD 79.4 %, 1,132 días bajo agua (pico 2021-11 → fin de 2024), 2022 −66.8 %. Supera a BTC solo porque ETH hizo ~20× contra ~10.7× de BTC. Mismo git y datos que EXP-0001 y EXP-0003.
- **Qué se aprendió**: es equiponderado solo al inicio (compra única, sin rebalanceo): en 2021 ETH ya pesaba ~2/3 de la cartera. Sharpe casi igual al de BTC (0.99 vs 0.93) con DD mayor: sumar ETH (correlación ~0.8) no diversifica.
- **Siguiente experimento propuesto**: cuando el universo pase a ≥ 4 pares (EXP-0004), registrar el equiponderado del mismo universo y rango; SOL arranca el 2020-08-11, así que o se lo excluye del benchmark o se documenta la entrada tardía con peso fijo. Variante con rebalanceo mensual solo si el reporte la soporta sin código nuevo de estrategia.
