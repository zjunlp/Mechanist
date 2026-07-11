#!/usr/bin/env python3
"""
SHAP KernelExplainer Demo: Model-Agnostic Explanations for Any Classifier

This script demonstrates how to use SHAP's KernelExplainer to explain
predictions of any model — in this case, a Support Vector Machine (SVM)
trained on the classic Iris dataset. KernelExplainer works with any function
that maps input features to predictions, making it fully model-agnostic.

Covers:
    - Training an S