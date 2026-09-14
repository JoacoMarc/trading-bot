# ADR-0009: Filtro de mercado a nivel cartera como protección del RiskManager

- Estado: aceptado
- Fecha: 2026-09-13
- Fase: 6

## Contexto

Cuatro corridas de la familia `ema_trend` (EXP-0007, WF-0001..0004) comparten dos fallas que no dependen de la entrada ni del timeframe: 2022 pierde (−7 % a −24 %) con decenas de entradas, y el drawdown de cartera llega al 30 % porque tres slots de 1 % sobre pares con correlación diaria media 0.65 son una sola apuesta de ≈ 2.6 %. El filtro de régimen actual (`close > EMA200`) se evalúa **por par** y en 4h: en un mercado bajista los rebotes de 4h lo cruzan seguido y el bot entra igual. El analista propuso, con criterios escritos antes de correr, un filtro de **mercado** (una sola variable a nivel cartera) que habilite o deshabilite todas las entradas.

## Decisión

- El filtro vive en `risk/market_filter.py` y lo compone `Protections` (ADR-0007): es una protección más, con `ReasonCode.MARKET_FILTER`, eventos `protection_triggered/cleared:market_filter` y la misma regla dura: **solo bloquea entradas**, nunca salidas ni stops.
- Regla: entradas habilitadas si el **cierre diario** del par de referencia (`BTC/USDT`) está por encima de su `EMA(200)` diaria **y** su retorno a 30 días es positivo. Umbrales redondos y fijos (200 / 30): el filtro se diseña sabiendo que 2022 fue el año malo, así que no se optimiza ni se ajusta a mano después de ver el OOS.
- Cierre diario = último cierre del par de referencia de cada día UTC, tomado de las velas del timeframe que corre el `Engine` (la vela que cierra a las 23:59:59.999). El estado cambia una vez por día, al cerrarse la primera vela del día siguiente; dentro del día es fijo. Sin lookahead: solo días completos.
- La EMA diaria se siembra con la SMA de los primeros 200 cierres (misma semilla que `indicators/`). Mientras la EMA o el momentum no estén definidos, el filtro se considera **habilitado** (sin información no se bloquea) y el reporte lo registra. El `Engine` alimenta el filtro con las velas de warmup del feed (`warmup_bars`, sin consumidor hasta ahora) para que llegue definido al inicio del rango: 1200 velas de 4h = 200 días, justo la EMA(200) diaria.
- El par de referencia tiene que estar en el universo (v1: BTC está). Un universo sin él deja el filtro habilitado y lo avisa en la línea de riesgo del reporte.
- Configuración: `risk.market_filter` (`enabled`, `pair`, `ema_days`, `momentum_days`), apagado por defecto: todas las corridas registradas hasta WF-0004 se reproducen sin cambios.
- Benchmark obligatorio cuando el filtro está activo: **B&H BTC filtrado** (`backtest/benchmark.py::gated_hold`): comprar BTC al open siguiente a que el filtro habilite, vender al open siguiente a que deshabilite, con las mismas fees y slippage. Si la estrategia no supera a ese benchmark, el edge es el filtro, no la estrategia. El walk-forward lo encadena por tramo OOS igual que el B&H BTC.

## Alternativas consideradas

- **Filtro dentro de la estrategia** (`ema_trend` mirando BTC): mezcla señal con riesgo, no sirve para otras estrategias y no puede ejecutar una salida de cartera. Descartado.
- **Filtro por par más lento (EMA200 diaria de cada par)**: no resuelve la correlación (los 8 pares cruzan juntos) y sí retrasa las entradas buenas. Descartado como primera variable; queda como idea si el de mercado falla.
- **Cerrar posiciones cuando el filtro se apaga**: convierte una protección en una señal de salida y viola el principio de que el riesgo no bloquea ni fuerza salidas de la estrategia; las posiciones abiertas siguen con su stop y trailing.
- **Optimizar `ema_days` / `momentum_days`**: WF-0002 mostró que optimizar parámetros elige ruido; los umbrales quedan fijos.

## Consecuencias

- Un solo cambio respecto de WF-0003 (control): la spec `ema-trend-v3` = v2 `state` 4h + este filtro. Confirma o refuta por diferencia contra WF-0003 con el mismo `data_hash`.
- `Engine.__init__` consume `warmup_bars()` del feed (antes sin consumidor): el `LiveFeed` de la Fase 7 tiene que proveerlo con el mismo contrato.
- Deuda: par de referencia fuera del universo (cargarlo aparte), estado del filtro en `status.json` (Fase 7), reanudación del breaker relativa al filtro.
