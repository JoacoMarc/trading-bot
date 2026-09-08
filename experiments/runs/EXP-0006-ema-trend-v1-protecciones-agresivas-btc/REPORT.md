# EXP-0006 — ema_trend 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v1.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares BTC/USDT, ETH/USDT, hash 183890dbdbc6
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 1.0 % (día UTC), circuit breaker DD 5 % (reanuda bajo 2 % o tras 30 d), pausa 12 velas tras 3 pérdidas seguidas, cooldown tras stop 6 velas
- Reproducibilidad: git 8def2fc, params b978b0fa53, datos 183890dbdbc6, 1.8 s en PC-Joaco

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
| Retorno total | +65.39 % | +972.20 % | +1439.95 % |
| CAGR | +8.62 % | +47.67 % | +56.72 % |
| Sharpe (diario) | 1.14 | 0.93 | 0.99 |
| Sortino (diario) | 2.26 | 1.37 | 1.42 |
| Calmar | 1.12 | 0.62 | 0.71 |
| Max drawdown / mayor tramo bajo agua | +7.73 % / 573 d | +77.04 % / 851 d | +79.35 % / 1132 d |
| Profit factor | 2.56 | — | — |
| Win rate | +40.79 % | — | — |
| Expectancy por trade | 86.20 | — | — |
| Trades / duración media | 76 / 116.6 h | 0 / — h | 0 / — h |
| Exposición | +12.99 % | +99.99 % | +99.99 % |
| Fees pagados / shortfall medio | 458.50 / 5.0 bps | 10.00 / 5.0 bps | 10.00 / 5.0 bps |

