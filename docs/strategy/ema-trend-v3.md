# ema_trend v3

- Estado: en evaluación
- Fecha: 2026-09-13
- Experimentos: WF-0005 (fijo, 4h, 8 pares, meseta); control: WF-0003 (v2 `state` sin filtro, mismo `data_hash`)
- Código: `src/tradingbot/strategy/strategies/ema_trend.py` sin cambios; el cambio es el filtro de mercado en `risk/market_filter.py` (ADR-0009), activado por `risk.market_filter.enabled`
- Sustituye a: [`ema-trend-v2.md`](ema-trend-v2.md) (`state` sin filtro de mercado, `descartada`)

## Hipótesis

Las cuatro corridas anteriores fallan por dos cosas que no dependen de la entrada ni del timeframe: 2022 pierde (WF-0003: −24.4 % con 122 entradas) y el drawdown de cartera llega al 30 % porque los tres slots operan pares con correlación 0.65 (una sola apuesta de ≈ 2.6 %, no tres de 1 %). El filtro de régimen por par (`close > EMA200` en 4h) no saca al bot de un mercado bajista: los rebotes de 4h lo cruzan seguido. La hipótesis es que un filtro **de mercado**, diario y a nivel cartera (BTC sobre su EMA200 diaria y con momentum de 30 días positivo) deja al bot en cash durante los tramos en que la mayoría de las entradas pierde (2022, la primera mitad de 2025) y conserva la mayor parte del PnL de los tramos buenos (2023–2024), mejorando Sharpe y drawdown por **dejar de operar**, no por operar mejor. El costo esperado: entradas tardías al salir de un bear (BTC tarda meses en cruzar la EMA200 diaria) y falsos apagados en correcciones dentro de un bull.

## Universo y timeframe

- Pares: universo v1 completo (8 pares USDT); sin recortes por PnL.
- Timeframe: 4h. La 1h queda descartada por costos (WF-0004: fees 9,273 sobre 10,000 en 2,549 trades).
- Datos: 2019-08-01 → 2025-09-01 (sin holdout); activación tardía de SOL y LINK como en v2.
- Warmup: 1200 velas de 4h; el filtro toma de ahí sus 200 cierres diarios iniciales.

## Reglas

Idénticas a v2 (`entry_mode=state`, cooldown 2, EMA 20/50/200, ADX 14 > 20, stop 2.0 ATR, trailing 3.0 ATR, salida por cruce, ranking por ADX, riesgo 1 %, tope 25 %, 3 slots, protecciones default) más:

- **Filtro de mercado (protección, ADR-0009):** entradas habilitadas solo si el cierre diario de BTC/USDT > EMA(200) diaria **y** retorno de BTC a 30 días > 0. Se evalúa una vez por día UTC con días completos. No cierra posiciones: las abiertas siguen con su stop y trailing. Mientras EMA o momentum no estén definidos, habilitado.
- Rechazos por el filtro quedan como `entry_rejected:market_filter`; los cambios de estado como `protection_triggered/cleared:market_filter`.

## Parámetros

| Parámetro | Valor v3 | Comentario |
|---|---|---|
| `risk.market_filter.enabled` | `true` | el cambio de esta versión |
| `risk.market_filter.pair` | `BTC/USDT` | par de referencia (está en el universo) |
| `risk.market_filter.ema_days` | 200 | fijo, no se optimiza |
| `risk.market_filter.momentum_days` | 30 | fijo, no se optimiza |
| resto | = v2 | sin cambios |

## Criterios prefijados (antes de correr WF-0005)

Sobre la curva OOS concatenada de WF-0005 (IS 24 m / OOS 6 m, 8 ventanas 2021-08 → 2025-08, modo fijo, `--plateau`, MC 5,000, semilla 42), comparando con WF-0003 (control) y con el benchmark **B&H BTC filtrado** (BTC con el filtro on, cash si off, mismos costos):

- **Confirma** (candidata a paper, sujeto al Gate 1 completo) si se cumplen todos: 2022 ≥ −8 % (muestra completa); DD OOS ≤ 25 %; Sharpe OOS ≥ 0.8 **y** ≥ Sharpe del B&H BTC filtrado OOS; PF OOS ≥ 1.3; 2023–2024 conservan ≥ 70 % del PnL que tuvo WF-0003 en esos años.
- **Refuta el filtro** si Sharpe OOS < 0.64 (peor que sin filtro), o PF OOS < 1.2, o Sharpe OOS ≤ Sharpe del B&H BTC filtrado OOS (el edge sería el filtro y no la estrategia: comprar BTC cuando el filtro dice sí rinde igual o más).
- Zona intermedia: `iterar` una sola vez más y solo con un cambio escrito antes de correr; queda 1 iteración de presupuesto después de esta.
- No se ajustan `ema_days` / `momentum_days` mirando el OOS.

## Comportamiento esperado por régimen

- **Alcista sostenido (2020-21, 2023-24):** el filtro debería estar encendido casi todo el tiempo; PnL ≈ WF-0003 en esos años (≥ 70 %). Alarma: apagados frecuentes en correcciones que cortan las mejores tendencias.
- **Bajista (2022):** filtro apagado la mayor parte del año; entradas 2022 << 122 y pérdida ≥ −8 %. Alarma: si 2022 sigue perdiendo más de 8 %, el filtro no captura el régimen y la palanca no es esta.
- **Transiciones (2023-01, 2025):** entradas tardías al salir del bear; se acepta perder el primer tramo de recuperación.

## Riesgos conocidos

- Look-ahead del diseño: los umbrales se eligen sabiendo cómo fue 2022; por eso son redondos, fijos y se juzgan contra el B&H filtrado (que usa el mismo filtro).
- El filtro no controla el riesgo agregado dentro de un régimen alcista: el DD de 2024-25 de WF-0003 (−23 %) puede repetirse. Si el filtro pasa pero el DD sigue > 25 %, la siguiente palanca es el tope de riesgo abierto total (≤ 2 %), no otro filtro.
- Sesgo de confirmación: la hipótesis nace de los cuatro fracasos anteriores; los criterios quedan escritos acá antes de correr y la refutación es binaria.

## Resultado y veredicto

Pendiente (se completa con WF-0005).
