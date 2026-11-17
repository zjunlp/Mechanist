# Research judgment

## Keep the original problem in view

Before choosing or refining a method, identify the bottom-line problem: what technical question must be answered, which bottleneck matters, what is outside the task, and what constraints the user supplied. The success condition is evidence about that problem, not merely a method that produces an attractive number.

Reviewer suggestions can drift toward a different, easier question. Before adopting one, ask: does this still solve the original problem? If a proposed fix changes the object, setting, or behavior being explained, make that change explicit rather than treating it as an ordinary implementation detail. Push back on advice that adds complexity without addressing the bottleneck.

## What makes a question worthwhile

Specific means testable, not tiny. A broad regularity can be valuable if it can be sharpened into a falsifiable statement. Do not force every candidate into a narrow prompt artifact just because that is easier to measure.

Compare an idea with the nearest findings, not merely the nearest topics. For each close work, ask what it actually established and what the proposed result would contradict, extend, or explain. If an expert would already predict the direction, the contribution may instead be the magnitude, mechanism, boundary, or a genuinely different setting; design the investigation to discover that difference.

Ask who changes a decision if the hypothesis is true and who changes one if false. A simple method can reveal an important phenomenon. High-stakes language alone does not make a contribution: if replacing a clinical or legal setting with a neutral one removes the whole contribution, ask what scientific role the original setting actually plays.

For an open direction, look across structural gaps: methods that work in one domain but have not been tested in another, contradictory findings, assumptions nobody has checked, unexplored scales, or missing diagnostic questions. Use the [behavior discovery strategies](behavior-discovery.md) to broaden the search rather than generating many near-duplicates of one framing.

## Prefer the smallest adequate method

Make the technical gap operational:

- Where does the current approach fail?
- Why are obvious fixes such as more data, a larger model, or a longer prompt insufficient?
- What is the smallest intervention that could answer the question or fix the bottleneck?
- Is a more current method genuinely a cleaner fit, or merely fashionable?

Compare plausible routes instead of combining every promising component into a large system. Keep the dominant scientific contribution clear. Reuse compatible models, dictionaries, and implementations where useful; a new module should have a specific role, not just a name.

Make the proposed method concrete where feasibility depends on it: internal objects, data, interfaces, representations, token positions, interventions or losses, trainable versus frozen parts, and inference path. “Add a planner” or “use an SAE” is not yet enough to implement or interpret a method.

## Design comparisons that distinguish explanations

For the question at hand, identify the intended explanation and plausible mundane rivals: decoding, tokenization, formatting, length, leakage, evaluator artifacts, general capability damage, or increased compute. Pair each consequential rival with a comparison that would distinguish it. A list of rivals without corresponding experiments does not resolve them.

For example, if steering changes a target response rate, ask whether the same change appears under matched random directions, whether responses remain coherent, and whether an unrelated behavior shifts as well. Those comparisons distinguish a specific control signal from generic perturbation more directly than adding many unrelated benchmarks.

For each useful comparison, make clear what changes, what stays matched, which observation would favor each explanation, and what remains unresolved. Baselines should be credible and comparable. A few strong comparisons usually teach more than a long list of weak ones.

## Ablations that teach something

A component ablation should answer a concrete question. Useful questions include:

- Does removing or replacing this component change the behavior attributed to it?
- Would a simpler alternative produce the same effect?
- Is an apparent gain explained by extra capacity, training data, compute, or search?
- Is the component actually different from the baseline, or is the proposed ablation a no-op?

Think through outcomes before running the comparison. If removing a component changes nothing, that can reveal redundancy or unnecessary complexity. If removal also destroys general ability, it does not isolate the component's specific contribution. Match relevant capacity and perturbation strength when those can explain the result.

Prioritize decisive, feasible comparisons. Config-only variants are often cheaper and less error-prone than rewriting an implementation. Model, dataset, and method swaps are useful when they test a plausible boundary or alternate account; filling every axis is not itself a scientific argument.

## Work through unsuccessful attempts

An implementation failure, an ineffective parameter choice, an unsuitable feature set, an unreliable measurement, and evidence against a hypothesis are different situations. Repair the implicated part rather than automatically abandoning the idea or rewriting the scientific question.

When an attempt produces no useful effect, look for the practical obstacle and continue: improve the contrast data, find a better feature set, widen the plausible coefficient range, change the site, tune the fine-tune, inspect the actual outputs, or consult an existing implementation and another model. The [intervention advice](interventions.md) and [training advice](training-and-execution.md) give concrete starting points.

Do not convert “I could not make it work” into “it cannot work.” Continue pursuing a viable result within the user's authorized resources. If those resources or your implementation capability prevent further progress, explain the obstacle and the next useful attempt. A technical boundary does not settle the scientific question.

## Using criticism

Another model can expose a missing comparison, a weak metric, or an implementation mistake. Ask actionable follow-ups: “What is the minimum experiment that distinguishes these explanations?” or “Which code or measurement assumption could make this result disappear?” Send the relevant material; a text consultation cannot read local files by name.

Accept valid criticism and push back on advice that changes the problem, adds unrelated modules, or expands experiments without resolving the central uncertainty. Another model's confidence is advice, not evidence. Improving a review score is not the research objective.

## Explaining findings

Make the account understandable without access to working notes: name the models, conditions, comparisons, and units that define the finding. Separate observed effects, proposed explanations, remaining alternatives, and promising follow-ups. Prefer actual quantities to broad adjectives and keep the same quantity and unit consistent wherever it appears.

A report should explain what was learned and what still needs work. Document format and figure conventions serve that explanation; they do not determine the research route.
