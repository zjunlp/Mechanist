# LLMs Know API Reference

## Module: src.compute_correctness

Functions for computing correctness of model outputs across different datasets.

### Function: compute_correctness_imdb(model_answers, labels)

Compute correctness for IMDB sentiment analysis task.

**Parameters:**
- `model_answers` (List[str]): Model predictions for sentiment
- `labels` (List[int]): Ground truth sentiment labels (0=negative, 1=positive)

**Returns:**
- `List[int]`: Binary correctness labels (1=correct, 0=incorrect)

**Source:** `src/compute_correctness.py`

---

### Function: compute_correctness_triviaqa(all_textual_answers, labels)

Compute correctness for TriviaQA question-answering task.

**Parameters:**
- `all_textual_answers` (List[str]): Model's generated answers
- `labels` (List[List[str]]): Acceptable ground truth answers

**Returns:**
- `List[int]`: Binary correctness labels

**Source:** `src/compute_correctness.py`

---

### Function: compute_correctness_winobias(model_answers, labels, wrong_labels)

Compute correctness for Winobias coreference resolution task.

**Parameters:**
- `model_answers` (List[str]): Model's pronoun resolutions
- `labels` (List[str]): Correct pronoun references
- `wrong_labels` (List[str]): Incorrect pronoun options

**Returns:**
- `List[int]`: Binary correctness labels

**Source:** `src/compute_correctness.py`

---

## Module: src.extract_exact_answer

Functions for extracting exact answers from generated text.

### Function: extract_exact_answer(model, tokenizer, correctness)

Extract exact answer tokens from model outputs.

**Parameters:**
- `model` (AutoModelForCausalLM): The language model
- `tokenizer` (AutoTokenizer): Model's tokenizer
- `correctness` (Dict): Dictionary containing model outputs and correctness labels

**Returns:**
- `Dict`: Updated correctness dictionary with exact answers

**Source:** `src/extract_exact_answer.py`

---

## Module: src.generate_model_answers

Functions for generating model answers on various datasets.

### Function: load_data_movies(test)

Load movie QA dataset.

**Parameters:**
- `test` (bool): Whether to load test set (True) or train set (False)

**Returns:**
- `pd.DataFrame`: Loaded movie dataset

**Source:** `src/generate_model_answers.py`

---

### Function: load_data_nli(split, data_file_names)

Load NLI (MNLI) dataset.

**Parameters:**
- `split` (str): Dataset split ('train' or 'validation')
- `data_file_names` (Dict[str, str]): Mapping of split names to file paths

**Returns:**
- `pd.DataFrame`: Loaded NLI dataset

**Source:** `src/generate_model_answers.py`

---

## Module: src.logprob_detection

Functions for hallucination detection using log probabilities.

### Function: load_logits(model_name, dataset, load_test)

Load pre-computed logits for a model and dataset.

**Parameters:**
- `model_name` (str): Hugging Face model identifier
- `dataset` (str): Dataset name
- `load_test` (bool): Whether to load test set

**Returns:**
- `torch.Tensor`: Logits tensor

**Source:** `src/logprob_detection.py`

---

### Function: load_input_output_ids(model_name, dataset, load_test)

Load tokenized input and output IDs.

**Parameters:**
- `model_name` (str): Model identifier
- `dataset` (str): Dataset name  
- `load_test` (bool): Whether to load test set

**Returns:**
- `Tuple[torch.Tensor, torch.Tensor]`: Input and output ID tensors

**Source:** `src/logprob_detection.py`

---

## Module: src.p_true_detection

Functions for hallucination detection using P(True) method.

### Function: get_p_true(data, model, tokenizer)

Calculate P(True) scores for hallucination detection.

**Parameters:**
- `data` (pd.DataFrame): Dataset with questions and answers
- `model` (AutoModelForCausalLM): Language model
- `tokenizer` (AutoTokenizer): Model tokenizer

**Returns:**
- `np.ndarray`: P(True) scores for each sample

**Source:** `src/p_true_detection.py`

---

## Module: src.probe

Core probing functionality for analyzing model representations.

### Function: train_probe(representations, labels, seeds, test_size=0.2)

Train a linear probe classifier on representations.

**Parameters:**
- `representations` (np.ndarray): Feature matrix (n_samples, n_features)
- `labels` (np.ndarray): Binary labels
- `seeds` (List[int]): Random seeds for multiple runs
- `test_size` (float): Fraction for test set

**Returns:**
- `Dict`: Training results including accuracy, precision, recall, F1

**Source:** `src/probe.py`

---

### Function: extract_representations(model, tokenizer, texts, layer_idx, token_position, probe_location)

Extract internal representations from specified model location.

**Parameters:**
- `model` (AutoModelForCausalLM): Language model
- `tokenizer` (AutoTokenizer): Model tokenizer
- `texts` (List[str]): Input texts
- `layer_idx` (int): Layer index to probe
- `token_position` (str): Token position ('last', 'first', or index)
- `probe_location` (str): Where to probe ('mlp', 'attention', etc.)

