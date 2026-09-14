# WF-0003 — ema_trend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v2.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 4d776a274063; activación tardía: LINK/USDT desde 2019-08-04, SOL/USDT desde 2021-02-27
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git 1a8c36b, params 3067ccea6a, datos 4d776a274063, 314.1 s en PC-Joaco

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
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +20.68 % | 1.80 | 15.07 % | 76 | 1.58 | 0 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | -9.33 % | -0.94 | 18.28 % | 46 | 0.57 | 3 (+98.96) |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +5.54 % | 0.68 | 15.83 % | 78 | 1.13 | 3 (+136.37) |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -6.24 % | -0.60 | 11.45 % | 93 | 0.81 | 1 (-17.56) |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +4.82 % | 0.52 | 10.41 % | 92 | 1.14 | 2 (-48.08) |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +23.87 % | 1.77 | 15.00 % | 80 | 1.72 | 1 (-95.06) |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +14.88 % | 1.26 | 13.02 % | 96 | 1.41 | 1 (-9.05) |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | -3.61 % | -0.14 | 16.75 % | 83 | 0.90 | 1 (-17.67) |

12 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) |
|---|---|---|
| Retorno total | +55.68 % | +175.83 % |
| CAGR | +11.70 % | +28.87 % |
| Sharpe (diario) | 0.64 | 0.76 |
| Sortino (diario) | 0.99 | 1.12 |
| Calmar | 0.39 | 0.37 |
| Max drawdown / mayor tramo bajo agua | +30.39 % / 848 d | +77.11 % / 852 d |
| Profit factor | 1.19 | — |
| Win rate | +33.54 % | — |
| Expectancy por trade | 7.94 | — |
| Trades / duración media | 644 / 85.7 h | 0 / — h |
| Exposición | +64.83 % | +100.00 % |
| Fees pagados / shortfall medio | 2,275.69 / 5.5 bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 15,567.85 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +184.13 %, Sharpe 0.83, max DD +35.97 %, 953 trades.

## Gate 1 — backtest -> paper: no aprobado (6 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.64 | FALLA |  |
| Profit factor OOS | >= 1.3 | 1.19 | FALLA |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 30.39 % | FALLA |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 5/8 (62 %) | OK | secundario |
| Trades muestra completa | >= 100 | 953 | OK |  |
| Trades curva OOS | >= 40 | 644 | OK |  |
| Régimen: retorno 2020 | > 0 | +71.72 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +61.63 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +21.53 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | +39.01 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | -24.43 % | FALLA | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 28.72 % (2022) | FALLA | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 92.86 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 38.61 % | FALLA |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -13.77 % | 17.42 % | 53 | -1,375.90 |
| 2020 | +71.72 % | 18.84 % | 187 | 5,032.77 |
| 2021 | +61.63 % | 22.68 % | 176 | 10,304.20 |
| 2022 | -24.43 % | 28.72 % | 111 | -5,836.45 |
| 2023 | +21.53 % | 14.41 % | 178 | 4,091.28 |
| 2024 | +39.01 % | 21.56 % | 162 | 8,412.31 |
| 2025 (parcial) | -7.00 % | 22.14 % | 86 | -2,064.48 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 644 trades, semilla 42: max DD p50 +18.36 %, p95 +38.61 %, p99 +51.80 %; retorno p05 -8.96 %, p50 +50.38 %.

## Meseta ±20 %

