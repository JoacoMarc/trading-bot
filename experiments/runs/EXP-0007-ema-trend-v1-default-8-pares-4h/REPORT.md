# EXP-0007 — ema_trend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 4d776a274063; activación tardía: LINK/USDT desde 2019-08-04, SOL/USDT desde 2021-02-27
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off
- Reproducibilidad: git 571beeb, params b978b0fa53, datos 4d776a274063, 6.8 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `adx_period` | `14` |
| `adx_threshold` | `20.0` |
| `atr_period` | `14` |
| `cooldown_candles` | `2` |
| `ema_fast` | `20` |
| `ema_regime` | `200` |
| `ema_slow` | `50` |
| `entry_mode` | `cross` |
| `stop_atr_mult` | `2.0` |
| `trailing_atr_mult` | `3.0` |
| `warmup_multiplier` | `6` |

## Métricas

| Métrica | Estrategia | B&H BTC | Equiponderado |
|---|---|---|---|
| Retorno total | +76.86 % | +972.20 % | +1251.80 % |
| CAGR | +9.82 % | +47.67 % | +53.40 % |
| Sharpe (diario) | 0.75 | 0.93 | 0.95 |
| Sortino (diario) | 1.29 | 1.37 | 1.35 |
| Calmar | 0.64 | 0.62 | 0.66 |
| Max drawdown / mayor tramo bajo agua | +15.45 % / 458 d | +77.04 % / 851 d | +81.13 % / 1390 d |
| Profit factor | 1.46 | — | — |
| Win rate | +34.68 % | — | — |
| Expectancy por trade | 31.09 | — | — |
| Trades / duración media | 248 / 94.3 h | 0 / — h | 0 / — h |
| Exposición | +25.73 % | +99.99 % | +99.99 % |
| Fees pagados / shortfall medio | 1,422.69 / 5.6 bps | 10.00 / 5.0 bps | 10.00 / 6.4 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 17,685.95 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | -1.98 % | +6.46 % | 7 | -198.22 |
| 2020 | +31.70 % | +10.73 % | 44 | 2,727.80 |
| 2021 | +21.85 % | +8.32 % | 42 | 3,207.18 |
| 2022 | -7.46 % | +12.39 % | 32 | -1,171.13 |
| 2023 | +19.16 % | +15.45 % | 49 | 2,793.38 |
| 2024 | +2.41 % | +11.75 % | 47 | 424.50 |
| 2025 | -0.44 % | +12.47 % | 27 | -73.18 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| ADA/USDT | 19 | -791.41 | +21.05 % |
| BNB/USDT | 41 | 620.42 | +34.15 % |
| BTC/USDT | 36 | 3,183.54 | +41.67 % |
| ETH/USDT | 34 | 3,598.11 | +47.06 % |
| LINK/USDT | 30 | 2,522.83 | +33.33 % |
| LTC/USDT | 39 | -1,127.22 | +25.64 % |
| SOL/USDT | 18 | 701.92 | +50.00 % |
| XRP/USDT | 31 | -997.87 | +25.81 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 7 |
| stop | 76 |
| trailing | 165 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:max_positions | 45 |
| protection_cleared:daily_loss_limit | 4 |
| protection_triggered:daily_loss_limit | 4 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LTC/USDT | 2025-01-30 12:00 @ 128.82 | 2025-02-01 23:59 @ 119.49 | stop | -194.63 | -7.44 % |
| XRP/USDT | 2024-06-17 20:00 @ 0.5183 | 2024-06-18 03:59 @ 0.4971 | stop | -192.20 | -4.29 % |
| XRP/USDT | 2025-03-03 00:00 @ 2.9410 | 2025-03-03 07:59 @ 2.6887 | stop | -191.39 | -8.77 % |
| XRP/USDT | 2025-05-22 16:00 @ 2.4342 | 2025-05-23 15:59 @ 2.3355 | stop | -190.75 | -4.25 % |
| XRP/USDT | 2025-03-15 04:00 @ 2.4260 | 2025-03-16 15:59 @ 2.2832 | stop | -188.84 | -6.08 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| LINK/USDT | 2023-10-20 12:00 @ 7.614 | 2023-11-13 23:59 @ 14.423 | trailing | 1,958.58 | +89.14 % |
| ETH/USDT | 2020-01-27 00:00 @ 168.00 | 2020-02-16 03:59 @ 260.07 | trailing | 1,358.55 | +54.55 % |
| BTC/USDT | 2024-11-06 04:00 @ 74385.71 | 2024-11-25 15:59 @ 95664.07 | trailing | 1,171.93 | +28.38 % |
| LTC/USDT | 2020-07-22 04:00 @ 43.93 | 2020-08-02 07:59 @ 59.08 | trailing | 1,000.95 | +34.25 % |
| ETH/USDT | 2020-12-26 16:00 @ 628.83 | 2021-01-04 11:59 @ 901.49 | trailing | 964.76 | +43.12 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (defaults v1 `cross` en 8 pares: top 10 > 100 % del PnL)
- **Alcance**: refutados por el criterio prefijado en EXP-0003; el universo de 8 pares se mantiene, lo que cambia es la estrategia → spec v2.
- **Por qué**: N llega a 248 (≥ 100) pero el edge no escala. BTC+ETH aportan 70 trades / +6,781.65 / PF 2.84 (los mismos de EXP-0003 menos 9 excluidos por slots, que sumaban −44.62); los 6 pares nuevos 178 trades / +928.67 / PF 1.07 / win rate 30.9 % con 1,011 de fees: cubren costos y nada más. Vol anual 13.6 % vs 7.7 % (×1.77) con retorno medio 10.2 % vs 9.0 % (×1.13) → Sharpe 1.17 → 0.75, por debajo del 0.93 del B&H BTC; Calmar 0.64 ≈ 0.62 del B&H. Top 5 = 84 % del PnL, top 10 = 133 % (sin ellos −2,567.59), sin top 20 −7,946.61. 2022 pasa de +4.47 % a −7.46 % (umbral −8 %) con 32 entradas (la spec alarma con 6): BTC+ETH +743.19, los otros 6 −1,914.32. Max DD 15.45 % (2022-07-30 → 2023-07-05), 458 d bajo agua.
- **Qué se aprendió**: (1) No es correlación ni slots: corr diaria con EXP-0003 0.65, beta BTC 0.07, 3 slots llenos solo el 5.1 % de las velas (2+: 11.1 %); los 45 rechazos no costaron nada. Son pares sin edge con esta regla: ADA (PF 0.41) y XRP (0.66) pierden en las dos mitades del rango, LTC (0.66) flipea (+868 → −1,967) y LINK flipea al revés (−319 → +2,127): elegir universo por PnL sería snooping. (2) 76 stops, todos perdedores (−10,231.27); 38 saltan en ≤ 24 h (−5,274.03): la entrada por cruce cae dentro del ruido y 2 ATR no la protege; 7/7 salidas por señal pierden; 79/165 trailing pierden (−6,006.50). (3) Costos 21.7 % del bruto (fees 1,422.69 + slippage ≈ 710.98) vs 9.5 % con 2 pares. (4) El 1 % de riesgo es vinculante (los stops cuestan mediana −1.00 % del equity); 61/248 en el tope del 25 %. (5) `daily_loss_limit` disparó 4 veces (2019-10-26, 2020-11-07, 2020-12-01, 2023-07-14 con −4.96 %), un día cada una, sin efecto visible. (6) Dust 24.37 USDT (Σpnl − Δequity), sigue sin mostrarse en el reporte.
- **Siguiente experimento propuesto**: ningún backtest más de rango completo con estos defaults; el veredicto de la familia lo dan WF-0001 (fijo) y WF-0002 (optimizado). La próxima iteración es la spec v2 con `entry_mode=state` (WF-0003; detalle y criterios de refutación en WF-0001).
