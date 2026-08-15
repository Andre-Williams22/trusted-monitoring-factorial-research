"""Registry integrity.

Every script used to carry its own copy of the tier/family tables and they
drifted. These tests exist so that a single edit to utils/config.py cannot
silently desynchronise the runner from the analysis.
"""

from __future__ import annotations

from utils import config


def test_every_model_has_a_complete_record():
    for model in config.MODELS:
        assert model.key and model.inspect_id and model.label
        assert model.tier in config.TIER_ORDER
        assert model.provider == model.provider.lower()


def test_keys_are_unique():
    keys = [m.key for m in config.MODELS]
    assert len(keys) == len(set(keys))


def test_derived_lookups_agree_with_the_registry():
    for model in config.MODELS:
        assert config.TIER[model.key] == model.tier
        assert config.FAMILY[model.key] == model.family
        assert config.LABEL[model.key] == model.label
        assert config.INSPECT_ID[model.key] == model.inspect_id


def test_strong_and_weak_match_the_published_design():
    """These three pairs define the attacker rows and the cross-family cells.
    The published results depend on them, so they are pinned."""
    assert config.STRONG == {"openai": "gpt55", "anthropic": "opus48", "google": "geminipro"}
    assert config.WEAK == {"openai": "gpt41mini", "anthropic": "haiku45", "google": "flashlite"}


def test_each_closed_provider_has_a_full_three_tier_ladder():
    for provider in ("openai", "anthropic", "google"):
        tiers = {m.tier for m in config.MODELS if m.provider == provider}
        assert tiers == {"weak", "mid", "strong"}, provider


def test_qwen_is_the_cross_lineage_reference():
    qwen = config.BY_KEY["qwen"]
    assert qwen.family not in {m.family for m in config.MODELS if m.key != "qwen"}
