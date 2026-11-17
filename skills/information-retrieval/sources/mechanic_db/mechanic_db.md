# Mechanic DB retrieval

Run [sources/mechanic_db/search.py](search.py) with Python. Resolve its path relative to the information-retrieval skill directory rather than the research working directory. Install [requirements.txt](requirements.txt) in the chosen environment if needed.

```text
python /path/to/information-retrieval/sources/mechanic_db/search.py --query "activation patching factual recall" --output /path/to/papers.json
python /path/to/information-retrieval/sources/mechanic_db/search.py --decomposed-file /path/to/query.json --output /path/to/papers.json --temporal-mode recent
```

Use `--query` for plain English text, or `--decomposed-file` for a UTF-8 JSON object following the [query construction guidance](#query-construction). Use `-` as the filename to read the object from stdin. The guidance explains database routing, exact fields, terminology, and optional HyDE; a hypothetical abstract is a retrieval aid, not a citation or finding.

Choose `--output` for the full result JSON. Relative paths resolve against the script's working directory; an absolute path avoids ambiguity. Stdout returns a compact JSON summary with count, tier, and the resolved output path; read that file for papers. This is a tool output requirement, not a research-wide storage convention.

Set `MECHANIC_DB_API_KEY` in the script's environment if available; anonymous access has lower limits. `MECHANIC_DB_BASE_URL` optionally changes the service URL. Credentials are not command-line arguments. The script retains direct connections to this service, ignoring ambient proxy variables.

`--temporal-mode` accepts `default`, `recent`, and `history`; `--top-k`, `--timeout`, `--poll-interval`, `--recent-alpha`, and `--recent-min-year` are configurable. Submission, rate-limit retries, and polling share the requested timeout. The service admits one search at a time and can take minutes. Failure prints JSON to stderr and exits nonzero; it is not an empty successful search. Refine queries when useful rather than for a fixed number of rounds.

## Query construction

### 1.1 — Decomposed JSON shape

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

### 1.2 — Route the query to databases

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

### 1.3 — Closed enums for interp_db structured fields (interp_db sub-queries only)

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

### 1.4 — Decomposition rules

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

**R4. `min_citations`** — set only if the user says "high-impact", "seminal", "classic", "important". Otherwise `null`. For "recent + highly cited", leave `null` (recent papers haven't accrued cites yet).

**R5. STRUCTURAL PAIRING — techniques ↔ components.**
- `circuit_discovery` ↔ `circuit` (and vice versa).
- `feature_dictionary_learning` (SAEs) ↔ `residual_stream` **or** `mlp_ffn` **or** `neuron`, **never** `circuit`.
- `causal_attribution` (activation patching, ROME) ↔ usually `mlp_ffn`, `attention`, or `residual_stream`.
- `probing` ↔ usually `residual_stream` or `attention`.
- `vocabulary_projection` (logit lens, tuned lens) ↔ `residual_stream`.
- `shap` ↔ component-agnostic (often `[]`).

Also pair techniques ↔ task_scenarios where natural: `causal_attribution` on factual recall ↔ `fact_knowledge`; probing for math reasoning ↔ `math` + `abilities:["reasoning"]`; persona/refusal/RLHF interp ↔ `persona` or `safety`. Generic mechanism studies → `task_scenarios:[]`.

**R6. TEMPORAL.** "recent"/"latest"/"in recent years"/"new developments" without an explicit year → choose a justified window relative to the current date. "since/from YEAR" → `year_min = YEAR`. "before/until YEAR" → `year_max = YEAR`. The `temporal_mode` argument (§1.7) is a *separate, softer* reranking lever; `year_min`/`year_max` are hard per-sub-query filters. Use both together when the user wants a hard floor *and* a recency tilt.

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

### 1.5 — Choose `temporal_mode`

| Mode | When to use |
|------|-------------|
| `default` | Generic survey or follow-up retrieval; no strong recency / history signal. |
| `recent` | User asks for "recent", "latest", "in recent years", "new developments", or you're filling the frontier of a development history. (Cloud defaults: α=0.08, year_min≥2020; override via the `recent_alpha` / `recent_min_year` arguments.) |
| `history` | User asks for "development history", "evolution of", "foundational work", or you're building the long-arc backbone of a development history. |

### 1.6 — Write the HyDE abstract (`hyde_text`) — integrated here

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