**Returns:**
- `np.ndarray`: Extracted representations

**Source:** `src/probe.py`

---

## Module: src.probe_all_layers_and_tokens

Functions for comprehensive layer and token analysis.

### Function: probe_all_layers(model, data, probe_config)

Probe all layers of a model to create performance heatmaps.

**Parameters:**
- `model` (AutoModelForCausalLM): Model to probe
- `data` (Dict): Dataset dictionary
- `probe_config` (Dict): Configuration for probing

**Returns:**
- `pd.DataFrame`: Probing results across layers and tokens

**Source:** `src/probe_all_layers_and_tokens.py`

---

## Module: src.probe_choose_answer

Functions for answer selection using trained probes.

### Function: choose_best_answer(probe, candidate_answers, representations)

Select the best answer from candidates using a trained probe.

**Parameters:**
- `probe` (LogisticRegression): Trained probe classifier
- `candidate_answers` (List[str]): Candidate answers to choose from
- `representations` (np.ndarray): Representations of candidates

**Returns:**
- `Tuple[str, float]`: Best answer and confidence score

**Source:** `src/probe_choose_answer.py`

---

## Module: src.probe_type_of_error

Functions for analyzing error types in model outputs.

### Function: classify_error_type(resampled_answers, ground_truth)

Classify the type of error based on resampled outputs.

**Parameters:**
- `resampled_answers` (List[str]): Multiple sampled answers
- `ground_truth` (str): Correct answer

**Returns:**
- `str`: Error type classification

**Source:** `src/probe_type_of_error.py`

---

## Module: src.probing_utils

Utility functions for probing experiments.

### Function: get_probe_location(model, layer_idx, probe_at)

Get the specific module to probe in a model.

**Parameters:**
- `model` (nn.Module): The neural network model
- `layer_idx` (int): Layer index
- `probe_at` (str): Probe location identifier

**Returns:**
- `nn.Module`: Module to probe

**Source:** `src/probing_utils.py`

---

### Function: normalize_representations(representations, method='standard')

Normalize representations for probing.

**Parameters:**
- `representations` (np.ndarray): Raw representations
- `method` (str): Normalization method ('standard', 'minmax', 'l2')

**Returns:**
- `np.ndarray`: Normalized representations

**Source:** `src/probing_utils.py`

---

## Module: src.resamples_utils

Utilities for handling resampled model outputs.

### Function: aggregate_resamples(resampled_outputs, aggregation='majority')

Aggregate multiple resampled outputs.

**Parameters:**
- `resampled_outputs` (List[List[str]]): Resampled outputs
- `aggregation` (str): Aggregation method

**Returns:**
- `List[str]`: Aggregated outputs

**Source:** `src/resamples_utils.py`

---

## Module: src.resampling

Functions for generating multiple samples from models.

### Function: resample_answers(model, tokenizer, questions, n_resamples, temperature=0.7)

Generate multiple answer samples for questions.

**Parameters:**
- `model` (AutoModelForCausalLM): Language model
- `tokenizer` (AutoTokenizer): Model tokenizer
- `questions` (List[str]): Input questions
- `n_resamples` (int): Number of resamples
- `temperature` (float): Sampling temperature

**Returns:**
- `List[List[str]]`: Resampled answers for each question

**Source:** `src/resampling.py`

---

## Module: src.resampling_merge_runs

Functions for merging parallel resampling runs.

### Function: merge_resampling_files(input_files, output_file)

Merge multiple resampling output files.

**Parameters:**
- `input_files` (List[str]): Paths to input files
- `output_file` (str): Path to merged output file

**Returns:**
- `None`: Writes merged data to output file

**Source:** `src/resampling_merge_runs.py`

---

## Configuration Parameters

### Supported Models
- `mistralai/Mistral-7B-Instruct-v0.2`
- `mistralai/Mistral-7B-v0.3`
- `meta-llama/Meta-Llama-3-8B`
- `meta-llama/Meta-Llama-3-8B-Instruct`

### Probe Locations
- `mlp`: Probe at MLP layers
- `mlp_last_layer_only_input`: Probe at last MLP layer input
- `attention`: Probe at attention layers

### Token Positions
- `last`: Last token in sequence
- `first`: First token in sequence
- `exact_answer_last_token`: Last token of exact answer
- Integer index: Specific token position

### Dataset Names
- `triviaqa` / `triviaqa_test`
- `hotpotqa` / `hotpotqa_test`
- `movies` / `movies_test`
- `winobias` / `winobias_test`
- `winogrande` / `winogrande_test`
- `mnli` / `mnli_test`
- `imdb` / `imdb_test`
- `math` / `math_test`
- `nq` (Natural Questions)
