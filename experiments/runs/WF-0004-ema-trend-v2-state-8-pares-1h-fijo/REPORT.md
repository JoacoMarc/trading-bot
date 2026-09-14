# WF-0004 — ema_trend 1h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v2.md`
- Datos: binance 1h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 8cda40027e99; activación tardía: SOL/USDT desde 2020-09-30
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git 1a8c36b, params 3067ccea6a, datos 8cda40027e99, 1274.3 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `adx_period` | `14` |
| `adx_threshold` | `20.0` |
| `atr_period` | `14` |
| `cooldown_candles` | `2` |
| `ema_fast` | `20` |
| `ema_regime` | `200` |
| `ema_slow` | `50` |
| `entry_mode` | `state` |
| `stop_atr_mult` | `2.0` |
| `trailing_atr_mult` | `3.0` |
| `warmup_multiplier` | `6` |

## Ventanas

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +9.33 % | 0.97 | 23.42 % | 293 | 1.09 | 3 (+16.23) |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | -4.07 % | -0.42 | 18.10 % | 256 | 0.94 | 0 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | -12.06 % | -0.94 | 18.51 % | 324 | 0.83 | 1 (-29.05) |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | +0.89 % | 0.30 | 11.90 % | 325 | 1.02 | 0 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | -3.23 % | -0.19 | 13.87 % | 346 | 0.96 | 1 (-5.52) |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | -24.29 % | -2.19 | 30.84 % | 338 | 0.71 | 1 (-34.74) |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +0.65 % | 0.25 | 17.92 % | 373 | 1.02 | 3 (-6.67) |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -17.61 % | -1.28 | 24.12 % | 294 | 0.74 | 0 |

9 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) |
|---|---|---|
| Retorno total | -43.45 % | +175.83 % |
| CAGR | -13.28 % | +28.87 % |
| Sharpe (diario) | -0.39 | 0.76 |
| Sortino (diario) | -0.59 | 1.12 |
| Calmar | -0.21 | 0.37 |
| Max drawdown / mayor tramo bajo agua | +62.69 % / 1359 d | +77.27 % / 850 d |
| Profit factor | 0.92 | — |
| Win rate | +29.66 % | — |
| Expectancy por trade | -1.83 | — |
| Trades / duración media | 2549 / 21.1 h | 0 / — h |
| Exposición | +63.80 % | +100.00 % |
| Fees pagados / shortfall medio | 9,272.67 / 5.4 bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 5,654.79 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno -19.97 %, Sharpe 0.02, max DD +60.90 %, 3607 trades.

## Gate 1 — backtest -> paper: no aprobado (9 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | -0.39 | FALLA |  |
| Profit factor OOS | >= 1.3 | 0.92 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.27 %) | 62.69 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 3/8 (38 %) | FALLA | secundario |
| Trades muestra completa | >= 100 | 3607 | OK |  |
| Trades curva OOS | >= 40 | 2549 | OK |  |
| Régimen: retorno 2020 | > 0 | +45.46 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +46.99 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +7.24 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -25.51 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | -19.34 % | FALLA | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 35.74 % (2021) | FALLA | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 0.00 % | FALLA |  |
| Monte Carlo DD p95 | <= 35 % | 113.87 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -23.63 % | 24.77 % | 223 | -2,358.74 |
| 2020 | +45.46 % | 19.71 % | 693 | 3,488.37 |
| 2021 | +46.99 % | 35.74 % | 576 | 5,295.47 |
| 2022 | -19.34 % | 23.42 % | 485 | -3,216.73 |
| 2023 | +7.24 % | 17.80 % | 691 | 1,096.30 |
| 2024 | -25.51 % | 35.63 % | 635 | -3,521.70 |
| 2025 (parcial) | -23.94 % | 32.85 % | 304 | -2,441.58 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 2549 trades, semilla 42: max DD p50 +62.67 %, p95 +113.87 %, p99 +141.15 %; retorno p05 -107.61 %, p50 -47.54 %.

## Meseta ±20 %

