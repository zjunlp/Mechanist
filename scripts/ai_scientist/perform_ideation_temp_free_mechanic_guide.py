import argparse
import json
import os
import os.path as osp
import re
import traceback
from typing import Any, Dict, List

import sys

sys.path.append(osp.join(osp.dirname(__file__), ".."))
from ai_scientist.llm import (
    AVAILABLE_LLMS,
    create_client,
    get_response_from_llm,
)

from ai_scientist.tools.mechanic_db import MechanicDBSearchTool
from ai_scientist.tools.base_tool import BaseTool

# Create tool instances
# Literature search shells out to ai_scientist/mechanic_db_search.py
# (`python mechanic_db_search.py "<query>"`); see ai_scientist/tools/mechanic_db.py.
mechanic_db_tool = MechanicDBSearchTool()

# Define tools at the top of the file
tools = [
    mechanic_db_tool,
    {
        "name": "FinalizeIdea",
        "description": """Finalize your idea by providing the idea details.

The IDEA JSON should include the following fields:
- "Name": A short descriptor of the idea. Lowercase, no spaces, underscores allowed.
- "Title": A catchy and informative title for the proposal.
- "Short Hypothesis": A concise statement of the main hypothesis or research question. Clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.
- "Related Work": A brief discussion of the most relevant related work and how the proposal clearly distinguishes from it, and is not a trivial extension.
- "Abstract": An abstract that summarizes the proposal in conference format (approximately 250 words).
- "Experiments": A list of experiments that would be conducted to validate the proposal. Ensure these are simple and feasible. Be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.
- "Risk Factors and Limitations": A list of potential risks and limitations of the proposal.""",
    },
]

# Create a tools dictionary for easy lookup
tools_dict = {tool.name: tool for tool in tools if isinstance(tool, BaseTool)}

# Create a string with the tool descriptions
tool_descriptions = "\n\n".join(
    (
        f"- **{tool.name}**: {tool.description}"
        if isinstance(tool, BaseTool)
        else f"- **{tool['name']}**: {tool['description']}"
    )
    for tool in tools
)

# Extract tool names for the prompt
tool_names = [
    f'"{tool.name}"' if isinstance(tool, BaseTool) else f'"{tool["name"]}"'
    for tool in tools
]
tool_names_str = ", ".join(tool_names)

system_prompt = f"""You are an experienced AI researcher who aims to propose high-impact research ideas resembling exciting grant proposals. Feel free to propose any novel ideas or experiments; make sure they are novel. Be very creative and think out of the box. Each proposal should stem from a simple and elegant question, observation, or hypothesis about the topic. For example, they could involve very interesting and simple interventions or investigations that explore new possibilities or challenge existing assumptions. Clearly clarify how the proposal distinguishes from the existing literature.

Ensure that the proposal does not require resources beyond what an academic lab could afford. These proposals should lead to papers that are publishable at top ML conferences.

You have access to the following tools:

{tool_descriptions}

Respond in the following format:

ACTION:
<The action to take, exactly one of {tool_names_str}>

ARGUMENTS:
<If ACTION is "SearchMechanicDB", provide the search query as {{"query": "your search query"}}. If ACTION is "FinalizeIdea", provide the idea details as {{"idea": {{ ... }}}} with the IDEA JSON specified below.>

If you choose to finalize your idea, provide the IDEA JSON in the arguments:

IDEA JSON:
```json
{{
  "idea": {{
    "Name": "...",
    "Title": "...",
    "Short Hypothesis": "...",
    "Related Work": "...",
    "Abstract": "...",
    "Experiments": "...",
    "Risk Factors and Limitations": "..."
  }}
}}
```

Ensure the JSON is properly formatted for automatic parsing.

Note: You should perform at least one literature search before finalizing your idea to ensure it is well-informed by existing research."""

