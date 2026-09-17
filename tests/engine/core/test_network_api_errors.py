"""A definitive answer from Kalshi must not be retried as a connection fault.

The API-error raise sat inside the same try block as the request, so the
generic except caught it and retried: a 404 or 401 made three attempts with
sleeps between them and then surfaced as a Connection Error. Wrong label,
wasted seconds, and a misleading log for the operator.
"""

from contextlib import asynccontextmanager

import pytest
from core.network import KalshiAPIError, KalshiClient

pytestmark = pytest.mark.network_internals


class _Response:
    def __init__(self, status, body=""):
        self.status = status
        self._body = body

    async def text(self):
        return self._body

    async def json(self):
        return {}


class _Session:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0
        self.closed = False

    @asynccontextmanager
    async def request(self, method, url, **kwargs):
        self.calls += 1
        yield _Response(self.statuses.pop(0))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("KALSHI_ENV", "demo")
    monkeypatch.setenv("KALSHI_DEMO_KEY_ID", "k")
    monkeypatch.setenv("KALSHI_DEMO_PRIVATE_KEY", "not-a-pem")
    c = KalshiClient()
    c.private_key = None  # unsigned is fine here; the status is what matters
    return c


async def _no_sleep(_):
    return None


class TestNonRetryableStatuses:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    async def test_a_4xx_is_raised_after_exactly_one_attempt(self, client, status, monkeypatch):
        session = _Session([status, status, status])
        client._session = session
        monkeypatch.setattr("asyncio.sleep", _no_sleep)

        with pytest.raises(KalshiAPIError):
            await client.request("GET", "/markets", retries=3)

        assert session.calls == 1, "a definitive answer was retried"

    @pytest.mark.asyncio
    async def test_it_is_not_relabelled_as_a_connection_error(self, client, monkeypatch):
        client._session = _Session([404])
        monkeypatch.setattr("asyncio.sleep", _no_sleep)

        with pytest.raises(KalshiAPIError) as info:
            await client.request("GET", "/markets", retries=3)

        assert "Connection Error" not in str(info.value)
        assert "404" in str(info.value)


class TestTransientStatusesStillRetry:
    @pytest.mark.asyncio
    async def test_a_503_then_a_200_succeeds_on_the_second_attempt(self, client, monkeypatch):
        session = _Session([503, 200])
        client._session = session
        monkeypatch.setattr("asyncio.sleep", _no_sleep)

        result = await client.request("GET", "/markets", retries=3)

        assert result == {}
        assert session.calls == 2
