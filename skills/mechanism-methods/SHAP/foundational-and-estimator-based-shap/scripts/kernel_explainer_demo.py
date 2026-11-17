#!/usr/bin/env python3
"""KernelSHAP demonstration on held-out Iris examples, not a research finding.

Dependencies: numpy, scikit-learn, shap. Background samples come from training
data; explained samples are held out. Choose a task-appropriate background for
real use: it defines the missing-feature reference distribution.
"""
def main():
    import numpy as np
    import shap
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split
    from sklearn.svm import SVC
    x, y = load_iris(return_X_y=True)
    x_train, x_test, y_train, _ = train_test_split(x, y, test_size=0.2, stratify=y, random_state=0)
    model = SVC(probability=True, random_state=0).fit(x_train, y_train)
    explainer = shap.KernelExplainer(model.predict_proba, x_train[:20])
    values = explainer.shap_values(x_test[:3], nsamples=100)
    print("Iris demonstration; explanation shape:", np.asarray(values).shape)

if __name__ == "__main__":
    main()
