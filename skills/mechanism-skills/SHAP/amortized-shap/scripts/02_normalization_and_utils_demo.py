#!/usr/bin/env python3
"""
FastSHAP Normalization & Utilities Demo
========================================
Demonstrates the low-level normalization functions and utility helpers
provided by FastSHAP:

  - additive_efficient_normalization
  - multiplicative_efficient_normalization
  - evaluate_explainer
  - MarginalImputer and BaselineImputer usage
  - Surrogate.generate_labels helper

These are the building blocks used internally by FastSHAP.train() and
can be useful when building custom