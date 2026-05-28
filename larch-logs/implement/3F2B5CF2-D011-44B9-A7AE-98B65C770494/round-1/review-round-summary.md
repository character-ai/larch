# Review Round 1

- Mode: `diff`
- 11 accepted, 1 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: _write_round_summary overwrites ok-fallback with ok
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Success-path `_write_round_summary` calls pass literal `ok`, so tier-4 `ok-fallback` success can be preserved in step3 env but misreported in `round-summary.env` and Gate tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: extract_patch mishandles multiple fenced diffs
- **Reviewer(s)**: dyn-extract-patch-awk-output.txt
- **Severity**: important
- **Concern**: Once extraction has started, later ```diff fences are emitted as patch body and closing fences are dropped, so multi-fence outputs can produce invalid combined patches instead of selecting the intended fenced block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-awk-output.txt: Address the concern above.


### FINDING_11: Tier-4 artifact overwrite loses revise forensics
- **Reviewer(s)**: dyn-artifact-overwrite-observability-output.txt
- **Severity**: important
- **Concern**: Tier-4 reuses `revise/` artifact names and `plan-review-loop.sh` does not persist the full revise KV contract, so committed design logs can lose the failed unified-diff artifacts and per-tier statuses needed to reconstruct fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-overwrite-observability-output.txt: Address the concern above.


### FINDING_12: Tier-4 failed launches can leave stale output artifacts
- **Reviewer(s)**: dyn-artifact-overwrite-observability-output.txt
- **Severity**: important
- **Concern**: Tier-4 attempts reuse `<tool>-output.txt` paths, but a failed `launch_tier` can return `no-patch` without truncating prior tier 1-3 output, leaving inconsistent published artifacts when another tier-4 tool later wins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-overwrite-observability-output.txt: Address the concern above.


### FINDING_2: Waterfall harness lacks tier-4 and ok-fallback assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fallback-state-isolation-output.txt, dyn-merge-tier4-coverage-output.txt, dyn-artifact-overwrite-observability-output.txt
- **Severity**: important
- **Concern**: `scripts/test-revise-plan-with-waterfall.sh` does not assert `REVISE_TIER_4_STATUS`, tier-4 file-replacement success, `REVISE_STATUS=ok-fallback`, or related tier-4 attempt outcomes, so the primary fallback behavior and telemetry can regress without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-fallback-state-isolation-output.txt: Address the concern above.
  - From dyn-merge-tier4-coverage-output.txt: Address the concern above.
  - From dyn-artifact-overwrite-observability-output.txt: Address the concern above.


### FINDING_3: plan-review-loop tests do not cover ok-fallback propagation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-artifact-overwrite-observability-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` stubs only ordinary `ok`, so loop handling of `REVISE_STATUS=ok-fallback`, `round-summary.env` retention, and non-`revision-failed` status can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-artifact-overwrite-observability-output.txt: Address the concern above.


### FINDING_4: Tier-4 status merge can downgrade worse failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fallback-state-isolation-output.txt, dyn-merge-tier4-coverage-output.txt
- **Severity**: important
- **Concern**: `merge_tier4_status` uses an incomplete pairwise case matrix that can replace more severe tier-4 statuses such as `invalid-patch` or `apply-failed` with less severe later statuses like `skipped-not-present`, `no-patch`, or `emit-plan-failed`, violating the documented severity ordering and potentially misclassifying final failure state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-fallback-state-isolation-output.txt: Address the concern above.
  - From dyn-merge-tier4-coverage-output.txt: Address the concern above.


### FINDING_5: Tier-4 file-replacement extraction may reject fenced or prefaced full-plan output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier-4 file-replacement extraction does not fully strip fences or preamble before validation, so otherwise usable full-plan LLM output can fail validation and leave the loop revision-failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: relevant-checks misses waterfall-only edits
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Edits to `revise-plan-with-waterfall.sh` do not trigger the revise waterfall harness in `scripts/relevant-checks.sh`, so local pre-commit checks can skip the relevant regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: extract_patch copies trailing prose after a closing fence
- **Reviewer(s)**: dyn-extract-patch-awk-output.txt
- **Severity**: important
- **Concern**: After patch extraction starts, a standalone closing fence is suppressed but subsequent narration is still copied into the candidate patch, making fenced diffs with trailing prose fail `git apply --check`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-awk-output.txt: Address the concern above.


### FINDING_9: extract_patch can start on illustrative markdown headers
- **Reviewer(s)**: dyn-extract-patch-awk-output.txt
- **Severity**: important
- **Concern**: The pre-start detector begins at the first `---`, `+++`, `@@`, or `diff --git` line anywhere in output, so example diff snippets before the real patch can be treated as the candidate patch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-awk-output.txt: Address the concern above.


