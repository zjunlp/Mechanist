---
name: model-consultation
description: "Discuss research with other AI models when your own reasoning may be incomplete, one-sided, or uncertain. Talk through what to do next, a claim's novelty or value, method choices, experiment designs, code and measurements, result interpretation, or draft findings, or explore alternative explanations and difficult questions together."
---

# Discussion with external models

Your reasoning reflects one model's knowledge and perspective. You may miss an explanation, repeat an assumption, or overlook a weakness even when confident. This skill lets you hold a discussion with other AI models: think a problem through together, ask a question, explore alternative approaches, or invite a check of your reasoning, code, or experimental design.

How you use these discussions is your choice. A discussion is often worthwhile when uncertainty persists, competing explanations are hard to distinguish, or another perspective could improve an important decision. Some examples:

- **Deciding what to do next:** when you are unsure how to proceed — which direction to take, which of several next steps to try, or how to move forward after a setback — describe the goal, what has been done, and the options you see, and talk it through with another model.
- **Novelty and value of a claim:** whether a hypothesis or finding is new relative to the closest prior work you have identified, and whether it matters. Another model may recall work you missed, but its literature memory can be incomplete or wrong; check cited work with [information retrieval](../information-retrieval/SKILL.md).
- **Choosing a direction or method:** comparing candidate phenomena, research strategies, or mechanism methods for the actual question, and asking for routes you have not considered.
- **Experiment design:** missing controls or baselines, confounds in the data or contrast, comparisons that would not distinguish the competing explanations, and the smallest experiment that would.
- **Code and measurement:** hook placement, tensor and position handling, metric or parser assumptions, and other implementation details that could create or hide an effect.
- **Interpreting results:** alternative explanations for an unexpected, weak, or null result, and how far the evidence supports a claim, before you commit to a conclusion.
- **Stuck diagnosis:** an ambiguous training curve, a persistent failure, or an intervention that does not work despite several attempts.
- **Explaining findings:** whether a draft report is clear, whether its claims exceed the evidence, and what a skeptical reader would question first.

You decide when to start a discussion, what to raise, and how far to take it. Other models can share your blind spots and make mistakes; weigh their reasoning against evidence rather than treating agreement as validation. Discussion is an optional resource, with no required review gate.

Run [scripts/chat.py](scripts/chat.py) with Python. Resolve its path relative to this skill directory rather than the research working directory. Install [scripts/requirements.txt](scripts/requirements.txt) in the chosen Python environment if needed.

```text
python /path/to/model-consultation/scripts/chat.py --prompt-file /path/to/question.txt
python /path/to/model-consultation/scripts/chat.py --prompt "Compare these two explanations: ..." --model MODEL
python /path/to/model-consultation/scripts/chat.py --prompt-file - --output /path/to/answer.json
```

Set `LLM_API_KEY` in the environment inherited by the script. `LLM_BASE_URL` defaults to `https://api.openai.com/v1`; `LLM_MODEL` defaults to `gpt-6.1-sol`. An optional `LLM_FALLBACK_MODEL` permits an explicitly selected fallback after failed retries. No key is accepted as a command-line argument.

Send the actual relevant text, constraints, weaknesses, and question. The external model cannot read local paths and has no conversation memory; include prior discussion needed for a follow-up. `--system` or `--system-file` supplies an optional role instruction. `--timeout` is per attempt; `--max-tokens` controls the response limit.

Success prints JSON with `response`, the requested and returned model names, and `fallback_used`. With `--output`, the full response goes to that file and stdout returns metadata and its path. Failure prints JSON to stderr and exits nonzero. Choose whether and where to save the result.
