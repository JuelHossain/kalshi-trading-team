"""Every operator-adjustable setting, in one registry, editable at runtime.

The engine used to read its tunables from three places: `core.constants`,
scattered `os.getenv` calls, and class attributes copied from constants at
import time. Nothing could be changed without editing files and restarting,
and the dashboard could only guess at the values.

This module is the single list. Each Setting knows its group, its type,
its default, whether it is a secret, and whether changing it needs a
restart. Values live in the process environment (which `engine/.env`
populates at boot) and are persisted back to that file, so an edit made
from the dashboard survives a restart and a fresh checkout still boots from
`.env.example`.

Live application works in two layers:
  1. `core.constants` module attributes are updated, so any reader that
     does `constants.X` at call time sees the new value.
  2. Registered *appliers* patch objects that copied a value at construction
     (agent class attributes, the vault, the auth manager). main.py
     registers them once the agents exist.
Settings whose readers cannot be patched (API clients built at start-up)
are marked `restart=True`; the update reports them so the dashboard can
offer a restart.

Secrets are never returned. `describe()` reports only whether one is set
and its last four characters, which is enough to tell keys apart.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import set_key, unset_key

Kind = str  # "int" | "float" | "bool" | "text" | "choice" | "secret" | "multiline_secret"


@dataclass(frozen=True)
class Setting:
    """One editable value: where it lives, what shape it has, how it applies."""

    key: str
    group: str
    kind: Kind
    default: Any
    label: str
    help: str
    restart: bool = False
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    unit: str = ""
    order: int = 0


def _s(*args, **kwargs) -> Setting:
    return Setting(*args, **kwargs)


# Order within a group follows list order.
REGISTRY: list[Setting] = [
    # ── Engine ────────────────────────────────────────────────────────────
    _s(
        "KALSHI_ENV",
        "engine",
        "choice",
        "demo",
        "Kalshi environment",
        "demo is play money on the demo exchange; prod is real money. Each has its own keys.",
        restart=True,
        choices=("demo", "prod"),
    ),
    _s(
        "IS_PAPER_TRADING",
        "engine",
        "bool",
        True,
        "Pin paper trading",
        "When on, every cycle is simulated no matter what a client asks for. Turn off only to arm live orders.",
        restart=False,
    ),
    _s(
        "KILL_SWITCH",
        "engine",
        "bool",
        False,
        "Environment kill switch",
        "A second kill switch, read before every cycle. On means no cycle is authorised.",
    ),
    _s(
        "MIN_CYCLE_INTERVAL_SECONDS",
        "engine",
        "int",
        30,
        "Minimum gap between cycles",
        "A cycle requested sooner than this after the last one is refused.",
        minimum=0,
        maximum=3600,
        unit="s",
    ),
    _s(
        "NTFY_TOPIC",
        "engine",
        "text",
        "kalshi-alerts",
        "ntfy.sh topic",
        "Push notification topic for fills. Empty disables notifications.",
    ),
    _s(
        "JSON_LOGS",
        "engine",
        "bool",
        False,
        "JSON console logs",
        "Emit machine-readable log lines on the console instead of the coloured display.",
    ),
    _s(
        "FRONTEND_ORIGIN",
        "engine",
        "text",
        "",
        "Extra allowed origin",
        "Origin (scheme://host:port) allowed to call the API besides localhost:3000.",
        restart=True,
    ),
    # ── Auth ──────────────────────────────────────────────────────────────
    _s(
        "AUTH_PASSWORD",
        "auth",
        "secret",
        "",
        "Dashboard password",
        "Required for every dashboard session. Applies immediately; open sessions stay signed in.",
    ),
    _s(
        "GHOST_API_KEY",
        "auth",
        "secret",
        "",
        "API bearer key",
        "Bearer token for non-public API routes. Applies immediately.",
    ),
    # ── Kalshi ────────────────────────────────────────────────────────────
    _s(
        "KALSHI_DEMO_KEY_ID",
        "kalshi",
        "text",
        "",
        "Demo key id",
        "API key id from the Kalshi demo site.",
        restart=True,
    ),
    _s(
        "KALSHI_DEMO_PRIVATE_KEY",
        "kalshi",
        "multiline_secret",
        "",
        "Demo private key",
        "RSA private key (PEM) matching the demo key id.",
        restart=True,
    ),
    _s(
        "KALSHI_PROD_KEY_ID",
        "kalshi",
        "text",
        "",
        "Production key id",
        "API key id from kalshi.com. Real money.",
        restart=True,
    ),
    _s(
        "KALSHI_PROD_PRIVATE_KEY",
        "kalshi",
        "multiline_secret",
        "",
        "Production private key",
        "RSA private key (PEM) matching the production key id. Real money.",
        restart=True,
    ),
    # ── AI ────────────────────────────────────────────────────────────────
    _s(
        "GEMINI_API_KEY",
        "ai",
        "secret",
        "",
        "Gemini API key",
        "Google AI Studio key the Brain and Soul use.",
        restart=True,
    ),
    _s(
        "GEMINI_MODEL",
        "ai",
        "text",
        "gemini-3.8-flash",
        "Gemini model",
        "Model id for the Brain's estimates. Applies to the next market analysed.",
    ),
    _s(
        "BRAIN_SEARCH_GROUNDING",
        "ai",
        "bool",
        True,
        "Google Search grounding",
        "Let the model search the web before estimating. Off is a comparison arm, not a mode to run in.",
    ),
    _s(
        "OPENROUTER_API_KEY",
        "ai",
        "secret",
        "",
        "OpenRouter API key",
        "Optional fallback when Gemini fails.",
        restart=True,
    ),
    # ── Brain ─────────────────────────────────────────────────────────────
    _s(
        "BRAIN_MIN_EDGE",
        "brain",
        "float",
        0.05,
        "Minimum edge to trade",
        "Expected profit per $1 contract required before a verdict is approved.",
        minimum=-1,
        maximum=1,
        step=0.005,
    ),
    _s(
        "BRAIN_CONFIDENCE_THRESHOLD",
        "brain",
        "float",
        0.85,
        "Confidence floor",
        "The model's self-reported confidence must reach this (0-1) or the market is vetoed.",
        minimum=0,
        maximum=1,
        step=0.01,
    ),
    _s(
        "BRAIN_ESTIMATE_SAMPLES",
        "brain",
        "int",
        3,
        "Estimates per market",
        "Independent estimates drawn per market; the median is used. 1 disables the ensemble.",
        minimum=1,
        maximum=9,
    ),
    _s(
        "BRAIN_MAX_DISAGREEMENT",
        "brain",
        "float",
        0.20,
        "Max disagreement",
        "Veto when the estimates spread wider than this (max minus min probability).",
        minimum=0,
        maximum=1,
        step=0.01,
    ),
    _s(
        "BRAIN_STALE_OPPORTUNITY_SECONDS",
        "brain",
        "float",
        300.0,
        "Stale after",
        "A queued market older than this is refused unanalysed.",
        minimum=10,
        maximum=86400,
        unit="s",
    ),
    # ── Senses ────────────────────────────────────────────────────────────
    _s(
        "SENSES_MIN_VOLUME",
        "senses",
        "int",
        200,
        "Minimum volume",
        "Markets with less traded volume are ignored.",
        minimum=0,
        maximum=10_000_000,
    ),
    _s(
        "SENSES_MAX_SPREAD_CENTS",
        "senses",
        "int",
        8,
        "Maximum spread",
        "Markets quoted wider than this many cents are ignored.",
        minimum=1,
        maximum=99,
        unit="¢",
    ),
    _s(
        "SENSES_MAX_DAYS_TO_CLOSE",
        "senses",
        "int",
        10,
        "Closing within",
        "Only markets closing within this many days are scanned.",
        minimum=1,
        maximum=365,
        unit="d",
    ),
    _s(
        "SENSES_STOCK_BUFFER_SIZE",
        "senses",
        "int",
        30,
        "Stock buffer",
        "How many tradeable markets one scan keeps in memory.",
        minimum=1,
        maximum=500,
    ),
    _s(
        "SENSES_QUEUE_BATCH_SIZE",
        "senses",
        "int",
        10,
        "Queued per cycle",
        "How many markets are handed to the Brain per cycle.",
        minimum=1,
        maximum=100,
    ),
    _s(
        "SENSES_RESCAN_COOLDOWN_SECONDS",
        "senses",
        "int",
        60,
        "Rescan cooldown",
        "When a scan leaves nothing queued, wait this long before scanning again.",
        minimum=0,
        maximum=3600,
        unit="s",
    ),
    _s(
        "SENSES_REQUEUE_AFTER_SECONDS",
        "senses",
        "float",
        21600.0,
        "Requeue after",
        "A market already queued is not queued again for this long.",
        minimum=0,
        maximum=604800,
        unit="s",
    ),
    # ── Hand ──────────────────────────────────────────────────────────────
    _s(
        "HAND_MAX_STAKE_CENTS",
        "hand",
        "int",
        7500,
        "Max stake per trade",
        "Kelly sizing is capped here whatever the edge.",
        minimum=100,
        maximum=1_000_000,
        unit="¢",
    ),
    _s(
        "HAND_KELLY_FRACTION",
        "hand",
        "float",
        0.25,
        "Kelly fraction",
        "Fraction of full Kelly to stake. 0.25 is the usual conservative choice.",
        minimum=0.01,
        maximum=1,
        step=0.05,
    ),
    _s(
        "HAND_STOP_LOSS_PCT",
        "hand",
        "float",
        0.50,
        "Stop loss",
        "Close when the price has fallen this fraction below entry.",
        minimum=0.05,
        maximum=1,
        step=0.05,
    ),
    _s(
        "HAND_TAKE_PROFIT_PCT",
        "hand",
        "float",
        0.80,
        "Take profit",
        "Close when the price has captured this fraction of the move to 100.",
        minimum=0.05,
        maximum=1,
        step=0.05,
    ),
    _s(
        "HAND_EXIT_BEFORE_EXPIRY_HOURS",
        "hand",
        "float",
        2.0,
        "Exit before expiry",
        "Close a losing position this many hours before settlement.",
        minimum=0,
        maximum=168,
        unit="h",
    ),
    # ── Vault ─────────────────────────────────────────────────────────────
    _s(
        "VAULT_PRINCIPAL_CENTS",
        "vault",
        "int",
        30000,
        "Principal",
        "The capital the kill switch and the profit lock measure against.",
        minimum=100,
        maximum=100_000_000,
        unit="¢",
    ),
    _s(
        "HARD_FLOOR_CENTS",
        "vault",
        "int",
        25500,
        "Hard floor",
        "No cycle is authorised while the balance is below this.",
        minimum=0,
        maximum=100_000_000,
        unit="¢",
    ),
    _s(
        "VAULT_KILL_SWITCH_PCT",
        "vault",
        "float",
        0.85,
        "Kill switch at",
        "Trip the kill switch when the balance drops below this fraction of principal.",
        minimum=0.1,
        maximum=1,
        step=0.01,
    ),
    _s(
        "VAULT_PROFIT_THRESHOLD_CENTS",
        "vault",
        "int",
        5000,
        "Profit lock",
        "Once the day's profit reaches this, the principal is locked and only house money trades.",
        minimum=0,
        maximum=100_000_000,
        unit="¢",
    ),
    # ── Queues ────────────────────────────────────────────────────────────
    _s(
        "MAX_EXECUTION_QUEUE_SIZE",
        "queues",
        "int",
        10,
        "Execution queue cap",
        "The Brain pauses analysis while this many verdicts wait for the Hand.",
        minimum=1,
        maximum=100,
    ),
    _s(
        "MAX_OPPORTUNITY_QUEUE_SIZE",
        "queues",
        "int",
        20,
        "Opportunity queue cap",
        "Senses skips a restock while this many markets wait for the Brain.",
        minimum=1,
        maximum=500,
    ),
    _s(
        "RESTOCK_THRESHOLD_VETO_COUNT",
        "queues",
        "int",
        5,
        "Restock after vetoes",
        "After this many vetoes in a row the Brain asks Senses for fresh markets.",
        minimum=1,
        maximum=100,
    ),
    _s(
        "RESTOCK_COOLDOWN_SECONDS",
        "queues",
        "int",
        60,
        "Restock cooldown",
        "Minimum gap between restock requests.",
        minimum=0,
        maximum=3600,
        unit="s",
    ),
    # ── Analytics ─────────────────────────────────────────────────────────
    _s(
        "SUPABASE_URL",
        "analytics",
        "text",
        "",
        "Supabase URL",
        "Optional analytics sink. Blank disables it.",
        restart=True,
    ),
    _s(
        "SUPABASE_KEY",
        "analytics",
        "secret",
        "",
        "Supabase key",
        "Anon key for the analytics sink.",
        restart=True,
    ),
]

GROUPS: dict[str, tuple[str, str]] = {
    "engine": ("Engine", "How and where the engine runs."),
    "auth": ("Access", "Who may open the dashboard and call the API."),
    "kalshi": ("Kalshi", "Exchange credentials. Demo and production are separate accounts."),
    "ai": ("Model", "The forecaster behind the Brain."),
    "brain": ("Brain", "When a market is worth a verdict."),
    "senses": ("Senses", "Which markets are scanned and queued."),
    "hand": ("Hand", "How positions are sized and exited."),
    "vault": ("Vault", "The capital rails."),
    "queues": ("Queues", "Back-pressure between the agents."),
    "analytics": ("Analytics", "Optional telemetry sink."),
}

_BY_KEY: dict[str, Setting] = {s.key: s for s in REGISTRY}
SECRET_KINDS = {"secret", "multiline_secret"}


def _parse_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def coerce(setting: Setting, raw: Any) -> Any:
    """Turn a string (or JSON value) into the setting's typed value, or raise ValueError."""
    if setting.kind == "bool":
        return _parse_bool(raw)
    if setting.kind == "int":
        value = int(float(str(raw).strip()))
    elif setting.kind == "float":
        value = float(str(raw).strip())
    elif setting.kind == "choice":
        value = str(raw).strip().lower()
        if value not in setting.choices:
            raise ValueError(f"{setting.key} must be one of {', '.join(setting.choices)}")
        return value
    else:
        return str(raw)
    if setting.minimum is not None and value < setting.minimum:
        raise ValueError(f"{setting.key} must be at least {setting.minimum}")
    if setting.maximum is not None and value > setting.maximum:
        raise ValueError(f"{setting.key} must be at most {setting.maximum}")
    return value