Rango: 2019-08-01 03:59 → 2025-08-31 23:59 UTC (2223 días, 13336 velas). Equity inicial 10,000.00 → final 16,538.85 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2019 | +1.00 % | +3.61 % | 4 | 100.43 |
| 2020 | +25.90 % | +6.23 % | 19 | 2,241.86 |
| 2021 | +11.03 % | +6.04 % | 12 | 1,780.23 |
| 2022 | +4.48 % | +3.86 % | 9 | 632.83 |
| 2023 | +2.16 % | +4.43 % | 15 | 320.91 |
| 2024 | +11.06 % | +7.73 % | 12 | 1,670.42 |
| 2025 | -1.18 % | +2.71 % | 5 | -195.31 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 40 | 3,311.40 | +40.00 % |
| ETH/USDT | 36 | 3,239.97 | +41.67 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 1 |
| stop | 21 |
| trailing | 54 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| entry_rejected:drawdown_halt | 2 |
| protection_cleared:consecutive_losses | 8 |
| protection_cleared:daily_loss_limit | 28 |
| protection_cleared:drawdown_halt | 3 |
| protection_cleared:pair_cooldown | 44 |
| protection_triggered:consecutive_losses | 8 |
| protection_triggered:daily_loss_limit | 28 |
| protection_triggered:drawdown_halt | 3 |
| protection_triggered:pair_cooldown | 44 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ETH/USDT | 2025-08-22 20:00 @ 4835.42 | 2025-08-25 07:59 @ 4585.23 | stop | -174.85 | -5.37 % |
| ETH/USDT | 2023-12-14 20:00 @ 2294.14 | 2023-12-15 23:59 @ 2207.95 | stop | -152.46 | -3.95 % |
| ETH/USDT | 2025-06-03 20:00 @ 2626.51 | 2025-06-05 19:59 @ 2536.88 | trailing | -151.82 | -3.61 % |
| ETH/USDT | 2022-02-15 16:00 @ 3124.18 | 2022-02-17 15:59 @ 2970.72 | stop | -149.33 | -5.11 % |
| ETH/USDT | 2021-12-08 20:00 @ 4383.57 | 2021-12-09 19:59 @ 4124.24 | stop | -148.38 | -6.11 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| ETH/USDT | 2020-01-27 00:00 @ 168.00 | 2020-02-16 03:59 @ 260.07 | trailing | 1,399.97 | +54.55 % |
| BTC/USDT | 2024-11-06 04:00 @ 74385.71 | 2024-11-25 15:59 @ 95664.07 | trailing | 1,082.22 | +28.38 % |
| ETH/USDT | 2020-12-26 16:00 @ 628.83 | 2021-01-04 11:59 @ 901.49 | trailing | 950.36 | +43.12 % |
| BTC/USDT | 2023-10-16 16:00 @ 28078.20 | 2023-11-03 11:59 @ 34172.96 | trailing | 793.33 | +21.48 % |
| ETH/USDT | 2021-04-26 04:00 @ 2456.13 | 2021-05-10 23:59 @ 3742.45 | trailing | 723.91 | +52.12 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (niveles agresivos en BTC+ETH; la mecánica del ADR-0007 queda validada)
- **Por qué**: cuesta sin proteger: −450.61 USDT (+65.4 % vs +69.9 %), Sharpe 1.17 → 1.14, DD 7.23 % → 7.73 %, mismo tramo bajo agua (573 d), 76 vs 79 trades, PF 2.60 → 2.56. El breaker disparó 3 veces (2020-03-08 5.07 %, 2021-03-04 5.29 %, 2024-01-03 5.10 %), siempre en la vela del fill de un stop, y las 3 veces reanudó por plazo de 30 d, 0 por nivel (en cash el DD no se movió). Bloqueó 3 entradas, todas ETH: 2021-03-29 +284.17, 2024-01-10 +192.44, 2024-01-31 −109.84 (+366.77 no capturado; los −84.27 restantes son posiciones más chicas en los 73 trades comunes). El halt de marzo 2020 no bloqueó nada: el filtro EMA200 ya tenía la estrategia en cash. Pérdida diaria (28), pausa (8) y cooldown (44) dispararon sin bloquear ninguna entrada. Los 2 eventos `entry_rejected` son 3 rechazos: los dos de ETH de enero 2024 colapsaron por par+motivo (corregido después de esta corrida: el dedupe solo aplica a velas consecutivas con señal).
- **Qué se aprendió**: (1) El DD subió con un breaker al 5 % porque el re-base tras 30 d convierte el 5 % en tope por episodio, no desde el máximo histórico: tras re-basar en 14,964.23 el 2024-02-02, los stops de marzo–abril midieron 2.77 % y no dispararon, mientras desde el pico real (15,768.23, 2023-11-02) el DD llegó a 7.73 %; y el +192.44 evitado había levantado la curva de EXP-0003 antes de esos stops. (2) Dispara después del stop, nunca antes: no recorta pérdidas, solo posterga la reanudación (episodios bajo agua 75/120/373 d → 75/125/374 d). (3) Con riesgo 1 %/trade, 1 % diario ≈ un stop o la devolución de un trailing (30 días ≥ 1 % en 6 años, 0 ≥ 3 %) y 5 % de DD = devolución de un trailing ganador + 2–6 salidas perdedoras (3 veces en 6 años, ninguna en un crash): los niveles agresivos miden la unidad de pérdida de la estrategia, no la cola. (4) El cooldown de 6 velas es redundante con `cross`: la reentrada mínima tras salida perdedora en el mismo par fue 7 velas (ETH 2023-12-26 → 12-27), la siguiente 17. (5) La pausa de 12 velas quedó a 4 velas de morder dos veces (+16 el 2023-12-27, +18 el 2021-04-26, que ganó +739.65). (6) El encabezado dice "reanuda bajo 2 %" por un `:.0f` en 8def2fc; el nivel efectivo fue 2.5 % (corregido para las próximas corridas).
- **Siguiente experimento propuesto**: no volver a probar 5 % / 1 % en BTC+ETH. EXP-0007: universo v1 (8 pares, SOL desde 2020-08-11), 4h, defaults 3 % / 20 %, pausa off, cooldown off; mide días ≥ 3 % y DD máximo con 3 slots ocupados. Si allí hay ≥ 5 disparos diarios o DD > 12 %, EXP-0008 = mismo universo con pausa 3 × 12 velas y cooldown 8 velas (el mínimo que mordería): confirma si el DD desde el máximo histórico baja ≥ 1 pp o el tramo bajo agua ≥ 30 d cediendo ≤ 2 pp de retorno; refuta si vuelve a costar retorno sin bajar el DD. Para la Fase 6, decidir si el re-base tras `drawdown_pause_days` va a pico × (1 − resume) en vez de a la equity actual, para que el umbral siga midiendo desde el máximo histórico.
