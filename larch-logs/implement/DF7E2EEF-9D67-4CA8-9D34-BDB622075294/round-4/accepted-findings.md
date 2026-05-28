### FINDING_11: missing revise-script rc failure test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness covers `failed-no-patch` but not the independent `rc!=0` failed-apply branch, so `LOOP_STATUS=revision-failed` mapping can regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: missing blank-severity default regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI does not assert that missing TSV severity defaults to nit and keeps `IMPORTANT_ACCEPTED_COUNT=0`, so convergence gating could silently inflate important counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: missing per-round dedup failure reset test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: A round-one dedup failure could leak degraded state into later rounds or block streak recovery without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: integration harness does not cover full plan acceptance matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-multi-round-integration.sh` only covers cap-hit parity and misses converge, SKILL/Gate-B, revision-failed, and cross-entry routing scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: missing explicit OOS duplicate-dedup regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Repeated OOS descriptions across rounds could duplicate cumulative OOS blocks without a harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: terminal result env schema is only partially asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `.step3-plan-review-result.env` tests do not assert the full terminal key set, so partial or corrupt env files could break SKILL rehydration unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: legacy single-pass golden layout test is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Legacy no-`--round-cap` artifact layout can drift because there is no golden file-list fixture comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Gate B passive-summary instructs unsafe env sourcing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` tells the orchestrator to source `.step3-plan-review-result.env`, allowing same-UID file tampering to execute shell code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_20: snapshot failure after successful revise leaves mutated plan and deletes forensics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_snapshot_round_dir` failure after revise/post-apply success exits as panel-failed while leaving `plan.txt` modified and deleting `round-N/revise` evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_21: snapshot failure clobbers intended terminal statuses
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Snapshot failures can overwrite statuses such as degraded-empty-collector, converged, emit-plan-failed, plan-validator-defects, or plan-size-trigger with panel-failed, causing downstream Step 3/3b routing and rollback behavior to diverge from the real terminal condition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: manual Gate B request can silently fall back to auto-apply
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `manual_gate_b` is read only through `jq` with a silent false default, so missing `jq` or malformed JSON can force auto-apply despite manual intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: design-log-publish intro describes stale publish scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.md` still introduces publish as `findings-classification.tsv`-only while the body documents the broader allowlist, which can mislead operators debugging publish failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: important finding count misses earlier blocks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_count_important_findings` only counts the final finding block because it resets on each new header without counting the previous block, allowing convergence despite earlier important accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


