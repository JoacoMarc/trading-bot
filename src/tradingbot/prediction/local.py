"""Inferencia paper sobre snapshots cerrados; errores bloquean compras, jamás stops."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from tradingbot.domain import Pair, Signal
from tradingbot.features.market import feature_frame
from tradingbot.prediction.base import EntryDecision
from tradingbot.research.models import predict, validate_model
from tradingbot.strategy.base import StrategyContext


class LocalFilter:
    def __init__(self, publication: Path, threshold: float) -> None:
        self.publication = publication
        self.threshold = threshold
        self.decisions: dict[Pair, EntryDecision] = {}
        self.signal_ts = 0

    def observe(self, contexts: Mapping[Pair, StrategyContext], signal_ts: int) -> None:
        self.decisions = {}
        self.signal_ts = signal_ts
        btc = contexts.get(Pair.parse("BTC/USDT"))
        if btc is None:
            return
        publication = json.loads(self.publication.read_text())
        model = publication["model"]
        validate_model(model, signal_ts, published_at=int(publication["published_at"]))
        for pair, ctx in contexts.items():
            features = feature_frame(ctx.candles, btc.candles).iloc[[-1]]
            if features.isna().any().any():
                continue
            value = float(predict(model, features)[0])
            accepted = value >= self.threshold
            self.decisions[pair] = EntryDecision(
                accepted,
                "prediction_accept" if accepted else "prediction_veto",
                f"{model['model_hash']}:{pair.symbol}:{signal_ts}",
            )

    def evaluate(self, signal: Signal, signal_ts: int) -> EntryDecision:
        if signal_ts != self.signal_ts:
            return EntryDecision(False, "prediction_stale")
        return self.decisions.get(signal.pair, EntryDecision(False, "prediction_missing"))
