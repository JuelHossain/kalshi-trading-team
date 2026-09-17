"""The persistent queues keep one connection and stay durable across a restart.

Each operation used to open, use and close its own connection, and every
single-row commit paid a full fsync: 2.6 ms per push and per pop, with the
Brain polling size() every second. One connection in WAL mode removes the
per-row sync while keeping the database consistent across a process crash,
which is the property these queues exist for.
"""

import pytest
from core.synapse import PersistentQueue, SynapseError


def _err(code: str) -> SynapseError:
    return SynapseError(agent_name="T", code=code, message="m", severity="LOW", domain="SYSTEM")


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "q.db")


class TestOneConnection:
    @pytest.mark.asyncio
    async def test_operations_share_the_connection(self, path):
        q = PersistentQueue(path, "queue_errors", SynapseError)
        before = q._conn
        await q.push(_err("A"))
        await q.size()
        await q.pop()
        assert q._conn is before
        q.close()

    def test_wal_journal_is_in_effect(self, path):
        q = PersistentQueue(path, "queue_errors", SynapseError)
        mode = q._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
        q.close()

    def test_close_is_idempotent(self, path):
        q = PersistentQueue(path, "queue_errors", SynapseError)
        q.close()
        q.close()


class TestDurability:
    @pytest.mark.asyncio
    async def test_rows_survive_a_restart(self, path):
        """The point of the queue: a new process sees what the old one queued."""
        q = PersistentQueue(path, "queue_errors", SynapseError)
        await q.push(_err("A"))
        await q.push(_err("B"))
        q.close()

        again = PersistentQueue(path, "queue_errors", SynapseError)
        assert await again.size() == 2
        first = await again.pop()
        assert first.code == "A"
        again.close()

    @pytest.mark.asyncio
    async def test_fifo_order_is_kept_across_the_reopen(self, path):
        q = PersistentQueue(path, "queue_errors", SynapseError)
        for c in ("A", "B", "C"):
            await q.push(_err(c))
        q.close()
        again = PersistentQueue(path, "queue_errors", SynapseError)
        assert [(await again.pop()).code for _ in range(3)] == ["A", "B", "C"]
        again.close()
