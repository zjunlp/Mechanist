# Training and execution

## Training quality and process health are different

A live process or an occupied GPU does not establish useful learning. Process health asks whether the session is alive and work is happening; training quality asks whether optimization and held-out behavior are progressing. A decreasing loss does not by itself establish the behavioral claim.

Useful signals while training include:

- **Loss trend:** is it decreasing across checkpoints, flat, or diverging?
- **Held-out behavior:** is the target behavior improving, and are unrelated capabilities preserved?
- **NaN / Inf:** do loss, gradients, or activations become nonfinite?
- **Spikes:** are large jumps transient noise or a sustained change?
- **Learning rate:** is the intended schedule actually being used?
- **Gradient norm:** are gradients exploding, vanishing, or unexpectedly absent?

## Interpreting the signals

| Signal | What it suggests | Useful response |
| --- | --- | --- |
| NaN / Inf or sustained loss divergence | A numerical, optimization, or data problem | Diagnose the objective, precision, gradients, learning rate, and inputs before spending more compute on the same failure |
| Held-out metrics severely regress | Overfitting, a bad objective, or capability damage | Compare with the baseline and inspect actual outputs; revise the training setup |
| Loss decreases and held-out behavior improves | Training is making useful progress | Continue and inspect less frequently as the run stabilizes |
| Loss is flat or metrics are noisy | Possibly normal early dynamics, possibly ineffective optimization | Look across multiple checkpoints and compare learning rate, gradients, data, and downstream behavior |
| Logs or a dashboard cannot be reached | A connectivity problem | Recover access or use another available output source; do not infer that training failed |

Do not stop on the first noisy checkpoint. Some loss spikes and flat early curves are normal. If the interpretation remains unclear, [consult another model](../model-consultation/SKILL.md) with the actual recent metrics, baseline, training stage, and the specific uncertainty. Ask whether to continue, diagnose a concrete fault, or wait for more evidence; the external model cannot inspect a dashboard or local path that you merely name.

The original monitoring recipe starts with checks about every 10 minutes and spaces them to 20, 30, then 60 minutes when consistently healthy. Use that as a practical starting point for long runs, adapting to run duration and checkpoint frequency. No timer, service, or fixed monitoring workflow is required.

## When the run looks healthy but the behavior did not learn

Read the [fine-tuning LR sweep advice](finetune-hyperparameter-sweep.md). Converged loss, healthy gradient norms, and rising reward are not substitutes for the user's behavioral success criteria. A learning rate copied from a paper is a candidate to search around, not a settled choice.

Try the LR range before concluding that a fine-tune does not work. If it still fails, investigate adapter capacity, target modules, training duration, effective batch size, objective, and data quality. For example, a low-rank adapter that does not reach the relevant modules may show a decreasing training loss without learning the desired transfer. An objective can improve a proxy while missing the target behavior. Neither situation establishes that the desired behavior is impossible.

## Working through execution failures

For local or SSH work, establish the actual environment, working directory, input paths, and authorized resources. Common failures have concrete remedies:

- **OOM:** reduce the microbatch, preserve effective batch with accumulation when needed, use gradient checkpointing, or choose compatible sharding/offload within the authorized devices.
- **Import error:** inspect the selected Python environment and install or resolve the missing compatible dependency there.
- **Missing input:** locate the actual model/data or correct the path rather than silently replacing it with a different scientific setting.
- **Shape or hook error:** inspect the model's real module structure, tuple outputs, padding, and tensor dimensions; templates may target another model family.
- **NaN / divergence:** inspect data, objective, precision, and learning rate instead of merely relaunching the same configuration.

If a fix fails, use the new traceback and outputs to refine the diagnosis. Consult source documentation, an existing compatible implementation, or an external model when stuck. Do not give up on a fixable implementation problem and report it as a scientific negative. Continue within the user's resource authorization; if that boundary prevents further work, explain the remaining technical obstacle.

Visible hardware does not imply authorization to occupy every GPU or provision resources.
