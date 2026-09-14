# EXP-0010 — regime_bh 4h

> Sección autogenerada por `tradingbot backtest`. Solo **Notas y veredicto** se escribe a mano.

## Configuración

- Estrategia: `regime_bh` · spec: `docs/strategy/regime-bh-v1.md`
- Datos: binance 4h 2025-09-01 → 2026-09-08 (incluye holdout), warmup 1212 velas, pares BTC/USDT, hash 4b239758a1fc
- Costos: fee 0.100 % en el activo recibido, slippage 5 bps
- Riesgo: riesgo/trade 1.00 %, tope 100 % del cash por posición, máx. 1 posiciones, exposición máx. 100 % · protecciones: pérdida diaria 3.0 % (día UTC), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 d), pausa por pérdidas off, cooldown tras stop off, filtro de mercado BTC/USDT (cierre diario > SMA200 y retorno 30 d > 0, solo benchmark)
- Reproducibilidad: git 278521b, params 937532e2f5, datos 4b239758a1fc, 0.3 s en PC-Joaco

| Parámetro | Valor |
|---|---|
| `bars_per_day` | `6` |
| `momentum_days` | `30` |
| `sma_days` | `200` |
| `stop_pct` | `0.2` |

## Métricas

| Métrica | Estrategia | B&H BTC | B&H BTC filtrado |
|---|---|---|---|
| Retorno total | +3.11 % | -27.21 % | +6.71 % |
| CAGR | +3.05 % | -26.75 % | +6.57 % |
| Sharpe (diario) | 0.41 | -0.51 | 0.48 |
| Sortino (diario) | 0.62 | -0.71 | 0.75 |
| Calmar | 0.48 | -0.50 | 0.56 |
| Max drawdown / mayor tramo bajo agua | +6.39 % / 322 d | +53.44 % / 337 d | +11.72 % / 319 d |
| Profit factor | 0.03 | — | — |
| Win rate | +25.00 % | — | — |
| Expectancy por trade | -85.92 | — | — |
| Trades / duración media | 4 / 126.0 h | 0 / — h | 0 / — h |
| Exposición | +10.91 % | +99.96 % | +10.86 % |
| Fees pagados / shortfall medio | 43.89 / 5.0 bps | 10.00 / 5.0 bps | 85.98 / 5.0 bps |

Rango: 2025-09-01 03:59 → 2026-09-08 15:59 UTC (372 días, 2236 velas). Equity inicial 10,000.00 → final 10,311.16 USDT.

## Desglose

### Por año

| Año | Retorno | Max DD | Trades | PnL |
|---|---|---|---|---|
| 2025 | -3.47 % | +6.23 % | 4 | -343.67 |
| 2026 | +6.81 % | +6.39 % | 0 | 0.00 |

### Por par

| Par | Trades | PnL | Win rate |
|---|---|---|---|
| BTC/USDT | 4 | -343.67 | +25.00 % |

### Motivos de salida

| Motivo | Trades |
|---|---|
| signal | 4 |

### Eventos del RiskManager

| Evento / motivo | Cantidad |
|---|---|
| protection_cleared:daily_loss_limit | 1 |
| protection_triggered:daily_loss_limit | 1 |

### Peores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2025-09-25 00:00 @ 113363.67 | 2025-09-26 00:00 @ 108939.99 | signal | -203.27 | -4.10 % |
| BTC/USDT | 2025-10-26 00:00 @ 111702.10 | 2025-10-30 00:00 @ 109966.28 | signal | -85.23 | -1.75 % |
| BTC/USDT | 2025-09-18 00:00 @ 116505.83 | 2025-09-22 00:00 @ 115174.67 | signal | -66.99 | -1.34 % |
| BTC/USDT | 2025-09-29 00:00 @ 112220.05 | 2025-10-11 00:00 @ 112718.10 | signal | 11.82 | +0.24 % |

### Mejores 5 trades

