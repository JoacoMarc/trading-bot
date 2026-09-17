# ml_filter v1 — Donchian filtrado por probabilidad a 24h

Estado: en evaluación, sin autorización de paper. Fecha: 2026-09-17.

Hipótesis: las variables disponibles al cierre permiten distinguir oportunidades
Donchian de mayor calidad. Ocho pares USDT, 4h, perfiles A/B existentes, mismos
stops/salidas/sizing. Solo se filtran ENTER_LONG; el ranking Donchian se conserva.

Features v1: retornos1/3/6/18,RSI14,ATR14/precio,ADX14,distancia EMA200 y canal60
en ATR,volumen/media20,retorno BTC6,retorno BTC diario30 y distancia SMA200 diaria,
identificador del par con ocho columnas fijas. Features comunes en batch y streaming.
EMA200 se siembra con SMA200 en una ventana fija de1213 barras (misma ventana en entrenamiento y paper). Solo días UTC completos; la hora de disponibilidad es cierre exclusivo.

Etiqueta: retorno de compra open(t+1) y venta open(t+7), neto de dos fees0.1% y
slippage5bps por lado; y=1 si >0. Rechazar etiquetas que atraviesen huecos. No es
probabilidad de ganancia de una posición Donchian ni se usa para cambiar tamaño.

Receta fija mensual (no optimización): en corte T, 21 meses de fit dentro de los
24 anteriores; últimos3 para calibrar sigmoide. Purga por label_end<T−3m/T,
simultánea en todos los pares. Historia inicial debe cubrir24 meses de calendario;
mínimo1000 filas fit/200 calibración y ambas clases. Ausencias son cobertura faltante.
Scaler fit solo en ajuste. Logística C=1,max_iter=1000; LightGBM100 árboles,
num_leaves15,max_depth5,learning_rate0.05,min_child_samples100,reg_lambda1,n_jobs2,
seed42, deterministic=true. Sin búsqueda de hiperparámetros.

Modelo disponible T+1h en simulación, vence próximo T+1h. En paper se exige además
la hora efectiva de publicación. Compras aceptadas con p>=0.55; falta de modelo,
datos o respuesta bloquea solo compras. Igual política y features en replay/paper.
Predicciones incluyen temporalidad y hash del artefacto. No usar el modelo final
para inferir sobre fechas anteriores. Meseta: canales Donchian60/20,ATR3 y umbral. 

Alcista: selección de rupturas; bajista: filtro diario; lateral: falsos positivos.
Riesgos: objetivo24h distinto de duración de trade, muestras solapadas, cambio de
régimen, pocos positivos, activos nuevos, costos y menor frecuencia por filtrado.
Regímenes sin cobertura de entrenamiento quedan n/a en gates, nunca aprobados.

Criterio primario incremental en ADR-0014. Resultados: pendientes.
