"""The engine must be able to reach Kalshi's demo environment.

A previous change removed demo mode "for production security" and hardcoded
`api.kalshi.co` as the only base URL. The effect was the opposite of security:
demo credentials cannot authenticate against the production host, so there was
no way to make a first connection, or run a paper soak against a real venue,
without pointing real credentials at real markets.

These tests fix the safe default in place. `KALSHI_ENV` unset means demo.
"""
import pytest

from core.network import KalshiClient


def _client(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    return KalshiClient()


@pytest.fixture(autouse=True)
def _clear_kalshi_env(monkeypatch):
    for var in (
        "KALSHI_ENV",
        "KALSHI_DEMO_KEY_ID", "KALSHI_DEMO_PRIVATE_KEY",
        "KALSHI_PROD_KEY_ID", "KALSHI_PROD_PRIVATE_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def test_defaults_to_demo(monkeypatch):
    """Unset must mean demo. A missing setting costs play money, not real money."""
    client = _client(
        monkeypatch, KALSHI_DEMO_KEY_ID="demo-id", KALSHI_DEMO_PRIVATE_KEY="not-a-key"
    )

    assert client.env == "demo"
    assert client.base_url == "https://demo-api.kalshi.co/trade-api/v2"


def test_production_requires_asking_for_it_by_name(monkeypatch):
    client = _client(
        monkeypatch,
        KALSHI_ENV="prod",
        KALSHI_PROD_KEY_ID="prod-id",
        KALSHI_PROD_PRIVATE_KEY="not-a-key",
    )

    assert client.base_url == "https://api.kalshi.co/trade-api/v2"


def test_demo_will_not_fall_back_to_production_credentials(monkeypatch):
    """Production keys must not satisfy a demo connection.

    Falling back between the two would authenticate against the wrong venue --
    at best a confusing failure, at worst real credentials on an unintended host.

    These are two separate tests rather than two blocks in one, because
    monkeypatch does not undo between statements: setting the production pair in
    the first block would leave it set for the second, which is exactly the
    fall-back this test claims does not happen.
    """
    with pytest.raises(ValueError, match="KALSHI_DEMO_KEY_ID"):
        _client(
            monkeypatch,
            KALSHI_PROD_KEY_ID="prod-id",
            KALSHI_PROD_PRIVATE_KEY="not-a-key",
        )


def test_production_will_not_fall_back_to_demo_credentials(monkeypatch):
    with pytest.raises(ValueError, match="KALSHI_PROD_KEY_ID"):
        _client(
            monkeypatch,
            KALSHI_ENV="prod",
            KALSHI_DEMO_KEY_ID="demo-id",
            KALSHI_DEMO_PRIVATE_KEY="not-a-key",
        )


def test_a_typo_is_refused_rather_than_guessed(monkeypatch):
    """'production' is not 'prod'. Guessing which was meant is how you trade live by accident."""
    with pytest.raises(ValueError, match="KALSHI_ENV must be one of"):
        _client(
            monkeypatch,
            KALSHI_ENV="production",
            KALSHI_PROD_KEY_ID="prod-id",
            KALSHI_PROD_PRIVATE_KEY="not-a-key",
        )


def test_missing_private_key_names_the_variable(monkeypatch):
    with pytest.raises(ValueError, match="KALSHI_DEMO_PRIVATE_KEY"):
        _client(monkeypatch, KALSHI_DEMO_KEY_ID="demo-id")
