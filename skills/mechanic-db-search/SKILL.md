---
name: mechanic-db-search
description: Paper retrieval via the cloud SEARCH service. The Agent builds a decomposed query JSON from its task context (preferred) or submits a polished free-form English query; the cloud service performs multi-ranker retrieval and fusion. Use as one of an important paper sources.
argument-hint: "[query]"
---

# mechanic-db-search — Cloud SEARCH Wrapper

Query: $ARGUMENTS

## What this skill does

Wrap the cloud-hosted `mechanic_database` SEARCH service so the Agent can:

1. **Submit a search** — preferably as an Agent-built **decomposed query JSON** that encodes **at most one sub-query per database** (db choice, closed-enum interp fields, keywords, **and an Agent-written HyDE abstract per sub-query**).
2. Receive a paper list (`papers[]`) and use it downstream.
3. Iterate: if results are unsatisfactory, refine and call again (up to 3 rounds).
4. Run multiple calls **in parallel** when appropriate.

All transport — auth, submit, poll, error handling, writing results to disk — lives in the **`mechanic-db` MCP server** (`mcp-servers/mechanic-db/server.py`), which exposes a single tool, **`search_papers`**. The MCP server only forwards the request: it does **not** validate the decomposition or run any splitter/HyDE itself — query correctness is this skill's job. The heavy retrieval — multi-ranker scoring + fusion, and (in flat mode) the splitter and HyDE generation — runs in the **cloud SEARCH service**. Call the `search_papers` tool directly; do not invoke any Python.

## Constants

- **TOOL** = the `search_papers` tool on the `mechanic-db` MCP server. Call it directly; do not invoke any Python.
- **API_KEY** — provided to the MCP server via the plugin manifest env mapping (`MECHANIC_DB_API_KEY`; set as an environment variable in the shell that launches Claude Code, or for Codex the cached `mcp.codex.json` `env`).
- **DEFAULT_TOP_K** = 300
- **TIMEOUT_SEC** = 1200 (one call ≈ 3-20 min; allow headroom)
- **MAX_REFINEMENT_ROUNDS** = 3

## Skip-when-unconfigured contract

## What the service searches

| ID | Scope |
|----|-------|
| `interp_db` | AI interpretability papers (~14k) — neural-network internal mechanisms in LLMs / Transformers / CNNs. Tagged along closed-enum axes (techniques / task_scenarios / abilities / components) plus free-text target_models / model_families. |
| `sciatlas_db` | All-discipline graph (~157M nodes) — neuroscience, psychology, cognitive science, computer science, biology, physics, chemistry, materials, humanities. Retrieved via semantic similarity + BM25. |

The cloud service decides per-sub-query which database to hit, runs multiple rankers in parallel (including a **HyDE-abstract vector channel**), and fuses the results. In **decomposed mode** it takes the Agent's per-sub-query plan verbatim and skips its own splitter. In **flat-query mode** the cloud splitter handles decomposition and HyDE generation.

---

# Mode 1 — Agent-built decomposed query (PREFERRED)

This is the recommended path for every call. The Agent's task context (`task.md`, the upstream research goal, prior turns, named entities, the domain hints the user dropped) yields a sharper per-sub-query plan — and a better HyDE abstract — than the cloud's generic splitter could produce from a free-form query. Use this mode unless the available context is too thin to fill out the JSON honestly.

## 1.1 — Decomposed JSON shape

The JSON is the **flat ParsedQuery** shape the cloud service consumes directly. The critical rule: **at most ONE sub-query per database.** `sub_queries` holds **1 or 2** objects — at most one `interp_db` and at most one `sciatlas_db`. Each database is searched **exactly once**. Any cross-domain or multi-topic breadth is packed *into* the relevant database's single sub-query (its `semantic_query` + `keywords`).