| Par | Entrada | Salida | Motivo | PnL | PnL % |
|---|---|---|---|---|---|
| BTC/USDT | 2025-09-29 00:00 @ 112220.05 | 2025-10-11 00:00 @ 112718.10 | signal | 11.82 | +0.24 % |
| BTC/USDT | 2025-09-18 00:00 @ 116505.83 | 2025-09-22 00:00 @ 115174.67 | signal | -66.99 | -1.34 % |
| BTC/USDT | 2025-10-26 00:00 @ 111702.10 | 2025-10-30 00:00 @ 109966.28 | signal | -85.23 | -1.75 % |
| BTC/USDT | 2025-09-25 00:00 @ 113363.67 | 2025-09-26 00:00 @ 108939.99 | signal | -203.27 | -4.10 % |

## Gráficos

`equity.png` (equity normalizada a 100 y drawdown), `trades.csv`, `equity.csv`.

## Notas y veredicto

- **Veredicto**: iterar
- **Por qué**: holdout pre-registrado, una sola vez, λ 0.5, git 278521b limpio. Letra del gate: **DD 6.39 % OK, PF 0.03 FALLA** (< 1.1). +3.11 %, Sharpe 0.41, exposición 10.9 %, 4 trades cerrados (−66.99, −203.27, +11.82, −85.23 = −343.67 USDT, win rate 25 %, todos `signal` en ≤ 288 h, sep–oct 2025) + 1 posición abierta desde el 2026-08-20 (fill ≈ 69,369; +657.83 no realizados al 2026-09-08 con BTC en 78,904) que la equity valúa a mercado pero el PF no cuenta (deuda conocida de ADR-0008). B&H BTC −27.2 % / DD 53.4 % (techo 126,011 el 2025-10-06, valle 58,382 el 2026-06-30); B&H filtrado +6.71 % / DD 11.7 %. Hipótesis: en cash 2025-10-30 → 2026-08-19 (294 días) mientras el B&H caía −37.4 % (−47.3 % al valle); retornos mensuales nov-2025 → jul-2026 = 0.00 %; pérdida acotada a 4 conmutaciones en el techo (−3.47 %; alarma de la spec −8 %). Es el segundo bear independiente y reproduce la anatomía de 2021-08 → 2022 (5 conmutaciones ≈ −8 %, luego 14 meses en cash). El PF depende de la fecha de corte: sintetizar la abierta al último close daría ≈ 1.86, pero es post hoc y **no se computa**. El veredicto `iterar` (medición del PF incompleta: 1 de 5 entradas abierta al corte) es una lectura menos literal que "un fallo refuta" de la spec; **firmado por el usuario el 2026-09-14** (la alternativa literal era `no-go`, familia cerrada hasta datos nuevos). Regla fijada ahora, antes de que cierre: PF sobre los 5 trades cerrados > 1.1 ⇔ salida neta ≥ ~75,000 USDT.
- **Qué se aprendió**: con ≤ 15 trades/año el PF del holdout mide la fecha de corte, no la estrategia: 4 trades del "cuerpo" (conmutaciones, PF histórico ≈ 0.2) y la única pierna larga abierta. La mecánica de DD funciona fuera de muestra por segunda vez (6.4 % vs 53.4 %); el edge de retorno sigue con una sola pierna nueva de 19 días. λ 0.5 y las protecciones no suman Sharpe (0.41 vs 0.48 del filtrado; pérdida diaria 1 disparo inerte, breaker 0). El B&H filtrado entra una vela 4h después que la estrategia (deuda menor). La spec esperaba 8–15 trades y hubo 5: un año 80 % apagado da todavía menos muestra. El pre-registro dijo "PF es casi una moneda" y aun así lo dejó vinculante: la próxima spec debe elegir criterios que discriminen o declararlos informativos antes de correr.
- **Siguiente experimento propuesto**: sin cambios de parámetros ni de spec. Cuando cierre la posición abierta del 2026-08-20 (régimen apagado o stop), correr `tradingbot backtest --config configs/regime-bh.yaml --from 2025-09-01 --include-holdout` con datos hasta esa fecha (nuevo EXP, misma config 937532e2f5) y leer el PF sobre los 5 trades cerrados: > 1.1 → `go` a paper como estaba pre-registrado (evidencia débil); ≤ 1.1 → `no-go` literal, familia cerrada, holdout gastado. Mientras tanto la Fase 7 puede arrancar por infraestructura con `regime_bh` como carga de prueba; el reloj del Gate 2 no arranca hasta cerrar el Gate 1. No probar `momentum_days` 35 ni salida solo por SMA.
