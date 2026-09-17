# Observador de propuestas Donchian v1

Fecha2026-09-17. Estado: observacional, ejecución deshabilitada.

Se evalúan todas las rupturas Donchian4h del universo fijo, antes de posición,
cash o filtros de cartera. Snapshot limitado a features market-v1, precio/stop
propuesto, símbolo y cierre exclusivo. No consulta noticias ni archivos. No se
incluye estado de una cartera: después de un veto las carteras divergen.

Política entry-review-v1: BUY significa aceptar la propuesta y HOLD vetarla;
no autoriza una compra, no decide cantidad ni puede cambiar stops. No se envían
salidas a este evaluador de entradas. Confianza numérica declarada por el modelo,
sin interpretación estadística. Prompt/proveedor/modelo/tarifas y política quedan
congelados por instancia. Una DB de observación nunca se mezcla con otra política.

Persistir propuesta antes de pedir respuesta, reserva conservadora de costo antes
de la API, respuesta y uso después. Repeticiones normales usan ID/hash estable.
Si un proceso muere durante una llamada, no repetirla: estado desconocido, reserva
conservada, HOLD. Expirar a cierre+45s incluyendo cola. Sin credenciales/modelo/
tarifas autorizadas solo se recolectan propuestas; no hay llamadas pagas automáticas.

Proveedor inicial intercambiable: puerto asíncrono; adaptador Anthropic aprovecha
SDK existente. Modelo y tarifas explícitos: no alias por defecto que pueda cambiar.
No se atribuye rentabilidad a ningún proveedor. Límites USD1/día y20/mes UTC,
reserva por bytes del input+sobrecarga y máximo de output; registrar uso real.
Timeout/JSON inválido/ID equivocado/429/vencimiento: HOLD. SDK sin retries ocultos;
429 con Retry-After se respeta solo si cabe antes del deadline absoluto.

La CLI replay analiza exclusivamente decisiones guardadas, no vuelve a consultar.
No es un backtest financiero y no pasa gates por contar recomendaciones BUY.
Antes de ejecutar LLM se requiere replay financiero con 1m, base aprobada con igual
espera,12semanas/40cierres por cartera y gate prospectivo ADR-0014. La política
compartida exige señal+60s, decisión<=señal+45s, vencimiento señal+120s y nunca
cotización anterior ni low intrabar anterior a la compra. Ver runbook de investigación.
