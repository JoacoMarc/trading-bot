"""Adaptador SDK simulado, contrato acotado y observación de posiciones aislada."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2 as httpx
import pytest
from anthropic import RateLimitError

from tradingbot.analyst.contract import run_contract
from tradingbot.analyst.positions import read_positions
from tradingbot.analyst.store import AdvisorStore
from tradingbot.analyst.worker import AdvisorWorker, AnthropicProvider, RateLimited
from tradingbot.decision.models import Answer, PositionContext, Proposal
from tradingbot.domain import Pair
from tradingbot.domain.positions import Position

from .test_observer import FakeProvider, config, proposal


async def test_sdk_contract_preserves_truncated_raw_and_retry_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = config()
    provider = AnthropicProvider("synthetic-not-a-secret", cfg)
    request = AsyncMock(
        return_value=SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"unfinished":')],
            usage=SimpleNamespace(input_tokens=125, output_tokens=512),
            stop_reason="max_tokens",
        )
    )
    monkeypatch.setattr(provider.client.messages, "create", request)
    store = AdvisorStore(tmp_path / "advisor.db", cfg.policy_hash)
    item = proposal()
    store.add(item)
    await AdvisorWorker(store, cfg, provider, lambda: 1_000_500).drain()
    row = store.rows()[0]
    assert row["state"] == "failed"
    assert row["answer"] is None
    assert row["raw_response"] == '{"unfinished":'
    assert row["stop_reason"] == "max_tokens"
    assert row["cost"] == "0.002685"
    assert request.await_args is not None
    assert request.await_args.kwargs["model"] == cfg.model
    assert (
        json.loads(request.await_args.kwargs["messages"][0]["content"])["proposal_id"]
        == item.proposal_id
    )
    response = httpx.Response(
        429,
        headers={"retry-after": "2"},
        request=httpx.Request("POST", "https://example.invalid/messages"),
    )
    request.side_effect = RateLimitError("synthetic", response=response, body=None)
    with pytest.raises(RateLimited) as limited:
        await provider.request(item)
    assert limited.value.wait_seconds == 2
    await provider.close()
    store.close()


async def test_synthetic_contract_is_bounded_persisted_and_has_no_financial_verdict(
    tmp_path: Path,
) -> None:
    provider = FakeProvider("ABSTAIN")
    output = tmp_path / "contract"
    result = await run_contract(config(), provider, output, now=lambda: 1_000_500)
    assert provider.calls == 3
    assert result["eligible"] is True
    assert result["financial_validation"] is False
    assert result["status"]["recommendations_by_action"] == {"ABSTAIN": 3}
    assert json.loads((output / "result.json").read_text()) == result
    with pytest.raises(FileExistsError):
        await run_contract(config(), provider, output)
    assert provider.calls == 3


async def test_exit_observer_persists_decimals_and_sell_without_orders(tmp_path: Path) -> None:
    cfg = config(review_kind="exit")
    provider = FakeProvider("SELL")
    result = await run_contract(cfg, provider, tmp_path / "exit", now=lambda: 20_000_500)
    assert result["eligible"] is True
    assert result["status"]["recommendations_buy"] == 0
    assert result["status"]["recommendations_by_action"] == {"SELL": 3}
    store = AdvisorStore(tmp_path / "exit/advisor.db", cfg.policy_hash)
    for row in store.rows():
        item = Proposal.model_validate_json(row["payload"])
        assert json.loads(item.payload())["position"]["qty"] == "1"
        assert item.snapshot_hash == row["snapshot_hash"]
    store.close()


@pytest.mark.parametrize(
    ("action", "valid"), [("SELL", True), ("HOLD", True), ("ABSTAIN", True), ("BUY", False)]
)
def test_exit_contract_validates_position_and_action(action: str, valid: bool) -> None:
    item = proposal()
    data = item.model_dump()
    data.update(
        policy="exit-review-v1",
        position=PositionContext(
            qty="1",
            entry_price="100",
            entry_time=500_000,
            stop_price="90",
            cash="9000",
            source_saved_at=1_000_000,
        ),
    )
    exit_item = Proposal.model_validate(data)
    answer = Answer.model_validate(
        dict(
            proposal_id=exit_item.proposal_id,
            snapshot_hash=exit_item.snapshot_hash,
            action=action,
            confidence=0.6,
            reason_code="trend_weak",
            reason="fixture",
        )
    )
    if valid:
        answer.validate_for(exit_item, 1_000_500)
    else:
        with pytest.raises(ValueError, match="incompatible"):
            answer.validate_for(exit_item, 1_000_500)
    assert exit_item.proposal_id != item.proposal_id


def test_position_source_is_read_only_and_rejects_stale_or_live(tmp_path: Path) -> None:
    path = tmp_path / "paper.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        "CREATE TABLE state(key TEXT,value TEXT); CREATE TABLE positions(data TEXT);"
    )
    session = {"mode": "paper", "saved_ts": 1_000_000}
    connection.executemany(
        "INSERT INTO state VALUES (?,?)",
        [("session", json.dumps(session)), ("engine", '{"cash":"9000"}')],
    )
    connection.commit()
    position = Position(
        pair=Pair.parse("BTC/USDT"),
        strategy="donchian",
        qty="1",
        entry_price="100",
        entry_time=500_000,
        stop_price="90",
        highest_close_since_entry="105",
        client_order_id="test-observed-position",
    )
    connection.execute("INSERT INTO positions VALUES (?)", (position.model_dump_json(),))
    connection.commit()
    before = path.read_bytes()
    observed = read_positions(path, 1_000_500)
    assert observed["BTC/USDT"].qty == position.qty
    assert observed["BTC/USDT"].cash == 9000
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="desactualizada"):
        read_positions(path, 16_000_000)
    with pytest.raises(ValueError, match="futura"):
        read_positions(path, 999_999)
    connection.execute(
        "UPDATE state SET value=? WHERE key='session'", (json.dumps({**session, "mode": "live"}),)
    )
    connection.commit()
    with pytest.raises(ValueError, match="no paper"):
        read_positions(path, 1_000_500)
    connection.close()
