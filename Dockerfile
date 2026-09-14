# syntax=docker/dockerfile:1.7
# Imagen del bot. Build multi-stage: deps con uv en el builder, runtime slim sin toolchain.

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# 1) Solo dependencias (capa cacheable mientras no cambie el lock)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2) El proyecto
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 1000 bot
ENV TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=builder --chown=bot:bot /app /app
COPY --chown=bot:bot configs ./configs
RUN mkdir -p data db logs experiments && chown -R bot:bot data db logs experiments
USER bot

# Los perfiles de larga duración (compose) leen el heartbeat de logs/status.json con
# `tradingbot status --check`; para comandos sueltos alcanza con que el binario responda.
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD ["tradingbot", "--version"]

ENTRYPOINT ["tradingbot"]
CMD ["--help"]