```json
{
  "original_query": "<user's query, verbatim>",
  "is_cross_domain": true,
  "sub_queries": [
    {
      "domain": "AI interpretability",
      "db": "interp_db",
      "semantic_query": "<≤60 words, packs ALL interp intent for this query>",
      "keywords": ["phrase", "..."],
      "year_min": null,
      "year_max": null,
      "min_citations": null,
      "techniques": [],
      "components": [],
      "task_scenarios": [],
      "abilities": [],
      "target_models": [],
      "model_families": [],
      "hyde_text": "<Agent-written hypothetical abstract — see §1.6>"
    },
    {
      "domain": "cognitive neuroscience",
      "db": "sciatlas_db",
      "semantic_query": "<≤60 words, packs ALL sciatlas intent for this query>",
      "keywords": ["phrase", "..."],
      "year_min": null,
      "year_max": null,
      "min_citations": null,
      "techniques": [],
      "components": [],
      "task_scenarios": [],
      "abilities": [],
      "target_models": [],
      "model_families": [],
      "hyde_text": "<Agent-written hypothetical abstract — see §1.6>"
    }
  ]
}
```

Sub-query fields:

| Field | When required | Content |
|-------|--------------|---------|
| `domain` | always | The **precise** scientific field. For interp_db use `"AI interpretability"`. For sciatlas_db name the actual field (`"cognitive neuroscience"`, `"wireless sensing"`, `"materials science"`) — or `"cross-domain"` only when the sciatlas content genuinely spans multiple fields. Drives the HyDE writer's vocabulary. Never a vague label like `"science"` or `"general"`. |
| `db` | always | `"interp_db"` **iff** the domain is AI mechanistic interpretability; `"sciatlas_db"` for every other field. **Each value appears at most once across `sub_queries`.** |
| `semantic_query` | always | Domain-flavored rewrite in English (**≤60 words**). Since this DB is searched only once, PACK IN every synonym, technical term, method name, and sub-topic within this DB's scope that the query touches — one broad, coherent search string (not a list glued together). |
| `keywords` | always (BOTH dbs) | 2-6 short phrases lifted or closely paraphrased from the query, covering this DB's full breadth. **Non-empty for both dbs.** Avoid generic terms ("study", "research", "paper"). |
| `year_min` / `year_max` / `min_citations` | optional | Temporal & citation constraints. `null` when absent (see R6/R4). |
| `techniques` / `components` / `task_scenarios` / `abilities` | interp_db only | Closed-enum arrays (§1.3). **Set all to `[]`** when `db == "sciatlas_db"`. |
| `target_models` / `model_families` | interp_db only | Free text. `target_models` = model names the user named (e.g. `"GPT-2 XL"`, `"GPT-J"`). `model_families` = the capitalised family (e.g. `"GPT"`, `"CLIP"`, `"LLaMA"`). **Set both to `[]`** when `db == "sciatlas_db"`. |
| `hyde_text` | always (recommended) | An Agent-written hypothetical abstract for this sub-query (§1.6). When present, the cloud service uses it verbatim for its HyDE vector channel; when omitted/empty, the cloud service generates one itself. |

**Invariants** (validate before submitting):
- `sub_queries` has 1 or 2 items, with **distinct `db` values** (at most one interp_db, at most one sciatlas_db).
- `db == "sciatlas_db"` ⇒ `techniques`/`components`/`task_scenarios`/`abilities`/`target_models`/`model_families` are all `[]`.
- `keywords` is non-empty for **every** sub-query.
- Top-level `is_cross_domain == (sub_queries.length == 2)`.

## 1.2 — Route the query to databases

Decide which database(s) the query needs, then emit **one sub-query per needed database**:
- **interp_db** — iff the query concerns AI mechanistic interpretability (internal mechanisms of neural nets: circuits, features, SAEs, attention heads, residual stream, causal tracing, …).
- **sciatlas_db** — for any other scientific content.

**Most queries need only ONE database → emit a single sub-query.** Emit BOTH only when the query genuinely spans an AI-interpretability topic AND a separate scientific topic. Do NOT add a second database just to be thorough — a single, sharp sub-query on the right database is the normal, preferred outcome for a single-domain query.

When one database has several topics or spans its field broadly, **do NOT split** — merge that breadth into that database's single sub-query by packing `semantic_query` and `keywords`. The old "one sub-query per fine-grained domain" style was wrong: over-splitting shreds each search's top-k budget and multiplies expensive sciatlas round-trips.

