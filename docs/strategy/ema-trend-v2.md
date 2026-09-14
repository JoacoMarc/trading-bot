# ema_trend v2

- Estado: en evaluación
- Fecha: 2026-09-13
- Experimentos: WF-0003 (fijo, 4h, 8 pares, meseta); si falla, WF-0004 (1h)
- Código: `src/tradingbot/strategy/strategies/ema_trend.py` (sin cambios respecto de v1: `entry_mode=state` ya existía; cambia la configuración evaluada)
- Sustituye a: [`ema-trend-v1.md`](ema-trend-v1.md) (defaults `cross` en 4h, `descartada` tras WF-0001 y WF-0002)

## Hipótesis

La v1 falló por la **entrada**, no por el filtro ni por la salida: en EXP-0007 los 76 stops fueron todos perdedores y 38 saltaron en menos de 24 h (la señal de cruce llega cuando el movimiento ya consumió parte del recorrido y 2 ATR de stop quedan dentro del ruido), y con `cross` una tendencia que sigue viva tras un stop no se vuelve a operar hasta el próximo cruce (SOL 2023-10 salió con +180 por trailing y la v1 no re-entró; la versión optimizada capturó +3,410 en el mismo tramo). `entry_mode=state` entra mientras `EMA(fast) > EMA(slow)` con ADX y régimen alcistas, y re-entra tras una salida una vez cumplido el cooldown: la apuesta es que la re-entrada recupera las tendencias largas que `cross` deja pasar y que el costo extra de whipsaws (más entradas, más fees) queda por debajo de esa ganancia. Si la hipótesis es correcta, el Sharpe OOS debería subir por más trades ganadores sobre las mismas tendencias, no por 1–2 trades más grandes.

## Universo y timeframe

- Pares: universo v1 completo (BTC, ETH, BNB, XRP, ADA, LTC, LINK, SOL contra USDT). No se recorta por PnL (sería snooping: LINK y LTC invirtieron su signo entre mitades del rango en EXP-0007).
- Timeframe: 4h (WF-0003). 1h solo como segunda corrida (WF-0004) si la de 4h falla.
- Datos: 2019-08-01 → 2025-09-01 (sin holdout); pares con activación tardía tras su warmup (SOL desde 2021-02-27, LINK desde 2019-08-04).
- Warmup: igual que v1 (6 × 200 = 1200 velas).

## Reglas

Idénticas a v1 salvo la entrada. Todas al cierre de `t`, ejecución al open de `t+1` (ADR-0002).

- **Régimen (filtro):** `close > EMA(200)`; no cierra posiciones abiertas.
- **Entrada (`state`):** `EMA(20) > EMA(50)`, `ADX(14) > 20`, régimen alcista, sin posición en el par y `bars_since_exit >= cooldown_candles` (2). Re-entra tras stop o trailing mientras la tendencia siga.
- **Stop inicial:** `2.0 × ATR(14)` bajo el precio, re-anclado al fill.
- **Trailing (chandelier):** `highest_close − 3.0 × ATR(14)`, solo sube. Se mantiene 3.0 a propósito: optuna eligió 4.0–4.5 en WF-0002 mirando el OOS y adoptarlo sería elegir mirando el resultado.
- **Salida por señal:** `EMA(20)` cruza bajo `EMA(50)`.
- **Ranking y sizing:** sin cambios (ADX descendente; 1 % de riesgo, tope 25 %, 3 slots).
- **Protecciones (ADR-0007):** defaults (pérdida diaria 3 %, DD 20 % con reanudación bajo 10 % o tras 30 días); no dispararon en la v1.

## Parámetros

| Parámetro | Valor v2 | Comentario |
|---|---|---|
| `entry_mode` | `state` | el cambio de esta versión |
| `cooldown_candles` | 2 | evita re-entrar en la vela siguiente al stop; rango 0–6 solo si v2 pasa el gate |
| `ema_fast` / `ema_slow` / `ema_regime` | 20 / 50 / 200 | fijos |
| `adx_period` / `adx_threshold` | 14 / 20 | fijos |
| `atr_period` / `stop_atr_mult` / `trailing_atr_mult` | 14 / 2.0 / 3.0 | fijos |
| `warmup_multiplier` | 6 | fijo |

No se optimiza nada en esta versión: WF-0002 mostró que el score in-sample anticorrelaciona con el OOS (−0.64) y que 50 trials sobre 24 meses eligen ruido.

## Criterios prefijados (antes de correr WF-0003)

Sobre la curva OOS concatenada de WF-0003 (IS 24 m / OOS 6 m, 8 ventanas 2021-08 → 2025-08, modo fijo, `--plateau`, Monte Carlo 5,000, semilla 42):

- **Confirma** (candidata a paper, sujeto al Gate 1 completo) si se cumplen todos: Sharpe OOS ≥ 0.8 y ≥ Sharpe del B&H BTC OOS; PF OOS ≥ 1.3; top 10 trades ≤ 150 % y top 2 ≤ 50 % del PnL OOS; PF sin los 2 mejores trades ≥ 1.1; ≥ 5/8 ventanas positivas por trades cerrados; costos (fees + slippage) ≤ 30 % del bruto ganador.
- **Refuta `state` en 4h** si Sharpe OOS ≤ 0.5 o PF OOS < 1.2 → WF-0004 con la misma lógica en 1h.
- Zona intermedia (0.5 < Sharpe OOS < 0.8): `iterar` una sola vez más, y solo con un cambio que salga de un diagnóstico escrito antes de la corrida, no del OOS.
- Se compara también con la muestra completa 2019-08 → 2025-08 con parámetros fijos: si la mejora está solo en 2019–2021, no cuenta.

## Comportamiento esperado por régimen

- **Alcista sostenido (2020-21, 2023-24):** más trades que v1 sobre las mismas tendencias (re-entradas tras stop), win rate similar o menor, PF mayor por capturar los tramos largos completos. Señal de alarma: el PnL sigue concentrado en 1–2 trades.
- **Bajista (2022):** el filtro EMA200 debería seguir dejando al bot afuera casi todo el año; los rebotes generarán más whipsaws que en v1 porque `state` entra en cuanto la condición se cumple. Alarma: pérdida 2022 peor que −8 % o más de 40 entradas en el año (v1 tuvo 32).
- **Lateral:** el peor caso empeora: cada vez que EMA20 supera EMA50 con ADX > 20 hay entrada, stop, cooldown de 2 velas y re-entrada. Alarma: fees + slippage > 30 % del bruto o PF < 1 en los tramos laterales de 2023.

## Riesgos conocidos

- Más entradas = más costos: la v1 en 8 pares ya gastaba el 21.7 % del bruto; `state` puede duplicar la cantidad de trades.
- Re-entrada en el mismo ruido: con cooldown 2 velas (8 h) un rango estrecho puede dar 3–4 stops seguidos en el mismo par; la pausa por pérdidas seguidas del RiskManager está apagada por default y no se activa en esta corrida para medir el efecto puro.
- Los slots (3) se llenan más seguido con 8 pares y señales continuas: el ranking por ADX decide y los rechazos crecen; hay que mirar `entry_rejected:max_positions` en el reporte.
- Sesgo de confirmación: la hipótesis nace de mirar WF-0001/WF-0002 (por eso los criterios quedan escritos acá antes de correr y la refutación es binaria).

## Resultado y veredicto

Pendiente (se completa con WF-0003 y, si hace falta, WF-0004).
