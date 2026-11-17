# Multiple-Choice Evaluation (LLM Judge, Not Regex)

## The point

MCQ probes compute their headline metric (accuracy, `P(chosen)`, `Δaccuracy` between arms, per-choice rate) by parsing a letter out of a free-form generation. **Parsing is the measurement** — a parser that mislabels 5–15 % of rows fabricates or destroys the Δ.

Naive case-insensitive letter regex has three symmetric failures:

1. **False positive — letter inside a word.** `re.search(r"[AB]", ...)` matches the first `A/a/B/b` anywhere: `"At the garden…"` → `A`, `"a valid choice…"` → `A`, `"option B refers to…"` before rejection → `B`. Fine-tuned / steered models that stop obeying "answer A or B only" produce exactly these strings.
2. **False negative — over-tight regex.** Tightening to `\banswer[:\s]+([AB])\b` misses `"A."`, `"(A)"`, `"I'd go with A"`, non-English preambles. The trade-off is inescapable inside a regex; disambiguation needs semantics.
3. **Silent coercion.** A two-bucket parser maps refusal / off-topic to whichever letter appears first (usually `A`). A 30 % refusal rate reads as a 30 % A-preference — a phantom effect that survives seeds because the coercion is deterministic.

## Recipe

**1. LLM judge on the full generation.** Send the raw generation plus the question stem with **all** option texts (not only letters — text is what removes the ambiguity a regex can't resolve) to a capable judge; the final per-row verdict must be three-way `CORRECT` / `INCORRECT` / `OTHER`. Refusal / off-topic / multiple / none / format-broken all land in `OTHER` and are **never** coerced into `CORRECT` or `INCORRECT`; report separately. If computing accuracy conditional on valid answers, make that denominator explicit and also show the invalid-answer rate by arm. A strict regex is fine as a fast pre-filter, but any prose after the match falls back to the judge. Two prompt shapes work — pick one:

**(a) Extract-then-compare.** Judge only extracts which option the model picked (`A` / `B` / … / `OTHER`); a hard-coded step outside the LLM compares against the gold letter. Cleanly separates parsing from scoring, and the extracted letter is auditable on its own.

```
You are extracting a multiple-choice answer from a model's free-form output.
Question and options:
{question_with_options}

Model's free-form answer:
{model_answer}

Which option did the model pick? Reply with EXACTLY ONE of:
  A / B / …  — model's answer semantically picks that option.
  OTHER      — refused, off-topic, picked multiple options, unparseable, or matches no option.

Do NOT guess a letter when the answer is a refusal or off-topic.
```
Then downstream: `verdict = "CORRECT" if extracted == gold_letter else ("OTHER" if extracted == "OTHER" else "INCORRECT")`.

**(b) Gold-relative direct judge.** Hand the judge the gold letter as well and ask for `CORRECT` / `INCORRECT` / `OTHER` in one shot. Fewer moving parts, and side-steps the judge's own token bias on `A` vs `B` because it never has to name a letter.

```
You are grading a model's answer to a multiple-choice question.
The gold answer is option {gold_letter}. Question and full option list:
{question_with_options}

Model's free-form answer:
{model_answer}

Reply with EXACTLY ONE of:
  CORRECT   — model's answer semantically matches option {gold_letter}.
  INCORRECT — model's answer semantically picks a different option.
  OTHER     — refused, off-topic, picked multiple options, unparseable, or matches no option.

Do NOT coerce a refusal or off-topic answer into INCORRECT.
```

Output shape (bare word, JSON field, XML tag) is up to you, as long as the three verdicts are the only legal values.

**2. Control position bias by rotating option order.** Instruction-tuned models carry a ~5–15 pp position bias for the first-listed option that persists after content swap. Run each item in every orientation (A/B swap for binary; a fixed rotation, e.g. 2–4 permutations, for A-D) and report per-orientation as well as averaged. A stable effect appears in every orientation; a sign-flip or > 50 % shrink under rotation is position bias, not the intervention.

**3. Never score with log-prob alone — it's blind to output corruption.** Verbalizer / cloze scoring is contaminated by token bias (`A` gets more prior mass), and — critically — it reads probability off the answer tokens without ever generating text, so a fully broken model (repetition loops, gibberish, refusals, off-language output) still yields a "clean" A-vs-B score you can't distinguish from real answering. Log-prob **cannot** detect output-corruption regressions; always generate on a subset and eyeball the outputs first. If used at all, cross-check against text-gen + judge on a held-out slice; > 5 pp disagreement → keep log-prob as diagnostic only.

## Non-negotiables

- **Three-way `{CORRECT, INCORRECT, OTHER}` verdict required** (whichever prompt shape produced it). Two-way parsers invent effects.
- **All orientations, always** — per-orientation numbers reported (A/B swap for binary; a fixed rotation for A-D).
- **Freeze judge config across arms** (model, prompt, temperature ≤ 0.2). Changing the judge confounds the intervention with the parser.
- **Choose a judge consistent with the task and available resources.** Use the user's specified judge when supplied. Otherwise choose an available suitable judge within the user's authorization; if none is available, use an appropriate benchmark scorer or structured extraction where it can resolve the actual answer format. A remote consultation sees only the text sent to it, so include the full question, options, and answer. Do not pretend an unavailable judge ran.

## Diagnosing a suspected parser artifact

Any one of these fires ⇒ the effect is un-measured until the parser is fixed:

- **Orientation instability** — Δ changes sign or shrinks > 50 % across orientations ⇒ position-bias-driven.
- **`OTHER` rate rises in the treated arm** ⇒ two-way coercion artifact, not a preference shift. Separate the preference among valid answers from the probability of producing a valid answer; do not hide a treated-arm increase in invalid outputs by silently excluding them.
- **Regex-vs-judge disagreement > 5 % on a 100-row spot-check** ⇒ one of them is systematically wrong (almost always the regex).

## Combining with interventions and fine-tuning

- **A parser failure needs a measurement fix.** If a null changes after semantic extraction replaces a naive regex, diagnose the parser before attributing the original null to the model or the intervention.
- **Read this advice when instruction-breaking interventions meet an MCQ eval.** [Fine-tuning](finetune-hyperparameter-sweep.md), [coefficient tuning](steering-coefficient-tuning.md), and [block selection](steering-block-selection.md) can alter letter-only instruction following — the exact regime where regex parsing silently fails.
- **Revisit extraction on model-family change.** Output conventions (`A.` vs `A)` vs `**A**` vs `Answer: A` vs non-English preambles) shift between families and between base / instruct / chat variants; refresh the judge's examples.

Log-probability remains appropriate when the question is explicitly about next-token probabilities. It is not a substitute for inspecting generated answers when the claim concerns coherent answering or generation behavior.
