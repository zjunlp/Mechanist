---
name: finetune-hyperparameter-sweep
description: 'Fine-tuning LR protocol — full FT, LoRA / QLoRA / DoRA / PEFT adapter, across SFT, DPO, and GRPO / PPO / RL objectives. Fires on ANY fine-tune, including (especially) when the plan already fixes a learning rate or copies one from a reference paper: a fixed LR is one grid point, never the answer, so LR is always swept over a wide range. The only test of an LR is whether the run hits the pass criteria in `task.md` or the milestone''s own claim criteria — loss, grad norm, and reward curves are never acceptance evidence, no matter how good they look. Criteria not met = change LR and re-run. Triggers: `learning_rate`, `SFTTrainer`, `DPOTrainer`, `GRPOTrainer`, `LoraConfig`, `peft_config`, `full fine-tune`, `SFT`, `DPO`, `GRPO`, `RLHF`, `QLoRA`, `DoRA`, `PEFT`, `adapter`.'
---

## Host compatibility

Before acting on a historical host tool name, read and apply the bundled `shared-references/host-compatibility.md`. Use the active host capability by meaning; never fabricate or call an unavailable literal tool name.

# Fine-Tuning LR Sweep

1. **Any fine-tune → always sweep LR over a wide range.** Whether the plan hard-codes an LR, copies one from a paper, or leaves it open makes no difference: that value is one grid point, never the answer.

2. **The only test of an LR is the criteria** — the pass criteria in `task.md`, or the claim criteria of the relevant experiment-plan milestone. Nothing else counts as acceptance evidence: a converged loss, a healthy grad norm, a rising reward, a "reasonable-looking" curve certify nothing. Criteria not met = LR not acceptable, no matter how good the training curves look.

3. **Criteria not met → change LR and re-run.** Keep going until an LR passes. Only after the whole LR range has failed should you touch anything else.