42 variantes, pasan +92.86 % (PF > 1.1 y retorno > 0). Informativo: +97.62 % de las variantes tiene Sharpe >= 0.5 x el base (0.83). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| adx_threshold=16.0, ema_fast=16, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +38.41 % | 1.05 | 0.33 | 1426 | no |
| adx_threshold=16.0, ema_fast=24, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +61.34 % | 1.08 | 0.43 | 1395 | no |
| adx_threshold=16.0, ema_fast=16, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +74.72 % | 1.09 | 0.48 | 1385 | no |
| adx_threshold=16.0 | +93.62 % | 1.15 | 0.57 | 1049 | sí |
| adx_threshold=16.0, ema_fast=24, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +100.02 % | 1.11 | 0.55 | 1403 | sí |
| adx_threshold=24.0, ema_fast=24, ema_slow=40, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +111.30 % | 1.16 | 0.74 | 948 | sí |
| adx_threshold=24.0, ema_fast=24, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +115.05 % | 1.13 | 0.61 | 1093 | sí |
| adx_threshold=24.0, ema_fast=24, ema_slow=60, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +126.96 % | 1.17 | 0.79 | 988 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (`state` en 4h refutado: PF OOS 1.19 < 1.2, DD 30 %)
- **Por qué**: la spec v2 fijó antes de correr que PF OOS < 1.2 refuta `state` en 4h y dio 1.193 (Sharpe 0.64 en zona intermedia no la salva: la refutación es binaria). Gate 1 falla 6 criterios: Sharpe 0.64 < 0.8 y < 0.76 del B&H BTC, PF 1.19, DD OOS 30.39 % (pico 2021-11-10 → valle 2023-01-01, 848 d bajo agua), 2022 −24.43 % con DD intra-año 28.72 %, MC p95 38.61 %. Contra WF-0001 (mismo `data_hash`) el retorno sube de +23.4 % a +55.7 % pero con ×3.95 trades, exposición 25.7 → 64.8 %, vol ×1.76 y DD ×2.1; la diferencia diaria pareada es t = 0.87 (corr 0.55): no hay evidencia de más edge, solo de más apalancamiento efectivo. Las alarmas de la spec para 2022 saltaron las dos (−24.43 % vs −8 %; 122 entradas vs 40).
- **Qué se aprendió**: (1) La re-entrada sí hizo su parte: 191 re-entradas tras stop en el mismo par aportaron +2,015 (39 % del PnL OOS) con PF 1.26, y las ≤ 48 h tuvieron win rate 38 % y PF 1.51; alargar el cooldown sería quitar lo único que funcionó. (2) Lo que refuta a `state` es la entrada a mitad de tendencia: 192 stops todos perdedores (−16,211 = 3.2× el PnL), 63 % en ≤ 24 h (v1 46 %), 190 trades ≤ 24 h que suman −12,256, y 98 salidas por señal con win rate 20 % (v1: 6): entra cuando la EMA20 apenas supera la EMA50 y el cruce inverso la saca. La patología "todos los stops pierden, la mayoría en el día" se repite en EXP-0007, WF-0001 y WF-0003: es la entrada, no el parámetro. (3) El DD no es un evento sino diseño de cartera: 40 % del tiempo con los 3 slots llenos sobre pares con correlación diaria media 0.65 (0.78 en 2022) equivale a una sola apuesta de ≈ 2.6 % de riesgo, no tres de 1 %; beta a BTC 0.22 vs 0.08 en v1; además de la caída de 30 %, hay dos episodios de 23 % en 2024-25 (MC p50 18 %). El filtro EMA200 por par no deja al bot afuera en un bear: 122 entradas en 2022. (4) La mejora de concentración (top 2 41 % vs 85 %, top 10 143 % vs 230 %) es real pero el cuerpo de la distribución sigue sin edge: PF sin los 10 mejores 0.92. Los costos pasan el criterio de la spec (10.7 % del bruto ganador) pero son el 39.8 % del PnL antes de costos (v1 29.6 %) y las fees se llevan el 44 % del neto. (5) La meseta 39/42 (98 % relativa) vuelve a ser una pendiente: ADX 24 y trailing 3.5 dan +442 % y +468 % en la muestra completa; adoptarlos ahora sería elegir mirando el resultado, y las dos direcciones significan "operar menos", que es el diagnóstico, no la solución. (6) El WF no registra los rechazos del RiskManager: agregar el conteo de `entry_rejected:*` por ventana al `REPORT.md` antes de la próxima corrida.
- **Siguiente experimento propuesto**: WF-0004 (1h, misma lógica, `--plateau`, MC 5,000) es la última corrida de la familia según la spec. Expectativa escrita antes de verlo: el ATR(14) en 1h es ≈ la mitad del de 4h, así que el stop en precio se acerca al ruido y la fracción de stops ≤ 24 h debería subir, no bajar; con ≈ 2,000–2,500 trades OOS y 30 bps de costo ida y vuelta contra un `pnl_pct` medio que en 4h fue 0.82 %, los costos deberían superar el 40 % del PnL bruto y el PF quedar ≤ 1.15, Sharpe ≤ 0.6. Cierre: si WF-0004 no aprueba el Gate 1 completo (Sharpe OOS ≥ 0.8 y ≥ B&H, PF ≥ 1.3, DD ≤ 25 %, 2022 ≥ −8 %, MC p95 ≤ 35 %), `no-go` de la familia `ema_trend` (cross/state × 4h/1h × fijo/optimizado agotados) sin gastar el holdout; no vale zona intermedia. Spec siguiente (v3, una idea): **entrada por pullback dentro de la tendencia**: mismas condiciones de estado (EMA20 > EMA50, close > EMA200, ADX > 20) pero se entra solo después de que el close cierre bajo la EMA20 y vuelva a cerrar por encima, con stop bajo el mínimo del pullback (no 2 ATR desde un close extendido); trailing 3.0 y salida por cruce sin cambios; riesgo agregado abierto declarado en la spec (≤ 2 % de la equity entre todos los slots, porque ρ ≈ 0.65 hace que 3 × 1 % sean ≈ 2.6 %). Confirma si Sharpe OOS ≥ 0.8 y ≥ B&H, PF ≥ 1.3, DD OOS ≤ 25 %, stops ≤ 24 h ≤ 40 % de los stops, 2022 ≥ −8 %. Refuta si PF OOS < 1.2 o Sharpe OOS ≤ 0.5 o los stops ≤ 24 h siguen ≥ 50 %: en ese caso la entrada no era el problema y la siguiente palanca es el filtro de mercado a nivel cartera (BTC > EMA200 diaria y retorno 30 d > 0 para habilitar entradas), no otra variante de entrada. No hacer: recortar LTC/ADA por PnL, tomar ADX 24 o trailing 3.5 de la meseta, alargar el cooldown, `--include-holdout`.
