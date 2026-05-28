### FINDING_1: Harness Drops Prior Regression Coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The rewritten `scripts/test-revise-plan-with-waterfall.sh` reduces the prior matrix and drops regression coverage for canonical plan path/argv guards, symlink/canonical invariants, heading-loss revert, emit-plan-failed, failed-validation/tier waterfall, codex-absent, and Claude-only paths. One reviewer also notes the new #3146 preamble/corrupt-patch path is not explicitly covered. CI can pass while important revise invariants regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Python Rewrite Deviates From Planned Bash/Awk Surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The implementation replaces the planned awk unified-diff strip and unchanged file-replacement `cp` path with embedded Python for both formats. This adds a `python3` dependency and changes extraction semantics in a Bash-3.2-oriented script without a shared helper, documentation, or parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Unified-Diff Extraction Chooses Corrupt Later Diff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Unified-diff extraction prefers the last diff candidate in a fence or unfenced response. If a model returns a valid `plan.txt` diff followed by an illustrative or corrupt wrong-path diff, the script can reject or mis-apply the later block and delay recovery until tier 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Unfenced Diff Extraction Keeps Trailing Prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Unfenced unified-diff extraction retains non-diff prose after the final hunk. A response with a valid patch followed by summary text can fail `git apply --check`, burning tiers 1-3 before tier-4 fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: `git apply --recount` Can Hide Patch Integrity Problems
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The use of `git apply --recount` may accept patches strict checking would reject by recomputing hunk counts. On long or repetitive plans, a recount-adjusted hunk could apply with wrong boundaries and silently corrupt `plan.txt`, especially when manual gating is disabled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: File-Replacement Extraction Uses First `diff_lines:` Trailer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-extract-patch-python-output.txt
- **Severity**: important
- **Concern**: File-replacement extraction stops at the first `diff_lines:` line in a `## Plan` block. If the plan body contains an illustrative or in-fence `diff_lines:` before the real trailer, the candidate can be truncated yet still pass validation and apply the wrong plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-extract-patch-python-output.txt: Address the concern above.

### FINDING_7: Fenced File-Replacement Fallback Cannot See Post-Fence Trailer
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: latent
- **Concern**: The fenced markdown fallback only sees lines inside the closing fence. If the authoritative `diff_lines:` trailer appears after the fence, the fallback can return only the in-fence slice and miss the valid replacement body/trailer combination.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.

### FINDING_8: Tier-4 Status Merge Keeps Less Severe Failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `merge_tier4_status`/`tier4_rank` can keep a later, less severe tier-4 status over an earlier worse one, such as `emit-plan-failed` over `apply-failed` or `invalid-patch`. The final loop status may remain failed, but `REVISE_TIER_4_STATUS` forensics misrepresent the worst tier-4 outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: Tier-4 Status Implementation Is Hard To Verify Against Spec
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `merge_tier4_status` uses numeric ranks rather than the plan’s explicit case block with `ok` stickiness. The behavior may be equivalent for some cases, but it is harder to audit against the specification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Tier-4 Status Documentation Conflicts With Merge Semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The sibling documentation says tier-4 aggregation keeps the worst recorded status, but the code currently keeps the highest rank/best non-ok failure in some mixed-failure cases. Operators may misread `REVISE_TIER_4_STATUS` during failed waterfall debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Candidate Patch Filename Documentation Is Stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Documentation still refers to `tier-candidate.patch`, while the code writes `codex-output-candidate.patch`/`*-output-candidate.patch`. Operator-facing docs and fixtures can become confusing even if allowlists still match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: `extract_patch` Failure Branch Is Misleading
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The shell checks `if ! extract_patch`, but the embedded Python exits 0 even for empty extraction. Maintainers may incorrectly assume Python extraction failures surface through that branch; they currently surface as empty/no-patch output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Tier-4 Fallback Overwrites Earlier Debug Artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Tier 4 overwrites raw outputs from tiers 1-3 that are useful when debugging corrupt unified diffs. After fallback, published revise artifacts may no longer contain the corrupt patches that caused fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: `revise.env` KV Contract Omits `REVISE_WINNING_TIER`
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: latent
- **Concern**: The documentation’s numbered KV contract lists nine keys and omits `REVISE_WINNING_TIER`, but `finalize()` always writes/emits it. Consumers following the “full revise KV contract” doc may not expect a key that is present in every artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_15: Plan Review Loop Does Not Fall Back To Durable `revise.env`
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: latent
- **Concern**: `_run_revise_with_status_parse()` parses only captured stdout for `REVISE_STATUS` and `REVISE_WINNING_TIER`; it does not read the new durable `round-N/revise/revise.env`. If stdout capture drops `REVISE_WINNING_TIER`, `round-summary.env` can remain empty even when the on-disk artifact is complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_16: Harness Does Not Verify `revise.env` Matches Stdout
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: latent
- **Concern**: The harness asserts stdout KVs, including `REVISE_TIER_4_STATUS`, but does not check that `plan-review/round-1/revise/revise.env` exists or matches the emitted contract. Stdout and durable artifacts could diverge without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Finalize Duplicates KV Emission
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `finalize` duplicates KV emission to `revise.env` and stdout, including `REVISE_TIER` and `REVISE_WINNING_TIER`. The duplication existed before but is amplified by more keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Unrelated Redaction Test Path Move
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `secret_path` was relocated outside the design tmpdir in `scripts/test-design-log-publish.sh`, which appears unrelated to the revise waterfall feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Gate B Docs Omit `ok-fallback`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gate B documentation does not mention `ok-fallback` in passive-summary mode, so operators reading gate prose may not distinguish fallback success from tier-1 unified-diff success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Branch Commit Inventory
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The reviewer listed branch commits versus `main`; this is contextual inventory rather than an in-scope defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Unified-Diff Path Positive Assessment
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The reviewer states the unified-diff fenced path correctly prefers the last diff block and that trailing prose causes `invalid-patch`, not silent wrong apply. This is a positive/diagnostic observation rather than an in-scope fix request.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Empty Extraction Exit 0 Is Intentional
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes `write_lines([])` plus exit 0 intentionally drives `no-patch` handling, with Python failure covered separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Docs Match Current First-Trailer Behavior But Conflict With Desired Trailer Semantics
- **Reviewer(s)**: dyn-extract-patch-python-output.txt
- **Severity**: nit
- **Concern**: The docs describe the current “first `diff_lines:`” behavior, but that conflicts with the desired post-closing-fence trailer behavior when an earlier in-fence `diff_lines:` exists under the same `## Plan`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-extract-patch-python-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Revise Winning Tier Positive Fix
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: nit
- **Concern**: The branch fixes a pre-existing mismatch by emitting both `REVISE_TIER` and `REVISE_WINNING_TIER` with the same value from the revise script itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Artifact Allowlist Coverage Is Correct
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: nit
- **Concern**: The reviewer confirms `revise.env` and `*-output-candidate.patch` artifact allowlist/test coverage are updated correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] No Runtime Reader Of `revise.env`
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: nit
- **Concern**: Aside from publish/snapshot allowlisting, nothing currently sources `revise.env`; integration stubs still write a minimal two-key fixture unrelated to production `finalize()` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Step3 Env Still Omits `REVISE_WINNING_TIER`
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: nit
- **Concern**: `write_step3_result_env` still omits `REVISE_WINNING_TIER`, but that predates this branch and affects Gate B’s step3 handoff rather than the new per-round `revise.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Unrelated Run Log Diff Noise
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: nit
- **Concern**: `larch-logs/implement/...` artifacts appear in the precomputed diff but are not part of the revise-env contract work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.
