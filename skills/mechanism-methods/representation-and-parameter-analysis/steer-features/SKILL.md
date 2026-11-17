---
name: steer-features
description: "Use this skill for feature-level steering of models \u2014 locating the internal feature that drives a target behavior, scoring and selecting it by its effect on the model's output, and directly amplifying or shrinking that feature's activation during generation to control behavior. Applies to features read from the model's own activations or from a Sparse Autoencoder (SAE); the bundled demo scripts happen to use an SAE, but the method does not require one."
---

## Method and use

Select internal features for behavioral control using input and output effects. Decide whether to clamp, scale, add a decoder direction, or replace a reconstruction. Check residual and reconstruction effects. The scoring and hook templates require real method adapters rather than random scores or directions.


# SAEs Are Good for Steering - If You Select the Right Features

> **Note — an SAE is optional.** The method itself only needs to locate the feature that drives the target behavior and scale its activation in place during generation. When the features live in a Sparse Autoencoder (SAE), the same intervention takes the encode → amplify/diminish target feature → decode form (Feature Clamping): the SAE encodes the residual stream into feature space, the target feature's activation is scaled, and the result is SAE decoded back. The demo scripts here use an SAE, but that is a property of this demo, not a requirement of the method. 

## When to Use
This skill should be activated when:
- Working with Sparse Autoencoders (SAEs) for model interpretability
- Steering language model outputs toward specific concepts or behaviors
- Analyzing and scoring SAE features (input vs output features)
- Implementing unsupervised decomposition of model latent spaces
- Comparing SAE steering with supervised steering methods
- Working with models like Gemma, LLaMA, or Pythia for feature-based steering
- Evaluating feature effectiveness for model control

Keywords: SAE, sparse autoencoder, model steering, feature selection, interpretability, latent space decomposition, output scoring, input scoring, neural network control

## Quick Reference
- **Paper**: [SAEs Are Good for Steering -- If You Select the Right Features](https://arxiv.org/abs/2505.20063)
- **Website**: [Project Page](https://technion-cs-nlp.github.io/saes-are-good-for-steering/)
- **Repository**: [GitHub](https://github.com/technion-cs-nlp/saes-are-good-for-steering)
- **Related Tool**: [Neuronpedia API](https://www.neuronpedia.org/api-doc#tag/features/POST/api/activation/new) for feature data

## Installation/Setup
```bash
# Install required packages
pip install -r requirements
pip install accelerate
pip install sae-lens

# For development/testing
git clone https://github.com/technion-cs-nlp/saes-are-good-for-steering
cd saes-are-good-for-steering
```

### Prerequisites
- Python 3.8+
- CUDA-capable GPU recommended for model inference
- Sufficient RAM for loading language models

## Core Features
- **Output Score Calculation**: Characterize features based on their effect on model output
- **Input Score Calculation**: Analyze features based on input token activation patterns
- **Feature Filtering**: Remove low-scoring features to improve steering effectiveness
- **Multi-Model Support**: Works with Gemma (2B/9B), LLaMA 3.1, and Pythia models
- **SAE Hook Integration**: Amplify specific SAE features during model inference
- **Generation Analysis**: Evaluate steering success with various metrics
- **Data Processing**: Handle feature data from Neuronpedia and custom sources

## Choosing an intervention

Clamping, scaling, decoder-direction addition, reconstruction replacement, and residual-preserving edits test different operations. Select the operation that fits and check reconstruction effects; see [intervention practice](../../../human-expertise/interventions.md). Templates need adaptation to the actual SAE and hook point.

## Usage Examples

### Calculate Output Scores
```bash
python ./src/output_score.py --model_type=<model_type> --features_file=<features_json> --cache_path=<filename_to_load_and_save>
```

### Calculate Input Scores
First, download feature data from Neuronpedia, then run:
```bash
python ./src/input_score.py --model_type=<model_type> --features_file=<features_json> --cache_path=<filename_to_load_and_save> --feature_data_path=<path>
```

### Example Model Types
- `gemma_2b`
- `gemma_9b`
- `gemma_9b_it` (instruction-tuned)
- `llama31`
- `pythia70`

## Key APIs/Models

### Supported Models
- **Gemma 2B**: Base language model for lightweight steering
- **Gemma 9B**: Larger capacity model for complex steering tasks
- **Gemma 9B-IT**: Instruction-tuned variant with enhanced steering capabilities
- **LLaMA 3.1**: Meta's language model for comparative analysis
- **Pythia 70M**: Small-scale model for rapid experimentation

### Core Classes/Functions
- `AmlifySAEHook`: Hook class for amplifying SAE features during inference
- `get_output_score()`: Calculate output scores for features
- `get_generation_success()`: Evaluate steering effectiveness
- `init_hook()`: Initialize SAE hooks for model steering

### Configuration Files
- Feature definitions: JSON files specifying layer, feature indices, and metadata
- Cache files: Stored scores and generation results for efficiency
- Instruction sets: Curated prompts for Concept500 evaluation

## Common Patterns & Best Practices

### Feature Selection Strategy
1. Calculate both input and output scores for all features
2. Filter out features with low output scores (< threshold)
3. Select features with high output scores but moderate input scores
4. This approach yields 2-3x improvement in steering effectiveness

### Efficient Processing
- Use caching to avoid recomputing scores
- Process features in batches when possible
- Store intermediate results for iterative analysis

### Steering Factor Optimization
- Test multiple steering factors (0.2 to 20.0)
- Start with lower factors for subtle steering
- Increase gradually to find optimal balance between effect and fluency

## Data Organization

### Available Datasets
- **Feature Files**: Pre-selected features for each model variant
- **Generated Texts**: Outputs at various steering factors
- **LLM Scores**: External evaluation of concept adherence, instruction following, and fluency
- **Axbench Instructions**: 131 instruction prompts for comprehensive evaluation

### File Structure

## Demo Scripts

### `scripts/compute_scores.py`


See [`scripts/compute_scores.py`](scripts/compute_scores.py) for the reference template. Adapt its model, data, and measurement assumptions.


### `scripts/steer_model.py`


See [`scripts/steer_model.py`](scripts/steer_model.py) for the reference template. Adapt its model, data, and measurement assumptions.


> Implementation status: some bundled functions are adaptation templates and raise `NotImplementedError` until connected to the actual method. Consult the API reference and source method; do not interpret demonstration outputs as measurements.

## Supporting material

- [api reference](references/api_reference.md): implementation detail for the selected backend.
- [Method papers](article_references.md).
- [Family papers](../article_references.md).
