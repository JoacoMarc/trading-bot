# configs/

Configuraciones YAML por modo (`backtest`, `paper`, `testnet`, `live`). Llegan en la Fase 1 como `*.example.yaml`.

`binance_gaps.json`: huecos reales de Binance por par y timeframe (ADR-0005). `tradingbot data-check` solo alerta por huecos que no estén acá; `--register` agrega los encontrados con una nota para revisar antes de commitear.

Reglas:
- Nunca contienen claves ni tokens. Los secretos van en `.env` (desarrollo) o `.env.live` (solo perfil live de compose).
- Precedencia: CLI > variables de entorno > YAML > defaults de la estrategia.
