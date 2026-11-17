# Training and execution

Process health and training quality differ. A live process does not establish learning; decreasing loss does not establish a behavioral claim. Inspect held-out behavior as well as loss, learning rate, gradient norms, and resource use.

NaN, sustained divergence, and severe regression motivate diagnosis. Noisy or flat early curves may be normal. An unreachable dashboard or log is a connectivity problem, not evidence of failure.

Learning rate, adapter capacity, target modules, objective, and data quality can all matter. Targeted sweeps can distinguish optimization issues from behavioral nulls. Values copied from other models may not transfer. Select the next knob from evidence rather than always sweeping learning rate first or repeating until the claim succeeds.

For local or SSH execution, establish the environment, working directory, authorized resources, and input paths. Confirm launch and completion separately. Exit status, logs, and outputs are complementary evidence; a stale file does not prove a new run succeeded. Choose storage appropriate to the task without a required naming or tracking protocol.

Visible hardware does not imply authorization to occupy every GPU or provision resources.
