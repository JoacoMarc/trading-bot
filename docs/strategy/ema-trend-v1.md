# ema_trend v1

- Estado: descartada (defaults `cross` en 4h; la familia sigue en [`ema-trend-v2.md`](ema-trend-v2.md))
- Fecha: 2026-09-08 (cerrada 2026-09-13)
- Experimentos: EXP-0003 (BTC+ETH), EXP-0004..0006 (protecciones), EXP-0007 (8 pares), WF-0001 (fijo), WF-0002 (optimizado)
- Código: `src/tradingbot/strategy/strategies/ema_trend.py`

## Hipótesis

En cripto las tendencias de 4h persisten lo suficiente para que un seguidor de tendencia con filtro de régimen supere los costos (0.10 % + 0.05 % de slippage por lado) y tenga drawdowns menores que buy & hold en mercados bajistas (2022), cediendo retorno en los alcistas. La ventaja, si existe, viene de (a) no estar comprado cuando el precio está bajo su EMA de 200 velas y (b) salir por stop/trailing antes de devolver toda la ganancia.

## Universo y timeframe

- Pares: universo v1 (BTC, ETH, BNB, XRP, ADA, LTC, LINK, SOL contra USDT). Backtests iniciales con BTC+ETH; el gate se evalúa con ≥ 4 pares.
- Timeframe: 4h (1h como alternativa a evaluar en la Fase 6).
- Datos: desde 2019-01-01 (SOL desde 2020-08-11, LINK desde 2019-01-16); holdout desde 2025-09-01 intocable.
- Warmup: `warmup_multiplier × período más largo` velas cerradas, donde el período más largo es `max(ema_regime, ema_slow, 2 × adx_period, 2 × atr_period)` (Wilder(n) pesa como una EMA(2n−1)). Default 6 × 200 = 1200 velas ≈ 200 días en 4h. Con menos, la EMA(200) sembrada con SMA arrastra > 1e-4 de diferencia respecto de la serie completa y el test de equivalencia falla. `strategy.warmup_candles` en la config solo puede ampliarlo.

## Reglas

Todas evaluadas al **cierre** de la vela `t` con velas cerradas; la orden se ejecuta al open de `t+1` (ADR-0002).

- **Régimen (filtro):** `close > EMA(ema_regime)`. Habilita entradas. Si el régimen se da vuelta con posición abierta, **no** la cierra: la posición sale por stop, trailing o cruce.
- **Entrada** (`entry_mode`):
  - `cross` (default): `EMA(fast)` cruza por encima de `EMA(slow)` en `t` (`fast[t] > slow[t]` y `fast[t-1] <= slow[t-1]`), con `ADX(adx_period) > adx_threshold`, régimen alcista y sin posición en el par.
  - `state`: `EMA(fast) > EMA(slow)`, `ADX > adx_threshold`, régimen alcista, sin posición en el par y al menos `cooldown_candles` velas desde la última salida en ese par. Re-entra tras un stop mientras la tendencia siga; el cooldown evita reentrar en la vela siguiente al stop.
- **Stop inicial:** `stop_atr_mult × ATR(atr_period)` por debajo del precio. La señal lo informa respecto del `close(t)` para el sizing; el `Engine` lo re-ancla al precio real del fill (`fill_price − distancia`).
- **Trailing (chandelier):** `highest_close_since_entry − trailing_atr_mult × ATR(t)`. El `PositionManager` solo lo sube, nunca lo baja; el `Broker` lo ejecuta (stop nativo en live).
- **Salida por señal:** `EMA(fast)` cruza por debajo de `EMA(slow)` en `t`. Motivo `SIGNAL`.
- **Ranking** cuando hay más entradas que slots: `strength = ADX(t)`, descendente; desempate alfabético (lo aplica el `RiskManager`).
- **Sizing** (lo aplica el `RiskManager`, no la estrategia): riesgo 1 % del equity por trade, tope 25 % del cash libre por posición, máximo 3 posiciones.

## Parámetros

