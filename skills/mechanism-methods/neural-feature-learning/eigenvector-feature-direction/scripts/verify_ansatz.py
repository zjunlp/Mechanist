#!/usr/bin/env python3
"""Compare a supplied layer's feature matrix with its empirical gradient matrix.

This helper measures uncentered Frobenius alignment of W.T @ W and
E[g @ g.T]. It does not reproduce the full DNFA experiments or compute gradients
for the caller. Supply gradients in the input coordinates of this weight matrix.
"""
import torch

def matrix_alignment(weight, input_gradients):
    """Return alignment for weight [out, in] and gradients [samples, in]."""
    if weight.ndim != 2 or input_gradients.ndim != 2:
        raise ValueError("Expected two matrices.")
    if weight.shape[1] != input_gradients.shape[1] or len(input_gradients) == 0:
        raise ValueError("Gradient coordinates must match the weight input dimension.")
    w = weight.detach().to(dtype=torch.float64)
    g = input_gradients.detach().to(device=w.device, dtype=w.dtype)
    nfm = w.T @ w
    egop = g.T @ g / len(g)
    denominator = torch.linalg.vector_norm(nfm) * torch.linalg.vector_norm(egop)
    if not torch.isfinite(denominator) or denominator == 0:
        raise ValueError("Alignment is undefined for zero or nonfinite matrices.")
    return ((nfm * egop).sum() / denominator).item()

if __name__ == "__main__":
    raise SystemExit("Import matrix_alignment and supply actual weights and matched input gradients.")
