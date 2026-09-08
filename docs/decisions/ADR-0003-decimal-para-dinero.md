# ADR-0003: Decimal para dinero; float64 solo en indicadores

- Estado: aceptado
- Fecha: 2026-09-07
- Fase: 0

## Contexto

Binance exige cantidades múltiplo de `stepSize` (BTC/USDT: 0.00001) y precios múltiplo de `tickSize`, y rechaza órdenes fuera de filtro (`-1013`) o sin saldo suficiente (`-2010`). Con `float`, `0.1 + 0.2 != 0.3`, los redondeos acumulan error y una venta por la cantidad "comprada" falla porque la fee se descontó del activo recibido. freqtrade usa `float` en todo y compensa con redondeos ad hoc.

## Decisión

- Precios, cantidades, fees, cash, equity y PnL viven en `decimal.Decimal`.
- La frontera float → Decimal es siempre `Decimal(str(x))`; nunca `Decimal(float)`.
- Cantidades se cuantizan al `stepSize` con `ROUND_DOWN`; precios al `tickSize`. `minNotional` se verifica en entradas y salidas.
- `Position.qty` es la cantidad **neta** tras la fee en activo base. El remanente por debajo del `stepSize` va a un ledger `dust`, fuera del equity operativo.
- `float64` (numpy/pandas) solo dentro de `indicators/` y para las series de precios que alimentan a la estrategia. La señal sale como enum + niveles que se convierten a Decimal en el `Engine`.

## Alternativas consideradas

- **float con redondeo al final**: simple, pero los errores aparecen justo en los bordes (min notional, saldo exacto) y son difíciles de reproducir.
- **Enteros en unidades mínimas (satoshis, centavos)**: correcto y rápido, pero cada par tiene su propio `stepSize`/`tickSize` y el código se llena de conversiones; Decimal con cuantización explícita es más legible.

## Consecuencias

- Tests con `hypothesis` sobre cuantización y contabilidad (cash ≥ 0, qty ≥ 0, suma de fees).
- Algo más lento que float en el loop de ejecución; irrelevante frente a las velas de 4h y al costo de los indicadores.
- Regla dura en `CLAUDE.md` (regla 1). El `trading-code-reviewer` busca `float(` sobre montos y `Decimal(` sobre floats.
