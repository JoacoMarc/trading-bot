# EXP-0009 — regime_bh 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1212 velas, pares BTC/USDT, hash 4b239758a1fc
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 100 % del cash por posición, máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Reproducibilidad: git f1dd153, params 937532e2f5, datos 4b239758a1fc, 1.1 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Métricas

| Métrica | Estrategia | B&H BTC | B&H BTC filtrado |
|---|---|---|---|
| Retorno total | +401.62 % | +972.20 % | +734.15 % |
| CAGR | +30.34 % | +47.67 % | +41.70 % |
| Sharpe (diario) | 1.19 | 0.93 | 1.12 |
| Sortino (diario) | 1.90 | 1.37 | 1.76 |
| Calmar | 1.20 | 0.62 | 0.97 |
| Max drawdown / mayor tramo bajo agua | +25.22 % / 704 d | +77.04 % / 851 d | +43.02 % / 707 d |
| Profit factor | 2.77 | — | — |
| Win rate | +42.11 % | — | — |
| Expectancy por trade | 704.82 | — | — |
| Trades / duración media | 57 / 403.2 h | 0 / — h | 0 / — h |
| Exposición | +43.08 % | +99.99 % | +43.41 % |
| Fees pagados / shortfall medio | 1,854.13 / 5.0 bps | 10.00 / 5.0 bps | 4,333.62 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 50,162.41 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -19.23 % | +20.58 % | 9 | -1,922.23 |
| 2020 | +109.51 % | +25.22 % | 8 | 203.39 |
| 2021 | +31.70 % | +22.69 % | 10 | 14,009.20 |
| 2022 | +0.00 % | +15.72 % | 0 | 0.00 |
| 2023 | +60.27 % | +15.72 % | 6 | 5,428.97 |
| 2024 | +35.86 % | +13.40 % | 16 | 20,818.14 |
| 2025 | +3.37 % | +17.82 % | 8 | 1,637.40 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 57 | 40,174.87 | +42.11 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 57 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 3 |
| protection_cleared:daily_loss_limit | 58 |
| protection_cleared:drawdown_halt | 4 |
| protection_triggered:daily_loss_limit | 58 |
| protection_triggered:drawdown_halt | 4 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2024-07-20 00:00 @ 66693.35 | 2024-08-04 00:00 @ 60667.64 | signal | -2,354.87 | -9.23 % |
| BTC/USDT | 2024-01-09 00:00 @ 46974.52 | 2024-01-13 00:00 @ 42761.34 | signal | -2,011.72 | -9.16 % |
| BTC/USDT | 2021-04-14 00:00 @ 63606.80 | 2021-04-19 00:00 @ 56121.93 | signal | -1,876.15 | -11.96 % |
| BTC/USDT | 2025-01-18 00:00 @ 104129.51 | 2025-02-03 00:00 @ 97651.73 | signal | -1,813.13 | -6.41 % |
| BTC/USDT | 2025-01-07 00:00 @ 102286.72 | 2025-01-08 00:00 @ 96906.12 | signal | -1,594.01 | -5.46 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2020-10-04 00:00 @ 10547.35 | 2021-02-07 00:00 @ 39161.41 | signal | 13,441.24 | +270.82 % |
| BTC/USDT | 2024-10-15 00:00 @ 66117.05 | 2024-12-22 00:00 @ 97243.35 | signal | 10,945.68 | +46.83 % |
| BTC/USDT | 2023-10-17 00:00 @ 28515.03 | 2024-01-08 00:00 @ 43907.04 | signal | 8,924.87 | +53.72 % |
| BTC/USDT | 2024-02-10 00:00 @ 47156.35 | 2024-04-04 00:00 @ 65930.28 | signal | 7,931.58 | +39.57 % |
| BTC/USDT | 2023-03-13 00:00 @ 22009.05 | 2023-04-23 00:00 @ 27802.94 | signal | 3,686.25 | +26.10 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: go (control)
- **Por qué**: diagnóstico de `regime_bh` v1 en la muestra completa (la decisión es WF-0006). +401.6 %, Sharpe 1.19, DD 25.22 %, PF 2.77, 57 trades (todos `signal`; el stop del 20 % no se ejecutó nunca) vs B&H BTC +972 % / 0.93 / 77.0 % y B&H BTC filtrado (mismo régimen, λ = 1) +734 % / 1.12 / 43.0 %. Sharpe sin 2022: 1.3 (B&H 1.38, filtrado 1.23); sin 2020-21: 0.87 (B&H 0.49). El DD máximo (pico 2019-08 → valle 2020-05-10) ocurrió con el circuit breaker ya re-basado: disparó el 2019-11-08 con DD 20.3 %, reanudó por plazo el 2019-12-08 y re-basó el pico de 10,171 a 8,077; el 20 % es tope por episodio, no de cuenta (deuda anotada desde EXP-0006).
- **Qué se aprendió**: anatomía de seguidor de tendencia: 28 trades > 96 h con win rate 61 % y +53,582 USDT contra 29 trades ≤ 96 h con win rate 24 % y −13,407; las conmutaciones ≤ 48 h (22/57) cuestan el 10.7 % del bruto y las fees solo el 2.9 %. Top 5 trades = 112 % del PnL; sin los top 10, PF 0.25. 2019-H2 fue el peor caso anticipado en la spec: 9 trades, PF 0.03, −19.2 % (B&H −30.7 % en el mismo tramo). 2024: 15 entradas (alarma > 12/año), baratas (−383 en las ≤ 48 h). Breaker: 4 disparos y 3 rechazos, todos en sep-2021 (bloqueó dos entradas perdedoras y re-entró 0.9 % más barato: +1.6 % de equity, una sola vez). Pérdida diaria: 58 disparos, 0 rechazos: inerte en esta estrategia, porque la entrada se decide al cierre del día y cuando hay pérdida diaria la cuenta ya está comprada.
- **Siguiente experimento propuesto**: ninguno más sobre esta muestra. Holdout una sola vez con la config final (`--include-holdout`, λ fijada antes en 0.5 por WF-0008/0009). Deuda: el REPORT debería listar la fecha de cada `protection_triggered` y el pico vigente; y el DD anual intra-año conviene complementarlo con el DD desde el pico histórico (25.22 % acá vs 22.69 % intra-año).
