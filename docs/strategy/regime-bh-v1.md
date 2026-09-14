# regime_bh v1

- Estado: confirmada en walk-forward (Gate 1 `aprobado (falta el holdout)`, WF-0006); holdout corrido (EXP-0010): DD OK, PF 0.03 FALLA con 1 de 5 entradas abierta al corte → `iterar` (medición incompleta; decisión del usuario, ver Resultado)
- Fecha: 2026-09-13
- Experimentos: EXP-0009 (muestra completa BTC), WF-0006 (BTC, fijo, meseta), WF-0007 (ETH como control), WF-0008 / WF-0009 (λ 0.5 / 0.75), EXP-0010 (holdout 2025-09 → 2026-09, λ 0.5), EXP-0011 (curva continua 2019-08 → 2026-09 con la config final)
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
| `risk.position_fraction` (λ) | 0.60 en la evaluación; **0.50 final** | corridas aparte con 0.50 y 0.75 (WF-0008/0009) | no es parámetro de estrategia: no entra en la meseta. Fijada en 0.5 por presupuesto de DD antes del holdout (ver Resultado) |

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

### Walk-forward (2026-09-13, git `f1dd153`, árbol limpio)

| Corrida | Config | Curva | Retorno | Sharpe | Max DD | PF | Trades | Gate 1 | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| EXP-0009 | BTC λ 0.6 | muestra completa 2019-08 → 2025-09 | +401.6 % | 1.19 | 25.2 % | 2.77 | 57 | — | go (control) |
| WF-0006 | BTC λ 0.6, `--plateau` | OOS 2021-08 → 2025-08 | +112.9 % | 1.04 | 17.8 % | 2.64 | 34 | aprobado (falta el holdout) | **go** |
| WF-0007 | ETH λ 0.6 (control) | OOS | +84.7 % | 0.77 | 19.9 % | 1.77 | 33 | no aprobado (DD intra-2021 38.7 %) | go (control) |
| WF-0008 | BTC λ 0.5 | OOS | +90.6 % | 1.04 | 15.3 % | 2.68 | 34 | incompleto (meseta n/a) | go (control) |
| WF-0009 | BTC λ 0.75 | OOS | +148.6 % | 1.05 | 21.5 % | 2.58 | 34 | no aprobado (DD intra-año 25.2 %, MC p95 37.7 %) | no-go |

Benchmarks OOS: B&H BTC +175.8 %, Sharpe 0.76, DD 77.1 %; B&H BTC filtrado (mismo régimen, λ = 1, sin protecciones) +193.2 %, Sharpe 1.01, DD 27.8 %.

**Criterios prefijados: confirma.** Sharpe OOS 1.04 ≥ 0.8 y > 0.76 del B&H; DD OOS 17.8 %; 2022 = 0.00 % (en cash); DD intra-año máx. 22.7 % (2021), 2020 13.0 %; PF 2.64; meseta 14/14 (PF > 1.1 y retorno > 0) y 14/14 con Sharpe ≥ 0.5 × base; Sharpe de la muestra completa sin 2022 = 1.3 (umbral de refutación 0.69 = 0.5 × 1.38 del B&H). Ningún criterio de refutación se dispara.

Lo que la confirmación **no** dice (WF-0006, Notas y veredicto): la ventaja sobre el B&H BTC es probable pero no significativa (bootstrap por bloques de la diferencia de Sharpe: P(Δ > 0) 0.79; la muestra tiene un solo bear completo); sin 2022 el B&H BTC tiene mejor Sharpe (1.38 vs 1.3): el edge es evitar el bear, que es la hipótesis; λ y las protecciones no aportan Sharpe, compran DD (Δ +0.03 vs el filtrado); el PnL está en 15 trades largos y el stop no se ejecutó nunca; la meseta es una pendiente en `momentum_days` (no se toca: sería ajuste sobre el OOS). Alarmas de la spec: 2019-H2 PF 0.03 y −19.2 % (peor caso anticipado, B&H −30.7 %); 2024 con 15 entradas (> 12). ETH confirma la dirección de la regla pero con λ 0.6 revienta el presupuesto de DD (regla del mercado, no del activo; un multi-activo exige λ por par).

**λ final = 0.5**, decidida antes del holdout con el presupuesto de la spec: el Sharpe es invariante (1.04 / 1.04 / 1.05) y el DD escala casi lineal (histórico 21.4 / 25.2 / 28.6 %); 0.6 ya tocó el 25 % desde el pico histórico y 0.75 falla el gate. Cuesta 3.3 pp de CAGR OOS. `configs/regime-bh.yaml` queda con 0.5.

