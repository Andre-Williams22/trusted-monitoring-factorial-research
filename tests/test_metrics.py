"""Tests for the metric layer.

The point of these is not coverage. It is to pin the two facts that caused
retractions in this project: that AUC degenerates into a detection rate when the
honest distribution is constant, and that TPR-at-zero-FPR is an affine rescaling
of AUC in exactly that case. If either stops being true, an analysis that
depends on it should fail loudly.
"""

from __future__ import annotations

import numpy as np
import pytest

from utils import config
from utils.metrics import auc, distinct_values, spearman, tpr_at_zero_fpr


def test_auc_perfect_separation():
    assert auc(np.zeros(10), np.ones(10)) == pytest.approx(1.0)


def test_auc_no_separation_is_chance():
    identical = np.zeros(10)
    assert auc(identical, identical) == pytest.approx(0.5)


def test_auc_credits_ties_at_half():
    # 5 attack samples above, 5 tied with honest -> 0.5 + 0.5*0.5
    honest = np.zeros(10)
    attack = np.r_[np.zeros(5), np.ones(5)]
    assert auc(honest, attack) == pytest.approx(0.75)


def test_auc_matches_closed_form_when_honest_is_constant():
    """The identity that made the AUC column a recall measure: 0.5 + p/2."""
    rng = np.random.default_rng(0)
    honest = np.zeros(100)
    for p in (0.0, 0.13, 0.41, 0.73, 1.0):
        attack = (rng.random(100) < p).astype(float)
        expected = 0.5 + (attack > 0).mean() / 2
        assert auc(honest, attack) == pytest.approx(expected, abs=1e-12)


def test_tpr_at_zero_fpr_is_affine_rescaling_of_auc_when_honest_constant():
    """TPR@0FPR == 2*(AUC - 0.5) exactly. This is why the metric swap changed
    only the cells where the monitor emits nonzero honest scores."""
    rng = np.random.default_rng(1)
    honest = np.zeros(100)
    for _ in range(20):
        attack = (rng.random(100) < rng.random()).astype(float)
        assert tpr_at_zero_fpr(honest, attack) == pytest.approx(2 * (auc(honest, attack) - 0.5))


def test_tpr_charges_a_monitor_for_flagging_honest_code():
    """A monitor with false alarms gets a higher threshold, so it must score
    lower than an otherwise identical monitor with none."""
    attack = np.r_[np.full(50, 0.5), np.zeros(50)]
    clean = tpr_at_zero_fpr(np.zeros(100), attack)
    noisy = tpr_at_zero_fpr(np.r_[np.full(10, 0.5), np.zeros(90)], attack)
    assert clean == pytest.approx(0.5)
    assert noisy == pytest.approx(0.0)
    assert noisy < clean


def test_tpr_mask_restricts_to_landed_attacks():
    attack = np.r_[np.ones(50), np.zeros(50)]
    landed = np.r_[np.zeros(50, dtype=bool), np.ones(50, dtype=bool)]
    assert tpr_at_zero_fpr(np.zeros(100), attack) == pytest.approx(0.5)
    assert tpr_at_zero_fpr(np.zeros(100), attack, landed) == pytest.approx(0.0)


def test_tpr_with_empty_mask_is_nan():
    empty = np.zeros(10, dtype=bool)
    assert np.isnan(tpr_at_zero_fpr(np.zeros(10), np.ones(10), empty))


def test_spearman_is_rank_based():
    assert spearman([1, 2, 3, 4], [10, 200, 3000, 40000]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_distinct_values_detects_a_degenerate_distribution():
    assert distinct_values(np.zeros(100)) == 1
    assert distinct_values(np.r_[np.zeros(90), np.full(10, 0.1)]) == 2
