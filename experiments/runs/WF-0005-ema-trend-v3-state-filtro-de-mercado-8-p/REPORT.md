# WF-0005 — ema_trend 4h walk-forward IS 24 m / OOS 6 m (fijo)

> Sección autogenerada por `tradingbot walkforward`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `ema_trend` · spec: `docs/strategy/ema-trend-v3.md`
- Datos: binance 4h 2019-08-01 → 2025-09-01 (sin holdout), warmup 1200 velas, pares ADA/USDT, BNB/USDT, BTC/USDT, ETH/USDT, LINK/USDT, LTC/USDT, SOL/USDT, XRP/USDT, hash 4d776a274063; activación tardía: LINK/USDT desde 2019-08-04, SOL/USDT desde 2021-02-27
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 25 % del cash por posición, máx. 3 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > EMA200 y retorno 30 d > 0)
- Walk-forward: IS 24 m / OOS 6 m, rodante, 8 ventanas; sin usar 2025-08-01 -> 2025-09-01; modo fijo (mismos parámetros en todas las ventanas)
- Reproducibilidad: git d27b4e4, params 3067ccea6a, datos 4d776a274063, 273.9 s en PC-Joaco

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

| # | IS | OOS | Parámetros | Retorno OOS | Sharpe | Max DD | Trades | PF | Abiertas al cierre | Rechazos por slots |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2019-08-01 -> 2021-08-01 | 2021-08-01 -> 2022-02-01 | base | +29.41 % | 2.46 | 9.29 % | 53 | 2.47 | 0 | 748 |
| 2 | 2020-02-01 -> 2022-02-01 | 2022-02-01 -> 2022-08-01 | base | -1.40 % | -0.51 | 3.44 % | 7 | 0.26 | 0 | 123 |
| 3 | 2020-08-01 -> 2022-08-01 | 2022-08-01 -> 2023-02-01 | base | +0.11 % | 0.07 | 3.56 % | 6 | 0.52 | 3 (+129.35) | 122 |
| 4 | 2021-02-01 -> 2023-02-01 | 2023-02-01 -> 2023-08-01 | base | -4.67 % | -0.49 | 13.16 % | 74 | 0.81 | 0 | 617 |
| 5 | 2021-08-01 -> 2023-08-01 | 2023-08-01 -> 2024-02-01 | base | +7.90 % | 0.81 | 12.03 % | 80 | 1.25 | 2 (-101.39) | 1038 |
| 6 | 2022-02-01 -> 2024-02-01 | 2024-02-01 -> 2024-08-01 | base | +18.17 % | 1.79 | 9.44 % | 64 | 1.84 | 1 (-90.69) | 858 |
| 7 | 2022-08-01 -> 2024-08-01 | 2024-08-01 -> 2025-02-01 | base | +12.01 % | 1.12 | 11.99 % | 83 | 1.36 | 1 (-8.83) | 1030 |
| 8 | 2023-02-01 -> 2025-02-01 | 2025-02-01 -> 2025-08-01 | base | +4.49 % | 0.65 | 14.03 % | 68 | 1.19 | 1 (-19.16) | 921 |

8 posiciones seguían abiertas al cierre de su tramo: la curva OOS las valúa a mercado (sin fee de salida) y no figuran en `trades.csv` ni en PF, expectancy o Monte Carlo (ADR-0008).

## Curva OOS concatenada

| Métrica | Estrategia | B&H BTC (OOS) | B&H BTC filtrado (OOS) | Equiponderado (OOS) |
|---|---|---|---|---|
| Retorno total | +81.75 % | +175.83 % | +185.96 % | +174.95 % |
| CAGR | +16.11 % | +28.87 % | +30.04 % | +28.77 % |
| Sharpe (diario) | 0.90 | 0.76 | 0.98 | 0.72 |
| Sortino (diario) | 1.46 | 1.12 | 1.57 | 1.03 |
| Calmar | 0.80 | 0.37 | 0.97 | 0.35 |
| Max drawdown / mayor tramo bajo agua | +20.25 % / 721 d | +77.11 % / 852 d | +30.86 % / 518 d | +81.53 % / 1108 d |
| Profit factor | 1.40 | — | — | — |
| Win rate | +34.25 % | — | — | — |
| Expectancy por trade | 15.56 | — | — | — |
| Trades / duración media | 435 / 86.0 h | 0 / — h | 0 / — h | 0 / — h |
| Exposición | +41.31 % | +100.00 % | +100.00 % | +100.00 % |
| Fees pagados / shortfall medio | 1,570.46 / 5.4 bps | 0.00 / — bps | 0.00 / — bps | 0.00 / — bps |


Rango OOS 2021-08-01 -> 2025-08-01. Equity encadenada 10,000.00 -> 18,175.11 USDT.

Muestra completa con parámetros fijos (2019-08-01 -> 2025-08-01): retorno +212.83 %, Sharpe 1.00, max DD +30.37 %, 671 trades.

