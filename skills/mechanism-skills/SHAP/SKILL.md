---
name: SHAP
description: SHAP (SHapley Additive exPlanations) is a unified, game-theoretic framework for local feature attribution. Treating a model's input features as players in a coalition game, SHAP assigns each feature its Shapley value — the average marginal contribution of that feature to the prediction across all possible feature subsets. Shapley values are the unique attributions satisfying local accuracy, missingness, and consistency, so the prediction decomposes additively into a baseline plus one Shapley value per feature, giving a per-prediction explanation that is theoretically grounded and model-agnostic.
---

## Advantage

SHAP unifies several previously ad-hoc attribution methods (LIME, DeepLIFT, Layer-wise Relevance Propagation, classic Shapley value methods such as Shapley regression and Shapley sampling) under one axiomatic framework, so attributions from different model families can be compared on the same scale. The decomposition is local — it explains a single prediction — yet averaging the absolute Shapley values over a dataset yields a global feature-importance ranking that inherits the same axiomatic foundation, supporting both per-instance debugging and dataset-level summaries. For tree ensembles, an exact polynomial-time estimator removes the usual exponential cost, making SHAP the de-facto standard for explaining XGBoost / LightGBM / CatBoost / scikit-learn tree models.

## Limitation

Computing exact Shapley values for an arbitrary model is exponential in the number of features, so practical use relies on estimators (KernelSHAP, sampling, deep- or gradient-based variants) whose accuracy depends on the number of samples / coalitions and on assumptions about how "missing" features should be modelled (typically marginal- vs conditional-expectation). The values themselves are *correlational* — they describe how the model uses features, not whether those features are causally related to the outcome — and additive decomposition can obscure strong feature interactions, which require interaction-aware Shapley extensions to surface.

## Submethods

The toolkit comprises two forms — per-sample estimators that compute Shapley values one input at a time, and amortized explainers that learn to predict them in a single forward pass:

- **Foundational and Estimator-based SHAP**:
The reference SHAP library covers the full taxonomy of Shapley estimators — model-agnostic (KernelSHAP), exact tree-specific (TreeSHAP), deep-learning (DeepExplainer / GradientExplainer for TensorFlow, Keras, PyTorch), and linear models — together with the standard plotting suite (waterfall, beeswarm, force, dependence) and interaction extensions. It is the right starting point for explaining any single model and serves as the reference implementation against which downstream methods are compared.
You can find a demo for this method in ./foundational-and-estimator-based-shap. This demo shows shap: Use this skill when working with SHAP (SHapley Additive exPlanations) to explain machine learning model predictions, compute feature importance, generate SHAP values for tree ensembles (XGBoost, LightGBM, CatBoost, scikit-learn), deep learning models (TensorFlow, Keras, PyTorch), NLP transformers, or any model-agnostic function.

- **Amortized SHAP (FastSHAP)**:
FastSHAP trains an auxiliary explainer network with a KernelSHAP-inspired objective so that, at inference time, a *single forward pass* through the explainer produces Shapley values for any input — turning per-sample optimization into amortized prediction. This makes Shapley-style attributions tractable in real-time settings (interactive UIs, streaming pipelines, image/superpixel explanations) and at data scales where running KernelSHAP per sample is prohibitive.
You can find a demo for this method in ./amortized-shap. This demo shows fastshap: Use this skill when you need to train amortized Shapley value explainers using FastSHAP, generate real-time local feature importance explanations for machine learning models (tabular or image), train surrogate models for feature masking, or understand how FastSHAP's KernelSHAP-inspired training objective works with PyTorch.
