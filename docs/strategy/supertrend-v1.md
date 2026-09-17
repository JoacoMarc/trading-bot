# Supertrend v1

- Estado: en evaluación; ninguna autorización de paper/live.
- Fecha: 2026-09-17. Experimentos: pendientes.

## Hipótesis y universo

Capturar cambios de tendencia con una banda ajustada a volatilidad. Comparar 4h y 1h
en los ocho pares USDT existentes, perfiles A/B y costos 5/10/20 bps. No optimizar.
Variante propia simplificada, no copia de los parámetros publicados en Freqtrade.

## Indicador y reglas exactas

ATR Wilder(n=10): TR inicial indefinido, semilla media de los primeros n TR y después
recurrencia de Wilder. BU/BL = (high+low)/2 ± multiplier(3)*ATR.
Primera banda válida: U=BU, L=BL, dirección=-1. No genera entrada.
U actual=BU si BU<U anterior o close anterior>U anterior; si no, conserva U.
L actual=BL si BL>L anterior o close anterior<L anterior; si no, conserva L.
Dirección -1 cambia a +1 solo con close>U actual; +1 cambia a -1 solo con close<L actual.
Igualdad conserva dirección. Línea=L en +1, U en -1.

Compra únicamente en transición -1→+1, volumen>0, ATR14>0 y stop positivo.
Venta con dirección=-1 y posición, independientemente de ATR y filtro.
Stop inicial=close−3*ATR14; trailing=mayor cierre desde entrada−3*ATR14, nunca baja.
Ranking=(close−línea)/ATR14, empate por símbolo. Señal t, fill open t+1.
Filtro diario BTC: SMA200 y retorno30 positivos, sin datos bloquea compras.

| Parámetro | Default | Sensibilidad | Paso |
|---|---:|---:|---:|
| atr_period | 10 | 8–12 | 1 |
| multiplier | 3 | 2.4–3.6 | 0.1 |
| stop_atr_mult | 3 | 2.4–3.6 | 0.1 |
| bars_per_day | 6 (4h) / 24 (1h) | fijo por intervalo | — |

Warmup mínimo max(202*bars_per_day,6*max(2*atr_period,28)). El estado recursivo se
conserva fuera de Strategy: la ventana de velas puede truncarse pero no se vuelve a
sembrar la dirección. Checkpoint transaccional para reinicios; misma semilla inicial
y prefijo de historia en replay y streaming. La equivalencia usa checkpoint cuando
la ventana necesita un estado anterior, no tolerancias más laxas. Duplicar una vela
recalcula desde el estado previo y no aplica Wilder dos veces.

## Comportamiento esperado y riesgos

Alcista: capturar continuidad tras cambio; bajista: filtro suele bloquear; lateral:
falsos cambios y costos. Riesgos: gaps, correlación cripto, sensibilidad al timeframe
y semilla inicial. La misma cantidad de barras en 1h y 4h cambia el horizonte físico.

## Resultado

Pendiente de pruebas y validación completa; ningún parámetro se ajusta tras resultados.
