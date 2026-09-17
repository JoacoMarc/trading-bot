"""Observador prospectivo sin broker; replay de respuestas almacenadas, nunca API histórica."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Annotated

import typer
import yaml

from tradingbot.analyst.store import AdvisorStore
from tradingbot.analyst.worker import AdvisorConfig, AdvisorWorker, AnthropicProvider
from tradingbot.cli.backtest_commands import ConfigOption, _fail, _load_config
from tradingbot.data.live_feed import LiveFeed
from tradingbot.decision.models import Answer, Proposal
from tradingbot.domain import Pair, SignalAction
from tradingbot.engine.series import RollingSeries
from tradingbot.exchange.binance import BinanceExchange
from tradingbot.features.market import FEATURE_VERSION, feature_frame
from tradingbot.strategy.base import StrategyContext
from tradingbot.strategy.registry import build_strategy, effective_warmup

advisor_app = typer.Typer(no_args_is_help=True)
PolicyOption = Annotated[Path, typer.Option("--policy")]
DBOption = Annotated[Path, typer.Option("--db")]


def load_policy(path: Path) -> AdvisorConfig:
    return AdvisorConfig.model_validate(yaml.safe_load(path.read_text()))


@advisor_app.command()
def observe(
    config: ConfigOption,
    policy: PolicyOption,
    db: DBOption = Path("db/advisor.db"),
    max_bars: Annotated[int | None, typer.Option("--max-bars", min=1)] = None,
) -> None:
    """Recolecta rupturas4h en tiempo real; paid_calls_enabled=false no llama a la API."""
    cfg = _load_config(config, {})
    settings = load_policy(policy)
    if cfg.strategy.name != "donchian" or cfg.strategy.timeframe.value != "4h":
        _fail(ValueError("observador v1 requiere Donchian4h"))
    strategy = build_strategy(cfg.strategy)
    exchange = BinanceExchange.create(
        timeout_ms=cfg.exchange.request_timeout_ms, recv_window_ms=cfg.exchange.recv_window_ms
    )
    store = AdvisorStore(db, settings.policy_hash)
    store.acquire_runner()
    context_hash = store.bind_context(
        {
            "strategy": cfg.strategy.model_dump(mode="json"),
            "execution": cfg.execution.model_dump(mode="json"),
            "risk": cfg.risk.model_dump(mode="json", exclude={"kill_switch_file"}),
            "features": FEATURE_VERSION,
        }
    )
    store.recover(exchange.now_ms())
    store.heartbeat(exchange.now_ms())
    provider = None
    if settings.paid_calls_enabled:
        if cfg.anthropic_api_key is None:
            store.close()
            _fail(ValueError("falta ANTHROPIC_API_KEY en el entorno"))
        assert cfg.anthropic_api_key is not None
        provider = AnthropicProvider(cfg.anthropic_api_key.get_secret_value(), settings)
    warmup = effective_warmup(cfg.strategy, strategy)
    feed = LiveFeed(exchange, list(cfg.strategy.pairs), cfg.strategy.timeframe, warmup)

    async def run() -> None:
        worker = (
            None if provider is None else AdvisorWorker(store, settings, provider, exchange.now_ms)
        )
        if worker is not None:
            await worker.drain()  # pendientes aún válidas, antes de descargar el warmup
        feed.bootstrap()
        series = RollingSeries(
            strategy, {p: feed.warmup_candles(p) for p in cfg.strategy.pairs}, window=warmup + 1
        )
        count = 0
        try:
            async for bar in feed:
                contexts = {}
                for pair in bar.pairs:
                    data = series.at(pair, bar)
                    if data is not None:
                        contexts[pair] = StrategyContext(
                            ohlcv=data.ohlcv, indicators=data.indicators, index=data.index
                        )
                btc = contexts.get(Pair.parse("BTC/USDT"))
                if btc is not None:
                    for pair, ctx in contexts.items():
                        signal = strategy.on_candle(ctx)
                        if signal.action is not SignalAction.ENTER_LONG:
                            continue
                        features = feature_frame(ctx.candles, btc.candles).iloc[-1]
                        if features.isna().any():
                            continue
                        proposal = Proposal(
                            instance=settings.instance,
                            context_hash=context_hash,
                            fee_rate=str(cfg.execution.fee_rate),
                            slippage_bps=str(cfg.execution.slippage_bps),
                            risk_per_trade=str(cfg.risk.risk_per_trade),
                            pair=pair.symbol,
                            signal_ts=bar.close_time + 1,
                            observed_at=exchange.now_ms(),
                            features={str(k): float(v) for k, v in features.items()},
                            close=str(ctx.candle.close),
                            stop=str(signal.stop_price),
                            provider=settings.provider,
                            model=settings.model,
                        )
                        store.add(proposal, settings.queue_capacity)
                # Otro proceso, sin posiciones ni stops que bloquear. Deadline incluye cola.
                store.recover(exchange.now_ms())
                if worker is not None:
                    await worker.drain()
                store.heartbeat(exchange.now_ms())
                typer.echo(json.dumps(store.status()))
                count += 1
                if max_bars is not None and count >= max_bars:
                    break
        finally:
            feed.stop()
            if provider is not None:
                await provider.close()
            store.close()

    asyncio.run(run())


@advisor_app.command()
def status(
    policy: PolicyOption,
    db: DBOption = Path("db/advisor.db"),
    check: Annotated[bool, typer.Option("--check")] = False,
) -> None:
    """Estados y gasto conservador; ninguna recomendación se cuenta como fill."""
    store = AdvisorStore(db, load_policy(policy).policy_hash)
    try:
        payload = store.status()
        typer.echo(json.dumps(payload, indent=2))
        if check and int(time.time() * 1000) - payload["heartbeat_ts"] > 2 * 14_400_000 + 300_000:
            raise typer.Exit(1)
    finally:
        store.close()


@advisor_app.command()
def replay(
    policy: PolicyOption,
    db: DBOption = Path("db/advisor.db"),
    output: Annotated[Path, typer.Option("--output")] = Path("experiments/advisor-replay.json"),
) -> None:
    """Audita decisiones guardadas. No simula PnL ni modifica una cartera."""
    store = AdvisorStore(db, load_policy(policy).policy_hash)
    rows = []
    try:
        for row in store.rows():
            proposal = Proposal.model_validate_json(row["payload"])
            action = "HOLD"
            valid = False
            if row["state"] == "decided" and row["answer"]:
                answer = Answer.model_validate_json(row["answer"])
                answer.validate_for(proposal, row["completed_at"])
                action, valid = answer.action, True
            rows.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "snapshot_hash": proposal.snapshot_hash,
                    "signal_ts": proposal.signal_ts,
                    "received_at": row["completed_at"],
                    "pair": proposal.pair,
                    "action": action,
                    "valid": valid,
                    "error": row["error"],
                    "cost_usd": row["cost"] or row["reserved"],
                }
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(
                {
                    "policy_hash": load_policy(policy).policy_hash,
                    "financial_validation": False,
                    "decisions": rows,
                    "status": store.status(),
                },
                handle,
                indent=2,
            )
        typer.echo(output)
    finally:
        store.close()
