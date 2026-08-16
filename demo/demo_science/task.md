# Task: Generating α-Helical DNA via Feature Steering — Validating that Evo2 Internal Features Can Causally Control Protein Secondary Structure  
<!-- Run mode: /auto — behavior-source: given-validation, mechanism: given -->

## Task Overview  
Within the pre-trained SAE of Evo2-7B, first confirm the existence of a set of features that selectively respond to "α-helix", then autoregressively generate DNA by amplifying those features, determine the optimal amplification strength, and use protein structure prediction tools to verify whether the α-helical content of the protein encoded by the generated sequences increases with the amplification strength, thereby proving that the feature is a causally manipulable knob.

## Reference Paper  
- *Genome modelling and design across all domains of life with Evo 2*.
- *InterPLM: discovering interpretable features in protein language models*.

## Model / Data  
- **Evo2-7B**: Download from `huggingface.co/arcinstitute/evo2_7b_262k`;  
- **SAE (Layer 26)**: Download from `huggingface.co/Goodfire/Evo-2-Layer-26-Mixed`.  
- **Hugging Face Token**: <Your_token>
- Other required datasets and tools may refer to the original paper’s configuration or be independently investigated and used.

## Environment  
- conda environment `scientist`: torch+CUDA, vortex/evo2, transformers, biopython, DSSP.  
- GPU: local machine 8×A800-80GB, up to 4 GPUs can be used simultaneously.

## Experiment Tips

- **Data.** Do NOT reverse-translate protein into DNA (codon-degeneracy noise + unnatural patterns). Use natural CDS from databases, annotating codons with real secondary-structure labels from experimental structures after proper alignment.

- **Feature selection is the biggest driver of success — and the hardest part.** Expect many tries; treat "find a better set" as the main job of the main experiment and iteration stage. A good "manipulable knob" set exists, but a bad set fails the whole task. Select by output-side causal effect, not input-side correlation:
  - *Correlation ≠ causal knob.* A feature correlated with helix (high Cohen's d / F1 on activations) is often just a "detector" — amplifying it may do nothing, break the ORF, or even lower helix. Working features often have different IDs, found only from the output side. (Thermometer vs thermostat.)
  - *Two-stage funnel.* (1) Input-side screen (cheap, no generation): shortlist a broad pool at a permissive threshold (e.g. Cohen's d ≥ 0.3, a few dozen); don't over-filter. (2) Output-side screen (real gate): steer each candidate individually → ESMFold → DSSP → measure Δα-helix vs baseline; admit only those with positive Δα-helix at an acceptable valid-fold rate.
  - *Rank by robustness, not just effect size.* Prefer features that are simultaneously high-Δ, high-valid-rate, and high-pLDDT; lead claims with those.
  - *Single vs joint steering.* Default to single-feature intervention (screen and headline claim per feature), also try joint multi-feature steering of the top candidates.

- **Scoring & validity.** Use the real scorer (ESMFold → DSSP). Evo2 outputs are off-distribution, so pLDDT ≥ 60 can reject most baselines and hide the signal — sweep the threshold, report both, and keep length / no-premature-stop filters. The feature may only beat the random control after pLDDT filtering.

- **Dose-response.** Look for a monotonic-increasing interval up to an interior optimum, not global monotonicity: effects rise, saturate, then collapse under over-steering. Confirm the feature beats norm-matched random-direction / random-feature controls under the same validity gating.

## Execution Instructions  
You are now automatically executing the experiment without human supervision. In the face of any situation, you have the highest autonomous decision-making authority.  
If the experiment encounters obstacles or unsatisfactory results, you must adjust on your own and continue the experiment. I will check your work progress in 24 hours.  
If you can not prepare tools and datasets well (e.g. need `sudo` to install some tools), stop and ask human to manage it. Do Not degrade the experiment due to this reason.
Send a brief report email to me (<your_email_address>) when you make progresses.