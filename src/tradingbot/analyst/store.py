"""SQLite de observación: propuestas, decisiones y presupuesto atómicos."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from filelock import FileLock

from tradingbot.decision.models import Proposal


class AdvisorStore:
    def __init__(self, path: Path, policy_hash: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._runner_lock = FileLock(str(path) + ".lock", timeout=0)
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS advisor_meta (
                id INTEGER PRIMARY KEY, policy_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY, snapshot_hash TEXT NOT NULL, payload TEXT NOT NULL,
                signal_ts INTEGER NOT NULL, observed_at INTEGER NOT NULL, deadline INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'queued', reserved TEXT NOT NULL DEFAULT '0',
                cost TEXT, day TEXT, month TEXT, completed_at INTEGER, answer TEXT, error TEXT,
                input_tokens INTEGER, output_tokens INTEGER, response_hash TEXT);
        """)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(proposals)")}
        if "raw_response" not in columns:
            self.db.execute("ALTER TABLE proposals ADD COLUMN raw_response TEXT")
        if "stop_reason" not in columns:
            self.db.execute("ALTER TABLE proposals ADD COLUMN stop_reason TEXT")
        meta_columns = {row[1] for row in self.db.execute("PRAGMA table_info(advisor_meta)")}
        if "contract" not in meta_columns:
            self.db.execute("ALTER TABLE advisor_meta ADD COLUMN contract TEXT")
        if "heartbeat_ts" not in meta_columns:
            self.db.execute("ALTER TABLE advisor_meta ADD COLUMN heartbeat_ts INTEGER DEFAULT 0")
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO advisor_meta(id,policy_hash) VALUES (1, ?)", (policy_hash,)
            )
        if (
            self.db.execute("SELECT policy_hash FROM advisor_meta WHERE id=1").fetchone()[0]
            != policy_hash
        ):
            self.db.close()
            raise ValueError("otra política/modelo/tarifas en esta DB; usar instancia nueva")

    def bind_context(self, context: dict[str, Any]) -> str:
        raw = json.dumps(context, sort_keys=True, separators=(",", ":"))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            current = self.db.execute("SELECT contract FROM advisor_meta WHERE id=1").fetchone()[0]
            if current is not None and current != raw:
                raise ValueError("otra receta de estrategia/costos/universo en esta DB")
            self.db.execute("UPDATE advisor_meta SET contract=? WHERE id=1", (raw,))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return hashlib.sha256(raw.encode()).hexdigest()

    def acquire_runner(self) -> None:
        self._runner_lock.acquire()

    def add(self, proposal: Proposal, max_pending: int = 32) -> bool:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute(
                "SELECT snapshot_hash FROM proposals WHERE id=?", (proposal.proposal_id,)
            ).fetchone()
            if old is not None:
                if old[0] != proposal.snapshot_hash:
                    raise ValueError("ID existente con otro snapshot")
                self.db.commit()
                return False
            pending = self.db.execute(
                "SELECT COUNT(*) FROM proposals WHERE state='queued'"
            ).fetchone()[0]
            state = "queued" if pending < max_pending else "saturated"
            self.db.execute(
                "INSERT INTO "
                "proposals(id,snapshot_hash,payload,signal_ts,observed_at,deadline,state) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    proposal.proposal_id,
                    proposal.snapshot_hash,
                    proposal.model_dump_json(),
                    proposal.signal_ts,
                    proposal.observed_at,
                    proposal.deadline,
                    state,
                ),
            )
            self.db.commit()
            return state == "queued"
        except BaseException:
            self.db.rollback()
            raise

    def recover(self, now: int) -> None:
        # No consultar otra vez una llamada cuyo resultado se desconoce.
        self.db.execute(
            "UPDATE proposals SET state='unknown',error='restart_inflight',completed_at=? "
            "WHERE state='inflight'",
            (now,),
        )
        self.db.execute(
            "UPDATE proposals SET state='expired',error='deadline',completed_at=? WHERE "
            "state='queued' AND deadline<?",
            (now, now),
        )

    def claim(
        self, now: int, reserve: Decimal, daily_limit: Decimal, monthly_limit: Decimal
    ) -> Proposal | None:
        today = datetime.fromtimestamp(now / 1000, tz=UTC)
        day, month = today.strftime("%Y-%m-%d"), today.strftime("%Y-%m")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT * FROM proposals WHERE state='queued' AND deadline>=? ORDER BY "
                "signal_ts,id LIMIT 1",
                (now,),
            ).fetchone()
            if row is None:
                self.db.commit()
                return None

            def spent(column: str, value: str) -> Decimal:
                return sum(
                    (
                        Decimal(r[0])
                        for r in self.db.execute(
                            f"SELECT COALESCE(cost,reserved) FROM proposals WHERE {column}=?",
                            (value,),
                        )
                    ),
                    Decimal(0),
                )

            if (
                spent("day", day) + reserve > daily_limit
                or spent("month", month) + reserve > monthly_limit
            ):
                self.db.execute(
                    "UPDATE proposals SET state='budget',error='budget_cap',completed_at=? WHERE "
                    "id=?",
                    (now, row["id"]),
                )
                self.db.commit()
                return None
            self.db.execute(
                "UPDATE proposals SET state='inflight',reserved=?,day=?,month=? WHERE id=?",
                (str(reserve), day, month, row["id"]),
            )
            self.db.commit()
            return Proposal.model_validate_json(row["payload"])
        except BaseException:
            self.db.rollback()
            raise

    def finish(
        self,
        proposal: Proposal,
        now: int,
        *,
        answer: str | None,
        error: str | None,
        cost: Decimal | None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        response_hash: str = "",
        raw_response: str = "",
        stop_reason: str = "",
    ) -> None:
        cursor = self.db.execute(
            "UPDATE proposals SET "
            "state=?,completed_at=?,answer=?,error=?,cost=?,input_tokens=?,output_tokens=?,"
            "response_hash=?,raw_response=?,stop_reason=? "
            "WHERE id=? AND state='inflight'",
            (
                "decided" if error is None else "failed",
                now,
                answer,
                error,
                None if cost is None else str(cost),
                input_tokens,
                output_tokens,
                response_hash,
                raw_response,
                stop_reason,
                proposal.proposal_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("decisión duplicada o propuesta no reclamada")

    def rows(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.execute("SELECT * FROM proposals ORDER BY signal_ts,id")]

    def heartbeat(self, now: int) -> None:
        self.db.execute("UPDATE advisor_meta SET heartbeat_ts=? WHERE id=1", (now,))

    def status(self) -> dict[str, Any]:
        rows = self.rows()
        states: dict[str, int] = {}
        cost = Decimal(0)
        accepted = 0
        actions: dict[str, int] = {}
        for row in rows:
            states[row["state"]] = states.get(row["state"], 0) + 1
            cost += Decimal(row["cost"] or row["reserved"])
            if row["answer"]:
                action = json.loads(row["answer"])["action"]
                actions[action] = actions.get(action, 0) + 1
                accepted += int(action == "BUY")
        return {
            "heartbeat_ts": self.db.execute(
                "SELECT heartbeat_ts FROM advisor_meta WHERE id=1"
            ).fetchone()[0],
            "proposals": len(rows),
            "states": states,
            "recommendations_buy": accepted,
            "recommendations_by_action": actions,
            "cost_usd_including_uncertain_reservations": str(cost),
            "mode": "OBSERVATION",
        }

    def close(self) -> None:
        self.db.close()
        self._runner_lock.release()
