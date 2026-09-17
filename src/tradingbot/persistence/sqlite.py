"""`SqliteStore`: el `TradeStore` durable de paper/testnet/live (ADR-0011).

SQLAlchemy Core síncrono sobre `sqlite+pysqlite`, un archivo por modo. Cada tabla tiene columnas
indexadas para consultar (par, timestamps, `client_order_id`) y una columna `data` con el JSON
del modelo pydantic (`model_dump(mode="json")`: los `Decimal` viajan como texto, sin pérdida).
`state` guarda lo que no es dominio: versión del esquema, última vela procesada, protecciones,
cash y dust. Un solo proceso escribe; WAL permite lectores concurrentes (`status`, `parity`).

`transaction()` agrupa varias escrituras en una sola transacción: el ciclo de una vela (fills,
posiciones, trades, snapshot y `state`) se confirma entero o no se confirma, así un corte a mitad
de ciclo no deja el cash sin la venta ni la posición sin el débito.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import event
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection
from sqlalchemy.engine import Engine as SAEngine

from tradingbot.domain.errors import ConfigError
from tradingbot.domain.orders import Fill, Order
from tradingbot.domain.pair import Pair
from tradingbot.domain.positions import PortfolioSnapshot, Position, Trade
from tradingbot.persistence.store import EventRecord

SCHEMA_VERSION = 1
SCHEMA_KEY = "schema_version"

metadata = sa.MetaData()

orders_table = sa.Table(
    "orders",
    metadata,
    sa.Column("client_order_id", sa.String(36), primary_key=True),
    sa.Column("pair", sa.String(24), nullable=False),
    sa.Column("side", sa.String(4), nullable=False),
    sa.Column("status", sa.String(20), nullable=False),
    sa.Column("created_ts", sa.Integer, nullable=False),
    sa.Column("updated_ts", sa.Integer, nullable=False),
    sa.Column("data", sa.Text, nullable=False),
    sa.Index("ix_orders_created_ts", "created_ts"),
)
fills_table = sa.Table(
    "fills",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("client_order_id", sa.String(36), nullable=False),
    sa.Column("pair", sa.String(24), nullable=False),
    sa.Column("side", sa.String(4), nullable=False),
    sa.Column("fill_ts", sa.Integer, nullable=False),
    sa.Column("data", sa.Text, nullable=False),
    sa.Index("ix_fills_fill_ts", "fill_ts"),
)
positions_table = sa.Table(
    "positions",
    metadata,
    sa.Column("pair", sa.String(24), primary_key=True),
    sa.Column("data", sa.Text, nullable=False),
)
trades_table = sa.Table(
    "trades",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("pair", sa.String(24), nullable=False),
    sa.Column("exit_time", sa.Integer, nullable=False),
    sa.Column("exit_client_order_id", sa.String(36), nullable=False, unique=True),
    sa.Column("data", sa.Text, nullable=False),
    sa.Index("ix_trades_exit_time", "exit_time"),
)
snapshots_table = sa.Table(
    "equity_snapshots",
    metadata,
    sa.Column("ts", sa.Integer, primary_key=True),
    sa.Column("equity", sa.Text, nullable=False),
    sa.Column("cash", sa.Text, nullable=False),
    sa.Column("data", sa.Text, nullable=False),
)
events_table = sa.Table(
    "events",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("ts", sa.Integer, nullable=False),
    sa.Column("kind", sa.String(40), nullable=False),
    sa.Column("pair", sa.String(24), nullable=True),
    sa.Column("reason", sa.String(80), nullable=False),
    sa.Column("payload", sa.Text, nullable=False),
    sa.Index("ix_events_ts", "ts"),
)
state_table = sa.Table(
    "state",
    metadata,
    sa.Column("key", sa.String(64), primary_key=True),
    sa.Column("value", sa.Text, nullable=False),
)

# Extensión aditiva: el schema v1 y los lectores anteriores siguen siendo compatibles.
notification_outbox = sa.Table(
    "notification_outbox",
    metadata,
    sa.Column("delivery_id", sa.Text, primary_key=True),
    sa.Column("created_ts", sa.Integer, nullable=False),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("silent", sa.Boolean, nullable=False),
    sa.Column("attempts", sa.Integer, nullable=False, default=0),
    sa.Column("next_attempt_ts", sa.Integer, nullable=False, default=0),
    sa.Column("sent_ts", sa.Integer, nullable=True),
)


def _dumps(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), separators=(",", ":"), ensure_ascii=False)


def _loads[M: BaseModel](cls: type[M], text: str) -> M:
    return cls.model_validate(json.loads(text))


def _load_snapshot(text: str) -> PortfolioSnapshot:
    # `marks` se serializa con el par como texto (`BTC/USDT`); pydantic no lo parsea solo.
    raw = json.loads(text)
    raw["marks"] = {Pair.parse(k): v for k, v in raw.get("marks", {}).items()}
    return PortfolioSnapshot.model_validate(raw)


class SqliteStore:
    """`TradeStore` sobre SQLite. Abre (o crea) la DB en `path` y valida `schema_version`."""

    def __init__(self, path: str | Path, *, busy_timeout_ms: int = 5_000) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._engine: SAEngine = sa.create_engine(
            f"sqlite+pysqlite:///{self._path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        self._tx: Connection | None = None

        @event.listens_for(self._engine, "connect")
        def _pragmas(dbapi_connection: Any, _record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        metadata.create_all(self._engine)
        self._check_schema()

    # ------------------------------------------------------------- ciclo de vida

    @property
    def path(self) -> Path:
        return self._path

    @property
    def in_transaction(self) -> bool:
        return self._tx is not None

    def close(self) -> None:
        self._engine.dispose()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Agrupa las escrituras del bloque en una transacción (anidable: la externa manda)."""
        if self._tx is not None:
            yield
            return
        with self._engine.begin() as conn:
            self._tx = conn
            try:
                yield
            finally:
                self._tx = None

    @contextmanager
    def _conn(self) -> Iterator[Connection]:
        """Conexión de la transacción abierta o una transacción propia de una sola sentencia."""
        if self._tx is not None:
            yield self._tx
            return
        with self._engine.begin() as conn:
            yield conn

    def _check_schema(self) -> None:
        current = self.load_state(SCHEMA_KEY)
        if current is None:
            self.save_state(SCHEMA_KEY, {"version": SCHEMA_VERSION})
            return
        version = current.get("version")
        if version != SCHEMA_VERSION:
            msg = (
                f"{self._path} tiene schema_version {version}, el código espera {SCHEMA_VERSION}; "
                "migrar la DB (ADR-0011) antes de arrancar"
            )
            raise ConfigError(msg)

    def pragma(self, name: str) -> Any:
        """Valor de un PRAGMA de la conexión (p. ej. `journal_mode`), para diagnóstico."""
        with self._engine.connect() as conn:
            return conn.exec_driver_sql(f"PRAGMA {name}").scalar()

    # ------------------------------------------------------------- escritura

    def save_order(self, order: Order) -> None:
        stmt = sqlite_insert(orders_table).values(
            client_order_id=order.client_order_id,
            pair=order.intent.pair.symbol,
            side=order.intent.side.value,
            status=order.status.value,
            created_ts=order.created_ts,
            updated_ts=order.updated_ts,
            data=_dumps(order),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[orders_table.c.client_order_id],
            set_={
                "status": stmt.excluded.status,
                "updated_ts": stmt.excluded.updated_ts,
                "data": stmt.excluded.data,
            },
        )
        with self._conn() as conn:
            conn.execute(stmt)

    def save_fill(self, fill: Fill) -> None:
        with self._conn() as conn:
            conn.execute(
                fills_table.insert().values(
                    client_order_id=fill.client_order_id,
                    pair=fill.pair.symbol,
                    side=fill.side.value,
                    fill_ts=fill.fill_ts,
                    data=_dumps(fill),
                )
            )

    def save_position(self, position: Position) -> None:
        stmt = sqlite_insert(positions_table).values(
            pair=position.pair.symbol, data=_dumps(position)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[positions_table.c.pair], set_={"data": stmt.excluded.data}
        )
        with self._conn() as conn:
            conn.execute(stmt)

    def remove_position(self, pair: Pair) -> None:
        with self._conn() as conn:
            conn.execute(sa.delete(positions_table).where(positions_table.c.pair == pair.symbol))

    def save_trade(self, trade: Trade) -> None:
        stmt = sqlite_insert(trades_table).values(
            pair=trade.pair.symbol,
            exit_time=trade.exit_time,
            exit_client_order_id=trade.exit_client_order_id,
            data=_dumps(trade),
        )
        # Reintento tras un reinicio: el mismo trade no se duplica.
        stmt = stmt.on_conflict_do_update(
            index_elements=[trades_table.c.exit_client_order_id],
            set_={"data": stmt.excluded.data, "exit_time": stmt.excluded.exit_time},
        )
        with self._conn() as conn:
            conn.execute(stmt)

    def snapshot_equity(self, snapshot: PortfolioSnapshot) -> None:
        stmt = sqlite_insert(snapshots_table).values(
            ts=snapshot.ts,
            equity=str(snapshot.equity),
            cash=str(snapshot.cash),
            data=_dumps(snapshot),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[snapshots_table.c.ts],
            set_={
                "equity": stmt.excluded.equity,
                "cash": stmt.excluded.cash,
                "data": stmt.excluded.data,
            },
        )
        with self._conn() as conn:
            conn.execute(stmt)

    def record_event(self, event_record: EventRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                events_table.insert().values(
                    ts=event_record.ts,
                    kind=event_record.kind,
                    pair=None if event_record.pair is None else event_record.pair.symbol,
                    reason=event_record.reason,
                    payload=json.dumps(dict(event_record.payload), ensure_ascii=False),
                )
            )

    def save_state(self, key: str, value: Mapping[str, Any]) -> None:
        """Guarda un mapa JSON-serializable bajo `key` (última versión gana)."""
        stmt = sqlite_insert(state_table).values(
            key=key, value=json.dumps(dict(value), ensure_ascii=False, default=str)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[state_table.c.key], set_={"value": stmt.excluded.value}
        )
        with self._conn() as conn:
            conn.execute(stmt)

    # ------------------------------------------------------------- lectura

    def enqueue_notification(self, delivery_id: str, text: str, silent: bool, ts: int) -> None:
        """Se llama dentro de la transacción del fill. Repetir un id no lo reenvía."""
        stmt = (
            sqlite_insert(notification_outbox)
            .values(
                delivery_id=delivery_id,
                created_ts=ts,
                text=text,
                silent=silent,
                attempts=0,
                next_attempt_ts=0,
            )
            .on_conflict_do_nothing(index_elements=[notification_outbox.c.delivery_id])
        )
        with self._conn() as conn:
            conn.execute(stmt)

    def pending_notifications(self, now_ms: int, limit: int = 5) -> list[dict[str, Any]]:
        table = notification_outbox
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(table)
                .where(
                    table.c.sent_ts.is_(None),
                    table.c.next_attempt_ts <= now_ms,
                )
                .order_by(table.c.created_ts, table.c.delivery_id)
                .limit(limit)
            ).mappings()
            return [dict(row) for row in rows]

    def finish_notification(self, delivery_id: str, now_ms: int) -> None:
        with self._conn() as conn:
            conn.execute(
                notification_outbox.update()
                .where(
                    notification_outbox.c.delivery_id == delivery_id,
                )
                .values(sent_ts=now_ms)
            )

    def retry_notification(self, delivery_id: str, attempts: int, next_ts: int) -> None:
        with self._conn() as conn:
            conn.execute(
                notification_outbox.update()
                .where(
                    notification_outbox.c.delivery_id == delivery_id,
                )
                .values(attempts=attempts, next_attempt_ts=next_ts)
            )

    def pending_notification_count(self) -> int:
        with self._conn() as conn:
            return int(
                conn.execute(
                    sa.select(sa.func.count())
                    .select_from(
                        notification_outbox,
                    )
                    .where(notification_outbox.c.sent_ts.is_(None))
                ).scalar_one()
            )

    def load_state(self, key: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                sa.select(state_table.c.value).where(state_table.c.key == key)
            ).scalar_one_or_none()
        if row is None:
            return None
        loaded: dict[str, Any] = json.loads(row)
        return loaded

    def load_open_positions(self) -> tuple[Position, ...]:
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(positions_table.c.data).order_by(positions_table.c.pair)
            ).scalars()
            return tuple(_loads(Position, text) for text in rows)

    def orders(self) -> tuple[Order, ...]:
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(orders_table.c.data).order_by(
                    orders_table.c.created_ts, orders_table.c.client_order_id
                )
            ).scalars()
            return tuple(_loads(Order, text) for text in rows)

    def fills(self) -> tuple[Fill, ...]:
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(fills_table.c.data).order_by(fills_table.c.fill_ts, fills_table.c.id)
            ).scalars()
            return tuple(_loads(Fill, text) for text in rows)

    def trades(self) -> tuple[Trade, ...]:
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(trades_table.c.data).order_by(trades_table.c.exit_time, trades_table.c.id)
            ).scalars()
            return tuple(_loads(Trade, text) for text in rows)

    def snapshots(self) -> tuple[PortfolioSnapshot, ...]:
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(snapshots_table.c.data).order_by(snapshots_table.c.ts)
            ).scalars()
            return tuple(_load_snapshot(text) for text in rows)

    def last_snapshot(self) -> PortfolioSnapshot | None:
        with self._conn() as conn:
            text = conn.execute(
                sa.select(snapshots_table.c.data).order_by(snapshots_table.c.ts.desc()).limit(1)
            ).scalar_one_or_none()
        return None if text is None else _load_snapshot(text)

    def events(self) -> tuple[EventRecord, ...]:
        with self._conn() as conn:
            rows = conn.execute(
                sa.select(
                    events_table.c.ts,
                    events_table.c.kind,
                    events_table.c.pair,
                    events_table.c.reason,
                    events_table.c.payload,
                ).order_by(events_table.c.id)
            ).all()
        return tuple(
            EventRecord(
                ts=int(ts),
                kind=str(kind),
                pair=None if pair is None else Pair.parse(str(pair)),
                reason=str(reason),
                payload=json.loads(payload),
            )
            for ts, kind, pair, reason, payload in rows
        )

    def counts(self) -> dict[str, int]:
        """Filas por tabla, para `status` y diagnóstico."""
        out: dict[str, int] = {}
        with self._conn() as conn:
            for table in (
                orders_table,
                fills_table,
                positions_table,
                trades_table,
                snapshots_table,
                events_table,
            ):
                out[table.name] = int(
                    conn.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
                )
        return out
