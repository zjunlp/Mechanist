#!/usr/bin/env python3
"""Additive efficiency normalization for supplied Shapley estimates.

For values [..., features, outputs], distribute the residual needed for the
values to sum to prediction minus the selected empty-coalition prediction.
Meeting this algebraic constraint alone does not validate an explanation.
"""
import numpy as np

def normalize_efficiency(values, prediction, baseline):
    values = np.asarray(values, dtype=float)
    if values.ndim < 2 or values.shape[-2] == 0:
        raise ValueError("Expected [..., features, outputs] with at least one feature.")
    target = np.asarray(prediction) - np.asarray(baseline)
    residual = target - values.sum(axis=-2)
    return values + np.expand_dims(residual / values.shape[-2], axis=-2)

if __name__ == "__main__":
    raise SystemExit("Import normalize_efficiency with your actual values, predictions, and baseline.")
