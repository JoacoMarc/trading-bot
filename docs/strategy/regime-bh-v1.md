# regime_bh v1

- Estado: en evaluación
- Fecha: 2026-09-13
- Experimentos: EXP-0009 (muestra completa BTC), WF-0006 (BTC, fijo, meseta), WF-0007 (ETH como control), WF-0008 / WF-0009 (λ 0.5 / 0.75)
- Código: `src/tradingbot/strategy/strategies/regime_bh.py`; sizing por fracción en `risk/sizing.py` (ADR-0010); config `configs/regime-bh.yaml`
- Origen: el filtro de mercado de ADR-0009 (`ema_trend` v3, WF-0005) rindió más que la estrategia que lo usaba; se lo evalúa solo.

## Hipótesis

En BTC la mayor parte del retorno se concentra en los tramos en que el precio está por encima de su media de 200 días y con momentum positivo, y la mayor parte del drawdown ocurre fuera de ellos (2018, 2022). Estar comprado solo en esos tramos debería conservar buena parte del retorno del buy & hold con una fracción de su drawdown, y por lo tanto un Sharpe mayor, después de costos. La ventaja, si existe, es un premio por momentum/tendencia de baja frecuencia bien documentado en la literatura de activos (time-series momentum) y visible en WF-0005: B&H filtrado Sharpe 0.98 vs B&H 0.76 en el OOS, con DD 31 % vs 77 %. El riesgo de la hipótesis es que el edge sea un solo evento (2022): la spec lo prueba explícitamente.

## Universo y timeframe

- Par principal: BTC/USDT. Control: ETH/USDT con la misma config (no elegido por PnL; sirve para ver si la regla es del activo o del mercado).
- Timeframe de las velas: 4h (`bars_per_day = 6`); las decisiones son diarias (último cierre de cada día UTC).
- Datos: 2019-08-01 → 2025-09-01 (sin holdout). Warmup: `(max(sma_days, momentum_days) + 2) × 6` = 1,212 velas ≈ 202 días, exacto (memoria finita).
- El criterio "universo ≥ 4 pares" del Gate 1 no aplica: la estrategia es de un activo; se documenta como excepción (ADR-0010).

## Reglas

Evaluadas al cierre de cada vela de 4h con **días completos**; la orden se ejecuta al open de la vela siguiente (ADR-0002).

- **Régimen (día D):** `cierre_diario(D) > SMA(sma_days)` de cierres diarios **y** `cierre_diario(D) / cierre_diario(D − momentum_days) − 1 > 0`. Se conoce al cierre de la última vela del día; las velas siguientes del día D+1 usan el régimen de D.
- **Entrada:** régimen encendido y sin posición → `ENTER_LONG`. Re-entra tras un stop mientras el régimen siga encendido (la vela siguiente).
- **Salida por señal:** régimen apagado con posición → `EXIT_LONG` al open siguiente.
- **Stop de seguridad:** `stop_pct` (20 %) bajo el precio, re-anclado al fill; no es de sizing, es contra un crash intradía con el régimen encendido. Sin trailing.
- **Sizing (`RiskManager`, modo `fraction`):** `position_fraction` λ = 0.60 de la equity, 1 posición. No hay riesgo por distancia al stop: el DD se presupuesta con λ (BTC con DD 40 % → cartera ≈ 24 %).
- **Protecciones (ADR-0007), defaults:** pérdida diaria 3 % (con λ 0.6, un día de BTC −5 % la dispara y solo bloquea re-entradas ese día), circuit breaker DD 20 % (reanuda bajo 10 % o tras 30 días). El filtro de mercado de riesgo va en `benchmark_only`: la estrategia ya trae el régimen y así el benchmark B&H filtrado usa la misma definición (`sma`).

## Parámetros

