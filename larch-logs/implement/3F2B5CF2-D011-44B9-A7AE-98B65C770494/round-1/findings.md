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

### FINDING_6: --recount can apply semantically wrong patches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `git apply --recount` may tolerate corrected hunk counts while still applying unintended line bodies, and there is no regression case documenting or bounding that best-effort behavior.
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

### FINDING_13: [OUT_OF_SCOPE] REVISE_TIER / REVISE_WINNING_TIER mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-artifact-overwrite-observability-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.sh` emits `REVISE_TIER`, while `plan-review-loop.sh` parses `REVISE_WINNING_TIER`, leaving winning-tier telemetry empty on success; reviewers marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-artifact-overwrite-observability-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] plan-review-loop docs omit ok-fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.md` does not list `ok-fallback` in the documented `REVISE_STATUS` vocabulary, so operator docs can drift from emitted round summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Existing LLM revise trust boundary remains prompt-injection prone
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The revise waterfall already lets validated LLM output replace `plan.txt`, and prompt inputs include issue/reviewer content without sanitization; tier 4 increases fallback success likelihood but reviewers marked the trust-boundary issue as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Missing REVISE_STATUS still defaults to ok
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The success path still collapses missing `REVISE_STATUS` to `ok`, which can mislabel forensics; reviewers marked this as pre-existing observability behavior rather than a new security issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Branch includes run-log artifacts
- **Reviewer(s)**: dyn-fallback-state-isolation-output.txt, dyn-merge-tier4-coverage-output.txt
- **Severity**: nit
- **Concern**: The branch includes `larch-logs/implement/...` run artifacts unrelated to revise logic, which may be accidental PR noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fallback-state-isolation-output.txt: Address the concern above.
  - From dyn-merge-tier4-coverage-output.txt: Address the concern above.
