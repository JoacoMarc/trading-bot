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
| ema_trend | v1 | descartada (defaults `cross` 4h: EXP-0003/0007, WF-0001/0002) | [`ema-trend-v1.md`](ema-trend-v1.md) |
| ema_trend | v2 | descartada (`entry_mode=state` refutado en 4h y 1h: WF-0003/0004) | [`ema-trend-v2.md`](ema-trend-v2.md) |
| ema_trend | v3 | descartada (v2 + filtro de mercado: Sharpe OOS 0.90 ≤ 0.98 del B&H filtrado; WF-0005); familia cerrada | [`ema-trend-v3.md`](ema-trend-v3.md) |
| regime_bh | v1 | confirmada en walk-forward (Gate 1 aprobado salvo holdout, WF-0006; λ final 0.5; ADR-0010). Holdout EXP-0010: DD 6.4 % OK, PF 0.03 FALLA con la pierna larga abierta al corte → `iterar` hasta que cierre (regla fijada en la spec; decisión del usuario) | [`regime-bh-v1.md`](regime-bh-v1.md) |
