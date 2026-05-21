```text
### FINDING_1: Empty-merge attestation contract, coverage gaps, and trust boundary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-attestation-protocol-output.txt, dyn-slot-normalization-symmetry-output.txt, dyn-test-coverage-gaps-output.txt
- **Concern**: Merge output with zero `### FINDING_N:` blocks now requires an explicit final-line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` whenever the input ballot still contains structured findings—stricter than an “unconditional clean pass on empty structured output” plan narrative—so narrative-only empty merges fail closed (`validation-failed`) and leave `findings.md` unchanged unless operators/templates match the new machine contract. There is broad agreement this needs stronger CI pinning (negative stub without the line; optionally assert the line survives into the rewritten ballot on the success path). Separately, accepting the bare public literal is only a weak integrity boundary: a mis-prompted or adversarially shaped merge can still clear structured findings while satisfying the string check, which should be treated as an LLM-trust/policy issue (monitor `REASON=ok-zero-findings`, document expectations, tighten only if policy demands provable binding).
- **Suggested revision**: Treat attestation as the explicit runtime contract: reconcile written plan/issue text with shipped behavior (or revert behavior to match plan), document across aggregator entrypoints/custom templates, add the missing negative regression(s), and tighten success assertions if the contract is “line must appear in persisted output,” plus document the trust model for the magic line.

### FINDING_2: Misleading `input_blocks` emptiness check after non-empty `input_slot_set`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-slot-normalization-symmetry-output.txt
- **Concern**: Multiple reviewers read `if not input_blocks(intext): return 0` (early in the zero-output validation path) as unreachable/misleading once `input_slot_set` is guaranteed non-empty from the same parsing pipeline, which harms maintainability and risks future refactors reintroducing subtle holes.
- **Suggested revision**: Remove the dead branch, replace with an explicit invariant/assertion + comment, or restructure checks so the intended fast-path vs fail-closed contract is obvious.

### FINDING_3: Python helper definition order hurts readability
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In the embedded Python, `oos_attributed_slots` is declared before `normalize_slot` in source order, which is harder to read even if name resolution is safe at runtime.
- **Suggested revision**: Reorder definitions (`normalize_slot` first) for top-down readability.

### FINDING_4: Input-side slot normalization vs planned output-only normalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Slots extracted from the input ballot are normalized (not only merge-output slots), diverging from a plan that described output-only normalization; this can change acceptance/dedup behavior versus the written asymmetry and can theoretically collapse distinct raw labels if they differ only by a trailing `(...)`.
- **Suggested revision**: Either narrow code to match the agreed plan scope, or update the plan/issue to explicitly require symmetric normalization and document the invariant that raw slot labels must not differ only by parenthetical suffixes unless that collapse is intended.

### FINDING_5: `normalize_slot` trailing-parenthesis stripping is intentionally limited (and may be overly broad)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-slot-normalization-symmetry-output.txt
- **Concern**: Documentation calls out a single trailing parenthetical peel; a single-pass `(... )` strip cannot cleanly handle nested/chained tails and may mishandle rare literal slot tokens whose real names legitimately end with a parenthetical segment—risking false acceptance against `input_slot_set` or incorrect merging if such shapes ever occur.
- **Suggested revision**: Document supported suffix shapes and failure modes; if production intent is narrowly “`(via …)`”-style annotations, restrict stripping to known patterns; iterate/stabilize only if chained suffixes matter; add regression tests only for observed real shapes.

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

### FINDING_9: Potential validation bypass from mismatched FINDING heading grammars (bash count vs Python blocks)
- **Reviewer(s)**: dyn-attestation-protocol-output.txt
- **Concern**: If bash-side “input finding count” can be driven by a looser heading regex than Python’s `input_blocks` parser, malformed headings could yield “aggregate anyway” with zero parsed input blocks and zero output blocks while skipping the intended empty-merge attestation gate—undermining the attestation contract and risking silent ballot replacement.
- **Suggested revision**: Align heading grammar end-to-end (grep/count vs Python split), pass the bash-derived input count into validation, and/or fail closed unless attested whenever the bash-derived structured-input count indicates a multi-finding ballot.

### FINDING_10: Orchestrator prompt formatting may cause models to emit non-matching attestation lines
- **Reviewer(s)**: dyn-attestation-protocol-output.txt
- **Concern**: Instructions demand a final line exactly equal to `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, but exemplars shown as Markdown inline code/backticks can cause compliant-intent outputs like backtick-wrapped or bullet-prefixed lines that fail the script’s exact-line predicate.
- **Suggested revision**: Show the required line as plain text (e.g., a `text` fence) and explicitly forbid backticks/bullets/markdown wrappers around the token.

### FINDING_11: [OUT_OF_SCOPE] `review-core.sh` captures aggregate stdout but does not branch on `REASON`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Pre-existing integration shape: aggregate stdout is captured while downstream logic does not key off `REASON` (not attributed to this PR’s functional requirements by the source reviewer).
- **Suggested revision**: N/A for this PR unless separately scoped to improve observability/branching.

### FINDING_12: [OUT_OF_SCOPE] `SECURITY.md` not updated for attestation / `ok-zero-findings`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Operators relying on `SECURITY.md` may not see how empty merges are authorized/signaled.
- **Suggested revision**: Update `SECURITY.md` only if/when security-relevant operator guidance should track this behavior (separate doc integration scope).

### FINDING_13: [OUT_OF_SCOPE] Committed implement run plan snapshots contradict shipped harness behavior
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-attestation-protocol-output.txt, dyn-test-coverage-gaps-output.txt
- **Concern**: Historical `larch-logs/implement/.../plan-goals-test.md` text still describes older expectations (e.g., `REASON=ok` vs `ok-zero-findings`, earlier unconditional empty-output behavior), which is confusing for humans auditing the run log.
- **Suggested revision**: Treat as historical log artifact or refresh in a follow-up log hygiene pass (not runtime behavior).

### FINDING_14: [OUT_OF_SCOPE] Observation: redundant guard around `ok-zero-findings` emission
- **Reviewer(s)**: dyn-attestation-protocol-output.txt
- **Concern**: Extra `INPUT_COUNT -ge 2` guard around `ok-zero-findings` is likely redundant given aggregation only runs for multi-input counts, but is consistent with intent.
- **Suggested revision**: Optional cleanup for clarity; not required for correctness.

### FINDING_15: [OUT_OF_SCOPE] Counterpoint: Python `def` order is not a forward-reference bug
- **Reviewer(s)**: dyn-slot-normalization-symmetry-output.txt
- **Concern**: Despite source order, Python binds names before `main()` runs; `oos_attributed_slots` sees `normalize_slot` defined; input/output sets use the same normalizer so set differences stay internally consistent.
- **Suggested revision**: No functional change required; readability remains an in-scope nit (see FINDING_3).

### FINDING_16: [OUT_OF_SCOPE] Branch hygiene: unrelated implement run artifacts under `larch-logs/implement/...`
- **Reviewer(s)**: dyn-slot-normalization-symmetry-output.txt
- **Concern**: Templated placeholders / run artifacts are orthogonal to aggregator correctness and raise separate repo/release hygiene questions.
- **Suggested revision**: Handle under separate release/log policy review.

### FINDING_17: [OUT_OF_SCOPE] Fixture/stub alignment confirmation (`labelled_slot`)
- **Reviewer(s)**: dyn-test-coverage-gaps-output.txt
- **Concern**: Reported as informational: labelled-slot fixture inputs align with stub output and expected merged count given normalization.
- **Suggested revision**: None unless a reviewer intended an actionable change (source reads as confirmation, not a defect).
```
