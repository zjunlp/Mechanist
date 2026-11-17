# Feature selection and intervention practice

## Locating and intervening on the target function

**1. Locate the neuron / feature for the target function, then intervene.**

- **If a description already exists** — an SAE feature label / auto-interp description, or a documented neuron function — map the target-function description to the matching feature / neuron index and test it directly. A label is a useful starting point, not proof that the feature controls the behavior.
- **Otherwise, Use a localization method** to find the layer / neuron / feature / circuit that carries the target function.

**2. Intervene/locate on the target behavior only — do not damage general ability.**

Ideally the localization / intervention moves **only** the target behavior and leaves the model's *general ability* intact. General ability refers to model abilities unrelated to the target function. It should be measured using forms appropriate to the model's own task, such as instruction following, PPL, fluency, or off-target QA / reasoning / factual recall. Always measure general ability *in parallel* with the target metric:

- **Full breakdown** — if the model's replies degrade into meaningless / garbled tokens (gibberish), general ability is completely destroyed: the model has been pushed off-distribution, and any movement in the target metric is an artifact, not a localization.
- **Valid result** — the target behavior moves while general ability remains intact or shows only a slight degradation. Report both metrics together; never report the target metric alone.


**3. Feature selection is the biggest driver of success — and the hardest part.**
Expect many tries; treat "find a better set" as the main job of the investigation. Do not mistake a poor candidate set for evidence that the target behavior has no manipulable internal signal. **The data you select features from must be deliberately prepared and designed** — the candidate set can be no better than the data it was mined from. Rules:

- **Behavior-positive, and verified.** The data used to find candidates must actually exhibit the target behavior — checked on the data itself, not assumed from how it was constructed or from a topic / source label.
- **Matched control.** The negative set must differ from the positive set **only** in the target behavior. If the two sets also differ in topic, format, language, length, or template, the features you find are detectors of that confound, not of the behavior.
- **Clean on general ability.** The positive data must be otherwise unremarkable on abilities unrelated to the target behavior (fluent, well-formed, on-distribution). Data that is degenerate elsewhere yields features that encode the degeneracy rather than the behavior.
- **Enough of it, and held out.** Mine candidates on one split and confirm the effect on a disjoint one; a set fitted to the selection inputs stops working the moment the inputs change.
- **Same measurement pipeline as the claim.** The data must be gradeable by the exact metric the claim is stated in — otherwise the candidates are being ranked on a proxy.

**4. Feature set — steering a target feature *set* usually works better than steering a single feature.**

A single feature / neuron usually exerts only limited control over the target behavior. Prefer intervening on a **set** of features — e.g. pick several features from the same layer and steer them jointly. When doing so, follow rules 1, 2 and 3 above.

User instructions take precedence over these defaults. Choose localization and intervention methods that answer the actual research question.

## Token positions and pooling

For a next-token question, the final prompt position is a useful readout. Sequence-level behavior may call for response-token pooling, excluding a shared prompt prefix. Match positions across examples and handle differing lengths, padding, and tokenization. Directions do not automatically transfer between hook points.

## Selecting sites and tuning strength

Read [block / layer selection](steering-block-selection.md) for screening signals, middle-to-late-layer heuristics, multi-layer windows, matched regional controls, and transferring relative depth across models.

Read [coefficient tuning](steering-coefficient-tuning.md) for wide geometric sweeps, local refinement, site-dependent strength, target/capability tradeoffs, and what to try when no coefficient works. These are interlocking choices: fix a candidate site set, tune strength there, and re-tune when changing sites. When diagnosing a failed steer, first consider whether coefficient or site mismatch explains the shortfall before abandoning the feature.

Matched random directions, unrelated features, norm controls, and off-target tasks help distinguish specific control from generic perturbation. Match effective intervention magnitudes and application positions. If random directions perform as well as a learned one, inspect the candidate data, selected features, site, and coefficient: an under-tuned or poorly selected signal can conceal an otherwise workable intervention.

Do not treat your inability to obtain an effect as a settled negative. Continue improving the feature set, position, strength, or method within the authorized resources. If you reach a resource or implementation limit, distinguish that limitation from evidence against the scientific hypothesis.

## SAE interventions

Feature clamping, scaling, decoder-direction addition, full reconstruction replacement, and residual-preserving edits change different things. For example, `h + decode(f_edited) - decode(f)` preserves the original reconstruction residual; replacing `h` with `decode(f_edited)` does not. Check actual bias and normalization conventions. Include reconstruction-only controls when reconstruction affects the outcome.

Compatible released dictionaries can save work. Training a new dictionary, using ICA, or using native activations are alternatives with different costs and evidence limits. Availability should not silently determine the question.
