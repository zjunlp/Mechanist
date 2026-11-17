---
name: model-consultation
description: "Seek other AI models' perspectives when your own reasoning may be incomplete, one-sided, or uncertain. Use for alternative explanations, independent checks, difficult questions, or critique of code and research designs."
---

# External model consultation

Your reasoning reflects one model's knowledge and perspective. You may miss an explanation, repeat an assumption, or overlook a weakness even when confident. This skill lets you consult other AI models to broaden the discussion: ask a question, seek an alternative approach, or invite a check of your reasoning, code, or experimental design.

Consider consultation when uncertainty persists, competing explanations are hard to distinguish, or an independent critique could improve an important decision. You decide when it is useful and what to ask. Other models can share your blind spots and make mistakes; weigh their reasoning against evidence rather than treating agreement as validation. Consultation is an optional resource, with no required review gate.

Run [scripts/chat.py](scripts/chat.py) with Python. Resolve its path relative to this skill directory rather than the research working directory. Install [scripts/requirements.txt](scripts/requirements.txt) in the chosen Python environment if needed.

```text
python /path/to/model-consultation/scripts/chat.py --prompt-file /path/to/question.txt
python /path/to/model-consultation/scripts/chat.py --prompt "Compare these two explanations: ..." --model MODEL
python /path/to/model-consultation/scripts/chat.py --prompt-file - --output /path/to/answer.json
```

Set `LLM_API_KEY` in the environment inherited by the script. `LLM_BASE_URL` defaults to `https://api.openai.com/v1`; `LLM_MODEL` defaults to `gpt-5.4`. An optional `LLM_FALLBACK_MODEL` permits an explicitly selected fallback after failed retries. No key is accepted as a command-line argument.

Send the actual relevant text, constraints, weaknesses, and question. The external model cannot read local paths and has no conversation memory; include prior discussion needed for a follow-up. `--system` or `--system-file` supplies an optional role instruction. `--timeout` is per attempt; `--max-tokens` controls the response limit.

Success prints JSON with `response`, the requested and returned model names, and `fallback_used`. With `--output`, the full response goes to that file and stdout returns metadata and its path. Failure prints JSON to stderr and exits nonzero. Choose whether and where to save the result; no research-wide recording convention applies.