# Define the initial idea generation prompt
idea_generation_prompt = """{workshop_description}

Here are the proposals that you have already generated:

'''
{prev_ideas_string}
'''

The following two guides describe how to (1) surface a new behavioral phenomenon worth explaining and (2) choose the mechanism-research strategy that explains it. Use them to shape your proposal.

===== BEGIN GUIDE 1: /mechanism-behavior-discovery =====

---
name: mechanism-behavior-discovery
description: 'Mine behavioral regularities in neural-network (LLM / multimodal) models — the upstream half of the project''s mission (find a behavior worth explaining, then investigate the mechanism behind it). Use this skill when the task is open-ended: surface a *new* behavioral phenomenon — a candidate claim / research direction — rather than investigate an already-named mechanism. It gives strategies for choosing which behavior to probe and how to choose the data that validates it. The output is a candidate phenomenon that hands off to `/mechanism-explore` for mechanistic investigation. Domain-general: no assumption about model family, modality, or task.'
---

# Mechanism — Behavior Discovery

The discovery half of the loop: before you can explain *why* a model does something, you need a behavior worth explaining. This skill helps surface a **new behavioral phenomenon** — a candidate claim — and choose the data that tests it. The sharpened phenomenon (a one-sentence falsifiable behavior, its data/metric, and a plausible internal locus) hands off to `/mechanism-explore`.

A phenomenon is an observable, reproducible regularity in a model's input→output behavior that is not obvious a priori. A candidate is worth pursuing when it is **real, non-obvious, specific, robust, and tractable** (a plausible internal locus exists to explain it).

## When to Use

The task is open-ended — "find something interesting about how this model behaves," "what's surprising here." Do **not** use it to explain an already-named behavior (that is `/mechanism-explore`) or to score a model on a fixed benchmark.

This skill runs only when the phenomenon is **not** already pinned by the user. When the user explicitly names the phenomenon to investigate, the caller skips discovery entirely and goes straight to explaining that named phenomenon — so a behavior-level override is handled by the caller, not here.

## Strategies for Choosing a Behavior to Investigate

1. **Transfer a behavioral phenomenon into a high-stakes domain.** Take a behavior already known elsewhere, move it into an important domain, and test whether it reappears — either under the same conditions or under stricter, more counterintuitive ones. Domains include but are not limited to:
   - Science domains: chemistry, biology, medicine, …
   - Language: how language systems evolve and develop, etymological / cognate relationships, ancient-text decipherment, and the language–intelligence relationship.
   - Multi-agent social science.
   - Creativity.
2. **Borrow from the human sciences.**
   - Take a finding from brain science, psychology, or developmental history and check whether LLMs exhibit the same behavior.
   - Compare how the human brain and LLMs process the same task, identifying similarities and differences. This usually requires EEG (or other neural) recordings of humans performing that task.
3. **Cross-modal transfer.** Take a phenomenon seen in text and check whether it appears in image / video / multimodal models.
4. **Reuse existing results in computer science.** Check whether earlier findings, methods, or conclusions in computer science apply to the current model or research question.
5. **Probe a phenomenon's conditions or causal origin.** Take a known (or just-surfaced) phenomenon and ask *when* it holds or *why* it arises.
   - **When it holds** — characterize the regime of validity. *Macro*: under what general condition or law does the phenomenon hold or break? *Micro*: vary a concrete knob — model scale, checkpoint, prompt format, language, in-context examples, difficulty, or domain — and find the specific point at which the behavior flips. Either a general boundary or a single flipping condition is itself a candidate claim.
   - **Why it arises** — trace it to a *training* cause (data frequency, order of acquisition across checkpoints, objective, RLHF stage) or an *inference* cause (decoding, attention/representation locus, prompt position, context length), yielding a claim of the form *"P is caused by C at stage S"*.
6. **Meta-analysis.** Distill a theory or law from prior research — e.g. the scaling law and the Densing Law of LLMs — and use a macro-level or mathematical-theory lens to characterize the regularity, including the conditions under which a given phenomenon holds.

## Some Rules

1. **Existing datasets first.** Check whether an existing dataset can test the behavior directly; if not, adapt one (relabel / filter / transform). Prefer datasets that are well-established — e.g. authoritative and widely cited, or those published in venues such as *Nature* / *Science*.

2. **Pitch at any altitude — a high-level behavior phenomenon and a fine-grained one are both good.** A candidate can be a broad, abstract regularity in how the model reasons, represents, or decides, or a narrow, concrete effect tightly scoped to a single input→output pattern. Both are worth pursuing — so do **not** default to ever-smaller, hyper-specific points. An important high-level phenomenon is often the more valuable and more illuminating target, *as long as* it is still sharpened into a falsifiable, testable one-sentence behavior — the **specific** bar (§ the five bars) means *operationalizable*, not *small*. Aim for a spread of altitudes across your candidates rather than a monoculture of tiny effects.
   - **High-level behavior phenomenon** — e.g. *"the model's expressed confidence is largely decoupled from whether its answer is actually correct"*; or *"the model's sycophancy is a capability distinct from its factual-knowledge competence"*.
   - **Fine-grained behavior phenomenon** — e.g. *"the model's multiple-choice answer flips with the option ordering, independent of content"*; or *"the model is more sycophantic when the prompt is phrased in the first person"*.

3. The move is strongest when you *tighten as you transfer*: not only just re-confirm a phenomenon in a new domain, but make its precondition harder or more counterintuitive while moving it somewhere the behavior actually carries consequences. The candidates that matter most are those where a small or innocuous-looking cause yields a disproportionate, high-stakes effect — prefer framings that widen that gap over ones that merely reproduce the original.

4. **Safety and risk in science domains are especially worth probing.** Chemistry, biology, medicine, healthcare, clinical diagnosis, and the like are high-priority directions: when an unsafe or risky phenomenon surfaces in some other domain, prioritize transferring it into one of these safety-critical domains — that is where the same behavior carries the highest stakes and is most worth investigating.

Identify the user's intent, then pick the strategy direction that best matches it to probe the behavior. Using the Strategies for Choosing a Behavior to Investigate above, brainstorm several promising and interesting LLM behavioral phenomena internally, then **commit to exactly one** as the candidate to hand off — the single phenomenon to explain. (The *mechanism* directions for explaining that one phenomenon may stay plural; producing a few candidate directions is `/mechanism-explore`'s job, not this stage's.)

**If a record of already-explored phenomena and their outcomes is provided**, pick a phenomenon that is **distinct from all of them**. In particular, do **not** re-propose a phenomenon already **established**, **conditional** (it holds, under stated conditions), or **not-established** (refuted) — those questions are answered; choose a genuinely new direction (you may build on what those outcomes taught you). A phenomenon left **`inconclusive`** is *not* settled (the test failed to decide) — it remains a valid retry target, not something to avoid. The phenomena you considered but did not commit to are worth noting as a backlog for a later round.

===== END GUIDE 1 =====

===== BEGIN GUIDE 2: /mechanism-explore =====

---
name: mechanism-explore
description: 'Macro-level strategic directions for investigating the *mechanism* behind a model behavior — the downstream half of the project''s mission (mine LLM behaviors, then explain the mechanism behind them). Use once a phenomenon is observed in a model — whether already established/known or freshly mined by `/mechanism-behavior-discovery` — and the task is to choose *how* to investigate the internal cause. It is the strategy layer above the concrete method families in `/mechanism-skills`, organized around six parallel research directions — **Location**, **Causal Intervention**, **Tuning & Editing**, **Formation Tracing**, **Unit Interpretation**, **Decision Auditing** — plus how to combine them into strategies. Domain-general: it prescribes strategy, not any single model, modality, or method.'
---

# Mechanism — Explore

The explanation half of the loop. Given a validated phenomenon, this skill is the **macro-level plan** for finding the mechanism behind it. It decides **which strategic directions to pursue, and in what order** — the families in **`/mechanism-skills`** execute the chosen directions.

> A mechanism claim is **causal**: "component X is responsible for behavior B" means intervening on X changes B in the predicted, specific way. *Locating* X is necessary but not sufficient — only intervention earns the word "mechanism."

## When to Use

A phenomenon is in hand — whether already established/known or handed off from `/mechanism-behavior-discovery` — and the question is now *where* it is computed, *whether* that component causes it, *whether* it can be tuned for use, *how* it formed, *what it means*, or *whether the model's decision is trustworthy*. Do **not** use this skill to find a phenomenon (that is `/mechanism-behavior-discovery`), nor as a substitute for the chosen family's method file in `/mechanism-skills`.

## The Six Research Directions

Six parallel directions for explaining a model. They are coordinate — each answers a different question and stands on its own — and they also chain into strategies (see below). **Location** is typically the natural entry point for the others, since most directions act on a component you have first located.

### 1. Location — *where* the behavior is computed

At inference time, find which internal function component for the behavior: a **layer**, a **neuron** (or head), a **circuit**, or a **featur/activation direction**. Use cheap correlational/attribution methods (probing, vocabulary projection, magnitude, attribution, circuit discovery, dictionary learning). Output: a ranked shortlist of candidates. This is **correlational** — a located component is a hypothesis, not yet the cause.

### 2. Causal Intervention — *whether* the component causes the behavior

Intervene on the located component and check the target behavior moves as predicted (amplify → behavior strengthens, ablate → behavior gone). Tools: **ablation**, **activation patching** (sufficiency / localization), **steering** (dose-response on a represented quantity). Always report **sign**, **magnitude / dose-response**, and **specificity** (a matched control component does nothing; off-target behavior intact). This is what promotes *located* to *mechanism*.

### 3. Tuning & Editing — *use* the component to improve capability

Directly tune or edit the located component to raise downstream task ability (steering vectors, parameter-space task vectors / weight editing, targeted fine-tuning). Distinct from direction 2: intervention is **diagnostic** (does X cause B?), tuning is **applied** (use X to make B better). Judged by downstream gains, not a causal verdict.

### 4. Formation Tracing — *how* the component formed (training-time)

Move from inference-time to training-time: (a) how the component **forms over training** (when it emerges, how it sharpens across checkpoints); (b) which **training data** is critical to it (influence functions / data attribution, data-ablation re-training). Explains the component's origin. The most expensive direction — use only when *genesis* is part of the claim.
> Reference: *Mechanistic Data Attribution: Tracing the Training Origins of Interpretable LLM Units.*

### 5. Unit Interpretation — *what* an internal unit means

Decode the human-understandable concept carried by an internal unit (neuron / feature / direction) — turning an opaque activation into a named meaning.

- **Dictionary decomposition.** Use a **sparse autoencoder (SAE)** to factor activations into monosemantic features and read off each feature's concept. When no SAE is available (or training one is too costly), use **ICA** to recover interpretable directions directly from activations as a lightweight substitute.
- **Model-explains-model (auto-interpretation).** Have a stronger model write and score natural-language explanations of a weaker model's units (e.g. a frontier LLM labeling another LM's neurons), giving scalable, automatically-validated descriptions.
- **Cross-modal interpretation.** For non-text models, map internal units to concepts in a shared multimodal space and surface them as readable visual/textual descriptions — e.g. **SemanticLens** for vision models.
> References: *Mechanistic understanding and validation of large AI models with SemanticLens* (vision); language-model-explains-language-model auto-interpretation work; InterPLM: discovering interpretable features in protein language models.

### 6. Decision Auditing — *whether* the model's decision is trustworthy

Trace the evidence a model relies on for a specific decision, then judge that evidence against domain knowledge. Two complementary uses:

- **Validate decision-making.** Audit whether a decision rests on valid, task-relevant features rather than spurious correlations (background artifacts, dataset bias, shortcut cues). By mapping each contributing unit to a concept (direction 5) and checking it against what *should* matter, you catch "right answer, wrong reason" before deployment — e.g. SemanticLens-style audits that expose the concepts driving a prediction and flag illegitimate ones.
- **Discover novel decision bases.** The same trace can surface features the model uses that humans had not recognized as relevant — turning interpretability into a source of new domain knowledge rather than only a check on old knowledge.
> Reference: *Using Interpretability to Identify a Novel Class of Alzheimer's Biomarkers.*

## Combining into Strategies

Any of the six directions can stand alone, and they also chain. Pick the shortest combination that answers your question.

| Strategy | Mechanism Directions | Specific Case |
|---|---|---|
| Mechanistic evidence | Location → Causal Intervention | "X causally drives B." |
| Capability / editing | Location → Tuning & Editing | "Tuning X improves downstream task T." |
| Complete account | Location → Causal Intervention → Formation Tracing | "X drives B, and forms at stage S from data D." |
| Explaining a model | Unit Interpretation | "Unit X encodes concept C." |
| Decision reliability | Unit Interpretation → Decision Auditing | "Decision D relies on C — valid (or spurious / novel)." 

There is **no default** — choose the strategy (or a few candidate strategies) from the user's intent, and let that choice define the claim you are trying to land. Each row is self-contained: e.g. Location + Causal Intervention locates the head / feature carrying the behavior, then ablates or steers it to confirm it causally drives the behavior — a complete finding on its own, so do not bolt on a direction the user's question does not need. If a strategy is already specified by the task or plan, follow that requirement.

## Goal

Based on the user's intent, design a few suitable mechanism-research strategies and directions for them. The common ones are the five strategies in the table above: **Mechanistic evidence** (Location + Causal Intervention), **Capability / editing** (Location + Tuning), **Complete account** (Location + Causal Intervention + Formation Tracing), **Explaining a model** (Unit Interpretation), and **Decision reliability** (Decision Auditing).

**Keep the mechanism claim at the right altitude — hypothesize the *kind* of component, not its exact identity.** The claim should assert that *some* internal component (a layer / neuron / head / circuit / feature direction) carries or causes the target behavior — not pin down *which specific* layer or *which exact* feature. Those concrete identities are precisely what the experiment stage is meant to discover (the Location + Causal Intervention work); fixing them at claim time pre-empts the experiments and risks committing to a specific the runs may not bear out.

**If a record of mechanism directions already investigated for this same phenomenon (with their outcomes) is provided**, propose a direction from the **candidate set = untried directions ∪ directions left `inconclusive`**. Do **not** re-propose a direction already shown to **hold (confirmed)** or already **refuted** — those are settled. A direction left **`inconclusive`** is *not* settled (the test failed to decide); it is a legitimate retry candidate, ideally with a stronger test. Build on what the prior outcomes established.

**An explicit user/plan-specified direction overrides this avoidance.** Per the "If a strategy is already specified by the task or plan, follow that requirement" rule above: when the task pins a direction, use it directly rather than picking a complementary untried one. Deciding whether to honor a pin that collides with an already-`confirmed`/`refuted` direction is the **caller's** responsibility, not this skill's — act on whatever honor-or-replace decision the caller hands you, and do **not** raise that confirmation yourself.

===== END GUIDE 2 =====

Begin by generating an interestingly new high-level research proposal that differs from what you have previously proposed.
"""

