# configs/

Configuraciones YAML por modo (`backtest`, `paper`, `testnet`, `live`). Llegan en la Fase 1 como `*.example.yaml`.

Reglas:
- Nunca contienen claves ni tokens. Los secretos van en `.env` (desarrollo) o `.env.live` (solo perfil live de compose).
- Precedencia: CLI > variables de entorno > YAML > defaults de la estrategia.
