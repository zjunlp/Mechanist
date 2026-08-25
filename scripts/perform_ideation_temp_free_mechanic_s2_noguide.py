import argparse
import json
import os.path as osp
import os
import sys

# The dependency closure is vendored beside this file, in scripts/ai_scientist/.
# Export AI_SCIENTIST_ROOT to run against a different checkout instead.
AI_SCIENTIST_ROOT = os.environ.get(
    "AI_SCIENTIST_ROOT", os.path.dirname(os.path.abspath(__file__))
)
if AI_SCIENTIST_ROOT not in sys.path:
    sys.path.append(AI_SCIENTIST_ROOT)

import ai_scientist.perform_ideation_temp_free_mechanic_noguide as base
from ai_scientist.tools.base_tool import BaseTool
from mechanic_db_semantic_scholar import CombinedMechanicDBSemanticScholarSearchTool


def _configure_base_module() -> None:
    combined_tool = CombinedMechanicDBSemanticScholarSearchTool()
    finalize_tool = next(
        tool
        for tool in base.tools
        if isinstance(tool, dict) and tool.get("name") == "FinalizeIdea"
    )

    base.mechanic_db_tool = combined_tool
    base.tools = [combined_tool, finalize_tool]
    base.tools_dict = {
        tool.name: tool for tool in base.tools if isinstance(tool, BaseTool)
    }
    base.tool_descriptions = "\n\n".join(
        (
            f"- **{tool.name}**: {tool.description}"
            if isinstance(tool, BaseTool)
            else f"- **{tool['name']}**: {tool['description']}"
        )
        for tool in base.tools
    )
    base.tool_names = [
        f'"{tool.name}"' if isinstance(tool, BaseTool) else f'"{tool["name"]}"'
        for tool in base.tools
    ]
    base.tool_names_str = ", ".join(base.tool_names)
    base.system_prompt = f"""You are an experienced AI researcher who aims to propose high-impact research ideas resembling exciting grant proposals. Feel free to propose any novel ideas or experiments; make sure they are novel. Be very creative and think out of the box. Each proposal should stem from a simple and elegant question, observation, or hypothesis about the topic. For example, they could involve very interesting and simple interventions or investigations that explore new possibilities or challenge existing assumptions. Clearly clarify how the proposal distinguishes from the existing literature.

Ensure that the proposal does not require resources beyond what an academic lab could afford. These proposals should lead to papers that are publishable at top ML conferences.

You have access to the following tools:

{base.tool_descriptions}

Respond in the following format:

ACTION:
<The action to take, exactly one of {base.tool_names_str}>

ARGUMENTS:
<If ACTION is "SearchMechanicDB", provide the search query as {{"query": "your search query"}}. This tool will search both halves of mechanic-db - AI interpretability and an all-discipline scientific graph - and return the 15 most relevant papers of each (30 in total), plus up to 5 more from Semantic Scholar, then deduplicate the combined results before returning them. If ACTION is "FinalizeIdea", provide the idea details as {{"idea": {{ ... }}}} with the IDEA JSON specified below.>

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


if __name__ == "__main__":
    _configure_base_module()

    parser = argparse.ArgumentParser(
        description="Generate AI scientist proposals - template free + mechanic-db(15 per database, 30 total) + semantic scholar(5)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-2024-05-13",
        choices=base.AVAILABLE_LLMS,
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
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Where to write the ideas JSON. Defaults to the workshop file with "
        ".md swapped for .json.",
    )
    args = parser.parse_args()

    client, client_model = base.create_client(args.model)

    with open(args.workshop_file, "r") as f:
        workshop_description = f.read()
    print(f"Using workshop description from {args.workshop_file} for idea generation.")
    print(f"Workshop description:\n{workshop_description}")

    idea_fname = args.output_file or args.workshop_file.replace(".md", ".json")
    print("Starting idea generation for", idea_fname)
    ideas = base.generate_temp_free_idea(
        idea_fname=idea_fname,
        client=client,
        model=client_model,
        workshop_description=workshop_description,
        max_num_generations=args.max_num_generations,
        num_reflections=args.num_reflections,
    )
    print(f"{args.workshop_file} generated {len(ideas)} ideas.")