42 variantes, pasan +0.00 % (PF > 1.1 y retorno > 0). Informativo: +45.24 % de las variantes tiene Sharpe >= 0.5 x el base (0.02). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| adx_threshold=16.0, ema_fast=24, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -87.80 % | 0.87 | -1.15 | 4989 | no |
| adx_threshold=16.0, ema_fast=16, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -70.56 % | 0.92 | -0.56 | 4984 | no |
| adx_threshold=16.0, ema_fast=16, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -65.19 % | 0.94 | -0.45 | 5122 | no |
| adx_threshold=16.0, ema_fast=24, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -61.54 % | 0.95 | -0.39 | 5101 | no |
| adx_threshold=24.0, ema_fast=24, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -59.23 % | 0.93 | -0.42 | 3907 | no |
| adx_threshold=24.0, ema_fast=16, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -57.58 % | 0.94 | -0.39 | 3985 | no |
| adx_threshold=24.0, ema_fast=24, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -57.29 % | 0.94 | -0.38 | 3954 | no |
| adx_threshold=24.0, ema_fast=16, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | -56.57 % | 0.93 | -0.38 | 3854 | no |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (1h refutada por costos; familia `ema_trend` cerrada)
- **Por qué**: Gate 1 falla 9 criterios y la spec v2 no admite zona intermedia. Curva OOS −43.45 %, Sharpe −0.39, PF 0.92, DD 62.69 % (pico 2021-09-06, 1,359 d bajo agua = 93 % del período) vs B&H BTC +175.8 %; 2022 −20.4 % y 2024 −29.6 % con BTC +120.6 %; muestra completa −19.97 % con 16,142 de fees (161 % del capital). Las 4 predicciones escritas en WF-0003 se cumplieron por exceso: 749 stops, 0 ganadores, 98.9 % ≤ 24 h (4h: 63 %); costos = 148 % del bruto antes de costos (predicho > 40 %); PF 0.92 ≤ 1.15; Sharpe −0.39 ≤ 0.6. No es ruido (2,549 trades) ni un par o un año: 7/8 pares negativos, todas las ventanas PF ≤ 1.09, todos los años PF ≤ 1.14, top 10 trades +5,153 y PF sin ellos 0.84.
- **Qué se aprendió**: (1) El −43 % es 100 % costos: bruto antes de costos +9,629 (t = 2.55), fees −9,254, slippage ≈ −5,041, neto −4,666 (t = −1.23). Con 231× el capital de turnover anual y 30.9 bps por ida y vuelta, la 1h necesita ≥ 31 bps brutos por trade y produce 20.8: ninguna variante de `ema_trend` con tenencia ≈ 1 día es viable con estos costos, y la meseta lo confirma (0/42; las únicas con Sharpe > 0.3 son las que operan menos). (2) Lo único que gana son los trades que sobreviven al primer día (845, win rate 69.7 %, +47,856) contra 1,704 ≤ 24 h que pierden −52,522 (win rate 9.8 %): la patología de entrar a mitad de tendencia con el stop dentro del ruido (EXP-0007 → WF-0003 → WF-0004) escala con la frecuencia. (3) La re-entrada tras stop, único hallazgo positivo de WF-0003 (+2,015, PF 1.26), da PF 1.00 en 1h: no era edge, era el tramo alcista en 4h. (4) El filtro EMA200 por par no protege la cartera: 2022 −20.4 % con 530 entradas y 2024 −29.6 % en un año de BTC +120 %. (5) Herramientas: el DD del Monte Carlo queda acotado a 100 % y el REPORT del WF ya muestra los rechazos por slots por ventana (pendientes desde WF-0003, aplicados en esta sesión).
- **Siguiente experimento propuesto**: cierre formal: spec v2 → `descartada`; familia `ema_trend` agotada (EXP-0007, WF-0001..0004: cross/state × 4h/1h × fijo/optimizado, todo `no-go`), holdout intacto. Quedan 1–2 iteraciones; dos caminos, ambos en **4h** (1h descartada por costos), WF fijo con `--plateau`, MC 5,000, semilla 42, control = WF-0003 (mismo `data_hash`). **(a) spec `ema-trend-v3`, entrada por pullback**: mismas condiciones de estado (EMA20 > EMA50, close > EMA200, ADX > 20) pero se entra solo cuando el close cierra bajo la EMA20 y vuelve a cerrar encima; stop bajo el mínimo del pullback (mín. 1.0 ATR, máx. 2.0 ATR); trailing 3.0 y salida por cruce sin cambios; riesgo agregado abierto ≤ 2 % de la equity (3 × 1 % con ρ ≈ 0.65 eran ≈ 2.6 %). Confirma: Sharpe OOS ≥ 0.8 y ≥ B&H, PF ≥ 1.3, DD ≤ 25 %, stops ≤ 24 h ≤ 40 % de los stops, 2022 ≥ −8 %, ≥ 100 trades muestra completa. Refuta: PF < 1.2 o Sharpe ≤ 0.5 o stops ≤ 24 h ≥ 50 % o < 40 trades OOS (el pullback puede vaciar la muestra). **(b) nueva familia `regime-gated`, filtro de mercado a nivel cartera**: entradas habilitadas solo si el close diario de BTC > EMA200 diaria y el retorno de BTC a 30 d > 0 (salidas nunca bloqueadas; va en `risk/` como protección, no en la estrategia; umbrales redondos y sin optimizar, porque el filtro se diseña sabiendo que 2022 fue el año malo); estrategia interna = `ema_trend` v2 `state` 4h sin tocar, para que el único cambio respecto de WF-0003 sea el filtro. Benchmark obligatorio: B&H BTC filtrado (BTC con filtro on, cash si off). Confirma: 2022 ≥ −8 %, DD OOS ≤ 25 %, Sharpe OOS ≥ 0.8 y ≥ B&H filtrado, PF ≥ 1.3, y 2023–24 conservan ≥ 70 % del PnL de WF-0003. Refuta: Sharpe OOS < 0.64 (peor que sin filtro) o PF < 1.2 o Sharpe ≤ el del B&H filtrado (el edge sería el filtro, no la estrategia). Recomendación: (b) primero, porque ataca la falla común a las 4 corridas (2022 y DD) con una sola variable contra un control existente; (a) reduce trades y puede quedar sin muestra. No hacer: 1h en ninguna variante, recortar pares por PnL, tomar ADX 24 / trailing 3.5 de la meseta, `--include-holdout`.
