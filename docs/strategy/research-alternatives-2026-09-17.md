# Investigación de estrategias alternativas — 2026-09-17

Estado: investigación y propuesta de experimentos; ninguna alternativa nueva fue implementada ni backtesteada en esta revisión.

Base revisada: commit local `23131ce`, código, configuraciones versionadas, especificaciones, `ROADMAP`, gates y artefactos de `experiments/runs/`. Tras resolver el acceso SSH, se verificaron también el checkout del VPS (`a68735b`), el contenedor paper, su configuración, estado y DB en modo de solo lectura. La diferencia entre esos commits se limita a `docs/ROADMAP.md`. Las cifras siguientes son simulaciones registradas, no rendimientos de una cuenta real. Se contrastaron métricas JSON con los trades y la equity exportados de las corridas principales.

Recomendación: mantener `regime_bh` como referencia y carga del paper actual; investigar primero retrocesos en tendencia y rupturas de rango en 4h, por separado. La rotación por momentum es una tercera línea prometedora, con más trabajo de cartera. Evaluar rendimiento neto y riesgo antes que cantidad de movimientos.

## 1. Qué hace hoy y por qué opera poco

`configs/paper.example.yaml` y `configs/regime-bh.yaml` usan `regime_bh` con BTC/USDT:

- Opera con velas de 4h, pero el régimen se construye con el último cierre diario UTC disponible.
- Habilita compra si el cierre diario supera la SMA de 200 días y el retorno de 30 días es positivo.
- Entra cuando el régimen está encendido y no hay posición; puede entrar a mitad de régimen o reentrar después de un stop.
- Destina aproximadamente el 50 % de la equity al abrir. No rebalancea continuamente al 50 %: el peso cambia con el precio.
- Mantiene hasta que el régimen se apague o se ejecute el stop de seguridad. No tiene toma de ganancias por objetivo ni trailing.
- El stop se especifica como 20 % de distancia desde la señal; `PositionManager` reancla esa distancia al fill. No equivale a un límite garantizado de pérdida de la cuenta.
- `max_positions=1` y un único par limitan la actividad por construcción. Bajar a 1h sin cambiar el régimen diario no generaría un sistema genuinamente más activo.

Fuentes locales: [estrategia](../../src/tradingbot/strategy/strategies/regime_bh.py), [config del paper](../../configs/paper.example.yaml), [especificación y resultados](regime-bh-v1.md).

La DB del VPS confirma una compra del paper el 2026-09-14 a las 20:00 UTC, todavía abierta al revisar el servidor el 2026-09-17. A la fecha de esta revisión eso es una observación demasiado corta para juzgar una estrategia que históricamente mantiene algunas posiciones durante meses. El detalle operativo figura en la sección 7.

Los límites diarios y de drawdown bloquean nuevas entradas; no liquidan automáticamente toda posición abierta. Reducirlos tampoco es una forma fiable de aumentar la actividad. Para diagnosticar inactividad operativa hay que distinguir régimen apagado, posición existente, breaker, kill switch, warmup y feed atrasado mediante estado y eventos.

## 2. Evidencia que ya tiene el proyecto

Comparación de curvas OOS registradas entre 2021-08-01 y 2025-08-01. Retornos acumulados, netos de los costos modelados. Los universos y tamaños difieren: sirve para diagnosticar las familias, no para atribuir toda diferencia exclusivamente a la señal.

| Corrida | Estrategia | Trades cerrados | Retorno | Sharpe | Caída máxima |
|---|---|---:|---:|---:|---:|
| WF-0001 | EMA cross, 8 pares, 4h | 163 | +23,4 % | 0,48 | 14,3 % |
| WF-0002 | EMA optimizada, 8 pares, 4h | 140 | +77,5 % | 1,03 | 15,5 % |
| WF-0003 | EMA state, 8 pares, 4h | 644 | +55,7 % | 0,64 | 30,4 % |
| WF-0004 | EMA state, 8 pares, 1h | 2.549 | −43,5 % | −0,39 | 62,7 % |
| WF-0005 | EMA state + filtro, 8 pares, 4h | 435 | +81,8 % | 0,90 | 20,3 % |
| WF-0008 | Régimen BTC, fracción 0,5, 4h | 34 | +90,6 % | 1,04 | 15,3 % |

