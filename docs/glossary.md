# Glosario

Conceptos de trading algorítmico usados en el proyecto, explicados para alguien que viene de software. Crece por fase: cada concepto nuevo que aparece en el código o en un reporte se agrega acá.

## Vela (candle, OHLCV)

Resumen de un intervalo de tiempo: precio de apertura (**open**), máximo (**high**), mínimo (**low**), cierre (**close**) y volumen. Se identifica por su `open_time` (ms UTC). Una vela está **cerrada** cuando terminó su intervalo; hasta entonces está "en formación" y sus valores cambian. El bot solo razona sobre velas cerradas.

## Timeframe

Duración de cada vela: `1m`, `1h`, `4h`, `1d`. En 4h hay 6 velas por día y ~2190 por año. Timeframes más largos generan menos señales, pagan menos comisiones y son menos sensibles al ruido, pero reaccionan más tarde.

## Lookahead bias (sesgo de anticipación)

Usar en la decisión de la vela `t` información que solo se conoce después (la vela `t+1`, el máximo de toda la serie, una normalización global). Hace que el backtest parezca excelente y que el bot real pierda. Se previene por construcción (la estrategia solo recibe datos hasta `t`) y se verifica con el test de equivalencia.

## Slippage (deslizamiento)

Diferencia entre el precio que asumiste y el precio real al que se ejecuta la orden, por movimiento del mercado y profundidad del libro. Un backtest sin slippage sobreestima resultados. Modelamos un slippage fijo en puntos básicos (bps; 1 bps = 0.01 %) y en live medimos el real como *implementation shortfall* = `fill_price − ref_price`.

## Fee (comisión), maker/taker

Lo que cobra el exchange por operar. **Taker** = orden que se ejecuta de inmediato contra el libro (market); **maker** = orden límite que espera. Binance Spot VIP0: 0.10 % ambas; 0.075 % pagando con BNB. Binance descuenta la fee del activo recibido (comprás BTC → pagás en BTC), salvo con BNB: por eso la cantidad neta de una posición es menor que la comprada.

## Drawdown (DD)

Caída desde el último máximo de la curva de equity hasta el mínimo posterior, en porcentaje. El **max drawdown** es la peor de esas caídas en el período. Mide el dolor que hay que tolerar para obtener el retorno; un 25 % de DD significa haber visto la cuenta caer un cuarto desde su pico.

## Sharpe ratio

Retorno excedente por unidad de volatilidad: `media(retornos) / desvío(retornos)`, anualizado. Lo calculamos sobre retornos **diarios** con tasa libre de riesgo 0 y `√365`. Sharpe > 1 es bueno; > 2 sospechoso en cripto sin costos realistas. Sortino es igual pero solo penaliza la volatilidad a la baja.

## Walk-forward

Validación temporal: se optimizan parámetros en una ventana *in-sample* (IS) y se evalúan en la ventana siguiente *out-of-sample* (OOS), que no se usó para optimizar. Se repite desplazando la ventana. Concatenar los tramos OOS da una curva "honesta" de cómo habría rendido la estrategia re-optimizada periódicamente.

## Overfitting (sobreajuste)

Parámetros que capturan el ruido del pasado en vez de una regularidad del mercado. Síntomas: gran diferencia IS vs OOS, resultados que se derrumban al mover un parámetro un 20 %, pocas operaciones, precisión absurda en los parámetros (EMA de 23.7). Defensas: walk-forward, meseta de parámetros, Monte Carlo, **holdout** (últimos 12 meses reservados y evaluados una sola vez).

## Régimen de mercado

Comportamiento dominante en un período: tendencia alcista, bajista o lateral (rango). Una estrategia de seguimiento de tendencia gana en tendencias y pierde en rangos; por eso usamos un filtro de régimen (`close > EMA200`) y evaluamos los resultados por año.

## Paper trading

Correr el bot con datos y precios en vivo pero con órdenes simuladas y saldo ficticio. Es el puente entre el backtest y el dinero real: revela problemas de conectividad, tiempos, fills y estado que el backtest no puede mostrar. freqtrade lo llama *dry-run*.

