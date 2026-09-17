"""Prueba sintética acotada del contrato de un modelo, sin precios históricos."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tradingbot.analyst.store import AdvisorStore
from tradingbot.analyst.worker import AdvisorConfig, AdvisorWorker, Provider
from tradingbot.decision.models import PositionContext, Proposal
from tradingbot.features.market import FEATURES


async def run_contract(
    config: AdvisorConfig,
    provider: Provider,
    output: Path,
    now: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    (output / "policy.json").write_text(config.model_dump_json(indent=2))
    store = AdvisorStore(output / "advisor.db", config.policy_hash)
    durations = []
    try:
        context_hash = store.bind_context(
            {"synthetic_contract": "v1", "cases": ["trend", "decline", "mixed"]}
        )
        for index, symbol in enumerate(["BTC/USDT", "ETH/USDT", "SOL/USDT"]):
            ts = now()
            values = dict.fromkeys(FEATURES, 0.0)
            for key in values:
                if key.startswith("ret"):
                    values[key] = [0.02, -0.02, 0.0][index]
            values["rsi14"] = [65.0, 30.0, 50.0][index]
            values["atr_ratio"] = 0.02
            values["volume_ratio"] = 1.0
            values[f"pair_{symbol.split('/')[0]}"] = 1.0
            position = (
                None
                if config.review_kind == "entry"
                else PositionContext(
                    qty="1",
                    entry_price="98",
                    entry_time=ts - 14_400_000,
                    stop_price="95",
                    cash="9000",
                    source_saved_at=ts,
                )
            )
            item = Proposal(
                instance="synthetic-contract",
                pair=symbol,
                context_hash=context_hash,
                policy="entry-review-v1" if position is None else "exit-review-v1",
                position=position,
                fee_rate="0.001",
                slippage_bps="5",
                risk_per_trade="0.0025",
                signal_ts=ts,
                observed_at=ts,
                features=values,
                close="100",
                stop="95",
                provider=config.provider,
                model=config.model,
                prompt_hash=config.prompt_hash,
            )
            store.add(item)
            started = time.perf_counter()
            await AdvisorWorker(store, config, provider, now).drain()
            durations.append(time.perf_counter() - started)
        status = store.status()
        result = {
            "model": config.model,
            "policy_hash": config.policy_hash,
            "synthetic": True,
            "financial_validation": False,
            "eligible": status["states"].get("decided", 0) == 3,
            "latency_seconds": durations,
            "mean_latency_seconds": sum(durations) / 3,
            "status": status,
            "selection_rule": (
                "3/3 válidas; menor costo, luego latencia media, luego modelo; máximo dos modelos"
            ),
        }
        (output / "result.json").write_text(json.dumps(result, indent=2))
        return result
    finally:
        store.close()
