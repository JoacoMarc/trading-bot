# ADR-0010: Gate 1 para estrategias de baja frecuencia y sizing por fracción fija

- Estado: aceptado
- Fecha: 2026-09-13
- Fase: 6

## Contexto

Cinco corridas de `ema_trend` (EXP-0007, WF-0001..0005) refutaron la familia, y en la última el único componente con ventaja robusta fue el filtro de mercado diario (ADR-0009): el B&H de BTC "filtrado" rindió más por unidad de riesgo que la estrategia que lo usaba (Sharpe OOS 0.98 vs 0.90; 1.10 vs 1.01 en muestra completa). La siguiente familia, `regime_bh`, es ese filtro convertido en estrategia: BTC long mientras el régimen diario está encendido, en cash cuando se apaga. Es de **baja frecuencia** (decenas de idas y vueltas en seis años) y de **tamaño fijo** (una fracción de la equity, no un riesgo por distancia al stop). El Gate 1 y el `RiskManager` estaban pensados para señales frecuentes con stop cercano: exigen ≥ 100 trades, Monte Carlo por remuestreo de trades y sizing por riesgo.

## Decisión

- **Umbrales de trades por spec.** `validation.trades_full_min` y `validation.trades_oos_min` (defaults 100 / 40) pasan a ser configurables desde `BotConfig`, quedan congelados en el `config.yaml` del `WF-` y se muestran en la tabla del gate. Cada spec declara los suyos y los justifica; `regime_bh` v1 usa 30 / 15 (una ida y vuelta por conmutación del régimen). El resto del gate (Sharpe, PF, DD, regímenes, meseta, holdout) no cambia.
- **Monte Carlo por bloques de retornos diarios (informativo).** Con pocos trades el bootstrap de PnL por trade dice poco; el walk-forward calcula además un bootstrap por bloques de 20 días de los retornos diarios de la curva OOS (5,000 corridas, misma semilla) y reporta percentiles de DD y retorno. No es criterio del gate en esta versión.
- **Sizing por fracción fija.** `risk.sizing_mode: risk | fraction`. En `fraction`, `RiskManager` dimensiona `position_fraction` × equity (acotado por el cash libre), sin mirar la distancia al stop; `risk_per_trade` y `max_position_pct` no aplican. El stop sigue siendo obligatorio en la señal y sigue publicándose: es de seguridad, no de sizing.
- **Régimen con memoria finita.** La estrategia calcula su régimen con `SMA(sma_days)` de cierres diarios y retorno a `momentum_days`, no con una EMA: ambos tienen ventana finita, así que la ventana de warmup reproduce exactamente la serie completa y `warmup_candles` puede ser la ventana misma (`(max(sma_days, momentum_days) + 2) × bars_per_day`), sin el multiplicador ≥ 5 que necesitan las medias exponenciales. Es una excepción documentada a la regla de la Fase 3, válida solo para indicadores de memoria finita.
- **Día completo, sin lookahead.** El régimen del día D se conoce al cierre de su última vela (23:59:59.999 UTC) y la orden sale al open siguiente; las velas intermedias de un día usan el régimen del último día completo. `bars_per_day` va en los parámetros (4h → 6) y se valida contra el timeframe de los datos.
- **Benchmark alineado.** `risk.market_filter` gana `average: ema | sma` y `benchmark_only`: con `benchmark_only` el filtro no bloquea entradas (la estrategia ya trae su régimen) pero el runner calcula el B&H BTC filtrado con la misma definición (`sma`). La estrategia se juzga contra ese benchmark, contra el B&H BTC y contra ETH como control.

## Alternativas consideradas

- **Relajar el tope de `risk_per_trade` para simular la fracción fija con un stop lejano**: acopla el tamaño al stop (un stop del 20 % con riesgo del 12 % del equity) y rompe la semántica de "riesgo por trade". Descartado.
- **EMA diaria como en el filtro de riesgo**: exige ≥ 5 × 200 días de warmup para converger (datos desde 2017) o acepta una discrepancia backtest/live por la semilla. La SMA evita el problema.
- **Bajar los umbrales de trades del gate para todos**: debilitaría el gate de las estrategias frecuentes. Por eso son por spec y quedan en el `config.yaml`.

## Consecuencias

- El `REGISTRY.md` mezcla familias con distinta frecuencia; los umbrales usados quedan en cada `WF-`.
- La familia `regime_bh` se evalúa con un solo par principal: el criterio "universo ≥ 4 pares" del plan no aplica y se documenta en la spec.
- Deuda: bootstrap por bloques como criterio del gate cuando haya calibración; `position_fraction` por par; el filtro de riesgo (`ema`) y el de la estrategia (`sma`) son dos implementaciones del mismo concepto.
