# Runbook: paper en un VPS

Mover el paper de la PC a una máquina en la nube para no depender de que la PC quede prendida. Es el mismo contenedor (`docker compose --profile paper`), la misma DB y el mismo runbook operativo ([paper.md](paper.md)); cambia dónde corre y cómo se mira.

## Elegir el VPS

- **Requisitos:** Linux x86-64 (Ubuntu 24.04 LTS), 2 vCPU, 2–4 GB de RAM, 20 GB de disco. La imagen pesa ~1 GB y el bot usa < 300 MB de RAM. Tráfico: unas pocas requests a Binance por cierre de 4 h.
- **Región: Europa** (Hetzner Falkenstein/Helsinki, DigitalOcean Amsterdam/Frankfurt). **No usar regiones de EE. UU.**: `api.binance.com` responde `451` desde IPs estadounidenses y el bot no arranca (`load_markets` falla). Argentina y Europa funcionan.
- Proveedores que sirven: Hetzner CX22/CPX11 (~4–5 €/mes), DigitalOcean Basic 1–2 GB (6–12 USD/mes). El tier gratuito de Oracle es ARM y en regiones de EE. UU. por defecto: evitarlo salvo que se elija una región europea y se verifique la build en `arm64`.
- Sin claves de Binance en el VPS: el paper no las necesita. Cuando llegue live (Fase 10), las claves van en `.env.live` con IP whitelisted a la del VPS.

## Preparar el servidor (una vez)

Conectarse por SSH como root (o el usuario con sudo que dé el proveedor) y:

```bash
apt-get update && apt-get upgrade -y && apt-get install -y git ufw unattended-upgrades
```

```bash
ufw default deny incoming && ufw default allow outgoing && ufw allow OpenSSH && ufw --force enable
```

```bash
curl -fsSL https://get.docker.com | sh
```

```bash
timedatectl set-timezone UTC && timedatectl set-ntp true
```

Comprobar que Binance responde desde esa IP (si devuelve `451`, la región no sirve):

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.binance.com/api/v3/time
```

## Clonar el repo (es privado)

En el VPS, crear una clave de solo lectura y cargarla como **Deploy key** del repo (GitHub → Settings → Deploy keys → Add, sin "write access"):

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "vps-trading-bot" && cat ~/.ssh/id_ed25519.pub
```

```bash
git clone git@github.com:JoacoMarc/trading-bot.git ~/trading-bot && cd ~/trading-bot
```

```bash
cp configs/paper.example.yaml configs/paper.yaml && docker compose build
```

## Migrar el estado desde la PC (opcional pero recomendado)

Así el paper continúa con la misma posición, el mismo pico del circuit breaker y el mismo historial en vez de arrancar de cero. Las velas cerradas entre la parada en la PC y el arranque en el VPS se procesan como reposición (no abren entradas).

En la PC (PowerShell o Git Bash), parar el paper y exportar el volumen de la DB:

```bash
docker compose --profile paper down
```

```bash
bash scripts/paper_state.sh export paper-state.tgz
```

Subir el archivo y restaurarlo en el VPS **antes** de levantar el paper:

```bash
scp paper-state.tgz root@IP_DEL_VPS:~/trading-bot/
```

En el VPS:

```bash
bash scripts/paper_state.sh import paper-state.tgz
```

Si se prefiere arrancar de cero, saltear esta sección: el bot crea `paper.db` vacío y entra cuando el régimen esté encendido.

## Arrancar y verificar

```bash
docker compose --profile paper up -d && docker compose --profile paper logs -f paper
```

Tiene que decir `reanudado desde la DB` (con estado migrado) o `arranque limpio`, y `status en logs/status.json`. Después:

```bash
docker compose --profile paper exec paper tradingbot status
```

**No dejar dos papers corriendo a la vez** (PC y VPS): en la PC queda parado con el `down` de arriba.

## Operar desde la PC

Todo por SSH; conviene un alias en el perfil de PowerShell (`notepad $PROFILE`):

```powershell
function paper-status { ssh root@IP_DEL_VPS "cd ~/trading-bot && docker compose --profile paper exec paper tradingbot status" }
```

- Estado: `paper-status`. Trades: `... exec paper tradingbot trades --db db/paper.db`.
- Frenar entradas: `ssh root@IP "touch ~/trading-bot/logs/STOP"`; con flatten: `echo flatten > logs/STOP`. Reanudar: borrar el archivo. Reanudar el circuit breaker: `touch ~/trading-bot/logs/RESUME`.
- Logs: `ssh root@IP "cd ~/trading-bot && docker compose --profile paper logs --since 24h paper"`.
- Paridad (`PAR-`) desde la PC: `scp` de la DB (`docker compose cp paper:/app/db/paper.db ./db/paper.db` en el VPS y luego `scp`), después `uv run tradingbot parity --config configs/paper.yaml --db db/paper.db --from ... --to ...` con los datos descargados.

## Actualizar el código

Cada cambio en `strategy/`, `risk/`, `engine/` o `execution/` reinicia el reloj del Gate 2 (`docs/GATES.md`). Para desplegar:

```bash
cd ~/trading-bot && git pull && docker compose build && docker compose --profile paper up -d
```

`up -d` reemplaza el contenedor: SIGTERM ordenado, estado en la DB, reanudación con reposición de las velas perdidas (segundos).

## Respaldo y monitoreo mínimo

- **Backup semanal de la DB** (cron en el VPS, domingo 03:00 UTC): `0 3 * * 0 cd ~/trading-bot && bash scripts/paper_state.sh export backups/paper-$(date +\%F).tgz`. Guardar una copia fuera del VPS cada tanto (`scp` a la PC).
- **Reinicios:** `docker inspect trading-bot-paper-1 --format '{{.RestartCount}}'` (el nombre del proyecto es la carpeta: `trading-bot-paper-1`). El watchdog interno sale con 1 si no completa un ciclo en 8 h 5 min y Docker lo relanza.
- **Alertas:** hasta la Fase 8 (Telegram) no hay aviso automático; revisar `paper-status` cuando se pueda. Con Telegram, el bot avisa fills, stops, breaker y errores.
- **Actualizaciones del SO:** `unattended-upgrades` aplica parches de seguridad; si reinicia el host, Docker levanta el contenedor solo (`restart: unless-stopped`).

## Problemas conocidos

- `load_markets` falla al arrancar con `451` o `Service unavailable from a restricted location`: región bloqueada por Binance; cambiar el VPS de región.
- `permission denied` en `logs/` o `configs/`: el contenedor corre como uid 1000; `chown -R 1000:1000 logs` en el VPS (los bind mounts heredan los permisos del host).
- El reloj del VPS desfasado (`feed_late` repetidos): `timedatectl set-ntp true` y verificar con `timedatectl`.
