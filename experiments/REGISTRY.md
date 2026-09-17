# Registro de experimentos

Índice de todas las corridas registradas. **No se edita a mano**: lo regenera `tradingbot experiments sync` a partir de `runs/*/metrics.json` y de la sección "Notas y veredicto" de cada `REPORT.md`. Prefijos: `EXP-` backtest · `WF-` walk-forward · `OPT-` optimización · `PAR-` paridad paper/backtest.

Holdout reservado: desde 2025-09-01 (ver `docs/GATES.md`). Ninguna corrida lo incluye salvo que la columna "Datos" diga `+holdout`.

| Id | Fecha | Estrategia | Params (hash) | Datos | Pares | TF | Retorno | Sharpe | Max DD | Trades | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-0001 | 2026-09-08 | buy_hold_bh_btc | e67aa67341 | 2019-08-01 → 2025-09-01 | BTC | 4h | +972.2 % | 0.93 | +77.0 % | 0 | go (línea base) |
| EXP-0002 | 2026-09-08 | buy_hold_equal_weight | a7ee9ad771 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +1439.9 % | 0.99 | +79.4 % | 0 | go (línea base) |
| EXP-0003 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | iterar |
| EXP-0004 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | go (control: reproducibilidad) |
| EXP-0005 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +69.9 % | 1.17 | +7.2 % | 79 | go (control: defaults sin costo) |
| EXP-0006 | 2026-09-08 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | BTC, ETH | 4h | +65.4 % | 1.14 | +7.7 % | 76 | no-go (niveles agresivos en BTC+ETH; la mecánica del ADR-0007 queda validada) |
| EXP-0007 | 2026-09-09 | ema_trend | b978b0fa53 | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +76.9 % | 0.75 | +15.5 % | 248 | no-go (defaults v1 `cross` en 8 pares: top 10 > 100 % del PnL) |
| EXP-0008 | 2026-09-14 | ema_trend | 3067ccea6a | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +225.4 % | 1.01 | +31.5 % | 681 | go (control: diagnóstico de v3 en muestra completa) |
| EXP-0009 | 2026-09-14 | regime_bh | 937532e2f5 | 2019-08-01 → 2025-09-01 | BTC | 4h | +401.6 % | 1.19 | +25.2 % | 57 | go (control) |
| EXP-0010 | 2026-09-14 | regime_bh | 937532e2f5 | 2025-09-01 → 2026-09-08 +holdout | BTC | 4h | +3.1 % | 0.41 | +6.4 % | 4 | iterar |
| EXP-0011 | 2026-09-14 | regime_bh | 937532e2f5 | 2019-08-01 → 2026-09-08 +holdout | BTC | 4h | +315.4 % | 1.10 | +21.4 % | 63 | go (control) |
| EXP-0012 | 2026-09-17 | pullback_rsi | bac0a7838b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -12.2 % | -1.24 | +13.2 % | 842 | no-go |
| EXP-0013 | 2026-09-17 | pullback_rsi | bac0a7838b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -15.1 % | -1.56 | +16.0 % | 842 | no-go |
| EXP-0014 | 2026-09-17 | pullback_rsi | bac0a7838b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -21.2 % | -2.25 | +21.8 % | 843 | no-go |
| EXP-0015 | 2026-09-17 | pullback_rsi | bac0a7838b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -30.7 % | -1.33 | +32.7 % | 1089 | no-go |
| EXP-0016 | 2026-09-17 | pullback_rsi | bac0a7838b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -35.3 % | -1.60 | +36.9 % | 1059 | no-go |
| EXP-0017 | 2026-09-17 | pullback_rsi | bac0a7838b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -47.2 % | -2.32 | +48.1 % | 1083 | no-go |
| EXP-0018 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +21.9 % | 1.05 | +5.2 % | 254 | no-go |
| EXP-0019 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +20.7 % | 1.00 | +5.4 % | 254 | no-go |
| EXP-0020 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +17.9 % | 0.87 | +6.0 % | 255 | no-go |
| EXP-0021 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +90.6 % | 1.28 | +8.9 % | 334 | iterar (investigación; no autorizado para paper) |
| EXP-0022 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +86.0 % | 1.23 | +9.2 % | 334 | iterar (investigación; no autorizado para paper) |
| EXP-0023 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +74.6 % | 1.11 | +10.4 % | 336 | iterar (investigación; no autorizado para paper) |
| EXP-0024 | 2026-09-17 | regime_bh | 937532e2f5 | 2019-08-01 → 2025-09-01 | BTC | 4h | +302.7 % | 1.17 | +21.4 % | 59 | go (control histórico; no habilita dinero real) |
| EXP-0025 | 2026-09-17 | supertrend | 68e7dfee94 | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +7.7 % | 0.51 | +2.7 % | 216 | no-go |
| EXP-0026 | 2026-09-17 | supertrend | 68e7dfee94 | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +16.1 % | 0.43 | +7.4 % | 285 | no-go |
| EXP-0027 | 2026-09-17 | supertrend | 9f823b9a22 | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | +15.2 % | 0.45 | +10.7 % | 855 | no-go |
| EXP-0028 | 2026-09-17 | supertrend | 9f823b9a22 | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | +9.7 % | 0.18 | +32.5 % | 1119 | no-go |
| EXP-0029 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.0 % | -0.01 | +1.5 % | 13 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| EXP-0030 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.7 % | -0.08 | +3.0 % | 15 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| EXP-0031 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +1.0 % | 0.20 | +1.0 % | 15 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| EXP-0032 | 2026-09-17 | donchian | c8d4a6af5b | 2019-08-01 → 2025-09-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +2.2 % | 0.17 | +3.0 % | 20 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0001 | 2026-09-09 | ema_trend | b978b0fa53 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +23.4 % | 0.48 | +14.3 % | 163 | no-go (Gate 1 no aprobado: Sharpe OOS 0.48) |
| WF-0002 | 2026-09-09 | ema_trend | b978b0fa53 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +77.5 % | 1.03 | +15.5 % | 140 | no-go (afinar parámetros refutada: 2 trades = 102 % del PnL) |
| WF-0003 | 2026-09-14 | ema_trend | 3067ccea6a | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +55.7 % | 0.64 | +30.4 % | 644 | no-go (`state` en 4h refutado: PF OOS 1.19 < 1.2, DD 30 %) |
| WF-0004 | 2026-09-14 | ema_trend | 3067ccea6a | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -43.5 % | -0.39 | +62.7 % | 2549 | no-go (1h refutada por costos; familia `ema_trend` cerrada) |
| WF-0005 | 2026-09-14 | ema_trend | 3067ccea6a | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +81.8 % | 0.90 | +20.3 % | 435 | no-go (v3 refutada: Sharpe OOS 0.90 ≤ 0.98 del B&H filtrado) |
| WF-0006 | 2026-09-14 | regime_bh | 937532e2f5 | 2021-08-01 → 2025-08-01 | BTC | 4h | +112.9 % | 1.04 | +17.8 % | 34 | go |
| WF-0007 | 2026-09-14 | regime_bh | 937532e2f5 | 2021-08-01 → 2025-08-01 | ETH | 4h | +84.7 % | 0.77 | +19.9 % | 33 | go (control) |
| WF-0008 | 2026-09-14 | regime_bh | 937532e2f5 | 2021-08-01 → 2025-08-01 | BTC | 4h | +90.6 % | 1.04 | +15.3 % | 34 | go (control) |
| WF-0009 | 2026-09-14 | regime_bh | 937532e2f5 | 2021-08-01 → 2025-08-01 | BTC | 4h | +148.6 % | 1.05 | +21.5 % | 34 | no-go |
| WF-0010 | 2026-09-17 | pullback_rsi | bac0a7838b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -9.4 % | -1.44 | +10.4 % | 529 | no-go |
| WF-0011 | 2026-09-17 | pullback_rsi | bac0a7838b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -24.8 % | -1.56 | +26.5 % | 694 | no-go |
| WF-0012 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +6.8 % | 0.61 | +5.1 % | 163 | no-go |
| WF-0013 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +36.3 % | 1.01 | +8.9 % | 213 | iterar (investigación; no autorizado para paper) |
| WF-0014 | 2026-09-17 | regime_bh | 937532e2f5 | 2021-08-01 → 2025-08-01 | BTC | 4h | +90.6 % | 1.04 | +15.3 % | 34 | go (control histórico; no habilita dinero real) |
| WF-0015 | 2026-09-17 | pullback_rsi | bac0a7838b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -11.6 % | -1.78 | +12.2 % | 529 | no-go |
| WF-0016 | 2026-09-17 | pullback_rsi | bac0a7838b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -16.1 % | -2.49 | +16.6 % | 532 | no-go |
| WF-0017 | 2026-09-17 | pullback_rsi | bac0a7838b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -29.4 % | -1.90 | +30.7 % | 694 | no-go |
| WF-0018 | 2026-09-17 | pullback_rsi | bac0a7838b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -38.5 % | -2.62 | +39.2 % | 696 | no-go |
| WF-0019 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +6.1 % | 0.55 | +5.4 % | 163 | no-go |
| WF-0020 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +4.8 % | 0.43 | +5.9 % | 163 | no-go |
| WF-0021 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +34.0 % | 0.95 | +9.2 % | 213 | iterar (investigación; no autorizado para paper) |
| WF-0022 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +28.9 % | 0.83 | +10.4 % | 214 | iterar (investigación; no autorizado para paper) |
| WF-0023 | 2026-09-17 | supertrend | 68e7dfee94 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +6.5 % | 0.67 | +2.7 % | 137 | no-go |
| WF-0024 | 2026-09-17 | supertrend | 68e7dfee94 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +5.9 % | 0.61 | +2.8 % | 137 | no-go |
| WF-0025 | 2026-09-17 | supertrend | 68e7dfee94 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +4.7 % | 0.48 | +3.0 % | 137 | no-go |
| WF-0026 | 2026-09-17 | supertrend | 68e7dfee94 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +5.7 % | 0.27 | +7.4 % | 187 | no-go |
| WF-0027 | 2026-09-17 | supertrend | 68e7dfee94 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +4.1 % | 0.20 | +7.8 % | 187 | no-go |
| WF-0028 | 2026-09-17 | supertrend | 68e7dfee94 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +0.9 % | 0.07 | +8.6 % | 187 | no-go |
| WF-0029 | 2026-09-17 | supertrend | 9f823b9a22 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -6.1 % | -0.33 | +10.8 % | 552 | no-go |
| WF-0030 | 2026-09-17 | supertrend | 9f823b9a22 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -10.7 % | -0.60 | +13.3 % | 555 | no-go |
| WF-0031 | 2026-09-17 | supertrend | 9f823b9a22 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -19.2 % | -1.12 | +21.3 % | 561 | no-go |
| WF-0032 | 2026-09-17 | supertrend | 9f823b9a22 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -26.4 % | -0.72 | +30.9 % | 746 | no-go |
| WF-0033 | 2026-09-17 | supertrend | 9f823b9a22 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -34.5 % | -1.00 | +37.7 % | 749 | no-go |
| WF-0034 | 2026-09-17 | supertrend | 9f823b9a22 | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 1h | -46.7 % | -1.46 | +49.3 % | 758 | no-go |
| WF-0035 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +0.3 % | 0.21 | +0.5 % | 3 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0036 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +0.3 % | 0.19 | +0.5 % | 3 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0037 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +0.2 % | 0.17 | +0.5 % | 3 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0038 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +0.1 % | 0.03 | +1.1 % | 4 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0039 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +0.0 % | 0.02 | +1.1 % | 4 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0040 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.0 % | -0.01 | +1.1 % | 4 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0041 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.0 % | -0.01 | +0.4 % | 3 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0042 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.0 % | -0.02 | +0.4 % | 3 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0043 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.0 % | -0.05 | +0.4 % | 3 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0044 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.7 % | -0.28 | +1.3 % | 5 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0045 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.7 % | -0.29 | +1.3 % | 5 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0046 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | -0.8 % | -0.33 | +1.3 % | 5 | no-go (ML v1 no promovible; Gate 1 incompleto) |
| WF-0047 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +6.8 % | 0.61 | +5.1 % | 163 | referencia (reproducción; no autoriza paper) |
| WF-0048 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +6.1 % | 0.55 | +5.4 % | 163 | referencia (reproducción; no autoriza paper) |
| WF-0049 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +4.8 % | 0.43 | +5.9 % | 163 | referencia (reproducción; no autoriza paper) |
| WF-0050 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +36.3 % | 1.01 | +8.9 % | 213 | referencia (reproducción; no autoriza paper) |
| WF-0051 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +34.0 % | 0.95 | +9.2 % | 213 | referencia (reproducción; no autoriza paper) |
| WF-0052 | 2026-09-17 | donchian | c8d4a6af5b | 2021-08-01 → 2025-08-01 | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | +28.9 % | 0.83 | +10.4 % | 214 | referencia (reproducción; no autoriza paper) |
| RES-0001 | 2026-09-17 | ml-dataset | 3f6f3ea5e3 | … → … | ADA, BNB, BTC, ETH, LINK, LTC, SOL, XRP | 4h | — | — | — | — | pendiente |
| RES-0002 | 2026-09-17 | ml-train-logistic | a996566241 | 2019-08-01 → 2025-09-01 |  | 4h | — | — | — | — | pendiente |
| RES-0003 | 2026-09-17 | ml-predictions | 7c1dca5c7b | … → … |  | 4h | — | — | — | — | pendiente |
| RES-0004 | 2026-09-17 | ml-train-lightgbm | 32443d806f | 2019-08-01 → 2025-09-01 |  | 4h | — | — | — | — | pendiente |
| RES-0005 | 2026-09-17 | ml-predictions | 224d5f41e2 | … → … |  | 4h | — | — | — | — | pendiente |
| RES-0006 | 2026-09-17 | paired-comparison | bc346a4012 | … → … |  | 4h | — | — | — | — | pendiente |
| RES-0007 | 2026-09-17 | paired-comparison | a420cc116c | … → … |  | 4h | — | — | — | — | pendiente |
| RES-0008 | 2026-09-17 | paired-comparison | 82737436f1 | … → … |  | 4h | — | — | — | — | pendiente |
| RES-0009 | 2026-09-17 | paired-comparison | 46a0a429b6 | … → … |  | 4h | — | — | — | — | pendiente |
