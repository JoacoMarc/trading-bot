# ADR-0014 — Investigación, indicadores recursivos y decisiones disponibles

Fecha: 2026-09-17. Implementación autorizada mediante el plan de siguiente etapa.

Los indicadores recursivos guardan checkpoint en SeriesProvider, fuera de Strategy.
Se persiste con el estado del motor en la misma transacción; formato y parámetros
deben coincidir al recuperar. Una ventana nueva sin checkpoint no equivale a una
serie completa: la validación compara procesamiento incremental con igual semilla.

ML admite float para variables/pesos en la frontera de investigación/predicción;
dinero y sizing conservan Decimal. Receta fija mensual con 24 meses de historia:
21 ajuste, 3 calibración; purgar etiquetas que alcanzan la frontera siguiente.
Disponibilidad histórica: corte mensual +1h; disponibilidad paper: finalización real.
Los períodos sin modelo válido son cobertura faltante, no evidencia de estar en cash.

Oportunidades para LLM v1 independientes de cartera: todas las señales brutas de
compra sin incluir cash/posición de otra instancia. Riesgo constante es contexto;
cada cartera valida sus posiciones/cash al consumir. SELL es solo observacional.
signal_ts = Candle.close_time + 1 (cierre exclusivo). Ningún fill puede preceder a
la decisión; ejecución diferida debe recorrer minutos en orden y activar stops
solo después del fill. Prohibido usar el mínimo completo de 4h anterior a comprar.

Criterio incremental primario congelado: delta Sharpe≥0.10, DD no más de 2 puntos
porcentuales peor, IC bilateral95% de delta Sharpe con límite inferior>0. Bootstrap
emparejado de retornos diarios, bloques móviles30d,5000 muestras,semilla42. La mejora
de DD queda secundaria. No elegir retrospectivamente entre ambas métricas.

Gate experimental LLM separado de Gate1: base A con Gate1 completo y misma ejecución,
12 semanas/40 cierres por cartera en replay de decisiones prospectivas congeladas,
PF≥1.3,DD≤25%,retorno positivo tras API y criterio incremental anterior. Falta de
muestra/cobertura significa incompleto. Nunca habilita live ni declara satisfecho
el Gate1 histórico de un LLM preentrenado. Infraestructura observacional puede
entregarse y funcionar aunque ningún modelo apruebe el paso a paper.
