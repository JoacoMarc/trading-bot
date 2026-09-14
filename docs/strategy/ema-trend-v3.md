# ema_trend v3

- Estado: descartada (refutada por el criterio prefijado: Sharpe OOS 0.90 ≤ 0.98 del B&H BTC filtrado; la familia `ema_trend` queda cerrada)
- Fecha: 2026-09-13 (cerrada el mismo día)
- Experimentos: WF-0005 (fijo, 4h, 8 pares, meseta) `no-go`; EXP-0008 (muestra completa, diagnóstico del breaker en 2024); control: WF-0003
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

- **WF-0005 (4h):** curva OOS 2021-08→2025-08 +81.8 %, Sharpe 0.90, DD 20.3 %, PF 1.40, 435 trades, exposición 41 %; 6/8 ventanas positivas; MC p95 25.8 %; meseta 42/42. Gate 1 falla por un solo criterio (retorno 2024 −0.05 % en la muestra completa, ligado al disparo del circuit breaker con DD intra-año 20.6 %). Benchmarks OOS: B&H BTC +175.8 % / Sharpe 0.76 / DD 77.1 %; **B&H BTC filtrado +186.0 % / Sharpe 0.98 / DD 30.9 %**.
- **Criterios prefijados:** confirma 2022 (−3.9 % ≥ −8 %), DD OOS (20.3 % ≤ 25 %), PF (1.40 ≥ 1.3), Sharpe ≥ 0.8; **refuta** porque Sharpe OOS 0.90 ≤ 0.98 del B&H filtrado. Lectura justa: el B&H filtrado dimensionado al mismo DD rinde +100 % vs +81.8 % y la diferencia pareada diaria es t −1.17: la estrategia no agrega nada a "comprar BTC cuando el filtro dice sí" salvo menos exposición (41 %, beta 0.36). El criterio "2023–24 ≥ 70 % del PnL de WF-0003" pasa solo en trades OOS (75 %); en la tabla de regímenes da 45 %.
- **Qué hizo el filtro:** exactamente lo prometido en 2022 (7 entradas vs 122; −3.9 % vs −24.4 %; encendido 8 de 365 días) y arregló DD, PF, Monte Carlo y costos de WF-0003; el precio fueron los años alcistas (2023 +11 %, 2024 +30 % vs +84 % / +73 % del B&H filtrado) por 39 apagados en 2024 y por la estructura 3 slots × 1 %. Sin 2022 el filtro no aporta (Sharpe B&H 1.62 > B&H filtrado 1.21 > estrategia 1.06): es control de drawdown, no generador de retorno.
- **Familia `ema_trend`:** cerrada tras cinco diseños (cross/state × 4h/1h × fijo/optimizado × filtro) con la misma patología: el cuerpo de la distribución no tiene edge (PF sin los 10 mejores trades 0.95; 57 % de los stops saltan en ≤ 24 h). Un v4 con entrada por pullback bajaría aún más la exposición sin atacar la brecha estructural con el B&H filtrado; no se gasta la última iteración en eso.
- **Próximo paso propuesto (decisión del usuario):** familia nueva `regime_bh`: BTC long mientras el filtro habilita, flat al deshabilitar, tamaño fijo λ ≈ 0.6 de la equity, stop amplio de seguridad, ETH como control; Gate 1 adaptado (pocos trades: Monte Carlo por bloques de retornos diarios, meseta sobre `ema_days` × `momentum_days` × λ) con confirmación/refutación escritas en el REPORT de WF-0005.