def _to_env(setting: Setting, value: Any) -> str:
    if setting.kind == "bool":
        return "true" if value else "false"
    return str(value)


@dataclass
class UpdateReport:
    """What a batch update did: applied now, needs a restart, or refused."""

    applied: list[str] = field(default_factory=list)
    restart_required: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "applied": self.applied,
            "restart_required": self.restart_required,
            "errors": self.errors,
        }


class Settings:
    """The live registry: typed reads from the environment, validated writes to `.env`."""

    def __init__(self, env_path: str | os.PathLike | None = None):
        self._env_path: Path | None = Path(env_path) if env_path else None
        self._appliers: dict[str, list[Callable[[Any], None]]] = {}

    @property
    def env_path(self) -> Path | None:
        return self._env_path

    @env_path.setter
    def env_path(self, value: str | os.PathLike | None) -> None:
        # main.py hands over a plain string; a str has no .parent.
        self._env_path = Path(value) if value else None

    # ── reads ──────────────────────────────────────────────────────────
    def spec(self, key: str) -> Setting:
        return _BY_KEY[key]

    def get(self, key: str) -> Any:
        setting = _BY_KEY[key]
        raw = os.environ.get(key)
        if raw is None or raw == "":
            return setting.default
        try:
            return coerce(setting, raw)
        except ValueError:
            return setting.default

    def get_int(self, key: str) -> int:
        return int(self.get(key))

    def get_float(self, key: str) -> float:
        return float(self.get(key))

    def get_bool(self, key: str) -> bool:
        return bool(self.get(key))

    def get_str(self, key: str) -> str:
        return str(self.get(key))

    def describe(self) -> dict:
        """Everything the dashboard needs to render an editor. Secrets are masked."""
        groups: dict[str, dict] = {}
        for setting in REGISTRY:
            title, blurb = GROUPS.get(setting.group, (setting.group, ""))
            group = groups.setdefault(
                setting.group, {"id": setting.group, "title": title, "help": blurb, "settings": []}
            )
            entry: dict[str, Any] = {
                "key": setting.key,
                "kind": setting.kind,
                "label": setting.label,
                "help": setting.help,
                "restart": setting.restart,
                "default": setting.default,
            }
            if setting.choices:
                entry["choices"] = list(setting.choices)
            for attr in ("minimum", "maximum", "step"):
                if getattr(setting, attr) is not None:
                    entry[attr] = getattr(setting, attr)
            if setting.unit:
                entry["unit"] = setting.unit
            if setting.kind in SECRET_KINDS:
                raw = os.environ.get(setting.key, "")
                entry["set"] = bool(raw)
                entry["hint"] = raw.strip()[-4:] if len(raw.strip()) >= 8 else ""
            else:
                entry["value"] = self.get(setting.key)
            group["settings"].append(entry)
        return {
            "groups": list(groups.values()),
            "env_file": str(self.env_path) if self.env_path else None,
        }

    # ── writes ─────────────────────────────────────────────────────────
    def register_applier(self, key: str, fn: Callable[[Any], None]) -> None:
        """Run `fn(value)` after `key` changes, to patch an object that copied the old value."""
        if key not in _BY_KEY:
            raise KeyError(key)
        self._appliers.setdefault(key, []).append(fn)

    def update(self, changes: dict[str, Any]) -> UpdateReport:
        """Validate, persist and apply a batch of changes. Never raises.

        Every key is validated before anything is written, so a batch with
        one bad value changes nothing. Empty secrets are refused: use the
        dedicated clear (value None) to unset one deliberately.
        """
        report = UpdateReport()
        typed: dict[str, Any] = {}
        for key, raw in changes.items():
            setting = _BY_KEY.get(key)
            if setting is None:
                report.errors[key] = "unknown setting"
                continue
            if raw is None:
                typed[key] = None
                continue
            if setting.kind in SECRET_KINDS and str(raw).strip() == "":
                report.errors[key] = "secret cannot be blank; clear it explicitly"
                continue
            try:
                typed[key] = coerce(setting, raw)
            except (TypeError, ValueError) as e:
                report.errors[key] = str(e) or "invalid value"
        if report.errors:
            return report

        for key, value in typed.items():
            setting = _BY_KEY[key]
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = _to_env(setting, value)
            try:
                self._persist(key, None if value is None else os.environ[key])
            except OSError as e:
                # Applied for this process; say plainly that it will not survive a restart.
                report.errors[key] = f"applied now but not saved to {self.env_path}: {e}"
            self._apply_constant(key, value if value is not None else setting.default)
            for fn in self._appliers.get(key, []):
                try:
                    fn(value if value is not None else setting.default)
                except Exception as e:  # an applier must not poison the batch
                    report.errors[key] = f"saved but not applied live: {e}"
            (report.restart_required if setting.restart else report.applied).append(key)
        return report

    def _persist(self, key: str, value: str | None) -> None:
        if self.env_path is None:
            return
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.env_path.exists():
            self.env_path.write_text("", encoding="utf-8")
        if value is None:
            unset_key(str(self.env_path), key)
        else:
            set_key(
                str(self.env_path), key, value, quote_mode="always" if "\n" in value else "auto"
            )

    @staticmethod
    def _apply_constant(key: str, value: Any) -> None:
        """Readers that do `constants.X` at call time see the new value."""
        from core import constants

        if hasattr(constants, key):
            setattr(constants, key, value)


class Live:
    """A class attribute that reads `core.constants.<key>` at access time.

    Agents used to copy a constant into a class attribute at import, which
    froze it for the life of the process. This descriptor keeps the
    attribute's name and lets tests assign an instance override, while an
    unassigned attribute always reflects the current setting.
    """

    def __init__(self, key: str):
        self.key = key
        self.slot = f"_live_{key}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        from core import constants

        if obj is not None and self.slot in obj.__dict__:
            return obj.__dict__[self.slot]
        return getattr(constants, self.key)

    def __set__(self, obj: Any, value: Any) -> None:
        obj.__dict__[self.slot] = value


# The process-wide instance. main.py points it at engine/.env at start-up.
settings = Settings()