Fuente: [registro](../../experiments/REGISTRY.md) y `metrics.json` de cada corrida. Los 34 trades equivalen a unos 8,5 por año en ese walk-forward, no a una frecuencia futura garantizada. El walk-forward concatena ventanas; no debe confundirse con una cuenta continua sin reinicios de ventana.

Los informes ya descartaron las variantes EMA evaluadas: el optimizado dependía de dos trades que sumaban el 102 % del PnL; la variante filtrada no superaba al benchmark BTC filtrado; 1h elevó mucho los costos. No propongo reabrir esa búsqueda cambiando solamente períodos o umbrales.

**La estrategia vigente todavía tiene validación pendiente.** En EXP-0010, holdout 2025-09-01 a 2026-09-08, la equity ganó 3,11 %, el DD fue 6,39 % y el PF de trades cerrados fue 0,033. Hay cuatro operaciones cerradas y una posición abierta al corte. Recalculando desde el archivo de trades, el PnL cerrado suma −343,67 USDT; la ganancia de equity depende de la posición abierta. Los trades no reconcilian por sí solos toda la equity: también intervienen valoración abierta, fees y dust.

El veredicto documentado es `iterar`, con una regla acordada para reevaluar al cerrar la posición. No corresponde presentar el Gate 1 completo como aprobado ni modificar retrospectivamente su umbral. Para nuevas familias, definir de antemano el tratamiento de posiciones abiertas al corte; extender la observación no crea un holdout independiente nuevo.

## 3. Alternativas priorizadas

Las reglas numéricas de esta sección son propuestas iniciales de investigación. No fueron elegidas por resultados y no son reglas validadas por los papers citados. La frecuencia esperada es cualitativa y debe medirse.

| Prioridad | Familia | Qué intenta capturar | Actividad posible | Encaje actual |
|---|---|---|---|---|
| 1 | Retroceso dentro de tendencia | Rebote de una caída corta en un mercado favorable | Más entradas y posiciones más cortas que `regime_bh`, por confirmar | Alto |
| 2 | Ruptura de rango / Donchian | Continuación después de superar máximos recientes | Intermedia; puede pasar semanas sin operar | Alto |
| 3 | Rotación por fuerza relativa | Persistencia de liderazgo entre monedas | Evaluación semanal; no exige operar cada semana | Medio; necesita lógica de cartera |
| 4 | Reversión a la media en rango | Vuelta al centro tras una desviación extrema | Potencialmente mayor; muy sensible a costos | Alto en indicadores, incierto en ventaja neta |

### 3.1 Retroceso en tendencia: primera prueba

Idea: conservar un contexto favorable de mercado, pero comprar después de una corrección corta y salir en el rebote. Cambia la lógica de entrada y de tenencia respecto de comprar un cruce o mantener durante todo el régimen.

Prototipo propuesto `pullback_rsi`, sobre 4h:

- Contexto: filtro diario BTC habilitado y cierre del activo por encima de su EMA200 de 4h. Son horizontes diferentes; no confundir esta EMA con la SMA diaria de `regime_bh`.
- Entrada: RSI(2) de la vela anterior ≤ 10 y RSI(2) actual > 10, sin posición. La señal representa recuperación después de sobreventa.
- Salida: RSI(2) ≥ 70 o 12 velas de 4h desde la entrada, lo que ocurra primero; salida al open siguiente.
- Stop inicial: distancia de 2,5 ATR(14), sin promediar a la baja y sin trailing en esta primera versión.
- Riesgo experimental inicial: 0,25 % de equity por stop, máximo 25 % de notional por posición, dos posiciones y 50 % de exposición agregada. Son límites de simulación propuestos, no garantía de DD ni recomendación de capital real.

Por qué probarla: usa indicadores y contratos existentes y permite investigar una causa concreta del fracaso anterior, entrar tarde con stops dentro del ruido. Su ventaja sigue siendo una hipótesis: esperar un rebote puede también empeorar el precio y producir muchas salidas pequeñas.

