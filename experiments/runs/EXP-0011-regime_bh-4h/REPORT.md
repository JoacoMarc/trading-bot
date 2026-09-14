# EXP-0011 — regime_bh 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2019-08-01 → 2026-09-08 (incluye holdout), warmup 1212 velas, pares BTC/USDT, hash 4b239758a1fc
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 100 % del cash por posición, máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Reproducibilidad: git 278521b, params 937532e2f5, datos 4b239758a1fc, 1.2 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Métricas

| Métrica | Estrategia | B&H BTC | B&H BTC filtrado |
|---|---|---|---|
| Retorno total | +315.38 % | +681.56 % | +790.32 % |
| CAGR | +22.19 % | +33.55 % | +36.02 % |
| Sharpe (diario) | 1.10 | 0.78 | 1.05 |
| Sortino (diario) | 1.75 | 1.14 | 1.65 |
| Calmar | 1.03 | 0.44 | 0.84 |
| Max drawdown / mayor tramo bajo agua | +21.44 % / 706 d | +77.04 % / 851 d | +43.02 % / 707 d |
| Profit factor | 2.57 | — | — |
| Win rate | +39.68 % | — | — |
| Expectancy por trade | 458.80 | — | — |
| Trades / duración media | 63 / 375.6 h | 0 / — h | 0 / — h |
| Exposición | +38.74 % | +99.99 % | +38.73 % |
| Fees pagados / shortfall medio | 1,552.34 / 5.0 bps | 10.00 / 5.0 bps | 5,050.94 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2026-09-08 15:59 UTC (2596 días, 15572 velas). Equity inicial 10,000.00 → final 41,538.20 USDT.

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
| 2025 | -0.68 % | +15.27 % | 12 | -257.76 |
| 2026 | +6.82 % | +8.63 % | 0 | 0.00 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 63 | 28,904.54 | +39.68 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 63 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| protection_cleared:daily_loss_limit | 39 |
| protection_cleared:drawdown_halt | 2 |
| protection_triggered:daily_loss_limit | 39 |
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

- **Veredicto**: go (control)
- **Por qué**: curva continua con la config final, informativa. 2019-08-01 → 2026-09-08, λ 0.5: +315.4 %, Sharpe 1.10, DD 21.44 %, PF 2.57, 63 trades vs B&H BTC +681.6 % / 0.78 / 77.0 % y filtrado +790.3 % / 1.05 / 43.0 %. Son los 59 trades de la muestra completa de WF-0008 (años 2019–2024 idénticos) más los 4 del holdout; el DD máximo sigue siendo el episodio 2019-08 → 2020-05. El holdout bajó el Sharpe de 1.18 a 1.10 (12 meses casi planos) y el del B&H de 0.93 a 0.78: la ventaja relativa creció (Δ +0.24 → +0.32). No decide nada: la decisión es EXP-0010.
- **Qué se aprendió**: anatomía sin cambios: 30 trades > 96 h (win rate 60 %, +40,502) vs 33 ≤ 96 h (win rate 21 %, −11,598); top 5 = 118 % del PnL; PF sin top 10 = 0.24; fees 2.3 % del bruto. La equity cierra 2.2 % bajo su máximo (42,484 el 2024-12-17): 630 días sin nuevo máximo, cerca del récord de 706; en paper esto se va a sentir como "no hace nada". Con λ 0.5 el breaker dispara 2 veces sin rechazos (λ 0.6: 4 y 3) y deja pasar 2 conmutaciones más en 2021. 2025 cierra −0.68 % (5 conmutaciones ene–feb −2,700, 2 piernas abr–ago +3,845, 4 conmutaciones sep–oct −1,385); 2026 YTD +6.82 % con la posición abierta.
- **Siguiente experimento propuesto**: ninguno sobre esta curva. Deuda para el reporte: sintetizar la posición abierta al cierre como trade (regla simétrica, gane o pierda) para que PF y equity cuenten lo mismo; corregir el desfase de una vela del B&H filtrado; listar fechas de `protection_triggered`.
