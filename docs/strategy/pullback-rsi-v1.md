# Retrocesos en tendencia — v1

Estado: hipótesis congelada antes de implementar; evaluada y descartada para paper el 2026-09-17.

Spot long-only, 4h, universo BTC/ETH/BNB/XRP/ADA/LTC/LINK/SOL contra USDT.
Entrar sin posición cuando cierre > EMA200 y RSI(2) anterior <= 10 < RSI(2) actual.
Ordenar entradas por `100 - RSI anterior`, empates por símbolo. Stop inicial: cierre
menos 2,5 ATR(14), reanclado al fill por el motor. Sin trailing. Salir si RSI >= 70 o
si el cierre actual completa 48 horas desde la apertura de la vela del fill de entrada.
El tiempo sale de Position.entry_time, incluso tras reiniciar. Señal en t, fill t+1.
ATR indefinido/no positivo impide entradas; nunca impide una salida temporal.

Filtro de cartera: BTC diario sobre SMA200 y momentum30 positivo, solo días UTC cerrados;
sin datos suficientes se bloquean entradas. El filtro no fuerza salidas. Warmup mínimo:
1212 velas (202 días), ampliado si los períodos de indicadores lo necesitan.

Perfiles A/B: riesgo por stop 0,0025/0,005, máximo 2/3 posiciones y exposición 0,5/0,75;
tope por posición 0,25, capital 10000, fee 0,001 y slippage 5 bps por lado.
Límite diario 0,03, DD 0,20, pausa 30 días. Parámetros de señal idénticos en ambos.

Validación: backtest y WF fijo 24m/6m antes de 2025-09-01, Gate 1 íntegro, Monte Carlo,
meseta ±20% sobre umbrales de entrada/salida RSI y multiplicador ATR (pasos 1/1/0,1).
RSI período, EMA, ATR período y duración quedan fijos. Costos adversos: 10 y 20 bps.
Solo A puede pasar a paper; holdout una vez por familia si pasa pre-holdout. No ajustar
parámetros para salvar resultados. Holdout ya observado para otras familias: documentarlo.

## Resultado

WF-0010 (A): retorno OOS −9,42 %, Sharpe −1,44, PF 0,63; WF-0011 (B):
−24,83 %, Sharpe −1,56, PF 0,60. Meseta 0/14 en ambos. Los mayores costos empeoran
los resultados. **No-go**, sin holdout ni paper; reglas originales preservadas.
Ver [comparación completa](../../experiments/candidates-2026-09-17/REPORT.md).