| Parámetro | Default | Meseta ±20 % / rango | Comentario |
|---|---|---|---|
| `sma_days` | 200 | 150–250 paso 10 | media de cierres diarios |
| `momentum_days` | 30 | 20–45 paso 5 | retorno a N días |
| `stop_pct` | 0.20 | 0.10–0.30 paso 0.05 | stop de seguridad |
| `bars_per_day` | 6 | fijo (4h) | validado contra el timeframe |
| `risk.position_fraction` (λ) | 0.60 | corridas aparte con 0.50 y 0.75 (WF-0008/0009) | no es parámetro de estrategia: no entra en la meseta |

No se optimiza nada: los valores son redondos y anteriores a mirar el OOS de esta familia (200/30 son los de ADR-0009).

## Criterios prefijados (antes de correr)

Umbrales de trades del gate para esta spec: ≥ 30 en la muestra completa y ≥ 15 en la curva OOS (`validation.trades_full_min/oos_min`, ADR-0010).

- **Confirma** (candidata a paper, sujeto al Gate 1 completo con esos umbrales) si se cumplen todos en WF-0006 (BTC, fijo, IS 24 m / OOS 6 m, `--plateau`, MC 5,000, semilla 42): Sharpe OOS ≥ 0.8 **y** ≥ Sharpe del B&H BTC OOS; DD OOS ≤ 25 %; 2022 ≥ −8 % y ningún año con DD intra-año > 25 % (incluido 2020, muestra completa); PF OOS ≥ 1.3; ≥ 80 % de las variantes de la meseta con PF > 1.1 y retorno > 0 **y** ≥ 80 % con Sharpe ≥ 0.5 × el base; **Sharpe de la muestra completa sin 2022 ≥ 0.8** (el edge no puede ser solo el bear).
- **Refuta la familia** si Sharpe OOS < Sharpe del B&H BTC OOS, o DD intra-2020 > 25 % en la muestra completa, o menos del 60 % de las variantes pasan, o Sharpe sin 2022 < 0.5 × el del B&H BTC sin 2022.
- **Control ETH (WF-0007):** informativo; si ETH pasa y BTC no (o al revés) se anota como riesgo de "regla del activo", no cambia el veredicto.
- **λ (WF-0008 λ 0.5, WF-0009 λ 0.75):** el Sharpe no debería moverse (es invariante a la escala); el DD sí. Sirve para elegir el presupuesto de DD, no para elegir λ por retorno.
- Zona intermedia: `iterar` una sola vez más con un cambio escrito antes de correr (p. ej. `momentum_days` 90 o salida solo por SMA). No se ajusta nada mirando el OOS.

## Comportamiento esperado por régimen

- **Alcista sostenido (2020-21, 2023-24):** comprado casi todo el tiempo; retorno ≈ λ × B&H menos los apagados falsos en correcciones (2024 tuvo ~39 en el filtro de ADR-0009). Alarma: más de 12 idas y vueltas por año o costos > 10 % del retorno bruto.
- **Bajista (2022):** en cash casi todo el año; pérdida acotada a las conmutaciones falsas de los rebotes. Alarma: 2022 < −8 %.
- **Crash con régimen encendido (2020-03, 2021-05):** el stop del 20 % y el circuit breaker actúan; la re-entrada espera al régimen. Alarma: DD intra-2020 > 25 %.
- **Lateral largo (2019-H2, 2023-H2):** el peor caso: conmutaciones seguidas con pérdidas chicas y costos. Alarma: PF < 1 en esos tramos.

## Riesgos conocidos

- Un solo activo y una sola regla: la muestra son ~6 años y ~2 ciclos; el Sharpe tiene un error estándar ≈ 0.4. Por eso se exige el criterio sin 2022 y se compara contra B&H, no solo contra 0.8.
- Look-ahead de diseño: 200 / 30 se conocen desde ADR-0009 (ya miraron 2022). Mitigación: la meseta y el criterio sin 2022.
- Interacción entre stop 20 %, breaker 20 % y re-entrada: puede dejar la estrategia afuera 30 días en un rebote fuerte.
- Costos bajos por construcción (pocas operaciones): si el resultado depende de operar seguido, la hipótesis está mal.

## Resultado y veredicto

Pendiente (se completa con EXP-0009 y WF-0006..0009).