De Nicola encontró reversión de retornos de BTC en horizontes de 1, 2 y 4 horas. Esto motiva explorar el fenómeno, pero no valida RSI(2), este filtro, ni beneficios actuales después de comisiones en Binance. [On the Intraday Behavior of Bitcoin, 2021](https://doi.org/10.5195/ledger.2021.213).

Riesgo principal: una corrección puede convertirse en caída sostenida. Este prototipo comparte exposición alcista con `regime_bh`; no presumir diversificación por tener otro nombre.

### 3.2 Ruptura de rango: segunda prueba

Prototipo propuesto `donchian`, sobre 4h:

- Mismo filtro diario BTC para el experimento inicial.
- Entrada: cierre actual por encima del máximo de las 60 velas **anteriores**, excluyendo la vela actual. Son 10 días con datos completos de 4h.
- Salida por señal: cierre por debajo del mínimo de las 20 velas anteriores.
- Stop inicial y trailing: 3 ATR(14), reutilizando el máximo cierre desde entrada para el trailing.
- Mismo presupuesto experimental de riesgo que el retroceso; ranking determinístico por exceso sobre el canal expresado en ATR.
- Toda señal se ejecuta en la apertura siguiente. No asumir que se compró al nivel de ruptura dentro de la vela.

Puede capturar movimientos que no coinciden con un cruce de medias. Falla especialmente con rupturas falsas y tiene riesgo de comprar caro tras una expansión brusca. Sigue perteneciendo a seguimiento de tendencia; la correlación con el bot actual puede ser alta.

La evidencia publicada es mixta: Hudson y Urquhart comparan varias familias técnicas, incluidas rupturas, pero reportan que sus reglas seleccionadas para BTC no produjeron retorno positivo en su período fuera de muestra. Justifica probar reglas simples con rigor, no asumir que Donchian gana. [Technical trading and cryptocurrencies](https://d-nb.info/1202710646/34).

Dejar volumen, compresión de volatilidad y confirmaciones adicionales para hipótesis posteriores. Agregarlas todas desde el principio amplía la búsqueda y dificulta saber qué aporta cada condición.

### 3.3 Rotación por momentum: tercera línea, mayor trabajo

Idea: dentro del universo permitido, mantener los activos con mayor retorno reciente, con una alternativa explícita de quedarse en cash.

Prototipo conceptual: evaluar una vez por semana; ordenar los ocho pares existentes por retorno de 14 días; seleccionar hasta dos con retorno positivo y contexto diario favorable. Definir antes de implementar la regla de salida del ranking, pesos, calendario UTC y tratamiento de órdenes pendientes. El horizonte de 14 días se inspira en la literatura; no se ha probado en este repositorio.

Liu, Tsyvinski y Wu documentan un factor de momentum entre criptomonedas. La revisión de Borri y coautores, versión de marzo de 2026, encuentra persistencia en la muestra posterior a 2020. Ambas estudian carteras y universos distintos; los resultados long-short no se trasladan automáticamente a un bot spot long-only de ocho pares después de costos. [Common Risk Factors in Cryptocurrency](https://www.nber.org/papers/w25882), [Coming of Age, sección 3.2](https://arxiv.org/html/2510.14435v4#S3.SS2).

El motor actual ordena **nuevas señales** por `strength`, pero no reemplaza automáticamente una posición porque otra moneda ahora sea mejor. `StrategyContext` solo expone la serie de un par. La rotación real necesita una decisión conjunta de cartera y reglas de rebalanceo; no alcanza con agregar pares al YAML.

Riesgos: liderazgo que se revierte, exposición común a altcoins y sesgo de supervivencia. Los ocho activos actuales sirven para una comparación controlada interna, pero no representan un universo histórico libre de sesgo. No elegir ni eliminar monedas según su PnL previo; habilitar cada una solo cuando existía, tenía datos y cumplía los criterios disponibles entonces.

### 3.4 Reversión en rango: experimento separado

Idea: entrar cuando el precio vuelve dentro de la banda inferior de Bollinger y salir al recuperar la media, únicamente en un contexto lateral definido antes del test.

Prototipo conceptual de 4h: Bollinger(20, 2), ADX(14) < 20, regreso del cierre al interior de la banda; salida al cierre que alcance la media, al vencer un plazo máximo o por stop. La salida a la media se ejecutaría en el open siguiente: el motor no tiene un take-profit límite intravela equivalente.

El riesgo es que un rango termine en tendencia bajista y encadene pérdidas. ADX mide intensidad, no dirección, y reacciona con demora. Necesita una política explícita de exclusión de caídas fuertes. La evidencia de reversión de BTC citada arriba no demuestra que esta regla Bollinger sea rentable.

No mezclar inicialmente esta lógica con el retroceso en tendencia: son hipótesis relacionadas, pero habilitan contextos diferentes. No asumir independencia entre ambas.

## 4. Opciones que postergaría

- **Scalping y market making:** el motor actual usa velas y fills de mercado; no modela cola de órdenes límite, selección adversa ni profundidad. Cambiar a minutos y asumir fills maker baratos daría una evaluación incompleta.
- **Grid y martingala:** una grilla spot acumula inventario al caer; subir tamaños tras perder puede amplificar la exposición. Necesitaría límites de inventario, salida de régimen y simulación de límites que hoy no existen. Muchas ventas ganadoras no bastan si queda inventario con pérdidas.
- **Arbitraje entre exchanges, pares long-short o funding:** requieren otros venues o derivados, nuevas fuentes de datos y contabilidad. Quedan fuera de [ADR-0004](../decisions/ADR-0004-alcance-v1.md). La revisión de 2026 también muestra que las fricciones limitan la implementación del arbitraje aparente. [Coming of Age, sección 3.5](https://arxiv.org/html/2510.14435v4#S3.SS5).
- **LLM decidiendo órdenes / aprendizaje por refuerzo:** no hay evidencia específica del repo que justifique esa complejidad. El alcance vigente pone al LLM fuera del loop. Primero obtener una comparación sólida con reglas simples.

## 5. Costos y restricciones de implementación

La configuración supone fee 0,10 % y slippage 5 bps = 0,05 % **por lado**. Una compra y venta cuestan aproximadamente 0,30 % del notional, antes de efectos de redondeo, gaps y variaciones de precio. En 1.000 USDT operados son unos 3 USDT por vuelta completa. Ese costo puede absorber gran parte de un rebote pequeño.

Es una hipótesis del simulador, no una verificación de las tarifas personales. Binance permite consultar comisiones de cuenta y símbolo mediante `GET /api/v3/account/commission`; descuentos y comisiones especiales deben verificarse cuando corresponda. [Documentación de comisiones](https://developers.binance.com/en/docs/products/spot/faqs/commission_faq).

Encaje técnico verificado:

- Ya existen RSI, ATR, ADX, Bollinger y máximos/mínimos móviles en `indicators/core.py`.
- `Strategy` / `StrategyContext`, los fills en t+1 y las salidas por señal permiten prototipos de retroceso y ruptura con pocos cambios de infraestructura.
- El stop temporal puede calcularse desde `Position.entry_time`, fijando con precisión si se cuentan horas o velas disponibles.
- Cada `Engine` recibe una estrategia. `PositionManager` identifica posiciones por `Pair`, y `RiskManager` rechaza una segunda entrada sobre el mismo par.
- No hay cartera multi-estrategia compartida lista para usar. Correr dos bots independientes sobre la misma cuenta sin coordinación duplicaría decisiones y presupuestos de riesgo.
- El broker real y testnet figuran pendientes en el roadmap. Las propuestas son para investigación y paper, no para desplegar trading real ahora.

Combinar señales solo después de medir por separado y con un presupuesto común. El 50 % que queda inicialmente en cash en `regime_bh` es parte de su reducción de riesgo; utilizarlo para otra estrategia cambia ese presupuesto. Comparar correlación de retornos, pérdidas simultáneas y contribución al DD, no sumar rentabilidades de backtests con cuentas completas independientes.

## 6. Plan de experimentos

El usuario pidió comparar **ambas opciones**: mejorar rendimiento con riesgo parecido y una alternativa más activa que acepte mayor riesgo. La comparación propuesta tiene dos escenarios, ambos de simulación:

| Aspecto | A: rendimiento con riesgo parecido | B: mayor actividad y riesgo permitido |
|---|---|---|
| Objetivo | Mejor expectativa neta sin deteriorar materialmente el DD y la volatilidad de la referencia | Medir si más señales ejecutadas compensan costos y caídas adicionales |
| Señales iniciales | Retroceso y ruptura, por separado, en 4h | Las mismas señales y períodos para separar el efecto del riesgo |
| Riesgo inicial por stop | 0,25 % de equity | 0,50 % de equity |
| Límite por posición | 25 % de equity | 25 % de equity |
| Posiciones simultáneas | Hasta 2 | Hasta 3 |
| Exposición máxima de entrada | 50 % | 75 % |
| Qué comparar | Retorno, DD, volatilidad, tiempo de recuperación y diferencia frente al benchmark | Lo anterior más beneficio marginal por exposición, costo y operación adicional |

Estos límites no predicen el DD: hay gaps, cambios de peso y correlación entre pares. No se puede declarar el escenario A de riesgo equivalente sin medir sus resultados. Tampoco aumentar el tamaño genera más señales; el tercer slot del B solo puede ejecutar oportunidades antes rechazadas. Si no existe ventaja neta con las señales base, aumentar el riesgo no la crea. Una versión en 1h sería un experimento posterior separado, no una consecuencia automática de elegir B. Los gates vigentes siguen aplicando a ambos; cualquier cambio de criterios exige una decisión previa a los resultados, no una relajación para salvar una corrida.

1. **Referencia congelada:** conservar la configuración y el historial del paper vigente. Usar `regime_bh` con fracción 0,5 como referencia de investigación, además de BTC buy & hold y BTC filtrado.
2. **Dos especificaciones pequeñas:** definir `pullback_rsi` y `donchian`, una configuración inicial por familia y criterios de descarte antes de ver resultados. Este informe no modifica los gates existentes ni aprueba una estrategia.
3. **Muestra diagnóstica:** BTC y ETH para verificar comportamiento. Luego el universo predefinido de ocho pares para evaluación, sin seleccionar ganadores; los criterios generales del proyecto requieren al menos cuatro pares para estas familias.
4. **Verificación del código:** tests de entrada/salida y stop, equivalencia de ventana y ausencia de lookahead, incluidos canal desplazado y uso de días UTC cerrados. Ejecutar por la CLI para registrar todos los experimentos.
5. **Comparación histórica:** walk-forward 24 meses IS / 6 meses OOS y backtest continuo sobre el mismo tramo. Comparar costos, exposición y riesgo, además de Sharpe, PF y DD; usar también una referencia de exposición/volatilidad comparable con reglas fijadas en IS, no escalada mirando el resultado OOS.
6. **Ablación limitada:** comparar cada candidata con y sin filtro diario, como diagnóstico predefinido de dónde proviene el resultado. No promover retrospectivamente la variante ganadora como si hubiera sido la única hipótesis.
7. **Costos adversos:** repetir la configuración congelada con slippage de 10 y 20 bps por lado, manteniendo fees explícitas. Medir a qué costo desaparece la expectativa neta; no rescatar una familia suponiendo descuentos no verificados.
8. **Robustez y concentración:** sensibilidad cercana de parámetros, resultados por año/par, PnL sin las operaciones de mayor aporte y bootstrap por bloques de retornos. Reportar también señales rechazadas por slots, exposición, filtro y protecciones.
9. **Validación nueva:** el período desde 2025-09-01 ya fue observado para `regime_bh`. No reutilizarlo repetidamente como holdout limpio. Registrar toda selección de familias y reservar una evaluación prospectiva con parámetros congelados. Para comparar candidatas, fijar ventanas y tratamiento de posiciones abiertas antes de observar el resultado.
10. **Paper candidato aislado:** solo al cumplir los criterios definidos; identificarlo como experimento nuevo, con DB, logs, archivos STOP/RESUME, notificaciones y capital simulado propios. No reutilizar el estado del paper vigente ni sumar presupuestos como si fueran una sola cuenta validada.

La frecuencia se reportará con entradas y cierres por mes, duración de posiciones y meses sin operar. También se medirá expectativa neta por trade y por día expuesto. Doscientas operaciones pequeñas y correlacionadas pueden aportar menos evidencia que lo que su conteo sugiere.

El riesgo de probar muchas variantes y elegir la más bonita está documentado por Bailey y coautores. El registro completo de intentos y una validación futura son relevantes incluso si cada variante individual tiene walk-forward. [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

## 7. Alcance de esta revisión y entorno

- Se revisaron código, configs versionadas, decisiones, gates y reportes; se recalcularon conteos y PF de corridas seleccionadas con Python estándar. No se ejecutaron backtests nuevos ni la suite del proyecto.
- La Mac no tiene `data/`, `db/` ni `configs/paper.yaml` en este checkout; `uv` no está disponible en el PATH inspeccionado. La investigación no necesitó levantar servicios ni instalar dependencias.
- El acceso inicial por SSH falló; luego el usuario instaló la clave pública de su Mac en `/root/.ssh/authorized_keys` mediante la consola de Hetzner. Se verificó acceso no interactivo con clave y comprobación estricta del host. La inspección posterior del bot fue de solo lectura; no se reinició el contenedor ni se modificaron su configuración, DB o posiciones.
- En la Mac, el comando verificado es `ssh -4 -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@204.168.166.166`. El ejecutable de Windows y el prefijo `&` no corresponden a zsh.
- Los cambios de esta revisión son documentación. No se alteraron estrategias, riesgo, configuraciones operativas ni historial de experimentos.

### 7.1 Estado del paper verificado en el VPS

Lectura del 2026-09-17 alrededor de las 13:00 UTC; última foto del bot publicada a las 12:01 UTC. Los precios y la equity siguientes corresponden a esa foto, no a una cotización en tiempo real de la revisión.

- Un contenedor, `tradingbot-paper-1`, en estado `healthy`, con aproximadamente 12 horas desde el último arranque. La DB conserva la historia anterior: 1 orden, 1 fill, 1 posición, 0 trades cerrados y 17 snapshots. El contador de sesión del proceso no es el historial completo.
- Configuración: `regime_bh`, BTC/USDT, 4h, fracción de entrada 0,5, máximo una posición, capital inicial simulado 10.000 USDT; coincide con la referencia analizada.
- Compra abierta: 0,06320673 BTC a 79.021,51 USDT, el 2026-09-14 a las 20:00 UTC. Stop publicado: 63.225,11 USDT. Marca de valoración: 76.482 USDT.
- Cash: 5.000,31 USDT. Equity: 9.834,49 USDT; variación de −165,51 USDT (−1,66 %) respecto del capital inicial. Todavía no hay operaciones cerradas con las que evaluar el PF del paper.
- Última vela procesada: apertura 08:00 UTC del 17/09, cerrada a las 12:00 UTC. Próximo cierre indicado: 16:00 UTC. En la foto no hay órdenes pendientes, kill switch ni bloqueos diarios o por drawdown activos; la señal de la sesión es mantener. No se observa un bloqueo operativo que explique la baja actividad.
- Telegram aparece conectado; registra 3 errores de polling acumulados en la sesión. Esa cifra aislada no prueba una interrupción actual y no se investigó su causa en esta revisión.
- En una muestra puntual, el contenedor consumía 363,5 MiB sobre 3,73 GiB de RAM del host y 0,02 % de CPU. Hay margen aparente para probar unas pocas instancias ligeras; medir consumo y llamadas a Binance al agregarlas. Esto no garantiza capacidad para backtests u optimizaciones simultáneas.

### 7.2 Varios bots paper al mismo tiempo

Sí: cada bot puede tener su propio saldo ficticio y recibir precios del mismo mercado. Para una comparación inicial, conservar el bot actual como control y agregar, después de la validación histórica, un paper de retroceso y otro de ruptura. Comenzar los candidatos en la misma fecha, con igual capital y supuestos de costos; comparar desde esa fecha también la curva normalizada del control y documentar que su posición venía abierta. Si se necesita igualdad exacta de condiciones iniciales, usar además una referencia nueva independiente.

El `compose.yaml` actual comparte el volumen `tradingbot-db` y los directorios de logs entre servicios derivados. Por eso no basta con escalar el servicio `paper`: varias instancias escribirían la misma DB y el mismo `status.json`, y compartirían las órdenes STOP/RESUME.

Cada instancia necesita un nombre y YAML propios, volumen de DB independiente, directorio de logs separado, archivos STOP/RESUME separados y un healthcheck que lea su estado. Si se usa Telegram, cada proceso debe tener su propio bot/token, o debe existir un único listener que enrute comandos por identificador; varios listeners con el mismo token pueden competir por las actualizaciones. Los secretos siguen fuera de los YAML y del repositorio.

Los 10.000 USDT ficticios de cada instancia representan experimentos independientes. Sumar sus saldos o retornos no demuestra qué habría pasado con una sola cuenta: una cartera combinada exige asignar el capital total entre estrategias y medir sus pérdidas simultáneas. No se implementó ni desplegó esta separación durante la revisión.
