### FINDING_12: [OUT_OF_SCOPE] Legacy single-pass tally errors keep LOOP_STATUS=complete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Legacy single-pass tally failures keep `LOOP_STATUS=complete` while multi-round failures use `tally-error`, so orchestrator short-circuit logic can diverge between paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] Assessor plan snapshots remain raw markdown fences
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-docs-contracts-output.txt
- **Severity**: latent
- **Concern**: Assessor feature blocks are hardened, but plan snapshot sections are still raw-catted into markdown fences. Malicious plan content can break prompt framing and inject assessor-steering text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-docs-contracts-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Python ship default proceeds despite documented security/parity gaps
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` is default Step 8+ while SECURITY/docs still describe unresolved review/parity gaps, exposing operators to a less-reviewed publication/merge path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] Raw reviewer findings are inlined without escaping
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Aggregator inputs still inline raw reviewer prose without the literal-redacted untrusted block contract, allowing findings prose to inject instructions adjacent to hardened scope-anchor content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] Docs still mention voter --scope-anchor-file argv
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-ship-cutover-output.txt
- **Severity**: nit
- **Concern**: Skill prose still references voter `--scope-anchor-file` argv even though the tally contract uses env/staged-anchor handoff and rejected argv plumbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_25: [OUT_OF_SCOPE] Relay terminal matrix excludes converged/cap-hit from env handoff
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: latent
- **Concern**: `_scope_anchor_handoff_value` excludes `converged` / `cap-hit`, matching current plan semantics, but future consumers may wrongly expect `SCOPE_ANCHOR_FILE` in Step 3 result envs on those terminals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_26: [OUT_OF_SCOPE] Multi-round stdout parsing can keep stale first-wins KVs
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: latent
- **Concern**: Multi-round loop stdout can include intermediate tally KVs before terminal KVs, while orchestrator parsing is first-wins per key. Later rounds may not override stale earlier values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_28: [OUT_OF_SCOPE] Python ship cold resume phase14 remains weaker than bash
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: Cold resume with `RESUME_PHASE=ship-pr-rrr-phase14` still routes to an unsupported continuation when the phase14 flag cannot be created, unlike the bash opt-in path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_32: [OUT_OF_SCOPE] read-tools staged-context carve-out is underdocumented
- **Reviewer(s)**: dyn-docs-contracts-output.txt
- **Severity**: nit
- **Concern**: Launch-subprocess docs describe context bodies as framed/redacted, but the `--read-tools` scout path stages files instead of prompt-inlining them and needs an explicit carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contracts-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_5: [OUT_OF_SCOPE] Scope-reduction dedup logic is embedded and duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: Plan-review dedup now has large inline Python and multiple overlapping implementations of marker/problem-text normalization, making the god-script harder to test and easier to drift from the marker helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_8: [OUT_OF_SCOPE] Branch bundles unrelated scope-anchor and Python ship-default work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch mixes plan-review scope-anchor changes with Python ship-default and other initiatives, making regressions, review traceability, and reverts harder to isolate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_9: [OUT_OF_SCOPE] Scout/read-tools scope context lacks inline literal-redacted hardening
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Scout scope context does not use the same inline literal-redacted block framing as other prompt surfaces, so untrusted issue prose can influence archetype selection with weaker delimiter hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


