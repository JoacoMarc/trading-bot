---
name: phase-close
description: Cierra la fase activa del trading-bot. Verifica el DoD (tests, ruff, mypy, docker si aplica, docs y ADRs), actualiza docs/ROADMAP.md y la memoria persistente, pide revisión al trading-code-reviewer cuando corresponde y propone el commit. Usar cuando el usuario diga "cerremos la fase", "terminamos la fase N" o al completar todos los entregables.
argument-hint: "[número de fase opcional]"
---

Objetivo: no dar por cerrada una fase sin evidencia. Cada paso reporta resultado real; si algo falla, se arregla o se deja explícito como pendiente.

Pasos:

1. Identificá la fase (activa en `docs/ROADMAP.md` o `$ARGUMENTS`) y su DoD en `docs/PLAN.md`.
2. Calidad: corré y mostrá el resultado de
   - `uv run ruff check .` y `uv run ruff format --check .`
   - `uv run mypy`
   - `uv run pytest` (y `uv run pytest -m network` si la fase agregó código que habla con Binance)
   - `docker compose build` cuando la fase cambió dependencias, Dockerfile o compose.
3. Entregables: recorré la lista de la fase en el plan y confirmá archivo por archivo. Lo que falte se lista como pendiente; no se marca la fase como cerrada con pendientes bloqueantes.
4. Revisión: si la fase tocó `strategy/`, `indicators/`, `engine/`, `execution/`, `risk/` o `exchange/`, invocá al agente `trading-code-reviewer` sobre los archivos cambiados y aplicá los bloqueantes antes de seguir.
5. Docs: ADRs de las decisiones tomadas (`/adr`), glosario con los conceptos nuevos, specs de estrategia actualizadas, `experiments/REGISTRY.md` regenerado si hubo corridas.
6. Actualizá `docs/ROADMAP.md`: marcá los checkboxes cumplidos, poné la fase en `cerrada` con la fecha, la siguiente en `en curso`, y agregá una línea de "Aprendizajes" con lo no obvio.
7. Memoria persistente: guardá en la memoria de Claude (directorio de memoria del proyecto) el estado de la fase cerrada y los aprendizajes que no se deducen del repo (decisiones descartadas, cosas que fallaron, preferencias del usuario). Actualizá `MEMORY.md`.
8. Proponé el commit: mostrá `git status --short`, un mensaje Conventional Commits en español (`feat(fase-N): ...`) con cuerpo breve, y esperá confirmación del usuario antes de ejecutar `git commit`.

Salida final (≤ 20 líneas): checklist del DoD con OK/FALLA por ítem, pendientes explícitos, y el mensaje de commit propuesto.
