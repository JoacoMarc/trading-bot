# Rupturas de rango — v1

Estado: hipótesis congelada antes de implementar; evaluada el 2026-09-17, no aprobada para paper.

Spot long-only, 4h, mismo universo, filtro diario, costos, perfiles A/B y validación
que pullback-rsi-v1. Warmup mínimo 1212 velas para el filtro de cartera.

Entrar sin posición cuando el cierre supera el máximo de las 60 velas anteriores;
el canal excluye siempre la vela actual. Fuerza = (cierre - canal superior) / ATR(14),
empates por símbolo. Salir cuando cierre < mínimo de las 20 velas anteriores.
Stop inicial = cierre - 3 ATR(14), reanclado al fill. Trailing = máximo cierre desde
entrada - 3 ATR(14); solo sube. ATR no positivo impide entradas o actualizar trailing,
pero no impide salidas. Señal t, ejecución t+1: no simular fill al nivel del canal.

Meseta ±20%: períodos de entrada/salida y multiplicador ATR, pasos 1/1/0,1.
Exigir período de salida < período de entrada. No optimizar después de ver resultados.
Pruebas específicas: excluir la vela actual, igualdad no rompe el canal, trailing
monótono, equivalencia de ventana y ausencia de lookahead.

## Resultado

WF-0012 (A): retorno OOS +6,81 %, Sharpe 0,61 < 0,80 requerido, DD 5,11 %.
**No-go** para A. WF-0013 (B): +36,29 %, Sharpe 1,01, DD 8,92 %; pasa pre-holdout,
pero el perfil B permanece limitado a investigación. Meseta 14/14 en ambos.
No se abrió holdout ni se activaron candidatas; no se reemplaza A por B después de mirar
resultados. Ver [comparación y costos adversos](../../experiments/candidates-2026-09-17/REPORT.md).
