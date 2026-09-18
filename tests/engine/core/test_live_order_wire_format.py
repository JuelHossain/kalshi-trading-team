"""The live order path must speak Kalshi's documented protocol.

Paper mode never reaches any of this, which is how four defects sat unnoticed
(audit finding, confirmed against Kalshi's docs and by execution):
  * the signature appended the request body -- GETs have none, so reads
    worked, but every order POST would have been rejected (401);
  * the body (market_id, action, side, type, integer price) matched no Kalshi
    schema;
  * Kalshi's success code for a created order, 201, raised as an error, so a
    real fill was reported as a failure and its reservation released;
  * POSTs were re-sent on timeouts and 5xx, which can fill one order twice.
"""

import base64

import pytest
from core.network import KalshiAPIError, KalshiClient, kalshi_order_body
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class TestTheOrderBody:
    @pytest.mark.parametrize(
        "side,action,price,expect_side,expect_price",
        [
            ("yes", "buy", 40, "bid", "0.4000"),  # buy YES = YES bid
            ("no", "buy", 30, "ask", "0.7000"),  # buy NO at 30c = sell YES at 70c
            ("yes", "sell", 1, "ask", "0.0100"),  # close YES
            ("no", "sell", 1, "bid", "0.9900"),  # close NO = buy YES at 99c
        ],
    )
    def test_sides_map_onto_the_yes_book(self, side, action, price, expect_side, expect_price):
        body = kalshi_order_body("KXA", side, price, 5, action)
        assert body["side"] == expect_side
        assert body["price"] == expect_price
        assert body["count"] == "5.00"

    def test_closes_are_reduce_only_and_entries_are_not(self):
        assert kalshi_order_body("KXA", "no", 1, 5, "sell")["reduce_only"] is True
        assert "reduce_only" not in kalshi_order_body("KXA", "yes", 40, 5, "buy")

    def test_orders_never_rest_and_carry_an_identity(self):
        a = kalshi_order_body("KXA", "yes", 40, 5, "buy")
        b = kalshi_order_body("KXA", "yes", 40, 5, "buy")
        assert a["time_in_force"] == "immediate_or_cancel"
        assert a["client_order_id"] and a["client_order_id"] != b["client_order_id"]


def test_the_signature_is_timestamp_method_path_only():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client = KalshiClient.__new__(KalshiClient)
    client.private_key = key
    client.key_id = "kid"

    headers = client._get_headers("POST", "/portfolio/events/orders")

    signed = f"{headers['KALSHI-ACCESS-TIMESTAMP']}POST/trade-api/v2/portfolio/events/orders"
    key.public_key().verify(
        base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"]),
        signed.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )


class _Resp:
    def __init__(self, status, body=None):
        self.status = status
        self._body = body or {}

    async def json(self, content_type=None):
        return self._body

    async def text(self):
        return str(self._body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


class _Session:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.sent = 0

    def request(self, method, url, **_kwargs):
        self.sent += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _client(outcomes):
    client = KalshiClient.__new__(KalshiClient)
    client.private_key = None
    client.base_url = "https://example.invalid/trade-api/v2"
    session = _Session(outcomes)

    async def get_session():
        return session

    client.get_session = get_session
    return client, session


@pytest.mark.network_internals
class TestTheTransport:
    @pytest.mark.asyncio
    async def test_201_is_success(self):
        client, _ = _client([_Resp(201, {"order_id": "o-1", "fill_count": "5.00"})])
        assert (await client.request("POST", "/portfolio/events/orders", json_data={}))[
            "order_id"
        ] == "o-1"

    @pytest.mark.asyncio
    async def test_a_post_is_not_resent_after_a_timeout(self, monkeypatch):
        import core.network

        async def no_sleep(_s):
            pass

        monkeypatch.setattr(core.network.asyncio, "sleep", no_sleep)
        client, session = _client([TimeoutError(), _Resp(201, {"order_id": "o-2"})])

        with pytest.raises(RuntimeError):
            await client.request("POST", "/portfolio/events/orders", json_data={})
        assert session.sent == 1, "an ambiguous POST must surface, not be re-sent"

    @pytest.mark.asyncio
    async def test_a_post_is_not_resent_after_a_5xx(self, monkeypatch):
        import core.network

        async def no_sleep(_s):
            pass

        monkeypatch.setattr(core.network.asyncio, "sleep", no_sleep)
        client, session = _client([_Resp(502), _Resp(201, {"order_id": "o-3"})])

        with pytest.raises(KalshiAPIError):
            await client.request("POST", "/portfolio/events/orders", json_data={})
        assert session.sent == 1

    @pytest.mark.asyncio
    async def test_reads_still_retry(self, monkeypatch):
        import core.network

        async def no_sleep(_s):
            pass

        monkeypatch.setattr(core.network.asyncio, "sleep", no_sleep)
        client, session = _client([_Resp(503), _Resp(200, {"balance": 1})])

        assert await client.request("GET", "/portfolio/balance") == {"balance": 1}
        assert session.sent == 2


class _Placer:
    """A client whose place_order answers like Kalshi V2 (fill_count as a string)."""

    def __init__(self, reply):
        self.reply = reply

    async def place_order(self, **_kwargs):
        return self.reply


async def _vault():
    from core.vault import RecursiveVault

    v = RecursiveVault(test_mode=True)
    v.HARD_FLOOR_CENTS = 0
    await v.initialize(100_000)
    return v


class TestWhatFilledIsWhatIsRecorded:
    @pytest.mark.asyncio
    async def test_no_fill_releases_the_reservation(self):
        from agents.hand.execution import execute_order

        vault = await _vault()
        reply = {"order_id": "o", "fill_count": "0.00", "remaining_count": "0.00"}

        result = await execute_order(_Placer(reply), vault, "KXA", 50, 1000, 10_000)

        assert result["success"] is False
        assert vault._reserved_funds == 0

    @pytest.mark.asyncio
    async def test_a_partial_fill_confirms_only_what_filled(self):
        from agents.hand.execution import execute_order

        vault = await _vault()
        reply = {"order_id": "o", "fill_count": "8.00", "remaining_count": "0.00"}

        result = await execute_order(_Placer(reply), vault, "KXA", 50, 1000, 10_000)

        assert result == {"success": True, "order_id": "o", "stake": 400}
        assert vault._reserved_funds == 0

    @pytest.mark.asyncio
    async def test_the_order_id_is_kept(self):
        from agents.hand.execution import execute_order

        vault = await _vault()
        reply = {"order_id": "o-9", "fill_count": "20.00"}

        result = await execute_order(_Placer(reply), vault, "KXA", 50, 1000, 10_000)

        assert result["order_id"] == "o-9" and result["stake"] == 1000
