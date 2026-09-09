# GATES — criterios para avanzar de etapa

Los criterios del plan (§2.3) hechos ejecutables (ADR-0008). El Gate 1 lo calcula `tradingbot walkforward` y queda en la tabla "Gate 1" del `REPORT.md` de cada `WF-NNNN`; los umbrales viven en `validation/gates.py` y acá, y cambian en los dos lugares a la vez. Un criterio `n/a` (no evaluable con esa corrida) **no** cuenta como aprobado.

## Holdout

Los últimos 12 meses de datos (desde **2025-09-01**) quedan reservados. Ningún backtest, walk-forward ni optimización los usa: `--to` los excluye por defecto y `--include-holdout` solo se usa en la corrida final de una familia de estrategia. Se evalúan **una sola vez** por familia; si la familia cambia después, el holdout ya está gastado y hay que esperar datos nuevos.

## Gate 1 — Backtest → Paper

Se evalúa con el universo final (≥ 4 pares) y la configuración de riesgo completa, sobre un `WF-` en modo fijo (los criterios de muestra completa y regímenes exigen parámetros fijos; en modo optimizado quedan `n/a`).

| Criterio | Umbral | Cómo se calcula |
|---|---|---|
| Walk-forward | IS 24 meses / OOS 6 meses, rodante, ventanas OOS contiguas | `build_windows`; solo ventanas completas; el paso es igual al OOS |
| Sharpe OOS | ≥ 0.8 **y** ≥ Sharpe de B&H BTC del mismo período | retornos diarios de la curva OOS concatenada (rf = 0, √365) vs B&H BTC encadenado sobre los mismos tramos OOS |
| Profit factor OOS | ≥ 1.3 | trades OOS acumulados (PnL en quote) |
| Max drawdown OOS | ≤ 25 % **y** ≤ 50 % del DD de B&H BTC OOS | curva OOS concatenada, mark-to-market por vela |
| Ventanas OOS positivas (secundario) | ≥ 60 % | retorno de cada tramo OOS |
| Cantidad de trades | ≥ 100 en la muestra completa **y** ≥ 40 en la curva OOS | muestra completa = mismo rango que todas las ventanas, parámetros fijos |
| Regímenes por año | positivo en 2020–21 y 2023–24; pérdida ≤ 8 % en 2022; ningún año con DD **intra-año** > 25 % | `validation/regimes.py` sobre la muestra completa; el DD intra-año reinicia el pico al empezar el año (el `REPORT.md` de backtest muestra otro DD anual, contra el pico corriente) |
| Meseta de parámetros | ±20 % en cada parámetro (uno a la vez) y en los vértices del hipercubo ±20 %: PF > 1.1 y retorno > 0 en ≥ 80 % de los casos | `--plateau`; variantes cuantizadas al paso del `search_space` de la estrategia |
| Monte Carlo | 5,000 remuestreos con reemplazo de los trades OOS: DD del percentil 95 ≤ 35 % | equity = cash inicial + PnL acumulado, semilla registrada |
| Holdout | PF > 1.1 y DD ≤ 25 % | `tradingbot backtest --include-holdout` con la config final, una sola vez |
| Tests | equivalencia/lookahead en verde | `uv run pytest` |

Veredicto del gate: `aprobado (falta el holdout)` si todo lo evaluable pasa; `incompleto` si algo quedó `n/a`; `no aprobado` si algo falla. El veredicto humano (`go | no-go | iterar`) va en "Notas y veredicto" y puede ser más estricto que el gate, nunca más laxo.

## Gate 2 — Paper → Live

| Criterio | Umbral |
|---|---|
| Duración | ≥ 8 semanas de paper desde el último cambio en `strategy/`, `risk/`, `engine/` o `execution/` |
| Paridad (`tradingbot parity`) | ≥ 95 % de señales coincidentes con el backtest del mismo período; desvío medio de fill ≤ 15 bps |
| Estabilidad | 0 excepciones no manejadas en las últimas 4 semanas |
| Reconciliación | exchange ↔ DB sin discrepancias |
| Kill switch | probado en paper (`tradingbot stop --flatten` contra el proceso real) |
| Testnet | ciclo completo entrada → stop nativo → salida verificado |
| Capital | lo define el usuario; se recomienda pequeño y se aumenta solo tras N semanas dentro de banda |

## Checklist de go-live (se completa en Fase 10)

Pendiente: API key solo lectura + spot trading, sin retiros, IP whitelisted; claves del modo real solo en el perfil `live` de compose; runbooks de live e incidentes; `risk-auditor` firma la checklist.
