---
name: phase-start
description: Arranca una sesión de trabajo sobre el trading-bot. Lee docs/ROADMAP.md, identifica la fase activa (o la indicada), muestra objetivo, entregables pendientes, DoD y archivos clave, verifica el estado del repo y propone el primer paso. Usar al comienzo de cada sesión o cuando el usuario diga "arranquemos la fase N".
argument-hint: "[número de fase opcional]"
---

Objetivo: dejar a la sesión con contexto completo de la fase antes de tocar código. No se escribe código dentro de esta skill.

Pasos:

1. Leé `docs/ROADMAP.md`. La fase activa es la primera con estado `en curso`; si el usuario pasó un número (`$ARGUMENTS`), usá esa. Si la fase indicada tiene una anterior sin cerrar, avisá.
2. Leé la sección correspondiente de `docs/PLAN.md` (sección "Fase N") para los detalles de entregables, verificación y DoD.
3. Verificá el estado del repo con `git status --short` y `git log --oneline -5`. Si hay cambios sin commitear de la sesión anterior, mostralos antes de seguir.
4. Corré `uv run pytest` (rápido) y reportá si la base está en verde. Si falla, eso es lo primero a resolver.
5. Revisá qué entregables de la fase ya existen en el repo (archivos listados en el plan) y marcá cuáles faltan.
6. Si la fase toca `strategy/`, leé la spec vigente en `docs/strategy/`. Si toca experimentos, mirá las últimas filas de `experiments/REGISTRY.md`.
7. Presentá al usuario, en ≤ 25 líneas: fase y objetivo, entregables pendientes, DoD, archivos clave, riesgos conocidos, y el primer paso concreto propuesto. Preguntá solo si hay una decisión que el plan no cubre.

Recordá las reglas duras de `CLAUDE.md`: nada de código de fases futuras, ADR para decisiones de arquitectura, spec antes de estrategia.