| Parámetro | Default | Rango a optimizar (Fase 6) | Paso |
|---|---|---|---|
| `ema_fast` | 20 | 10–30 | 1 |
| `ema_slow` | 50 | 40–100 | 5 |
| `ema_regime` | 200 | fijo en v1 | — |
| `adx_period` | 14 | fijo en v1 | — |
| `adx_threshold` | 20 | 15–30 | 1 |
| `atr_period` | 14 | fijo en v1 | — |
| `stop_atr_mult` | 2.0 | 1.5–4.0 | 0.5 |
| `trailing_atr_mult` | 3.0 | 2.0–5.0 | 0.5 |
| `entry_mode` | `cross` | {`cross`, `state`} | — |
| `cooldown_candles` | 2 | 0–6 (solo `state`) | 1 |
| `warmup_multiplier` | 6 | fijo | — |

Restricciones: `ema_fast < ema_slow < ema_regime`; precisión de los reales ≤ 0.001 (regla anti-overfitting heredada de freqtrade).

## Indicadores y semillas

`EMA` sembrada con la SMA de las primeras `n` velas (compatibilidad TA-Lib); `ATR` con suavizado de Wilder (`α = 1/n`) sobre el true range desde la segunda vela; `ADX` según el algoritmo exacto de TA-Lib (lookback `2n − 1`). Todos verificados contra fixtures TA-Lib en `tests/fixtures/indicators/`.

## Comportamiento esperado por régimen

- **Alcista sostenido (2020-21, 2023-24):** pocas entradas, largas, cerradas por trailing; retorno positivo pero por debajo de buy & hold en las subas verticales (el trailing corta antes del techo).
- **Bajista (2022):** el filtro `close > EMA200` deja al bot casi todo el año afuera; pérdida acotada a los whipsaws de los rebotes. Señal de alarma: más de 6 entradas en el año o pérdida > 8 %.
- **Lateral (rangos amplios):** el peor caso. Cruces falsos con ADX cerca del umbral; el filtro ADX debería filtrar la mitad. Señal de alarma: profit factor < 1 en tramos laterales largos.

## Riesgos conocidos

- Whipsaws en la zona del cruce: `cross` es más selectivo pero pierde la tendencia si el primer intento fue stopeado; `state` re-entra y paga más costos. Se evalúan ambos en la Fase 6.
- Gaps bajistas al open de `t+1`: el stop se re-ancla al fill, así que el riesgo por trade se mantiene en ~1 % aunque el precio de entrada sea peor.
- Correlación BTC/ETH ~0.8: tres posiciones simultáneas no son tres apuestas independientes; el tope de exposición del `RiskManager` lo mitiga parcialmente.
- Dependencia del filtro de régimen: en subas desde el fondo (2023-01) entra tarde porque `close > EMA200` demora meses.
- ADX con período 14 en 4h reacciona lento a tendencias nuevas; puede filtrar entradas válidas.

## Resultado y veredicto

- **BTC+ETH 4h (EXP-0003):** +69.9 %, Sharpe 1.17, DD 7.2 %, PF 2.60, 79 trades en 6 años; `iterar` por muestra chica y concentración (top 10 = 111 % del PnL). La salida por señal casi no actúa (1/79): el trailing 3×ATR sale antes.
- **8 pares 4h (EXP-0007):** +76.9 %, Sharpe 0.75, DD 15.5 %, PF 1.46, 248 trades; `no-go`. Los 6 pares nuevos aportan trades pero PF 1.07 y costos del 21.7 % del bruto; 76 stops todos perdedores, 38 en ≤ 24 h; 7/7 salidas por señal perdedoras.
- **Walk-forward fijo (WF-0001):** curva OOS 2021-08→2025-08 +23.4 %, Sharpe 0.48 (< 0.8 y < 0.76 del B&H BTC), DD 14.3 %, PF 1.31, 163 trades; Gate 1 no aprobado solo por Sharpe. El edge vive en 2019-08→2021-08 y no persiste: la muestra continua restringida al mismo rango da Sharpe 0.43. La meseta 42/42 con retornos de +7 % a +277 % según `trailing_atr_mult` no es robustez.
- **Walk-forward optimizado (WF-0002):** Sharpe OOS 1.03 pero 2 trades = 102 % del PnL; el score in-sample anticorrelaciona −0.64 con el OOS; `no-go`: afinar parámetros de esta versión queda refutado.
- **Veredicto de la versión:** `descartada`. Diagnóstico: la entrada por cruce llega tarde (stops dentro del ruido) y no re-entra tras un stop con la tendencia viva. Sigue la v2 con `entry_mode=state`.