Set `is_cross_domain = true` **iff** you emit sub-queries for BOTH databases; else `false`.

**Soft cognitive bias (do not force).** When an LLM / AI-interpretability query is really about a COGNITIVE phenomenon with a clear human-cognition counterpart — reasoning, language, memory, attention, planning, concepts, belief/uncertainty, learning — you *may* also emit a `sciatlas_db` sub-query framed in cognitive science / cognitive neuroscience / psychology terms, **if** you judge that human-cognition literature genuinely relevant. This is a mild option, NOT a rule: when in doubt, stay single-database. Never manufacture a cognitive angle for queries that are purely technical or belong to another field (wireless sensing, materials, systems/infra, pure ML engineering).

Examples:
- "SAE features and hippocampal place cells" → 2 domains: [AI interpretability, neuroscience]
- "belief/uncertainty in LLMs and human brain" → 2 domains: [AI interpretability, cognitive neuroscience]
- "multipath propagation in wireless sensing" → 1 domain: [wireless communications]
- "ROME rank-one editing" → 1 domain: [AI interpretability]
- "working memory capacity" → 1 domain: [cognitive psychology]

Tie-breakers:
- "Applying X to Y" is 2 domains unless X is a generic ML method with no field-specific literature worth surveying.
- Don't invent a third domain just because the query mentions a tool ("using PyTorch to study …" → no "deep learning frameworks" domain).
- If the same field appears at two granularities ("hippocampus" + "episodic memory" — both neuroscience), combine into one sub-query.

## 1.3 — Closed enums for interp_db structured fields (interp_db sub-queries only)

**CRITICAL: closed enums. If a concept isn't in the list, use `[]` — do not substitute or invent values.**

```
techniques:     vocabulary_projection
                magnitude_analysis
                representation_and_parameter_analysis
                probing
                feature_dictionary_learning
                gradient_detection
                causal_attribution
                circuit_discovery
                shap
                neural_feature_learning

task_scenarios: fact_knowledge
                math
                code
                science
                persona
                safety
                bias
                sycophancy
                social_computation_and_communication

abilities:      information_processing
                understanding
                reasoning
                planning
                innovation
                cognition

components:     mlp_ffn
                attention
                layer_normalization
                neuron
                circuit
                sparse_moe_expert
                word_embedding
                residual_stream

target_models:  free-text model names the user mentioned   (e.g. "GPT-2", "GPT-2 XL", "GPT-J", "CLIP", "LLaMA", "Pythia")
model_families: free-text capitalised family of those models (e.g. "GPT", "CLIP", "LLaMA", "Pythia")
```

## 1.4 — Decomposition rules

**R1. EMPTY-OVER-WRONG.** When you cannot find an exact enum match, the value is `[]` — never substitute. A *wrong* tag actively poisons the BM25 + vector ranking inside the matched bucket; an *empty* tag falls back to semantic search alone and is safe.

| ✗ Wrong | ✓ Right | Why |
|---------|---------|-----|
| `abilities: ["learning"]` | `abilities: ["information_processing"]` or `[]` | "learning" is not in the enum |
| `task_scenarios: ["reasoning"]` | `abilities: ["reasoning"]`, `task_scenarios: []` | "reasoning" is an **ability**, not a task_scenario |
| `components: ["transformer"]` | `components: []` | "transformer" is the architecture, not a component |
| `techniques: ["interpretability"]` | `techniques: []` | "interpretability" is the field name |
| `components: ["FFN"]` | `components: ["mlp_ffn"]` | use the exact enum spelling |

**R2. `task_scenarios` is for FUNCTIONAL TASK LABELS** (what the model is *doing*), not cognitive processes. Set `task_scenarios = []` unless the query clearly targets one of: fact_knowledge, math, code, science, persona, safety, bias, sycophancy, social_computation_and_communication.

**R3. `abilities` is ALMOST ALWAYS `[]`.** Only set it when the query EXPLICITLY centers on reasoning / planning / understanding / cognition / innovation / information_processing as its main topic.