### Holdout (pre-registrado antes de correr, 2026-09-13)

- Una sola vez, con la config final (λ 0.5, mismos parámetros): EXP-0010 = holdout solo (`--from 2025-09-01 --include-holdout`, 2025-09-01 → 2026-09-08, ~12 meses), sobre el que se mide el criterio del gate **PF > 1.1 y DD ≤ 25 %**; EXP-0011 = curva continua 2019-08-01 → 2026-09-08 con la misma config (informativa: la equity que hubiera visto una cuenta desde el inicio, sin el corte artificial del 2025-09-01).
- Expectativa: 8–15 trades; PF > 1.1 es casi una moneda con tan pocos, así que el criterio que discrimina es el DD. Un pase es evidencia débil (12 meses más de la misma familia de mercado); un fallo refuta. La evidencia fuerte para esta hipótesis llega con el próximo bear.
- Si pasa: `go` a paper (Fase 7) con esta config; en el runbook: el breaker re-basa el pico en backtest pero en paper/live solo reanuda con `resume()`, y la pérdida diaria es inerte en esta estrategia. Si falla: la familia queda en `no-go` y el holdout gastado; nada de ajustar `momentum_days` para pasar.

### Resultado del holdout (2026-09-13, git `278521b`, árbol limpio)

| Corrida | Rango | Retorno | Sharpe | Max DD | PF | Trades | B&H BTC | B&H filtrado |
|---|---|---|---|---|---|---|---|---|
| EXP-0010 | holdout 2025-09-01 → 2026-09-08 | +3.11 % | 0.41 | 6.39 % | **0.03** | 4 cerrados + 1 abierta | −27.2 %, DD 53.4 % | +6.71 %, DD 11.7 % |
| EXP-0011 | continua 2019-08-01 → 2026-09-08 | +315.4 % | 1.10 | 21.44 % | 2.57 | 63 | +681.6 %, 0.78, 77.0 % | +790.3 %, 1.05, 43.0 % |

- **Letra del gate: DD pasa, PF falla.** Los 4 trades cerrados son conmutaciones en el techo de sep–oct 2025 (−343.67 USDT, −3.47 %); la única pierna larga (entrada 2026-08-20, +657.83 no realizados al corte) está abierta y el PF no la cuenta (deuda de ADR-0008: las abiertas al cierre no se sintetizan). Sintetizada daría PF ≈ 1.86, pero es post hoc y no se computa.
- **Hipótesis:** el holdout fue el segundo bear independiente (BTC −27 %, −47 % al valle) y la estrategia hizo lo que promete: 294 días en cash (nov-2025 → jul-2026 con retorno mensual 0.00 %), pérdida acotada a las conmutaciones del techo (alarma −8 % no disparada), DD 6.4 % vs 53.4 %. Lo que no confirma es el edge de retorno: una sola pierna nueva de 19 días.
- **Veredicto: `iterar`, con la medición del PF declarada incompleta** (1 de 5 entradas abierta al corte; el pre-registro no dijo qué hacer en ese caso). Es una lectura menos literal que "un fallo refuta" y **la firma el usuario**; la alternativa literal es `no-go` (familia cerrada hasta datos nuevos; el holdout ya fue visto). **Regla fijada ahora, antes de que cierre la posición:** cuando cierre (régimen apagado o stop), correr `tradingbot backtest --config configs/regime-bh.yaml --from 2025-09-01 --include-holdout` con datos hasta esa fecha (misma config, params `937532e2f5`) y leer el PF sobre los 5 trades cerrados: > 1.1 (⇔ salida neta ≥ ~75,000 USDT) → `go` a paper como estaba pre-registrado; ≤ 1.1 → `no-go` literal. Cero grados de libertad: sin cambios de parámetros, de spec ni de umbral. Mientras tanto la Fase 7 puede arrancar por infraestructura con `regime_bh` como carga de prueba; las semanas de paper no cuentan para el Gate 2 hasta cerrar el Gate 1.
- **Observación metodológica (para un ADR futuro, separada de este veredicto):** para familias con ≤ 15 trades/año el criterio de holdout "PF > 1.1 sobre trades cerrados" mide la fecha de corte, no la estrategia. Propuesta a evaluar: DD ≤ 25 % y ≤ 50 % del DD del B&H (mark-to-market), retorno ≥ 0 o ≥ λ × B&H filtrado − tolerancia, PF solo con ≥ 15 trades cerrados (si no, `n/a`), y posiciones abiertas al corte sintetizadas siempre.
