# Research task — take a behavior as given, then discover its mechanism
<!-- Run: /auto — behavior-source: given, mechanism: discovery -->

## Behavior (given)
Take the following behavior as established — do not re-validate it. On matched
propositions, instruction-tuned LLMs handle first-person belief attributions less
reliably than third-person ones: when asked to confirm the truth of a true statement P,
accuracy on the first-person framing ("I believe that P. Is P true?") is systematically
lower than on the matched third-person framing ("James believes that P. Is P true?").

"Belief" is defined per *Language models cannot reliably distinguish belief from
knowledge and fact* (Suzgun et al., 2024; the KaBLE benchmark).

## Scope
- Falsifiable mechanistic hypothesis: which internal component / layer / direction carries
  the first-person epistemic framing, and how does it causally produce the accuracy drop?
- Include at least one "boring" null.

## Resources
- Models: Llama-3.1-8B-Instruct, Mistral-7B-Instruct-v0.2.
- Data: the KaBLE dataset from the paper above (extend with matched controls as needed).
