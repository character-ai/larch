# Review Round 2

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 0
- Exonerated findings: 3
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Empty-merge attestation contract, coverage gaps, and trust boundary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-attestation-protocol-output.txt, dyn-slot-normalization-symmetry-output.txt, dyn-test-coverage-gaps-output.txt
- **Concern**: Merge output with zero `### FINDING_N:` blocks now requires an explicit final-line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` whenever the input ballot still contains structured findings—stricter than an “unconditional clean pass on empty structured output” plan narrative—so narrative-only empty merges fail closed (`validation-failed`) and leave `findings.md` unchanged unless operators/templates match the new machine contract. There is broad agreement this needs stronger CI pinning (negative stub without the line; optionally assert the line survives into the rewritten ballot on the success path). Separately, accepting the bare public literal is only a weak integrity boundary: a mis-prompted or adversarially shaped merge can still clear structured findings while satisfying the string check, which should be treated as an LLM-trust/policy issue (monitor `REASON=ok-zero-findings`, document expectations, tighten only if policy demands provable binding).
- **Suggested revision**: Treat attestation as the explicit runtime contract: reconcile written plan/issue text with shipped behavior (or revert behavior to match plan), document across aggregator entrypoints/custom templates, add the missing negative regression(s), and tighten success assertions if the contract is “line must appear in persisted output,” plus document the trust model for the magic line.


### FINDING_10: Orchestrator prompt formatting may cause models to emit non-matching attestation lines
- **Reviewer(s)**: dyn-attestation-protocol-output.txt
- **Concern**: Instructions demand a final line exactly equal to `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, but exemplars shown as Markdown inline code/backticks can cause compliant-intent outputs like backtick-wrapped or bullet-prefixed lines that fail the script’s exact-line predicate.
- **Suggested revision**: Show the required line as plain text (e.g., a `text` fence) and explicitly forbid backticks/bullets/markdown wrappers around the token.


### FINDING_2: Misleading `input_blocks` emptiness check after non-empty `input_slot_set`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-slot-normalization-symmetry-output.txt
- **Concern**: Multiple reviewers read `if not input_blocks(intext): return 0` (early in the zero-output validation path) as unreachable/misleading once `input_slot_set` is guaranteed non-empty from the same parsing pipeline, which harms maintainability and risks future refactors reintroducing subtle holes.
- **Suggested revision**: Remove the dead branch, replace with an explicit invariant/assertion + comment, or restructure checks so the intended fast-path vs fail-closed contract is obvious.


### FINDING_4: Input-side slot normalization vs planned output-only normalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Slots extracted from the input ballot are normalized (not only merge-output slots), diverging from a plan that described output-only normalization; this can change acceptance/dedup behavior versus the written asymmetry and can theoretically collapse distinct raw labels if they differ only by a trailing `(...)`.
- **Suggested revision**: Either narrow code to match the agreed plan scope, or update the plan/issue to explicitly require symmetric normalization and document the invariant that raw slot labels must not differ only by parenthetical suffixes unless that collapse is intended.


### FINDING_6: New success signal `REASON=ok-zero-findings` may break external consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Successful attested empty merges surface `REASON=ok-zero-findings` instead of always `REASON=ok`, which can misclassify success in out-of-repo dashboards/scripts that key only on `REASON=ok`, and also diverges from plan text that expected `REASON=ok` for the zero-output regression.
- **Suggested revision**: Standardize on one success reason (revert to `REASON=ok` if compatibility wins) or document/audit all consumers and update plan references accordingly.


### FINDING_7: Persisted ballot may include the attestation line as visible prose
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If the attestation line is written into the merged `findings.md` without stripping, voting/review surfaces may show `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` to humans as part of the ballot.
- **Suggested revision**: Strip post-validation before atomic replace, or explicitly document and handle it in downstream renderers/consumers.


### FINDING_8: Plan traceability gap for shipped orchestrator prompt updates
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `agents/orchestrator-aggregator.md` changes supporting the new empty-merge attestation protocol were not reflected in the plan’s file touch list, reducing traceability (process/plan fidelity rather than a functional defect by itself).
- **Suggested revision**: Extend the written plan/PR summary to list orchestrator prompt changes as intentional deliverables.


