---
name: experiment-review
description: Revisa una corrida registrada (EXP/WF/OPT/PAR) del trading-bot y escribe su veredicto: lee los artefactos, pide el análisis al agente backtest-analyst, acuerda el veredicto con el usuario, lo escribe en la sección "Notas y veredicto" del REPORT.md y regenera REGISTRY.md. Usar cuando el usuario diga "revisemos el EXP-000N", "qué veredicto le ponemos" o al terminar un backtest.
argument-hint: "<EXP-NNNN>"
---

Pasos:

1. Id: `$ARGUMENTS` (p. ej. `EXP-0003`). Ubicá la carpeta con `uv run tradingbot experiments show $ARGUMENTS`; leé su `REPORT.md` y `metrics.json`.
2. Validez: si `meta.git_dirty` es true o la corrida incluye holdout sin ser la final, señalalo primero: esa corrida no puede ser evidencia final aunque el número sea bueno.
3. Invocá al agente `backtest-analyst` con el id y el contexto (qué se quería probar, corridas comparables). Recibís resumen, red flags, veredicto y el texto para el reporte.
4. Presentá al usuario el veredicto propuesto en ≤ 15 líneas y preguntá si está de acuerdo o quiere ajustarlo. El veredicto es una decisión del usuario, no del agente.
5. Con el acuerdo, editá **solo** la sección `## Notas y veredicto` del `REPORT.md` de la corrida:
   - `- **Veredicto**: go | no-go | iterar` (uno solo, en minúsculas)
   - `- **Por qué**:` números concretos (retorno vs benchmark, DD, trades, PF)
   - `- **Qué se aprendió**:`
   - `- **Siguiente experimento propuesto**:` con parámetros o cambios de spec concretos
6. `uv run tradingbot experiments sync` y mostrá la fila nueva de `experiments/REGISTRY.md`.
7. Si el veredicto es `iterar` con cambios de reglas, el siguiente paso es `/new-strategy <nombre> vN+1` (spec antes que código). Si es `no-go`, dejá en la spec vigente (`docs/strategy/`) la sección "Resultado y veredicto" actualizada para que nadie repita la prueba.

Nunca cambies `config.yaml`, `metrics.json` ni los CSV de una corrida registrada.
