"""Shared library for the trusted-monitoring factorial.

Scripts under ``scripts/`` are thin CLIs; the logic lives here.

    config   model registry (tier / family / label) and paths
    metrics  AUC, TPR at zero FPR, rank correlation - no sklearn or scipy
    data     cell loading with an on-disk score cache
    stats    variance decomposition, bootstrap intervals, permutation tests
    viz      shared matplotlib styling and the validated tier ramp
"""

from utils import config, data, metrics, stats, viz

__all__ = ["config", "data", "metrics", "stats", "viz"]
