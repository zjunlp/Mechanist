# Fine-Tuning LR Sweep

1. **Any fine-tune → always sweep LR over a wide range.** Whether the plan hard-codes an LR, copies one from a paper, or leaves it open makes no difference: that value is one grid point, never the answer.

2. **The only test of an LR is the criteria** — the user's target behavior or the success criteria of the experiment. Nothing else counts as acceptance evidence: a converged loss, a healthy grad norm, a rising reward, a "reasonable-looking" curve certify nothing. Criteria not met = LR not acceptable, no matter how good the training curves look.

3. **Criteria not met → change LR and re-run.** Keep going until an LR passes. Only after the whole LR range has failed should you touch anything else.

A fixed LR copied from another model, paper, or earlier run is a useful candidate, not evidence that the current fine-tune is well configured. Use the actual downstream behavior to choose among rates; a healthy training curve alone does not show that the behavior was learned.

If the LR range does not produce a working fine-tune, continue diagnosing capacity (LoRA rank / scaling), target modules, training steps, effective batch size, objective, and data quality. A model that never learned the intended behavior is not a sound basis for explaining why that behavior exists or how it transfers.

Carry out the search within the user's resource authorization. If resources prevent continuing, explain which tuning questions remain open; do not turn an unsuccessful fine-tune into a conclusion that the proposed behavior is absent. For the distinction between training dynamics and behavioral success, see [training and execution](training-and-execution.md).