## Gate 1 — backtest -> paper: no aprobado (1 criterios fallan)

| Criterio | Umbral | Valor | Resultado | Nota |
|---|---|---|---|---|
| Sharpe OOS | >= 0.8 y >= B&H BTC (0.76) | 0.90 | OK |  |
| Profit factor OOS | >= 1.3 | 1.40 | OK |  |
| Max DD OOS | <= 25 % y <= 50 % del DD B&H (77.11 %) | 20.25 % | OK |  |
| Universo activo en OOS | todos los pares con datos en todas las ventanas | 8/8 | OK |  |
| Ventanas OOS positivas | >= 60 % | 6/8 (75 %) | OK | secundario |
| Trades muestra completa | >= 100 | 671 | OK |  |
| Trades curva OOS | >= 40 | 435 | OK |  |
| Régimen: retorno 2020 | > 0 | +73.24 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2021 | > 0 | +115.50 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2023 | > 0 | +17.52 % | OK | muestra completa, parámetros fijos |
| Régimen: retorno 2024 | > 0 | -0.05 % | FALLA | muestra completa, parámetros fijos |
| Régimen: retorno 2022 | >= -8 % | -3.93 % | OK | muestra completa, parámetros fijos |
| Régimen: max DD intra-año | <= 25 % | 20.64 % (2024) | OK | muestra completa, parámetros fijos |
| Meseta ±20 % | >= 80 % de variantes con PF > 1.1 y retorno > 0 | 100.00 % | OK |  |
| Monte Carlo DD p95 | <= 35 % | 25.80 % | OK |  |
| Holdout | PF > 1.1 y DD <= 25 % | - | n/a | una sola vez, al final |

## Regímenes por año (muestra completa, parámetros fijos)

| Año | Retorno | Max DD intra-año | Trades | PnL |
|---|---|---|---|---|
| 2019 (parcial) | -11.55 % | 12.36 % | 32 | -1,154.08 |
| 2020 | +73.24 % | 14.74 % | 139 | 5,285.96 |
| 2021 | +115.50 % | 11.86 % | 131 | 18,912.14 |
| 2022 | -3.93 % | 5.64 % | 10 | -1,297.36 |
| 2023 | +17.52 % | 13.14 % | 146 | 5,888.20 |
| 2024 | -0.05 % | 20.64 % | 144 | -314.60 |
| 2025 (parcial) | -16.05 % | 17.56 % | 69 | -5,805.25 |

## Monte Carlo (bootstrap de trades OOS)

5,000 corridas sobre 435 trades, semilla 42: max DD p50 +12.80 %, p95 +25.80 %, p99 +34.68 %; retorno p05 +13.21 %, p50 +66.65 %.

## Meseta ±20 %

42 variantes, pasan +100.00 % (PF > 1.1 y retorno > 0). Informativo: +100.00 % de las variantes tiene Sharpe >= 0.5 x el base (1.00). Las 8 peores:

| Cambios | Retorno | PF | Sharpe | Trades | Pasa |
|---|---|---|---|---|---|
| adx_threshold=16.0, ema_fast=24, ema_slow=60, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +113.61 % | 1.21 | 0.76 | 868 | sí |
| adx_threshold=16.0, ema_fast=16, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +120.90 % | 1.21 | 0.66 | 947 | sí |
| adx_threshold=16.0, ema_fast=24, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +146.88 % | 1.22 | 0.72 | 982 | sí |
| adx_threshold=16.0, ema_fast=16, ema_slow=40, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +180.38 % | 1.27 | 0.82 | 976 | sí |
| adx_threshold=24.0, ema_fast=24, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +183.66 % | 1.27 | 0.85 | 830 | sí |
| adx_threshold=16.0, ema_fast=16, ema_slow=60, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +184.48 % | 1.32 | 0.99 | 908 | sí |
| adx_threshold=24.0, ema_fast=16, ema_slow=60, stop_atr_mult=1.5, trailing_atr_mult=2.5 | +190.13 % | 1.28 | 0.88 | 797 | sí |
| adx_threshold=16.0, ema_fast=24, ema_slow=40, stop_atr_mult=2.5, trailing_atr_mult=2.5 | +198.66 % | 1.34 | 1.03 | 893 | sí |

## Gráficos

`equity.png` (curva OOS concatenada base 100 y B&H BTC OOS, con drawdown), `trades.csv` (trades OOS), `equity.csv`.

## Notas y veredicto

