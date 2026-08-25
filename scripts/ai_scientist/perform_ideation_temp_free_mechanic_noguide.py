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
        description="Generate AI scientist proposals - template free"
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