# Define the reflection prompt
idea_reflection_prompt = """Round {current_round}/{num_reflections}.

In your thoughts, first carefully consider the quality, novelty, and feasibility of the proposal you just created.
Include any other factors that you think are important in evaluating the proposal.
Ensure the proposal is clear and concise, and the JSON is in the correct format.
Do not make things overly complicated.
In the next attempt, try to refine and improve your proposal.
Stick to the spirit of the original idea unless there are glaring issues.

If you have new information from tools, such as literature search results, incorporate them into your reflection and refine your proposal accordingly.

Results from your last action (if any):

{last_tool_results}
"""


def _flush_ideas(idea_fname: str, idea_str_archive: List[str]) -> None:
    """把当前已攒的 idea 立即原子落盘（写临时文件再 rename），防止中途中断丢失。
    仅做持久化 I/O，不改变任何生成逻辑。"""
    try:
        ideas = [json.loads(s) for s in idea_str_archive]
        tmp = idea_fname + ".tmp"
        with open(tmp, "w") as f:
            json.dump(ideas, f, indent=4)
        os.replace(tmp, idea_fname)
    except Exception:
        # 落盘失败不应打断生成主流程，仅告警
        print(f"[WARN] incremental flush to {idea_fname} failed:")
        traceback.print_exc()


def generate_temp_free_idea(
    idea_fname: str,
    client: Any,
    model: str,
    workshop_description: str,
    max_num_generations: int = 20,
    num_reflections: int = 5,
    reload_ideas: bool = True,
) -> List[Dict]:
    idea_str_archive = []
    # load ideas from file
    if reload_ideas and osp.exists(idea_fname):
        with open(idea_fname, "r") as f:
            idea_str_content = json.load(f)
            for idea in idea_str_content:
                idea_str_archive.append(json.dumps(idea))
            print(f"Loaded {len(idea_str_archive)} ideas from {idea_fname}")
    else:
        print(f"No ideas found in {idea_fname}. Starting from scratch.")

    # 重试机制：跑到真正攒够 max_num_generations 个「本次新增」idea 为止，
    # 空回复 / 临时失败的名额会自动重试；上限 = 目标数 * IDEA_MAX_ATTEMPTS_MULT。
    target_new = max_num_generations
    initial_count = len(idea_str_archive)
    attempt = 0
    max_attempts = max(
        max_num_generations + 2,
        max_num_generations * int(os.environ.get("IDEA_MAX_ATTEMPTS_MULT", "3")),
    )
    while (len(idea_str_archive) - initial_count) < target_new and attempt < max_attempts:
        attempt += 1
        done = len(idea_str_archive) - initial_count
        print()
        print(
            f"Generating proposal {done + 1}/{target_new} "
            f"(attempt {attempt}/{max_attempts})"
        )
        try:
            prev_ideas_string = "\n\n".join(idea_str_archive)

            last_tool_results = ""
            idea_finalized = False
            msg_history = []

            for reflection_round in range(num_reflections):
                if reflection_round == 0:
                    # Use the initial idea generation prompt
                    prompt_text = idea_generation_prompt.format(
                        workshop_description=workshop_description,
                        prev_ideas_string=prev_ideas_string,
                    )
                else:
                    # Use the reflection prompt, including tool results if any
                    prompt_text = idea_reflection_prompt.format(
                        current_round=reflection_round + 1,
                        num_reflections=num_reflections,
                        last_tool_results=last_tool_results or "No new results.",
                    )
                    # Last reflection round: force finalization. Some models (e.g.
                    # claude-opus) keep choosing SearchMechanicDB every round and
                    # never emit FinalizeIdea, exhausting all attempts with 0 ideas.
                    # On the final round they must commit to an idea instead of searching.
                    if reflection_round == num_reflections - 1:
                        prompt_text += (
                            "\n\nThis is the FINAL round for this proposal. You have searched "
                            "enough. You MUST now finalize: respond with ACTION: FinalizeIdea "
                            "and the complete idea JSON in ARGUMENTS. Do NOT call "
                            "SearchMechanicDB again — no more searches are allowed."
                        )

                response_text, msg_history = get_response_from_llm(
                    prompt=prompt_text,
                    client=client,
                    model=model,
                    system_message=system_prompt,
                    msg_history=msg_history,
                )

                # Parse the LLM's response
                try:
                    # Use regular expressions to extract the components
                    action_pattern = r"ACTION:\s*(.*?)\s*ARGUMENTS:"
                    arguments_pattern = r"ARGUMENTS:\s*(.*?)(?:$|\nTHOUGHT:|\n$)"

                    action_match = re.search(
                        action_pattern, response_text, re.DOTALL | re.IGNORECASE
                    )
                    arguments_match = re.search(
                        arguments_pattern, response_text, re.DOTALL | re.IGNORECASE
                    )

                    if not all([action_match, arguments_match]):
                        raise ValueError("Failed to parse the LLM response.")

                    action = action_match.group(1).strip()
                    arguments_text = arguments_match.group(1).strip()
                    print(f"Action: {action}")
                    print(f"Arguments: {arguments_text}")

                    # gpt-5.4 often emits MULTIPLE action blocks in one response, e.g. a
                    # SearchMechanicDB block IMMEDIATELY followed by a full FinalizeIdea
                    # block. The regexes above only capture the FIRST block (the search), so
                    # the model's actual decision to FinalizeIdea is dropped and it loops on
                    # search until attempts run out (0 ideas). If an explicit FinalizeIdea
                    # block with an idea payload is present, prefer it.
                    if action != "FinalizeIdea":
                        fin_match = re.search(
                            r"ACTION:\s*FinalizeIdea\s*ARGUMENTS:\s*(\{.*)",
                            response_text,
                            re.DOTALL | re.IGNORECASE,
                        )
                        if fin_match:
                            action = "FinalizeIdea"
                            arguments_text = fin_match.group(1).strip()
                            print("Detected FinalizeIdea among multiple action blocks; honoring it.")

                    # If arguments are wrapped in ```json blocks, extract the content
                    if arguments_text.startswith("```json"):
                        arguments_text = re.search(
                            r"```json\s*(.*?)\s*```", arguments_text, re.DOTALL
                        ).group(1)

                    # Process the action and arguments
                    if action in tools_dict:
                        # It's a tool we have defined
                        tool = tools_dict[action]
                        # Parse arguments
                        try:
                            arguments_json = json.loads(arguments_text)
                        except json.JSONDecodeError:
                            # Some models (e.g. gpt-5.4) append extra/duplicated content
                            # after the JSON object; parse the first valid object and
                            # ignore the trailing remainder instead of failing the attempt.
                            try:
                                arguments_json, _ = json.JSONDecoder().raw_decode(
                                    arguments_text.lstrip()
                                )
                            except json.JSONDecodeError:
                                raise ValueError(f"Invalid arguments JSON for {action}.")

                        # Use the tool
                        try:
                            # Assuming the arguments match the parameters of the tool
                            result = tool.use_tool(**arguments_json)
                            last_tool_results = result
                        except Exception as e:
                            last_tool_results = f"Error using tool {action}: {str(e)}"
                    elif action == "FinalizeIdea":
                        # Parse arguments
                        try:
                            try:
                                arguments_json = json.loads(arguments_text)
                            except json.JSONDecodeError:
                                # Tolerate trailing/duplicated content after the JSON object
                                arguments_json, _ = json.JSONDecoder().raw_decode(
                                    arguments_text.lstrip()
                                )
                            idea = arguments_json.get("idea")
                            if not idea:
                                raise ValueError("Missing 'idea' in arguments.")

                            # Append the idea to the archive
                            idea_str_archive.append(json.dumps(idea))
                            print(f"Proposal finalized: {idea}")
                            # 每生成一个 idea 立即落盘，防止中途中断/被 kill 丢失进度
                            _flush_ideas(idea_fname, idea_str_archive)
                            idea_finalized = True
                            break
                        except json.JSONDecodeError:
                            raise ValueError("Invalid arguments JSON for FinalizeIdea.")
                    else:
                        print(
                            "Invalid action. Please specify one of the available tools."
                        )
                        print(f"Available actions are: {tool_names_str}")
                except Exception as e:
                    print(
                        f"Failed to parse LLM response. Response text:\n{response_text}"
                    )
                    traceback.print_exc()
                    break  # Exit the loop if parsing fails

            if idea_finalized:
                continue  # Move to the next idea

        except Exception as e:
            print("Failed to generate proposal:")
            traceback.print_exc()
            continue

    new_count = len(idea_str_archive) - initial_count
    if new_count < target_new:
        print(
            f"[WARN] 只生成了 {new_count}/{target_new} 个新 idea（已用完 {attempt} 次尝试）。"
            f"可调大 IDEA_MAX_ATTEMPTS_MULT 或稍后重跑续攒。"
        )

    # Save ideas
    ideas = [json.loads(idea_str) for idea_str in idea_str_archive]

    with open(idea_fname, "w") as f:
        json.dump(ideas, f, indent=4)
    print(f"Stored {len(ideas)} ideas in {idea_fname}")
    return ideas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate AI scientist proposals - template free + mechanism guides"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-2024-05-13",
        choices=AVAILABLE_LLMS,
        help="Model to use for AI Scientist.",
    )
    parser.add_argument(
        "--max-num-generations",
        type=int,
        default=1,
        help="Maximum number of proposal generations.",
    )
    parser.add_argument(
        "--workshop-file",
        type=str,
        default="ideas/i_cant_believe_its_not_better.md",
        help="Path to the workshop description file.",
    )
    parser.add_argument(
        "--num-reflections",
        type=int,
        default=5,
        help="Number of reflection rounds per proposal.",
    )
    args = parser.parse_args()

    # Create the LLM client
    client, client_model = create_client(args.model)

    with open(args.workshop_file, "r") as f:
        workshop_description = f.read()
    print(f"Using workshop description from {args.workshop_file} for idea generation.")
    print(f"Workshop description:\n{workshop_description}")

    # Create output filename by replacing .md extension with .json
    idea_fname = args.workshop_file.replace(".md", ".json")
    print("Starting idea generation for", idea_fname)
    ideas = generate_temp_free_idea(
        idea_fname=idea_fname,
        client=client,
        model=client_model,
        workshop_description=workshop_description,
        max_num_generations=args.max_num_generations,
        num_reflections=args.num_reflections,
    )
    print(f"{args.workshop_file} generated {len(ideas)} ideas.")
