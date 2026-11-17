# Image preprocessing

`Resize(256)` preserves aspect ratio by resizing the short side; `Resize((256, 256))` forces a square. A subsequent center crop selects different pixels for non-square inputs. This can alter top activations, descriptions, and attribution while outputs remain plausible.

Match the intended weights or reference experiment. Native processors, timm configurations, CLIP, classic ResNet evaluation, and torchvision V2 weights can use different conventions. Shared transforms are appropriate for deliberate matched-pixel comparisons, not a universal interpretability default.

Check interpolation, antialiasing, crop size, channels, normalization, and training augmentation leaking into evaluation. If preprocessing is ambiguous, assess relevant sensitivity. Align reference-image selection and intervention measurements.

For component-to-concept vectors, consider activating images, relevant-region crops, and semantic embedding. The [multimodal family](../mechanism-methods/multi-modal/SKILL.md) describes combining CRP with CLIP-Dissect and when either alone is useful.
