# <ID> — <estrategia> <versión>

> Sección autogenerada por `tradingbot backtest` (Fase 4). Solo la sección **Notas y veredicto** se escribe a mano (usuario o `backtest-analyst`).

## Configuración

- Estrategia y versión de spec: `docs/strategy/<...>.md`
- Params: (tabla)
- Datos: exchange, pares, timeframe, `from` → `to` (¿incluye holdout?), hash de datos
- Costos: fee, `pay_with_bnb`, slippage
- Riesgo: riesgo por trade, tope por posición, máx. posiciones, protecciones activas
- Reproducibilidad: git sha, hash de `config.yaml`, semillas, host, duración

## Métricas

| Métrica | Estrategia | Buy & hold BTC | Equiponderado |
|---|---|---|---|
| Retorno total | | | |
| CAGR | | | |
| Sharpe (diario) | | | |
| Sortino (diario) | | | |
| Calmar | | | |
| Max drawdown / duración | | | |
| Profit factor | | | |
| Win rate | | | |
| Expectancy por trade | | | |
| Trades / duración media | | | |
| Exposición | | | |
| Fees pagados / shortfall medio | | | |

## Desglose

- Por año (retorno, DD, trades)
- Por par
- Peores 5 trades y mejores 5 trades (par, fechas, motivo de salida, PnL)
- Distribución de motivos de salida (stop, trailing, señal, STUCK)

## Gráficos

`equity.png` (equity + drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: go | no-go | iterar
- **Por qué**:
- **Qué se aprendió**:
- **Siguiente experimento propuesto**:
