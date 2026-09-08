# Specs de estrategias

Toda estrategia tiene una spec acá **antes** del código. La spec es la hipótesis que el backtest va a intentar refutar; si cambia la estrategia, se escribe una versión nueva (`<nombre>-v2.md`) y se registra en qué experimentos se evaluó cada una. `/new-strategy <nombre>` genera el scaffold (Fase 3).

## Plantilla

```markdown
# <nombre> v<N>

- Estado: borrador | en evaluación | descartada | en paper | en live
- Fecha: YYYY-MM-DD
- Experimentos: EXP-XXXX, WF-XXXX, OPT-XXXX

## Hipótesis
Qué regularidad del mercado explota y por qué debería persistir después de costos.

## Universo y timeframe
Pares, quote, timeframe, período de datos, warmup.

## Reglas
- Régimen (filtro): ...
- Entrada: ...
- Salida por señal: ...
- Stop inicial y trailing: ...
- Sizing: ...

## Parámetros
| Parámetro | Default | Rango a optimizar | Paso |

## Comportamiento esperado por régimen
Alcista / bajista / lateral: qué debería pasar y qué sería una señal de alarma.

## Riesgos conocidos
Whipsaws, gaps, correlación entre pares, dependencia del filtro, etc.

## Resultado y veredicto
Se completa después de los experimentos: qué pasó, qué se aprendió, qué sigue.
```

## Estrategias

| Estrategia | Versión | Estado | Spec |
|---|---|---|---|
| ema_trend | v1 | borrador (Fase 3) | `ema-trend-v1.md` (pendiente) |
