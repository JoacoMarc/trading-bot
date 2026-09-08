# GATES — criterios para avanzar de etapa

> **Estado: borrador.** Son los criterios acordados en el plan (`PLAN.md`, §2.3). Se formalizan y se vuelven ejecutables en la **Fase 6**, cuando existan `walkforward`, `plateau`, `montecarlo` y `regimes`. Hasta entonces sirven como referencia para diseñar las métricas.

## Holdout

Los últimos 12 meses de datos (desde **2025-09-01**) quedan reservados. Ningún backtest ni optimización los usa: `--to` los excluye por defecto y `--include-holdout` solo se usa en la corrida final de una familia de estrategia. Se evalúan **una sola vez** por familia.

## Gate 1 — Backtest → Paper

Se evalúa con el universo final (≥ 4 pares) y la configuración de riesgo completa, al cierre de la Fase 6.

| Criterio | Umbral |
|---|---|
| Walk-forward | IS 24 meses / OOS 6 meses, rodante (≈ 9 ventanas desde 2019); ventanas OOS concatenadas en una sola curva |
| Sharpe OOS (retornos diarios, rf = 0, √365) | ≥ 0.8 **y** ≥ Sharpe de buy & hold BTC del mismo período |
| Profit factor OOS | ≥ 1.3 |
| Max drawdown OOS | ≤ 25 % **y** ≤ 50 % del DD de buy & hold BTC |
| Ventanas OOS positivas (secundario) | ≥ 60 % |
| Cantidad de trades | ≥ 100 en la muestra completa **y** ≥ 40 en la curva OOS |
| Regímenes por año | positivo en 2020–21 y 2023–24; pérdida ≤ 8 % en 2022; ningún año con DD > 25 % |
| Meseta de parámetros | ±20 % en cada parámetro (uno a la vez) y en los vértices del hipercubo ±20 %: PF > 1.1 y retorno > 0 en ≥ 80 % de los casos |
| Monte Carlo (5000 remuestreos de trades) | DD del percentil 95 ≤ 35 % |
| Holdout | PF > 1.1 y DD ≤ 25 % |
| Tests | equivalencia/lookahead en verde |

## Gate 2 — Paper → Live

| Criterio | Umbral |
|---|---|
| Duración | ≥ 8 semanas de paper desde el último cambio en `strategy/`, `risk/`, `engine/` o `execution/` |
| Paridad (`tradingbot parity`) | ≥ 95 % de señales coincidentes con el backtest del mismo período; desvío medio de fill ≤ 15 bps |
| Estabilidad | 0 excepciones no manejadas en las últimas 4 semanas |
| Reconciliación | exchange ↔ DB sin discrepancias |
| Kill switch | probado en paper |
| Testnet | ciclo completo entrada → stop nativo → salida verificado |
| Capital | lo define el usuario; se recomienda pequeño y se aumenta solo tras N semanas dentro de banda |

## Checklist de go-live (se completa en Fase 10)

Pendiente: API key solo lectura + spot trading, sin retiros, IP whitelisted; `.env.live` solo en perfil `live`; runbooks de live e incidentes; `risk-auditor` firma la checklist.
