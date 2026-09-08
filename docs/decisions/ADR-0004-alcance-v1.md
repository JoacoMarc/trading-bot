# ADR-0004: Alcance v1 — Binance Spot, solo long, quote USDT

- Estado: aceptado
- Fecha: 2026-09-07
- Fase: 0

## Contexto

El objetivo es validar un bot confiable antes de arriesgar dinero, con una sola persona construyéndolo por fases. Cada dimensión extra (futures, shorts, multi-exchange, múltiples quotes) multiplica los casos de borde de ejecución y contabilidad, y aleja la fecha en la que hay algo verificable corriendo en paper.

## Decisión

- **Exchange**: solo Binance Spot. Las abstracciones (`Broker`, `MarketFeed`) existen para testear y para el camino único backtest/paper/live (ADR-0002), no para soportar otros exchanges.
- **Dirección**: solo long. Sin margin ni futures; sin apalancamiento ni liquidaciones.
- **Quote**: todos los pares del universo cotizan en USDT; `BotConfig` lo valida. El equity se expresa en USDT.
- **Universo inicial**: 8 pares líquidos con historia desde 2019–2020 (BTC, ETH, BNB, XRP, ADA, LTC, LINK, SOL); backtests iniciales con BTC+ETH; el gate se evalúa con ≥ 4 pares.
- **Estrategia inicial**: una familia (trend following `ema_trend` en 4h). Otras familias solo después de que la primera pase o falle el gate con evidencia registrada.
- **LLM**: analista fuera del loop (Fase 9); nunca decide ni ejecuta trades.
- **Interfaz**: CLI + Telegram. Sin dashboard web en v1.

## Alternativas consideradas

- **Futures desde el inicio**: permite shorts y ganar en bajistas, pero agrega margen, liquidación y funding, y el riesgo de errores caros durante el aprendizaje.
- **Diseñar la abstracción para futures ahora**: código especulativo que no se va a ejercitar en meses; se agrega en el backlog cuando el spot esté en live.
- **Multi-exchange vía ccxt**: ccxt lo facilita, pero cada exchange tiene filtros, fees y semántica de stops distintos; no aporta al objetivo de validar confiabilidad.

## Consecuencias

- Menos código, menos casos de borde, paper trading antes.
- Un long-only con filtro de régimen va a perder o quedarse afuera en mercados bajistas: el gate lo contempla (pérdida ≤ 8 % en 2022) en vez de exigir ganar siempre.
- Backlog explícito en `docs/PLAN.md` Fase 11: futures, multi-timeframe, segunda estrategia, dashboard.
