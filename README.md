# trading-bot

Bot de trading propio para Binance Spot, construido por fases. Un solo motor para backtest, paper trading y live; dinero real solo después de pasar los gates de validación.

- Plan completo: [docs/PLAN.md](docs/PLAN.md)
- Estado por fase: [docs/ROADMAP.md](docs/ROADMAP.md)
- Decisiones de arquitectura: [docs/decisions/](docs/decisions/)
- Experimentos: [experiments/REGISTRY.md](experiments/REGISTRY.md)

## Uso rápido

```bash
uv sync
uv run tradingbot doctor
uv run pytest
```
