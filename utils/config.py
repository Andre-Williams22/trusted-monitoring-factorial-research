"""Single source of truth for the model registry and shared paths.

Every script previously carried its own copy of the tier/family/label tables,
under four different names. They drifted. This module owns them; nothing else
should define a model constant.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# --------------------------------------------------------------------------
# model registry
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Model:
    """One model, in both its runtime and its analysis identity.

    `key` is the short token used in log paths (``atk-gpt55__mon-haiku45__n100``),
    `inspect_id` is what actually gets called, `label` is the display name used
    in tables and figures, and `provider` is the lowercase routing key.
    """

    key: str
    inspect_id: str
    label: str
    family: str  # display name: OpenAI | Anthropic | Google | Qwen
    provider: str  # routing key: openai | anthropic | google | qwen
    tier: str  # weak | mid | strong


# Google models route via OpenRouter: the direct AI Studio API hit a per-project
# DAILY quota (a 429 with 30x1800s backoff, i.e. an overnight stall that looks
# exactly like slowness), and gemini-2.5-pro / gemini-3-pro-preview 404 for new
# accounts there. Qwen is monitor-only and never an attacker; override its id
# with QWEN_MODEL and verify with a LIMIT=2 smoke test before a full run.
MODELS: tuple[Model, ...] = (
    Model("gpt41mini", "openai/gpt-4.1-mini-2025-04-14", "gpt-4.1-mini", "OpenAI", "openai", "weak"),
    Model("gpt54mini", "openai/gpt-5.4-mini", "gpt-5.4-mini", "OpenAI", "openai", "mid"),
    Model("gpt55", "openai/gpt-5.5", "gpt-5.5", "OpenAI", "openai", "strong"),
    Model("haiku45", "anthropic/claude-haiku-4-5", "claude-haiku-4-5", "Anthropic", "anthropic", "weak"),
    Model("sonnet5", "anthropic/claude-sonnet-5", "claude-sonnet-5", "Anthropic", "anthropic", "mid"),
    Model("opus48", "anthropic/claude-opus-4-8", "claude-opus-4-8", "Anthropic", "anthropic", "strong"),
    Model("flashlite", "openrouter/google/gemini-3.1-flash-lite", "gemini-3.1-flash-lite", "Google", "google", "weak"),
    Model("flash", "openrouter/google/gemini-3.5-flash", "gemini-3.5-flash", "Google", "google", "mid"),
    Model("geminipro", "openrouter/google/gemini-3.1-pro-preview", "gemini-3.1-pro", "Google", "google", "strong"),
    Model("qwen", os.environ.get("QWEN_MODEL", "openrouter/qwen/qwen-2.5-72b-instruct"),
          "Qwen-2.5-72B", "Qwen", "qwen", "strong"),
)

BY_KEY: dict[str, Model] = {m.key: m for m in MODELS}
TIER: dict[str, str] = {m.key: m.tier for m in MODELS}
FAMILY: dict[str, str] = {m.key: m.family for m in MODELS}
LABEL: dict[str, str] = {m.key: m.label for m in MODELS}
INSPECT_ID: dict[str, str] = {m.key: m.inspect_id for m in MODELS}
PROVIDER: dict[str, str] = {m.key: m.provider for m in MODELS}

TIER_ORDER: dict[str, int] = {"weak": 0, "mid": 1, "strong": 2}

#: Strongest and weakest model per provider - the attacker choices and the
#: cross-family monitor pairings are built from these.
STRONG = {m.provider: m.key for m in MODELS if m.tier == "strong" and m.provider != "qwen"}
WEAK = {m.provider: m.key for m in MODELS if m.tier == "weak"}

# --------------------------------------------------------------------------
# analysis conventions
# --------------------------------------------------------------------------

#: Suspicion score column emitted by control_arena's samples_df.
SUSPICION_COL = "score_max_suspicion_scorer"

#: A cell whose attacker never lands a working backdoor carries no signal - its
#: AUC pins at chance and it would dominate any pooled fit. Cells below this many
#: successful attacks are dropped from every comparative analysis.
MIN_SUCCESSFUL_ATTACKS = 5

#: Fraction of the expected sample count a cell must reach to count as complete.
COMPLETENESS_TOLERANCE = 0.99


def limit() -> int:
    """Samples per mode (honest / attack). 100 for the funded runs."""
    return int(os.environ.get("LIMIT", "100"))


def log_root() -> str:
    return os.environ.get("LOG_ROOT", "logs/monitor_exp")


def figure_dir() -> str:
    return os.environ.get("FIG_DIR", "figures")


def score_cache() -> str:
    """Parsing .eval transcripts is slow; raw scores are cached here."""
    return os.environ.get("SCORE_CACHE", ".score_cache.pkl")


def bootstrap_draws() -> int:
    return int(os.environ.get("BOOTSTRAP", "4000"))