## Stop-loss y trailing stop

**Stop-loss**: precio al que se cierra una posición perdedora para acotar la pérdida; lo fijamos a `k × ATR` bajo el precio de entrada. **Trailing stop**: stop que sube a medida que el precio sube (nunca baja), para proteger ganancias; usamos el "chandelier": máximo cierre desde la entrada menos `k × ATR`. En live el stop vive como orden nativa en el exchange para que se ejecute aunque el bot esté caído.

## ATR (Average True Range)

Promedio del rango real de las últimas N velas (incluye gaps). Mide volatilidad en unidades de precio; sirve para poner stops y dimensionar posiciones de forma proporcional a cuánto se mueve el activo.

## clientOrderId e idempotencia

Identificador que el bot asigna a cada orden antes de enviarla (`tb-{estrategia}-{PAR}-{open_time}-{B|S}`). Como es determinístico, reintentar la misma decisión produce el mismo id y Binance rechaza el duplicado en vez de abrir dos posiciones. También permite cruzar trade a trade el paper con el backtest del mismo período (`parity`).

## Dust (polvo)

Restos de un activo por debajo del `stepSize` mínimo que el exchange permite operar (por ejemplo 0.000004 BTC). Aparecen porque la fee se descuenta del activo comprado y porque las ventas se redondean hacia abajo. No se pueden vender, así que se contabilizan aparte y no forman parte del equity operativo.

## Implementation shortfall

Diferencia entre el precio de referencia del modelo (el open de la vela siguiente a la señal) y el precio real del fill, en bps y con signo: positivo cuando el fill fue peor. Es la medida honesta del slippage real y se reporta en paper y live.

## Vela en formación

La vela cuyo intervalo todavía no terminó: su `close`, `high`, `low` y `volume` cambian con cada trade. Binance la devuelve como última fila de `klines`. Guardarla contaminaría el backtest con datos que en vivo no se conocían al cierre, así que el downloader solo persiste velas con `open_time + timeframe ≤ hora_del_exchange`.

## Hueco (gap) de datos

Uno o más `open_time` faltantes entre la primera y la última vela de una serie. Puede ser real (mantenimiento de Binance, par suspendido) o un problema de descarga. Los reales se registran en `configs/binance_gaps.json`; `data-check` alerta solo por los no registrados.

## tickSize, stepSize y minNotional

Filtros por símbolo de Binance: **tickSize** es el incremento mínimo de precio (BTC/USDT: 0.01), **stepSize** el incremento mínimo de cantidad (0.00001 BTC) y **minNotional** el valor mínimo de una orden en quote (5 USDT). Una orden que no los respeta se rechaza. ccxt los expone como `precision` y `limits`, pero en Binance `precision` son tamaños de paso, no cantidad de decimales.

## Rate limit

Cuota de requests que impone el exchange: Binance Spot pesa cada endpoint (`REQUEST_WEIGHT`, 6000 por minuto por IP) y limita órdenes (100 cada 10 s). Excederla devuelve 429 y, si se insiste, 418 con baneo temporal de la IP. El adapter respeta el rate limiter de ccxt y reintenta con backoff solo estos errores transitorios.

## EMA y SMA

**SMA**: promedio simple de las últimas `n` velas; todas pesan igual. **EMA**: promedio exponencial, `EMA_t = α·precio_t + (1−α)·EMA_{t−1}` con `α = 2/(n+1)`; las velas recientes pesan más y reacciona antes. El cruce de una EMA rápida sobre una lenta es la señal clásica de cambio de tendencia. Una EMA de 200 velas se usa como filtro de régimen: precio por encima = tendencia de fondo alcista.

## Semilla y warmup de un indicador

Los indicadores recursivos (EMA, RSI, ATR, ADX) necesitan un valor inicial o **semilla**; nosotros usamos la de TA-Lib (la SMA de las primeras `n` velas) para poder comparar exactamente. La influencia de la semilla decae con el tiempo: por eso la estrategia exige un **warmup** de varias veces el período más largo antes de decidir. Con warmup corto, el bot en vivo (que recomputa sobre una ventana) y el backtest (que usa toda la serie) verían valores distintos; el test de equivalencia lo detecta.