- **Veredicto**: no-go (v3 refutada: Sharpe OOS 0.90 ≤ 0.98 del B&H filtrado)
- **Por qué**: la spec fijó antes de correr que Sharpe OOS ≤ Sharpe del B&H BTC filtrado refuta el filtro como agregado a `ema_trend`, y dio 0.897 vs 0.977. La lectura es justa: el Sharpe es invariante a la escala, y el B&H filtrado dimensionado al mismo DD (λ 0.62) rinde +100 % vs +81.75 %, y a la misma vol (λ 0.58) +92.9 % con DD 18.5 % < 20.25 %; la ventaja de DD (20 % vs 31 %) es tamaño (exposición 41 %, beta 0.36 al BTC filtrado), no selección. La diferencia pareada diaria es t −1.17 (−4.0 bps/d; −7.9 bps/d en los días con filtro on): no hay evidencia de que la estrategia agregue algo a "comprar BTC cuando el filtro dice sí", que era lo que había que demostrar. Gate 1 falla además por 2024 (−0.05 % en muestra completa vs +30.0 % en la cadena OOS: DD intra-año 20.64 % > 20 % del breaker, que las ventanas OOS no alcanzan al re-basar el pico cada 6 meses), y el criterio "2023–24 ≥ 70 % del PnL de WF-0003" solo pasa en trades OOS (75 %): en la tabla de regímenes da 45 % (2024: −315 vs 8,412).
- **Qué se aprendió**: (1) El filtro hizo lo prometido en 2022 (7 entradas vs 122; −3.93 % vs −24.43 %; encendido 8/365 días) y arregló todo lo que WF-0003 fallaba: DD OOS 30.4 → 20.3 %, PF 1.19 → 1.40, MC p95 38.6 → 25.8 %, costos 39.8 → 25.6 % del bruto, con exposición 65 → 41 %; el precio fueron los años alcistas (2023 +11.0 % y 2024 +30.0 % vs +83.7 % / +72.5 % del B&H filtrado) por 39 apagados en 2024 (dos de 32 y 34 días con BTC plano) y por la estructura 3 slots × 1 %. (2) Toda la mejora 0.64 → 0.90 vino de no operar: el cuerpo de la distribución sigue sin edge (PF sin top 10 0.95, v2 0.92; top 10 = 113 % del PnL; los mismos 4 trades en el top 5 de ambas corridas; 57 % de los stops ≤ 24 h con −9,276 = 137 % del PnL). Quinta corrida con la misma patología: la familia `ema_trend` queda cerrada (cross/state × 4h/1h × fijo/optimizado × filtro). (3) El filtro por sí solo es una apuesta de un solo evento: sin 2022, Sharpe B&H 1.62 > B&H filtrado 1.21 > estrategia 1.06; sirve como control de DD, no como generador de retorno, y su exposición real es 45 % de los días (el REPORT dice 100 % porque la métrica de exposición del benchmark encadenado no distingue cash). (4) El criterio de regímenes es sensible al estado del circuit breaker: un WF re-basa el pico por ventana, la muestra completa no; con noviembre = 101 % del PnL de 2024, una pausa de 30 días en octubre–noviembre borra el año. Agregar al REPORT del WF los `protection_triggered` por año de la muestra completa; EXP-0008 corre la misma config sobre la muestra completa como diagnóstico. (5) El benchmark B&H filtrado fue la pieza que hizo decidible el experimento; mantenerlo en toda corrida futura que use el filtro.
- **Siguiente experimento propuesto**: no gastar la última iteración en v4 (pullback + tope 2 %): la brecha con el B&H filtrado está en los años alcistas y es estructural (beta 0.36); una entrada más selectiva baja más la exposición y el cuerpo de la distribución no mostró edge en cinco diseños. Propuesta de familia nueva `regime_bh` v1 (decisión del usuario), con spec y ADR que adapte el Gate 1 (universo de 1–2 pares, trades = idas y vueltas del filtro, Monte Carlo por bootstrap en bloques de retornos diarios): BTC/USDT, long cuando el filtro habilita (cierre diario > EMA200d y retorno 30 d > 0), flat al deshabilitar, tamaño fijo λ = 0.6 de la equity (presupuesto de DD 25 % con margen; en OOS λ 0.6 dio +97 % / DD 19.2 %), stop obligatorio amplio (−20 % del fill, definido en la spec; la salida es el filtro), costos y protecciones default iguales; corridas `backtest` 2019-08-01 → 2025-08-01 (incluye 2020-03 y 2021-05) y `walkforward` fijo con `--plateau` sobre ema_days {150, 200, 250} × momentum_days {20, 30, 45} × λ {0.5, 0.6, 0.75}; ETH/USDT una sola variante como control, no elegida por PnL. Confirma si Sharpe de la muestra completa ≥ 0.8 y ≥ B&H BTC del mismo rango, DD ≤ 25 % incluido intra-2020, 2022 ≥ −8 %, ≥ 80 % de las 27 variantes con Sharpe ≥ 0.8 y DD ≤ 25 %, y Sharpe sin 2022 ≥ 0.8. Refuta si Sharpe completa < B&H BTC, o DD 2020 > 25 %, o < 60 % de variantes pasan, o Sharpe sin 2022 < 0.5 × el del B&H sin 2022 (el edge sería solo 2022). No hacer: v4 pullback, recortar pares, elegir λ o ema_days mirando el OOS, `--include-holdout`.
