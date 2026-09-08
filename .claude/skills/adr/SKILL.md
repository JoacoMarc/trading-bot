---
name: adr
description: Crea un Architecture Decision Record en docs/decisions/ a partir de la plantilla, con el siguiente número disponible. Usar cuando se toma una decisión de arquitectura, de stack o de alcance que futuras sesiones deben respetar.
argument-hint: "<título corto de la decisión>"
---

Pasos:

1. Título: `$ARGUMENTS`. Si está vacío, preguntá el título antes de seguir.
2. Número: listá `docs/decisions/ADR-*.md`, tomá el mayor número y sumá 1 (4 dígitos). El slug es el título en minúsculas, sin tildes, con guiones.
3. Copiá `docs/decisions/TEMPLATE.md` a `docs/decisions/ADR-NNNN-<slug>.md` y completá:
   - **Contexto**: el problema y las restricciones reales (no genéricas).
   - **Decisión**: una afirmación clara, en presente.
   - **Alternativas consideradas**: cada una con el motivo concreto por el que se descartó.
   - **Consecuencias**: qué se vuelve más fácil, qué más difícil, qué reglas duras se derivan (y si hay que agregarlas a `CLAUDE.md`).
   - Estado `aceptado`, fecha de hoy, fase actual.
4. Si la decisión reemplaza a un ADR anterior, marcá el anterior como `reemplazado por ADR-NNNN`.
5. Si la decisión implica una regla operativa nueva, proponé la línea exacta para `CLAUDE.md` y agregala si el usuario está de acuerdo.
6. Mostrá el ADR completo al usuario.

Estilo: conciso, en español, sin relleno. Un ADR típico tiene 30–60 líneas.
