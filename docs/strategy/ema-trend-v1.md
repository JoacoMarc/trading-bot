# ema_trend v1

- Estado: en evaluación
- Fecha: 2026-09-08
- Experimentos: (pendientes, Fase 4: EXP-0003 default BTC+ETH 4h)
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

Pendiente (se completa con EXP-0003 y el walk-forward de la Fase 6).