## ADX (Average Directional Index)

Mide la **fuerza** de la tendencia (no su dirección) en 0–100 a partir de los movimientos direccionales suavizados de Wilder. Por debajo de ~20 el mercado está en rango; por encima hay tendencia. Lo usamos como filtro de entrada y como `strength` para rankear señales cuando hay más entradas que slots.

## Suavizado de Wilder

Media exponencial con `α = 1/n` (más lenta que la EMA estándar del mismo período), introducida por Welles Wilder para RSI, ATR y ADX. TA-Lib y la mayoría de las plataformas la usan; la reproducimos igual.

## Buy & hold (benchmark)

Comprar al inicio del período y no hacer nada más. Es la vara contra la que se mide cualquier estrategia: si un bot con costos, stops y esfuerzo no mejora al menos el drawdown de comprar y mantener, no aporta. En cada reporte aparecen dos: buy & hold de BTC y una cartera equiponderada de los pares operados, ambos con los mismos costos de entrada que el bot.

## CAGR, Calmar y Sortino

**CAGR**: retorno anual compuesto equivalente, `(final/inicial)^(365.25/días) − 1`; permite comparar períodos de distinta duración. **Calmar**: CAGR dividido por el max drawdown; cuánto retorno anual se obtiene por unidad de dolor. **Sortino**: como el Sharpe pero solo penaliza la volatilidad de los días negativos (la buena volatilidad no cuenta en contra).

## Profit factor, win rate y expectancy

**Profit factor**: suma de las ganancias de los trades ganadores dividida por la suma de las pérdidas de los perdedores; por encima de 1.3 el sistema paga sus costos con margen. **Win rate**: fracción de trades ganadores; solo tiene sentido junto con el tamaño relativo de ganancias y pérdidas (un seguidor de tendencia gana con 35–45 % de aciertos). **Expectancy**: PnL medio por trade; lo que cabe esperar de la siguiente operación.

## Exposición

Fracción del tiempo con capital invertido. Un 13 % de exposición con retorno positivo significa que el capital estuvo en efectivo el 87 % del tiempo: menos retorno absoluto que buy & hold, pero mucho menos drawdown y capital disponible.

## Position sizing (dimensionamiento)

Cuánto comprar. Usamos riesgo fijo: arriesgar el 1 % del equity por operación, `qty = equity × 0.01 / (precio_entrada − stop)`. Así una operación que toca el stop pierde ~1 % del capital sin importar la volatilidad del par.

## Circuit breaker (cortacircuito por drawdown)

Protección que frena las entradas nuevas cuando el equity cae un porcentaje dado desde su máximo (pico) de la corrida. Las posiciones abiertas siguen su curso con stops y trailing, porque el riesgo nunca bloquea salidas. Reanuda cuando el drawdown vuelve por debajo de un nivel de reanudación (por defecto la mitad del umbral) o, si el bot quedó en cash y el DD no se mueve, tras un plazo en días que re-basa el pico; en paper/live solo reanuda una orden manual (ADR-0007).

## Kill switch (interruptor de emergencia)

Orden externa de "no abrir más posiciones": en este bot, el archivo `logs/STOP` o el comando `tradingbot stop`. Con `--flatten` además vende todo a mercado en la próxima vela. Permite intervenir sin matar el proceso ni perder los stops en reposo.

## Pérdida diaria máxima (daily loss limit)

Porcentaje del equity que se acepta perder en un día UTC, medido contra el equity al cierre del día anterior. Al alcanzarlo no hay entradas hasta el día siguiente: acota el daño de un día de whipsaws o de un gap simultáneo en varios pares.

## Cooldown (enfriamiento)

Velas que deben pasar tras una salida antes de volver a entrar. Hay dos: el de la estrategia (`cooldown_candles`, solo en `entry_mode=state`) y el del riesgo, por par tras una salida perdedora por stop o trailing (`cooldown_candles_after_stop`) o global tras N pérdidas seguidas (`pause_after_consecutive_losses`). Evita re-entrar en el mismo ruido que acaba de sacar al bot.
