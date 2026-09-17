"""Worker acotado y separado de ejecución; todos los errores terminan sin comprar."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbot.analyst.store import AdvisorStore
from tradingbot.decision.models import PROMPT, PROMPT_HASH, Answer, Proposal


class AdvisorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    instance: str = "donchian-observer-v1"
    provider: Literal["anthropic"] = "anthropic"
    model: str = Field(min_length=1, max_length=100)
    paid_calls_enabled: bool = False
    input_usd_per_million: Decimal = Field(default=Decimal(0), ge=0)
    output_usd_per_million: Decimal = Field(default=Decimal(0), ge=0)
    daily_usd: Decimal = Field(default=Decimal(1), gt=0)
    monthly_usd: Decimal = Field(default=Decimal(20), gt=0)
    max_output_tokens: int = Field(default=512, ge=128, le=1024)
    max_input_bytes: int = Field(default=16384, ge=2048, le=32768)
    concurrency: int = Field(default=2, ge=1, le=4)
    queue_capacity: int = Field(default=32, ge=8, le=128)

    @model_validator(mode="after")
    def tariffs(self) -> Self:
        if self.paid_calls_enabled and (
            self.input_usd_per_million <= 0
            or self.output_usd_per_million <= 0
            or self.model == "MODEL_NOT_SELECTED"
        ):
            raise ValueError("llamadas pagas exigen modelo y tarifas verificadas explícitas")
        return self

    @property
    def policy_hash(self) -> str:
        payload = {**self.model_dump(mode="json"), "prompt_hash": PROMPT_HASH}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @property
    def reservation(self) -> Decimal:
        return (
            Decimal(self.max_input_bytes + 1024) * self.input_usd_per_million
            + Decimal(self.max_output_tokens) * self.output_usd_per_million
        ) / Decimal(1_000_000)


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    async def request(self, proposal: Proposal) -> ProviderResponse: ...


class RateLimited(Exception):
    def __init__(self, wait_seconds: float) -> None:
        self.wait_seconds = wait_seconds


class AdvisorWorker:
    def __init__(
        self, store: AdvisorStore, config: AdvisorConfig, provider: Provider, now: Callable[[], int]
    ) -> None:
        self.store, self.config, self.provider, self.now = store, config, provider, now

    async def process_one(self) -> bool:
        if not self.config.paid_calls_enabled:
            return False
        proposal = self.store.claim(
            self.now(), self.config.reservation, self.config.daily_usd, self.config.monthly_usd
        )
        if proposal is None:
            return False
        response: ProviderResponse | None = None
        answer: Answer | None = None
        error: str | None = None
        received_at: int | None = None
        try:
            if len((PROMPT + proposal.payload()).encode()) > self.config.max_input_bytes:
                raise ValueError("input_limit")
            if (
                proposal.model != self.config.model
                or proposal.provider != self.config.provider
                or proposal.prompt_hash != PROMPT_HASH
            ):
                raise ValueError("policy_mismatch")
            for attempt in range(3):
                remaining = (proposal.deadline - self.now()) / 1000
                if remaining <= 0:
                    raise TimeoutError("deadline")
                try:
                    response = await asyncio.wait_for(
                        self.provider.request(proposal), timeout=remaining
                    )
                    received_at = self.now()
                    break
                except RateLimited as exc:
                    if (
                        attempt == 2
                        or exc.wait_seconds < 0
                        or exc.wait_seconds >= (proposal.deadline - self.now()) / 1000
                    ):
                        raise TimeoutError("rate_limit_deadline") from exc
                    await asyncio.sleep(exc.wait_seconds)
            if response is None:
                raise ValueError("empty_response")
            answer = Answer.model_validate_json(response.text)
            assert received_at is not None
            answer.validate_for(proposal, received_at)
        except Exception as exc:
            # No guardar str(exc) de SDK: puede contener cabeceras/cuerpo o secretos.
            error = type(exc).__name__
        cost = None
        response_hash = ""
        if response is not None:
            cost = (
                Decimal(response.input_tokens) * self.config.input_usd_per_million
                + Decimal(response.output_tokens) * self.config.output_usd_per_million
            ) / Decimal(1_000_000)
            response_hash = hashlib.sha256(response.text.encode()).hexdigest()
        self.store.finish(
            proposal,
            self.now() if received_at is None else received_at,
            answer=answer.model_dump_json() if answer is not None and error is None else None,
            error=error,
            cost=cost,
            input_tokens=0 if response is None else response.input_tokens,
            output_tokens=0 if response is None else response.output_tokens,
            response_hash=response_hash,
            raw_response="" if response is None else response.text,
        )
        return True

    async def drain(self) -> None:
        async def consumer() -> None:
            while await self.process_one():
                pass

        await asyncio.gather(*(consumer() for _ in range(self.config.concurrency)))


class AnthropicProvider:
    def __init__(self, api_key: str, config: AdvisorConfig) -> None:
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key, max_retries=0)
        self.config = config

    async def request(self, proposal: Proposal) -> ProviderResponse:
        from anthropic import RateLimitError

        try:
            message = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_output_tokens,
                system=PROMPT,
                messages=[{"role": "user", "content": proposal.payload()}],
            )
        except RateLimitError as exc:
            # Un límite de gasto sin Retry-After no se reintenta.
            wait = exc.response.headers.get("retry-after")
            if wait is None:
                raise RateLimited(60) from exc
            raise RateLimited(float(wait)) from exc
        text = "".join(block.text for block in message.content if block.type == "text")
        if message.stop_reason != "end_turn":
            text = ""  # truncada/tool_use: formato inválido, conserva el consumo real
        return ProviderResponse(text, message.usage.input_tokens, message.usage.output_tokens)

    async def close(self) -> None:
        await self.client.close()
