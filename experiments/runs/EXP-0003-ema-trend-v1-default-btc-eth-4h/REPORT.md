# EXP-0003 — ema_trend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares BTC/USDT, ETH/USDT, hash 183890dbdbc6
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 %
- Reproducibilidad: git c78726e, params b978b0fa53, datos 183890dbdbc6, 1.9 s en PC-Joaco

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
| Retorno total | +69.89 % | +972.20 % | +1439.95 % |
| CAGR | +9.10 % | +47.67 % | +56.72 % |
| Sharpe (diario) | 1.17 | 0.93 | 0.99 |
| Sortino (diario) | 2.31 | 1.37 | 1.42 |
| Calmar | 1.26 | 0.62 | 0.71 |
| Max drawdown / mayor tramo bajo agua | +7.23 % / 573 d | +77.04 % / 851 d | +79.35 % / 1132 d |
| Profit factor | 2.60 | — | — |
| Win rate | +41.77 % | — | — |
| Expectancy por trade | 88.64 | — | — |
| Trades / duración media | 79 / 114.8 h | 0 / — h | 0 / — h |
| Exposición | +13.35 % | +99.99 % | +99.99 % |
| Fees pagados / shortfall medio | 488.54 / 5.0 bps | 10.00 / 5.0 bps | 10.00 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 16,989.46 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +1.00 % | +3.61 % | 4 | 100.43 |
| 2020 | +25.90 % | +6.23 % | 19 | 2,241.86 |
| 2021 | +13.44 % | +5.57 % | 13 | 2,087.20 |
| 2022 | +4.47 % | +3.87 % | 9 | 646.56 |
| 2023 | +2.16 % | +4.43 % | 15 | 327.91 |
| 2024 | +11.66 % | +7.23 % | 14 | 1,799.13 |
| 2025 | -1.18 % | +2.71 % | 5 | -200.65 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 40 | 3,371.54 | +40.00 % |
| ETH/USDT | 39 | 3,630.89 | +43.59 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 1 |
| stop | 22 |
| trailing | 56 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| — | 0 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ETH/USDT | 2025-08-22 20:00 @ 4835.42 | 2025-08-25 07:59 @ 4585.23 | stop | -179.63 | -5.37 % |
| ETH/USDT | 2025-06-03 20:00 @ 2626.51 | 2025-06-05 19:59 @ 2536.88 | trailing | -155.96 | -3.61 % |
| ETH/USDT | 2023-12-14 20:00 @ 2294.14 | 2023-12-15 23:59 @ 2207.95 | stop | -155.77 | -3.95 % |
| ETH/USDT | 2022-02-15 16:00 @ 3124.18 | 2022-02-17 15:59 @ 2970.72 | stop | -152.59 | -5.11 % |
| ETH/USDT | 2021-12-08 20:00 @ 4383.57 | 2021-12-09 19:59 @ 4124.24 | stop | -151.60 | -6.11 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ETH/USDT | 2020-01-27 00:00 @ 168.00 | 2020-02-16 03:59 @ 260.07 | trailing | 1,399.97 | +54.55 % |
| BTC/USDT | 2024-11-06 04:00 @ 74385.71 | 2024-11-25 15:59 @ 95664.07 | trailing | 1,111.77 | +28.38 % |
| ETH/USDT | 2020-12-26 16:00 @ 628.83 | 2021-01-04 11:59 @ 901.49 | trailing | 950.36 | +43.12 % |
| BTC/USDT | 2023-10-16 16:00 @ 28078.20 | 2023-11-03 11:59 @ 34172.96 | trailing | 810.58 | +21.48 % |
| ETH/USDT | 2021-04-26 04:00 @ 2456.13 | 2021-05-10 23:59 @ 3742.45 | trailing | 739.65 | +52.12 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: iterar
- **Por qué**: la hipótesis sobrevive en su forma débil: DD 7.2 % vs 77.0 % de B&H BTC, +69.9 % vs +972 % (cede el 93 % del retorno), 2022 +4.5 % con DD 3.9 %, Sharpe 1.17 > 0.93, PF 2.60, 2020–2024 todos positivos. Pero la evidencia de edge es fina: 79 trades (< 100 del gate); Sharpe con error estándar ≈ 0.53 (indistinguible de B&H); los 10 mejores trades son el 111 % del PnL (sin ellos, −773 USDT) y el PF sin los 5 mejores cae a 1.46; 2022 depende de 2 trades del 2022-03-16 (+929; sin ellos −2.0 %) y tiene 9 entradas contra la alarma de 6 de la spec; 2023 sin el BTC de octubre (+811) = −483; 2025 (8 meses) PF 0.4. B&H BTC escalado a la misma volatilidad (k = 0.122): +51.8 % / DD 14.2 %; la estrategia gana, pero por 10 trades. Nada refutado, nada probado.
- **Qué se aprendió**: (1) La salida por señal es letra muerta (1/79): con trailing 3×ATR la posición sale siempre antes del cruce EMA20 < EMA50; la estrategia efectiva es "cruce + chandelier". 23 de 56 trailing son perdedores (subió 1–3 ATR y devolvió). (2) 12 de 22 stops saltan en ≤ 24 h (≤ 6 velas): la entrada por cruce llega tarde y 2 ATR queda dentro del ruido de las primeras velas; los 22 stops son perdedores (−2,748). (3) Sizing: 39/79 trades pegados al tope del 25 % del cash (riesgo real < 1 %); los stops cuestan −0.94 % mediana / −1.05 % máx del equity, así que el 1 % se cumple; el CAGR de 9 % es en parte una decisión de sizing, no solo de señal. (4) Costos (fees 489 + slippage 244 = 733) = 9.5 % del bruto: la ejecución no es el problema. (5) Exposición 13 %, beta 0.04 contra BTC: el DD bajo es en gran parte estar en cash; 573 días bajo agua (2022-03-29 → 2023-10-23). (6) 20 de 79 trades son entradas simultáneas BTC+ETH; con 2 pares y 3 slots el RiskManager no actúa nunca (0 eventos): ranking y límites siguen sin validar. (7) Σpnl de `trades.csv` (7,002.43) − Δequity (6,989.46) = 12.96 USDT (0.19 %): es el costo de entrada de los restos por debajo del `stepSize` (dust), que `Trade.pnl` no descuenta y el equity excluye; el reporte debería mostrar el dust (deuda para la Fase 6). (8) Fase 5: las protecciones declaradas en este `config.yaml` (pérdida diaria 3 %, DD 20 %) no estaban implementadas cuando se corrió; recargarlo con el código de la Fase 5 las aplica. La reproducción exacta es EXP-0004 (protecciones en `null`).
- **Siguiente experimento propuesto**: (a) EXP-0004: mismos defaults, 4h, universo v1 completo (8 pares, SOL desde 2020-08-11), 2019-08-01 → 2025-09-01; busca N ≥ 100 y activa `max_positions=3` + ranking por ADX. Refuta si PF < 1.3 o si el top 10 vuelve a ser > 100 % del PnL. (b) EXP-0005: idem con `entry_mode=state`, `cooldown_candles=2`. Confirma si N sube ≥ 30 % con PF sin top 5 ≥ 1.5 y costos < 20 % del bruto; refuta si PF < 1.3. (c) EXP-0006: `cross` con `stop_atr_mult=3.0` (dentro de 1.5–4.0). Confirma si los stops ≤ 24 h caen a la mitad sin bajar el PF sin top 5; si el PF no mejora, el problema es la entrada tardía, no el stop → priorizar 1h o `state`. (d) Después WF-0001 (IS 24 m / OOS 6 m) con defaults sobre 8 pares, Monte Carlo 5,000 corridas (DD p95 con esta concentración) y meseta ±20 %. No elegir entre (a)–(c) por retorno full-sample: el optimizador corre solo en IS.