**R4. `min_citations`** — set only if the user says "high-impact", "seminal", "经典", "重要的". Otherwise `null`. For "recent + highly cited", leave `null` (recent papers haven't accrued cites yet).

**R5. STRUCTURAL PAIRING — techniques ↔ components.**
- `circuit_discovery` ↔ `circuit` (and vice versa).
- `feature_dictionary_learning` (SAEs) ↔ `residual_stream` **or** `mlp_ffn` **or** `neuron`, **never** `circuit`.
- `causal_attribution` (activation patching, ROME) ↔ usually `mlp_ffn`, `attention`, or `residual_stream`.
- `probing` ↔ usually `residual_stream` or `attention`.
- `vocabulary_projection` (logit lens, tuned lens) ↔ `residual_stream`.
- `shap` ↔ component-agnostic (often `[]`).

Also pair techniques ↔ task_scenarios where natural: `causal_attribution` on factual recall ↔ `fact_knowledge`; probing for math reasoning ↔ `math` + `abilities:["reasoning"]`; persona/refusal/RLHF interp ↔ `persona` or `safety`. Generic mechanism studies → `task_scenarios:[]`.

**R6. TEMPORAL.** "recent"/"latest"/"近年来"/"新进展" without an explicit year → `year_min = 2024`. "since/from YEAR" → `year_min = YEAR`. "before/until YEAR" → `year_max = YEAR`. The `temporal_mode` argument (§1.7) is a *separate, softer* reranking lever; `year_min`/`year_max` are hard per-sub-query filters. Use both together when the user wants a hard floor *and* a recency tilt.

**R7. SELF-CHECK before submitting.**
1. Every `techniques`/`components`/`task_scenarios`/`abilities` value is **literally** in the enum block (case-sensitive, underscore-separated).
2. Every `sciatlas_db` sub-query has all six interp fields = `[]`.
3. Every sub-query has non-empty `keywords`.
4. `sub_queries` has 1 or 2 items with **distinct `db` values**; `is_cross_domain == (sub_queries.length == 2)`.
5. Each sub-query's `semantic_query` is a single coherent search string (≤60 words) that packs that database's full intent.
6. `original_query` copied **verbatim**, including non-English characters.
7. Each sub-query has a `hyde_text` written per §1.6 (or deliberately omitted to let the cloud service generate it).

**R8. SUB-QUERY COUNT.** At most 2 — one per database. Never emit two sub-queries for the same database; merge that database's topics into its single sub-query instead.

**R9. LANGUAGE.** The user query may be in Chinese or any language. **All `semantic_query`, `keywords`, `domain`, and `hyde_text` must be in English** — both databases index English text. Translate using the field's standard English vocabulary, not literal word-for-word.

**R10. CONTEXT-AWARE DECOMPOSITION (this mode's unique value).** When `task.md` or prior conversation reveals constraints, lean in: previously-narrowed model family → `target_models`/`model_families`; mechanistic-interp upstream goal → bias the interp sub-query's enums toward the upstream technique; ruled-out sub-area → drop it from `sub_queries`; survey sweep → broader `keywords`; follow-up to a specific paper → narrower `keywords` + `target_models` set when known.

## 1.5 — Choose `temporal_mode`

| Mode | When to use |
|------|-------------|
| `default` | Generic survey or follow-up retrieval; no strong recency / history signal. |
| `recent` | User asks for "recent", "latest", "近年来", "新进展", or you're filling the frontier of a development history. (Cloud defaults: α=0.08, year_min≥2020; override via the `recent_alpha` / `recent_min_year` arguments.) |
| `history` | User asks for "发展史", "evolution of", "foundational work", or you're building the long-arc backbone of a development history. |

## 1.6 — Write the HyDE abstract (`hyde_text`) — integrated here

**HyDE = Hypothetical Document Embeddings.** For each sub-query you write a short fake-but-realistic abstract; the cloud service embeds it and uses it as an extra retrieval vector that lands semantically close to real papers on the topic. Writing it here (rather than letting the cloud's small splitter model write it) gives sharper, on-vocabulary abstracts grounded in your full task context.

Write `hyde_text` into **every** sub-query (there are at most two). Length: **120-180 words** for a specific sub-query; **180-260 words** for a BROAD sub-query (one that names a whole research area rather than a specific method/paper — there, enumerate the field's landmark threads instead of faking one paper).

**STRICT RULES (all sub-queries):**
1. Do NOT invent method names, framework names, or acronyms (no "XXX-Net", no "We propose ABC").
2. Do NOT fabricate specific numbers, percentages, or statistics.
3. No title, no keywords line, no markdown (`**`, `##`). One plain paragraph only.
4. Write as if **ANALYZING** an existing phenomenon / testing an established hypothesis — NOT proposing a new method. Use "We investigate…", "We analyze…", "Our analysis reveals…", "Results indicate…", "Findings support the hypothesis that…".
5. Use ONLY real, established terminology that actually appears in that field's published literature.

**For `db == "interp_db"`** — write in mechanistic-interpretability / model-analysis style. Pull from the real vocabulary when relevant: superposition, polysemantic vs monosemantic features, sparse autoencoders / dictionary learning, residual stream, feature steering/splitting/absorption, L0 sparsity, dead features; causal tracing, activation patching, causal mediation analysis, indirect effect, clean/corrupted run, knowledge localization, MLP layers, attention heads, circuit analysis; logit lens / tuned lens; CLIP / ViT / LLaVA decomposition where it's a vision-language query.

**For `db == "sciatlas_db"`** — write in the style of an empirical paper **in that sub-query's own field** (`domain`), using that field's standard instruments, paradigms, and framing. Do NOT default to neuroscience vocabulary for a non-neuro field. Illustrative vocab by field:
- Cognitive neuroscience / psychology: fMRI BOLD, ERP, EEG, dorsolateral prefrontal cortex, hippocampus, default mode network, RSA, MVPA, n-back, prospect theory, theory of mind.
- Wireless sensing / communications: channel state information (CSI), OFDM, multipath propagation, Doppler shift, MIMO, beamforming, time-of-flight, FMCW radar, Wi-Fi sensing, angle-of-arrival.
- Economics / econometrics: difference-in-differences, instrumental variables, regression discontinuity, panel data, treatment effect, fixed effects.
- Materials science / physics: density functional theory (DFT), X-ray diffraction, band gap, ab initio, phase transition, first-principles.
- Molecular biology / genomics: RNA-seq, CRISPR-Cas9, gene expression, knockout, GWAS.
- For any other field, use that field's own equivalent vocabulary.

**BROAD variant** (180-260 words): read like the introduction of a survey paper *in that field* — name the key sub-areas, methods, and canonical concepts; do NOT advocate for one, list them. (E.g. for "mechanistic interpretability": superposition & polysemantic neurons, SAEs / dictionary learning / monosemantic features, induction heads & in-context learning, circuit discovery, causal tracing / activation patching, knowledge neurons in MLPs, residual stream, attention-head decomposition, logit/tuned lens, grokking.)

If you genuinely cannot write a faithful abstract (too little context), **omit `hyde_text`** (or set it to `""`) and the cloud service will generate one — this is the safe fallback, never invent content to fill it.

## 1.7 — Invocation

Call the **`search_papers`** MCP tool. Pass the decomposition as the `decomposed`
argument (a JSON object, **not** a file path) and an **absolute** `output` path
to write the result to. Pick the output path under the current project dir, e.g.:

```text
output:        <ABS_PWD>/mechanic_db_cache/<YYYYMMDD_HHMMSS>_<short_tag>.json
decomposed:    { ... the full decomposition object from §1.1, validated against R1-R10, with hyde_text filled ... }
temporal_mode: default
top_k:         300
```

`<ABS_PWD>` must be the absolute path of the project working directory (run
`pwd` once if unsure) — the MCP server's own cwd is not the project dir, so a
relative `output` would not land where downstream steps read it.

Tool arguments: `output` (required, absolute path), `decomposed` (object) **or**
`query` (string) — mutually exclusive, `temporal_mode {default,recent,history}`,
`recent_alpha`, `recent_min_year` (both recent-only), `top_k`, `timeout`,
`poll_interval`. The tool writes the full response JSON to `output` and returns a
compact `{count, output, skipped}` summary.

## 1.8 — Worked examples

### Example 1 — Single domain, AI interpretability only
**Query:** `"ROME 是怎么实现 rank-one editing 的？"`

```json
{
  "original_query": "ROME 是怎么实现 rank-one editing 的？",
  "is_cross_domain": false,
  "sub_queries": [
    {
      "domain": "AI interpretability",
      "db": "interp_db",
      "semantic_query": "ROME rank-one model editing factual association GPT MLP weight update causal tracing",
      "keywords": ["ROME", "rank-one editing", "factual association"],
      "year_min": null,
      "year_max": null,
      "min_citations": null,
      "techniques": ["causal_attribution"],
      "components": ["mlp_ffn"],
      "task_scenarios": ["fact_knowledge"],
      "abilities": [],
      "target_models": ["GPT-2 XL", "GPT-J"],
      "model_families": ["GPT"],
      "hyde_text": "We investigate how factual associations are stored and edited in autoregressive transformer language models. Using causal tracing, we localize the decisive computation for factual recall to a small set of middle-layer MLP modules at the last subject token, where the feed-forward network behaves as a linear associative memory mapping subject representations to object predictions. We analyze a rank-one update to a single MLP down-projection matrix that inserts a new key-value association while leaving unrelated predictions intact. Our analysis reveals that the edited weight changes the model's factual prediction in a targeted, generalizable way across paraphrases, and we examine specificity by measuring interference on neighboring facts. We compare weight-level editing against fine-tuning and hypernetwork-based editors, and probe the residual stream to characterize how the modified MLP output propagates to the logits. Results indicate that mid-layer MLP layers act as the primary locus of factual knowledge in GPT-style models."
    }
  ]
}
```

### Example 2 — Single domain, neuroscience (sciatlas_db)
**Query:** `"海马体在情景记忆形成中的作用？"`

```json
{
  "original_query": "海马体在情景记忆形成中的作用？",
  "is_cross_domain": false,
  "sub_queries": [
    {
      "domain": "cognitive neuroscience",
      "db": "sciatlas_db",
      "semantic_query": "hippocampus role episodic memory formation encoding consolidation medial temporal lobe",
      "keywords": ["hippocampus", "episodic memory", "memory consolidation", "medial temporal lobe"],
      "year_min": null,
      "year_max": null,
      "min_citations": null,
      "techniques": [],
      "components": [],
      "task_scenarios": [],
      "abilities": [],
      "target_models": [],
      "model_families": [],
      "hyde_text": "We investigate the role of the hippocampus in the encoding and consolidation of episodic memories. Using event-related fMRI and intracranial recordings during associative encoding tasks, we measured BOLD responses and theta-band activity in the hippocampus and surrounding medial temporal lobe structures, including entorhinal and parahippocampal cortex. Our analysis relates subsequent-memory effects at encoding to successful retrieval, and examines how hippocampal-neocortical interactions during post-encoding rest and sleep support systems-level consolidation. Representational similarity analysis indicates that the hippocampus binds distributed cortical features into integrated event representations, while pattern separation and pattern completion processes in dentate gyrus and CA3 distinguish overlapping experiences. Findings support the hypothesis that the hippocampus is necessary for rapid encoding of episodic detail and for reinstating cortical activity patterns during retrieval, with gradual transfer to neocortex over time."
    }
  ]
}
```

### Example 3 — Cross-domain (AI interp + cognitive neuroscience)
**Query:** `"belief/confidence/uncertainty in LLMs and human brain"`

```json
{
  "original_query": "belief/confidence/uncertainty in LLMs and human brain",
  "is_cross_domain": true,
  "sub_queries": [
    {
      "domain": "AI interpretability",
      "db": "interp_db",
      "semantic_query": "uncertainty confidence belief representation in LLM, calibration features, epistemic uncertainty probing transformer",
      "keywords": ["uncertainty", "confidence", "belief representation"],
      "year_min": null,
      "year_max": null,
      "min_citations": null,
      "techniques": ["probing", "representation_and_parameter_analysis"],
      "components": ["residual_stream"],
      "task_scenarios": [],
      "abilities": ["cognition"],
      "target_models": [],
      "model_families": [],
      "hyde_text": "We investigate how large language models internally represent confidence and uncertainty about their own predictions. Using linear probes trained on residual stream activations, we analyze whether a low-dimensional direction encodes the model's epistemic state, separating cases where the model is confidently correct from confidently wrong. Our analysis relates these internal signals to output token probabilities and calibration, and tests whether probing-derived uncertainty estimates generalize across factual recall, arithmetic, and multiple-choice formats. We further examine representation- and parameter-level structure to characterize where belief-like signals emerge across layers, and whether steering along the identified direction modulates hedging behavior. Results indicate that an internal notion of confidence is linearly decodable and partially dissociable from surface output probabilities."
    },
    {
      "domain": "cognitive neuroscience",
      "db": "sciatlas_db",
      "semantic_query": "belief uncertainty confidence representation human brain prefrontal cortex Bayesian inference neural correlates",
      "keywords": ["belief", "uncertainty", "Bayesian brain", "prefrontal cortex"],
      "year_min": null,
      "year_max": null,
      "min_citations": null,
      "techniques": [],
      "components": [],
      "task_scenarios": [],
      "abilities": [],
      "target_models": [],
      "model_families": [],
      "hyde_text": "We investigate the neural representation of belief, confidence, and uncertainty during perceptual and value-based decision making. Using fMRI and computational modeling, we fit Bayesian and drift-diffusion models to behavior and regress trial-by-trial estimates of decision confidence and uncertainty against BOLD activity. Our analysis identifies correlates in dorsolateral and ventromedial prefrontal cortex, anterior cingulate, and parietal cortex, and examines how the brain encodes both estimation uncertainty and confidence in a choice. Findings support the hypothesis that prefrontal circuits implement an approximate Bayesian computation, representing graded certainty that guides information seeking and metacognitive report."
    }
  ]
}
```

### Example 4 — Recent frontier, single interp domain (recency via temporal_mode + year_min + vocab)
**Query:** `"SAE 上有没有什么新的扩展方法？"`

The "newness" is carried three ways: the `temporal_mode: recent` argument, `year_min: 2024` (R6), and recency-flavored vocabulary in `semantic_query` / `hyde_text`.

```json
{
  "original_query": "SAE 上有没有什么新的扩展方法？",
  "is_cross_domain": false,
  "sub_queries": [
    {
      "domain": "AI interpretability",
      "db": "interp_db",
      "semantic_query": "recent extensions sparse autoencoders LLM interpretability transcoders cross-layer SAE feature splitting scaling",
      "keywords": ["sparse autoencoder", "transcoders", "feature splitting"],
      "year_min": 2024,
      "year_max": null,
      "min_citations": null,
      "techniques": ["feature_dictionary_learning"],
      "components": ["residual_stream", "neuron"],
      "task_scenarios": [],
      "abilities": [],
      "target_models": [],
      "model_families": [],
      "hyde_text": "We investigate recent extensions to sparse autoencoders for decomposing the activations of large language models into interpretable features. We analyze variants that modify the sparsity mechanism and architecture, including approaches that replace MLP computation with learned dictionaries and methods that share features across layers of the residual stream. Our analysis characterizes how dictionary width and sparsity interact with reconstruction fidelity, the prevalence of dead features, and feature splitting and absorption as scale increases. We evaluate monosemanticity of recovered features through activation analysis and steering, and compare training objectives that aim to reduce shrinkage in the sparse code. Results indicate that architectural and objective changes can improve the fidelity-interpretability trade-off relative to baseline sparse autoencoders while exposing new failure modes in feature geometry."
    }
  ]
}
```

---

# Mode 2 — Flat free-form query (FALLBACK)

Use this only when the Agent's task context is too thin to fill out the decomposed JSON honestly (e.g. a one-shot call with no `task.md`, no upstream goal, no prior turns). The cloud splitter then handles decomposition **and HyDE generation** on a best-effort basis, but recall is meaningfully worse than decomposed mode — there is no upside when context is available.

## 2.1 — Query quality rules

| Rule | Detail |
|------|--------|
| **English only** | Both databases index English text. Translate Chinese / other-language user terms using the field's standard English vocabulary. |
| **Pack synonyms and technical terms** | Name the field's actual jargon ("ROME rank-one editing causal tracing factual association MLP") rather than vague paraphrase. |
| **Cover all relevant domains** | Name each domain's terminology in the same query — the cloud splitter fans them out. |
| **Length** | Aim for ≤80 words. Beyond that, focus dilutes. |
| **Preserve user's named entities** | Model names ("GPT-2 XL", "Pythia", "LLaMA"), method names ("SAE", "ROME", "logit lens"), dataset names appear verbatim when the user mentioned them. |

## 2.2 — Invocation

Call the **`search_papers`** MCP tool with the flat `query` instead of
`decomposed`:

```text
output:        <ABS_PWD>/mechanic_db_cache/<YYYYMMDD_HHMMSS>_<short_tag>.json
query:         <the polished English query from §2.1, verbatim>
temporal_mode: default
top_k:         300
```

When context becomes available later (e.g. after reading `task.md`), prefer rebuilding the call in Mode 1.

---

# Read the result

The `search_papers` tool writes the full response JSON to the `output` path. The only field downstream should rely on is `papers[]`:

```json
{
  "papers": [
    {
      "paper_id": "W123...",
      "title": "...",
      "year": 2023,
      "cited_by_count": 42,
      "abstract": "...",
      "doi": "...",
      "authors": [...]
    }
  ],
  "skipped": false
}
```

When the output JSON contains `"skipped": true`, treat mechanic-db as an unavailable source for this run.

Order: fused rank across all rankers (best first). The output JSON is the data carrier for this skill.


---

# Evaluate and refine (multi-round)

Skim returned titles to judge coverage. Titles clearly unrelated to the **original** user query are ranker noise — discount them.

When coverage is unsatisfactory, refine and call again (new output path to keep both rounds side by side). Cap at **3 rounds** per caller.

| Symptom | Adjustment |
|---------|-----------|
| Results off-topic | Tighten `semantic_query`; tighten the interp enums; raise specificity of `keywords`; sharpen `hyde_text` toward the exact sub-topic. |
| Missing cross-domain content | Add the missing database's sub-query (or, if it exists, broaden its `semantic_query` + `keywords` + `hyde_text` to name the intersection); ensure `is_cross_domain: true` when both dbs are present. |
| Missing a sub-field | Broaden the relevant database's single sub-query (`semantic_query` + `keywords`) to cover it — do NOT add a second sub-query for the same db. |
| Too few results | Increase `top_k`; relax `year_min`/`min_citations`. |
| Recency mismatch | Switch `temporal_mode` and/or set `year_min`. |
| Wrong-enum suspicion | Re-run R7 self-check; replace bad enum values with `[]`. |
| HyDE drifted off-topic | Rewrite `hyde_text` with field-specific vocabulary, analysis (not proposal) framing; or omit it to let the cloud service regenerate. |
| Returned 0 papers | Usually too-strict filters (`year_min`/`min_citations`/over-tight enums); re-call with relaxed decomposition. |

---

# Failure modes & graceful degradation

| Symptom | `search_papers` behaviour | Caller's responsibility |
|---------|---------------------------|--------------------------|
| HTTP 401 / 403 (invalid key) | Returns an `isError` result carrying the server message. | Treat as unavailable; proceed. |
| HTTP 429 (quota exhausted) | Returns an `isError` result with the message. | Proceed with other sources. |
| HTTP 5xx / connection error | Returns an `isError` result. | Proceed with other sources. |
| Polling timeout (>1200 s) | Returns an `isError` result (`polling exceeded …`). | Proceed with other sources. |
| Job status `failed` / `error` | Returns an `isError` result with the server's error payload. | Proceed with other sources. |

This skill is **an important supplement**, never a replacement: callers (`/research-lit`, `/idea-creator`, `/mhistory`, …) merge its results with their existing sources (arXiv, S2, Zotero, local PDFs, Exa, DeepXiv, WebSearch) and de-duplicate by `paper_id` / `doi` / normalized title.
