# Runbooks

Procedimientos operativos. Se escriben en la fase que los necesita y se prueban antes de usarlos en serio.

| Runbook | Fase | Contenido |
|---|---|---|
| [paper-multiestrategia.md](paper-multiestrategia.md) | extensión 6/8 | Papers aislados, imágenes por revisión, backup/rollback, emisores Telegram y protocolo de aprobación; candidatas desactivadas tras validación |
| `paper.md` | 7/8 | Arranque/parada con compose, suspensión de Windows, Docker Desktop al inicio, deriva de reloj (`wsl --shutdown`), Windows Update, lectura de `logs/status.json`; Telegram (BotFather, `chat_id`, `.env`, `telegram-test`, comandos y niveles) |
| `vps.md` | 7/8 | Paper en un VPS: elección (región fuera de EE. UU. por Binance), Docker, deploy key, migración del estado con `scripts/paper_state.sh`, operación por SSH, redeploy, backups |
| `incident.md` | 8 | Bot caído con posición abierta, exchange en mantenimiento, clave revocada, stop nativo ejecutado sin que el bot lo viera |
| `live.md` | 10 | Creación de API key (permisos, IP), `.env.live`, triple confirmación, reconciliación, cierre manual de posiciones, aumento de capital |
