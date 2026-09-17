"""Contratos del observador, sin tráfico de red ni llamadas pagas."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import pytest
from filelock import Timeout

from tradingbot.analyst.store import AdvisorStore
from tradingbot.analyst.worker import AdvisorConfig, AdvisorWorker, ProviderResponse, RateLimited
from tradingbot.decision.models import Answer, Proposal
from tradingbot.features.market import FEATURES


def proposal(n: int = 0) -> Proposal:
    return Proposal(
        instance="test",
        context_hash="0" * 64,
        fee_rate="0.001",
        slippage_bps="5",
        risk_per_trade="0.0025",
        pair=f"{['BTC', 'ETH', 'SOL'][n]}/USDT",
        signal_ts=1_000_000,
        observed_at=1_000_100,
        features=dict.fromkeys(FEATURES, 1.0),
        close="100",
        stop="90",
        provider="anthropic",
        model="frozen-test-model",
    )


class FakeProvider:
    def __init__(self, behavior: str = "ok") -> None:
        self.behavior = behavior
        self.calls = 0

    async def request(self, item: Proposal) -> ProviderResponse:
        self.calls += 1
        await asyncio.sleep(0)
        if self.behavior == "timeout":
            raise TimeoutError
        if self.behavior == "429":
            raise RateLimited(60)
        payload = {
            "proposal_id": item.proposal_id,
            "snapshot_hash": item.snapshot_hash,
            "action": "BUY",
            "confidence": 0.6,
            "reason": "fixture",
        }
        if self.behavior == "id":
            payload["proposal_id"] = "wrong"
        return ProviderResponse(
            "invalid" if self.behavior == "json" else json.dumps(payload), 100, 50
        )


def config(**kwargs: object) -> AdvisorConfig:
    return AdvisorConfig.model_validate(
        dict(
            model="frozen-test-model",
            paid_calls_enabled=True,
            input_usd_per_million="1",
            output_usd_per_million="5",
            **kwargs,
        )
    )


@pytest.mark.parametrize("behavior", ["ok", "timeout", "429", "id", "json"])
async def test_responses_and_failures_are_persisted_once(tmp_path: Path, behavior: str) -> None:
    cfg = config()
    store = AdvisorStore(tmp_path / "advisor.db", cfg.policy_hash)
    item = proposal()
    assert store.add(item)
    assert not store.add(item.model_copy(update={"observed_at": 1_000_200}))
    provider = FakeProvider(behavior)
    worker = AdvisorWorker(store, cfg, provider, lambda: 1_000_500)
    await worker.drain()
    await worker.drain()
    assert provider.calls == 1
    row = store.rows()[0]
    assert row["state"] == ("decided" if behavior == "ok" else "failed")
    assert bool(row["answer"]) == (behavior == "ok")
    if behavior not in {"timeout", "429"}:
        assert row["cost"] == "0.00035"
        assert row["raw_response"]
    else:
        assert row["cost"] is None  # reserva conservadora, resultado incierto
    with pytest.raises(ValueError, match="otro snapshot"):
        store.add(item.model_copy(update={"stop": "80"}))
    store.close()


async def test_budget_atomic_across_workers_and_restart(tmp_path: Path) -> None:
    cfg = config(daily_usd="0.02", monthly_usd="0.02")
    path = tmp_path / "advisor.db"
    store = AdvisorStore(path, cfg.policy_hash)
    for n in range(3):
        store.add(proposal(n))
    # Un proceso cae después de reservar pero antes de confirmar la respuesta.
    claimed = store.claim(1_000_200, cfg.reservation, cfg.daily_usd, cfg.monthly_usd)
    assert claimed is not None
    store.close()
    resumed = AdvisorStore(path, cfg.policy_hash)
    resumed.recover(1_000_300)
    provider = FakeProvider()
    worker = AdvisorWorker(resumed, cfg, provider, lambda: 1_000_500)
    await asyncio.gather(worker.process_one(), worker.process_one())
    assert provider.calls == 0
    assert resumed.status()["states"] == {"unknown": 1, "budget": 2}
    assert Decimal(resumed.status()["cost_usd_including_uncertain_reservations"]) == cfg.reservation
    resumed.close()


def test_expiry_schema_lock_and_policy_isolation(tmp_path: Path) -> None:
    cfg = config()
    path = tmp_path / "advisor.db"
    store = AdvisorStore(path, cfg.policy_hash)
    store.acquire_runner()
    context = {"strategy": {"entry_period": 60}, "universe": ["BTC/USDT"]}
    assert len(store.bind_context(context)) == 64
    assert store.bind_context(context) == store.bind_context(context)
    with pytest.raises(ValueError, match="otra receta"):
        store.bind_context({**context, "strategy": {"entry_period": 48}})
    second = AdvisorStore(path, cfg.policy_hash)
    with pytest.raises(Timeout):
        second.acquire_runner()
    second.close()
    with pytest.raises(ValueError, match="otra política"):
        AdvisorStore(path, "different")
    item = proposal()
    store.add(item)
    store.recover(item.deadline + 1)
    assert store.status()["states"] == {"expired": 1}
    with pytest.raises(ValueError):
        Answer.model_validate(
            {
                "proposal_id": item.proposal_id,
                "snapshot_hash": item.snapshot_hash,
                "action": "SELL",
                "confidence": 0.8,
                "reason": "no position",
            }
        )
    store.close()


async def test_disabled_provider_never_calls_and_saturation_is_recorded(tmp_path: Path) -> None:
    cfg = config().model_copy(update={"paid_calls_enabled": False})
    store = AdvisorStore(tmp_path / "advisor.db", cfg.policy_hash)
    assert store.add(proposal(), max_pending=1)
    assert not store.add(proposal(1), max_pending=1)
    provider = FakeProvider()
    await AdvisorWorker(store, cfg, provider, lambda: 1_000_500).drain()
    assert provider.calls == 0
    assert store.status()["states"] == {"queued": 1, "saturated": 1}
    store.close()


async def test_restart_reclaims_queued_and_uses_single_receipt_timestamp(tmp_path: Path) -> None:
    cfg = config()
    path = tmp_path / "advisor.db"
    first = AdvisorStore(path, cfg.policy_hash)
    item = proposal()
    first.add(item)
    first.close()
    restored = AdvisorStore(path, cfg.policy_hash)
    restored.recover(1_000_500)
    clock = iter([1_000_500, 1_000_500, item.deadline, item.deadline + 1])
    provider = FakeProvider()
    worker = AdvisorWorker(restored, cfg, provider, lambda: next(clock))
    assert await worker.process_one()
    row = restored.rows()[0]
    assert row["completed_at"] == item.deadline
    assert row["state"] == "decided"
    Answer.model_validate_json(row["answer"]).validate_for(item, row["completed_at"])
    assert provider.calls == 1
    restored.close()
