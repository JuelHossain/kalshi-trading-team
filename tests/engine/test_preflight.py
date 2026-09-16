"""The preflight check must not lie about a machine's readiness.

It is the thing standing between a misconfigured laptop and a confusing
failure at the Kalshi handshake, so its two dangerous outcomes are reporting
ready when something is missing, and printing a secret.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "engine" / "scripts" / "preflight.py"

LEAKED = "993728"
SECRET_KEY_ID = "demo-key-id-shhh"
GOOD_PASSWORD = "a-properly-long-new-password"


@pytest.fixture(scope="module")
def pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()


def _run(env: dict) -> subprocess.CompletedProcess:
    base = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "engine")}
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True, env={**base, **env}, cwd=str(ROOT),
    )


def _configured(pem: str, **overrides) -> dict:
    env = {
        "KALSHI_ENV": "demo",
        "KALSHI_DEMO_KEY_ID": SECRET_KEY_ID,
        "KALSHI_DEMO_PRIVATE_KEY": pem,
        "AUTH_PASSWORD": GOOD_PASSWORD,
        "GHOST_API_KEY": "ghost-key",
        "GEMINI_API_KEY": "gemini-key",
        "IS_PAPER_TRADING": "true",
    }
    env.update(overrides)
    return env


def test_never_prints_a_secret(pem):
    """Anything printed reaches scrollback, shell history and screenshots."""
    result = _run(_configured(pem))

    assert SECRET_KEY_ID not in result.stdout
    assert GOOD_PASSWORD not in result.stdout
    assert "BEGIN RSA PRIVATE KEY" not in result.stdout
    assert "PRIVATE KEY-----" not in result.stdout


def test_reports_ready_only_when_it_is(pem):
    result = _run(_configured(pem))

    assert result.returncode == 0, result.stdout
    assert "Ready." in result.stdout


def test_refuses_the_leaked_password(pem):
    """The whole reason this check exists: a .env still carrying the old value."""
    result = _run(_configured(pem, AUTH_PASSWORD=LEAKED))

    assert result.returncode == 1
    assert "ROTATE IT" in result.stdout
    assert LEAKED not in result.stdout, "it printed the password while warning about it"


@pytest.mark.parametrize(
    "missing",
    ["KALSHI_DEMO_KEY_ID", "KALSHI_DEMO_PRIVATE_KEY", "AUTH_PASSWORD",
     "GHOST_API_KEY", "GEMINI_API_KEY"],
)
def test_every_required_variable_is_actually_required(pem, missing):
    """A check that passes with a credential absent is worse than no check."""
    env = _configured(pem)
    env.pop(missing)

    result = _run(env)

    assert result.returncode == 1, f"reported ready without {missing}"
    assert missing in result.stdout


def test_a_malformed_key_is_distinguished_from_a_missing_one(pem):
    result = _run(_configured(pem, KALSHI_DEMO_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nnope\n"))

    assert result.returncode == 1
    assert "will not parse" in result.stdout


def test_production_is_flagged_not_silently_accepted(pem):
    """Pointing at real money must be visible in the output."""
    result = _run(_configured(
        pem, KALSHI_ENV="prod",
        KALSHI_PROD_KEY_ID="prod-id", KALSHI_PROD_PRIVATE_KEY=pem,
    ))

    assert "REAL MONEY" in result.stdout


def test_a_typo_in_the_venue_is_refused(pem):
    result = _run(_configured(pem, KALSHI_ENV="production"))

    assert result.returncode == 1
    assert "not 'demo' or 'prod'" in result.stdout
